import os
import time
import uuid
import hmac
import hashlib
import secrets
import logging
from functools import wraps
from flask import request, jsonify, g
from werkzeug.local import LocalProxy

# Configuração de logging
logger = logging.getLogger(__name__)

# Em ambiente de produção, esses dados estariam em um banco de dados
# Por enquanto, usaremos uma estrutura em memória para simplificar
API_KEYS = {
    "test_key": {
        "user_id": "test_user",
        "name": "Test User",
        "rate_limit": 100,
        "created_at": time.time(),
        "expires_at": time.time() + (30 * 24 * 60 * 60),  # 30 dias
        "permissions": ["read", "write"],
        "active": True
    }
}

# Armazenamento de requisições para rate limiting
REQUEST_COUNTS = {}

def get_current_user():
    """Obtém o usuário atual da requisição"""
    return getattr(g, 'user', None)

current_user = LocalProxy(get_current_user)

def generate_api_key():
    """Gera uma nova API key"""
    return secrets.token_hex(16)

def verify_api_key(api_key):
    """Verifica se a API key é válida"""
    if api_key in API_KEYS:
        key_data = API_KEYS[api_key]
        
        # Verificar se a chave está ativa
        if not key_data.get("active", False):
            return False, "API key inativa"
        
        # Verificar se a chave não expirou
        if key_data.get("expires_at", 0) < time.time():
            return False, "API key expirada"
            
        # Chave válida
        return True, key_data
    
    return False, "API key inválida"

def check_rate_limit(api_key, limit=60, window=60):
    """
    Verifica se o usuário excedeu o limite de requisições
    
    Args:
        api_key: A chave de API do usuário
        limit: Número máximo de requisições permitidas
        window: Janela de tempo em segundos
    
    Returns:
        (bool, int): (limite excedido, requisições restantes)
    """
    current_time = time.time()
    
    # Se a chave não estiver no dicionário, adiciona
    if api_key not in REQUEST_COUNTS:
        REQUEST_COUNTS[api_key] = []
    
    # Remove entradas antigas (fora da janela de tempo)
    REQUEST_COUNTS[api_key] = [t for t in REQUEST_COUNTS[api_key] if t > current_time - window]
    
    # Verifica se excedeu o limite
    if len(REQUEST_COUNTS[api_key]) >= limit:
        # Consegue o número de requisições restantes (sempre 0 neste caso)
        remaining = 0
        return True, remaining
    
    # Adiciona o timestamp atual
    REQUEST_COUNTS[api_key].append(current_time)
    
    # Calcula requisições restantes
    remaining = limit - len(REQUEST_COUNTS[api_key])
    
    return False, remaining

def require_api_key(f):
    """Decorator para rotas que exigem autenticação via API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Obter API key do header ou query parameter
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            api_key = request.args.get('api_key')
            
        # Se não forneceu API key
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "API key não fornecida",
                "error_code": 401
            }), 401
        
        # Verificar API key
        is_valid, result = verify_api_key(api_key)
        if not is_valid:
            logger.warning(f"Tentativa de acesso com API key inválida: {api_key}")
            return jsonify({
                "status": "error",
                "message": result,  # result contém a mensagem de erro
                "error_code": 401
            }), 401
        
        # Neste ponto, result contém os dados da chave (key_data)
        key_data = result
        
        # Verificar rate limit
        user_limit = key_data.get("rate_limit", 60)
        exceeded, remaining = check_rate_limit(api_key, limit=user_limit)
        
        # Adicionar headers de rate limit
        response_headers = {
            "X-RateLimit-Limit": str(user_limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time() + 60))
        }
        
        if exceeded:
            logger.warning(f"Rate limit excedido para API key: {api_key}")
            response = jsonify({
                "status": "error",
                "message": "Limite de requisições excedido. Tente novamente mais tarde.",
                "error_code": 429
            })
            
            # Adicionar headers à resposta
            for key, value in response_headers.items():
                response.headers[key] = value
                
            return response, 429
        
        # Armazenar dados do usuário para uso na view
        user_info = {}
        if isinstance(key_data, dict):
            user_info = {
                "user_id": key_data.get("user_id", "unknown"),
                "name": key_data.get("name", "Unknown User"),
                "permissions": key_data.get("permissions", []),
                "rate_limit": user_limit,
                "rate_limit_remaining": remaining
            }
        
        g.user = user_info
        
        # Chamar a view original
        response = f(*args, **kwargs)
        
        # Se a resposta for uma tupla (resposta, status_code)
        if isinstance(response, tuple):
            response_obj, status_code = response
            
            # Se for um objeto de resposta Flask
            if hasattr(response_obj, "headers"):
                for key, value in response_headers.items():
                    response_obj.headers[key] = value
        
        # Se for apenas um objeto de resposta Flask
        elif hasattr(response, "headers"):
            for key, value in response_headers.items():
                response.headers[key] = value
        
        return response
    
    return decorated_function

def admin_required(f):
    """Decorator para rotas que exigem permissão de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user or "admin" not in current_user.get("permissions", []):
            return jsonify({
                "status": "error",
                "message": "Permissão negada. Acesso somente para administradores.",
                "error_code": 403
            }), 403
        return f(*args, **kwargs)
    
    return decorated_function

# Funções de gerenciamento de API keys (para uso administrativo)

def create_api_key(user_id, name, rate_limit=60, expires_days=30, permissions=None):
    """
    Cria uma nova API key
    
    Args:
        user_id: ID do usuário
        name: Nome do usuário ou aplicação
        rate_limit: Limite de requisições por minuto
        expires_days: Dias até a expiração da chave
        permissions: Lista de permissões
    
    Returns:
        dict: Dados da API key criada
    """
    if permissions is None:
        permissions = ["read"]
    
    api_key = generate_api_key()
    
    API_KEYS[api_key] = {
        "user_id": user_id,
        "name": name,
        "rate_limit": rate_limit,
        "created_at": time.time(),
        "expires_at": time.time() + (expires_days * 24 * 60 * 60),
        "permissions": permissions,
        "active": True
    }
    
    return {
        "api_key": api_key,
        "user_id": user_id,
        "name": name,
        "rate_limit": rate_limit,
        "expires_at": time.time() + (expires_days * 24 * 60 * 60),
        "permissions": permissions
    }

def revoke_api_key(api_key):
    """Revoga uma API key"""
    if api_key in API_KEYS:
        API_KEYS[api_key]["active"] = False
        return True
    return False