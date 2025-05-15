import os
import re
import time
import logging
import hashlib
import mimetypes
from io import BytesIO
from PIL import Image
from functools import wraps
from flask import request, jsonify
from werkzeug.utils import secure_filename

# Configuração de logging
logger = logging.getLogger(__name__)

# Configurações de segurança
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

def is_allowed_file(filename):
    """
    Verifica se o arquivo tem uma extensão permitida
    
    Args:
        filename: Nome do arquivo
    
    Returns:
        bool: True se a extensão for permitida, False caso contrário
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_image(file_storage):
    """
    Verifica se o arquivo é uma imagem válida tentando abri-la com PIL
    
    Args:
        file_storage: Objeto FileStorage do Flask
    
    Returns:
        bool: True se o arquivo for uma imagem válida, False caso contrário
    """
    try:
        file_storage.seek(0)
        img = Image.open(file_storage)
        img.verify()  # Verifica se a imagem é válida
        return True
    except Exception as e:
        logger.warning(f"Arquivo inválido: {str(e)}")
        return False
    finally:
        file_storage.seek(0)  # Reinicia o ponteiro do arquivo para uso posterior

def check_file_content(file_storage):
    """
    Verifica o conteúdo do arquivo e calcula seu hash
    
    Args:
        file_storage: Objeto FileStorage do Flask
    
    Returns:
        dict: Informações sobre o arquivo
    """
    try:
        file_storage.seek(0)
        content = file_storage.read()
        
        # Calcula o hash SHA-256 do conteúdo
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Tenta determinar o tipo MIME
        mime_type, _ = mimetypes.guess_type(file_storage.filename)
        
        # Verifica o tamanho
        file_size = len(content)
        
        # Se for um arquivo de imagem, tenta obter suas dimensões
        dimensions = None
        try:
            image = Image.open(BytesIO(content))
            dimensions = image.size
        except:
            pass
        
        return {
            "filename": secure_filename(file_storage.filename),
            "size_bytes": file_size,
            "hash": file_hash,
            "mime_type": mime_type,
            "dimensions": dimensions
        }
    except Exception as e:
        logger.error(f"Erro ao verificar conteúdo do arquivo: {str(e)}")
        return None
    finally:
        file_storage.seek(0)  # Reinicia o ponteiro do arquivo para uso posterior

def validate_file_upload(f):
    """
    Decorator para validar uploads de arquivos
    
    Verifica:
    - Se o arquivo existe
    - Se o tamanho está dentro do limite
    - Se a extensão é permitida
    - Se o conteúdo é válido (para imagens)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se o arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "Nenhum arquivo enviado",
                "error_code": 400
            }), 400
        
        file = request.files['file']
        
        # Verificar se um arquivo foi selecionado
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "Nenhum arquivo selecionado",
                "error_code": 400
            }), 400
        
        # Verificar extensão do arquivo
        if not is_allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": f"Extensão de arquivo não permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}",
                "error_code": 400
            }), 400
        
        # Verificar tamanho do arquivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_CONTENT_LENGTH:
            return jsonify({
                "status": "error",
                "message": f"Tamanho máximo de arquivo excedido. Limite: {MAX_CONTENT_LENGTH/(1024*1024)}MB",
                "error_code": 413
            }), 413
        
        # Para imagens, verificar validade
        if file.filename and any(file.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            if not is_valid_image(file):
                return jsonify({
                    "status": "error",
                    "message": "Arquivo enviado não é uma imagem válida",
                    "error_code": 400
                }), 400
        
        # Adicionar informações do arquivo ao request para uso no endpoint
        file_info = check_file_content(file)
        if file_info:
            # Armazenar em g ao invés de diretamente no request
            from flask import g
            g.file_info = file_info
            
        return f(*args, **kwargs)
    
    return decorated_function

def add_security_headers(response):
    """
    Adiciona cabeçalhos de segurança à resposta HTTP
    
    Args:
        response: Objeto de resposta Flask
    
    Returns:
        response: Objeto de resposta com cabeçalhos adicionados
    """
    # Previne MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Controla como o navegador pode incorporar a página em frames
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Habilita proteção XSS em navegadores antigos
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy básica
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    
    # Strict Transport Security - força HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Configurar CORS para permitir apenas origem especificada
    response.headers['Access-Control-Allow-Origin'] = '*'  # Em produção, substituir por domínio específico
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
    
    return response

def compress_image(image, max_size=1800, quality=85):
    """
    Comprime uma imagem para reduzir seu tamanho
    
    Args:
        image: Objeto PIL.Image
        max_size: Dimensão máxima (largura ou altura)
        quality: Qualidade da compressão JPEG (1-100)
    
    Returns:
        PIL.Image: Imagem comprimida
    """
    if not isinstance(image, Image.Image):
        return image
    
    # Obter dimensões originais
    width, height = image.size
    
    # Redimensionar se alguma dimensão for maior que max_size
    if width > max_size or height > max_size:
        # Preservar proporção
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        # Redimensionar
        image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Converter para RGB se for RGBA (para JPG)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    # Criar buffer para salvar a imagem comprimida
    output = BytesIO()
    
    # Salvar com compressão
    image.save(output, format='JPEG', quality=quality, optimize=True)
    
    # Reiniciar o buffer e retornar a imagem
    output.seek(0)
    return Image.open(output)

def log_request_info():
    """
    Registra informações sobre a requisição atual
    """
    endpoint = request.endpoint
    method = request.method
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    api_key = request.headers.get('X-API-Key', 'None')
    
    logger.info(f"Request: {method} {endpoint} - IP: {ip} - API Key: {api_key}")
    
    # Registrar informações sobre arquivos enviados
    if request.files:
        for key, file in request.files.items():
            logger.info(f"File upload: {file.filename} - Size: {file.content_length or 'Unknown'}")
    
    return