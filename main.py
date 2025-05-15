import os
import time
import logging
import base64
from typing import List
from io import BytesIO
from PIL import Image
from functools import wraps

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Importar modelos e serviços
from models import OCRResponse, CameraRequest
from ocr_service import process_image_ocr
from camera_service import process_camera_image

# Importar módulos de segurança e monitoramento
from auth import require_api_key, verify_api_key, create_api_key
from security import validate_file_upload, add_security_headers, compress_image, log_request_info
from monitoring import api_monitor

##########################
# IMPLEMENTAÇÃO FLASK
##########################
from flask import Flask, request, jsonify, render_template, url_for, redirect, g
from werkzeug.utils import secure_filename

# Inicializar Flask app
app = Flask(__name__,
    static_folder='static',
    template_folder='templates'
)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload size
app.config['API_KEY_REQUIRED'] = False  # Definir como True em produção

# Middleware para adicionar cabeçalhos de segurança
@app.after_request
def after_request(response):
    return add_security_headers(response)

# Middleware para logging de requisições
@app.before_request
def before_request():
    log_request_info()
    g.start_time = time.time()

# Middleware para monitoramento
@app.after_request
def after_request_monitoring(response):
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        endpoint = request.endpoint or 'unknown'
        status_code = response.status_code
        ip = request.remote_addr
        api_monitor.record_request(endpoint, status_code, duration_ms, ip)
    return response

# Decorador para API key opcional
def optional_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config['API_KEY_REQUIRED']:
            return require_api_key(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function

# Adicionar endpoint para redirecionar para a documentação da API
@app.route('/api-docs')
def api_docs():
    """Redirecionamento para documentação da API"""
    return render_template('api_docs.html')

@app.route('/')
def read_root():
    """Serve the web interface for the OCR service"""
    return render_template("index.html")

@app.route('/ocr/upload', methods=['POST'])
@optional_api_key
@validate_file_upload
def ocr_upload():
    """
    Process OCR on an uploaded document image
    
    Returns:
        JSON: Extracted text and status
    """
    start_time = time.time()
    
    # A validação do arquivo já foi feita pelo decorator validate_file_upload
    file = request.files['file']
    
    # Obter parâmetros opcionais da consulta
    language = request.args.get('language', 'por')
    document_type = request.args.get('document_type', 'generic')
    enhanced_processing = request.args.get('enhanced_processing', 'true').lower() == 'true'
    
    logger.info(f"Received file upload: {file.filename}")
    logger.info(f"Parameters: language={language}, document_type={document_type}, enhanced={enhanced_processing}")
    
    try:
        # Read the file content
        file_bytes = file.read()
        file_size = len(file_bytes)
        
        # Convert to Image using PIL
        image_pil = Image.open(BytesIO(file_bytes))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
            
        # Comprimir imagem se for grande
        if file_size > 1024 * 1024:  # Se maior que 1MB
            image_pil = compress_image(image_pil, max_size=1800, quality=85)
        
        # Process the image with OCR
        extracted_text = process_image_ocr(image_pil)
        
        # Calcular tempo de processamento
        processing_time = (time.time() - start_time) * 1000  # em milissegundos
        
        # Registrar métricas
        api_monitor.record_ocr_processing(
            duration_ms=processing_time,
            success=True,
            language=language,
            document_type=document_type,
            file_size=file_size
        )
        
        return jsonify({
            "text": extracted_text,
            "status": "success",
            "processing_time_ms": processing_time,
            "language_detected": language,
            "document_type": document_type
        })
    
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        
        # Registrar falha
        api_monitor.record_ocr_processing(
            duration_ms=0,
            success=False,
            language=language,
            document_type=document_type
        )
        
        return jsonify({
            "status": "error", 
            "message": f"OCR processing error: {str(e)}",
            "error_code": 500
        }), 500

@app.route('/ocr/camera', methods=['POST'])
@optional_api_key
def ocr_camera():
    """
    Process OCR on an image captured from camera
    
    Returns:
        JSON: Extracted text and status
    """
    start_time = time.time()
    
    logger.info("Received camera capture request")
    
    try:
        # Get JSON data from request
        data = request.json
        if not data or 'image_data' not in data:
            return jsonify({
                "status": "error", 
                "message": "Missing image data",
                "error_code": 400
            }), 400
        
        # Obter parâmetros opcionais do JSON
        language = data.get('language', 'por')
        document_type = data.get('document_type', 'generic')
        enhanced_processing = data.get('enhanced_processing', True)
        
        logger.info(f"Parameters: language={language}, document_type={document_type}, enhanced={enhanced_processing}")
        
        # Process the camera image
        image = process_camera_image(data['image_data'])
        
        if image is None:
            return jsonify({
                "status": "error", 
                "message": "Invalid camera image",
                "error_code": 400
            }), 400
        
        # Extrair tamanho da imagem base64
        image_data = data['image_data']
        if image_data.startswith('data:image'):
            # Extrair parte base64
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        file_size = len(image_bytes)
        
        # Comprimir imagem se for grande
        if file_size > 1024 * 1024:  # Se maior que 1MB
            image = compress_image(image, max_size=1800, quality=85)
        
        # Process the image with OCR
        extracted_text = process_image_ocr(image)
        
        # Calcular tempo de processamento
        processing_time = (time.time() - start_time) * 1000  # em milissegundos
        
        # Registrar métricas
        api_monitor.record_ocr_processing(
            duration_ms=processing_time,
            success=True,
            language=language,
            document_type=document_type,
            file_size=file_size
        )
        
        return jsonify({
            "text": extracted_text,
            "status": "success",
            "processing_time_ms": processing_time,
            "language_detected": language,
            "document_type": document_type
        })
    
    except Exception as e:
        logger.error(f"Error processing camera image: {str(e)}")
        
        # Registrar falha com valores padrão
        lang = 'por'
        doc_type = 'generic'
        
        # Tentar obter valores do escopo corrente, com segurança
        try:
            if 'data' in locals() and isinstance(data, dict):
                if 'language' in data:
                    lang = data['language']
                if 'document_type' in data:
                    doc_type = data['document_type']
        except Exception:
            # Silenciar qualquer erro ao tentar acessar dados que podem não existir
            pass
            
        api_monitor.record_ocr_processing(
            duration_ms=0,
            success=False,
            language=lang,
            document_type=doc_type
        )
        
        return jsonify({
            "status": "error", 
            "message": f"OCR processing error: {str(e)}",
            "error_code": 500
        }), 500

@app.route('/api/stats', methods=['GET'])
@optional_api_key
def get_api_stats():
    """
    Obter estatísticas de uso da API
    
    Returns:
        JSON: Estatísticas de uso
    """
    try:
        stats = api_monitor.get_stats()
        return jsonify({
            "status": "success",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving stats: {str(e)}",
            "error_code": 500
        }), 500

@app.route('/api/detailed-stats', methods=['GET'])
@optional_api_key
def get_detailed_stats():
    """
    Obter estatísticas detalhadas
    
    Returns:
        JSON: Estatísticas detalhadas
    """
    try:
        # Obter período de dias da query string
        days = request.args.get('days', 7, type=int)
        stats = api_monitor.get_detailed_stats(days=days)
        return jsonify({
            "status": "success",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error retrieving detailed stats: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving detailed stats: {str(e)}",
            "error_code": 500
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """
    Verificar saúde da API
    
    Returns:
        JSON: Status da API
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "uptime": "OK",
        "endpoints": [
            {"path": "/", "methods": ["GET"], "description": "Interface web"},
            {"path": "/ocr/upload", "methods": ["POST"], "description": "OCR por upload de arquivo"},
            {"path": "/ocr/camera", "methods": ["POST"], "description": "OCR por captura de câmera"},
            {"path": "/api/stats", "methods": ["GET"], "description": "Estatísticas da API"},
            {"path": "/api/health", "methods": ["GET"], "description": "Verificação de saúde"},
            {"path": "/api-docs", "methods": ["GET"], "description": "Documentação da API"}
        ]
    })

@app.route('/admin/api-keys', methods=['POST'])
@require_api_key
def admin_create_api_key():
    """
    Criar nova API key (apenas para admins)
    
    Returns:
        JSON: Nova API key
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided",
            "error_code": 400
        }), 400
    
    try:
        user_id = data.get('user_id')
        name = data.get('name')
        rate_limit = data.get('rate_limit', 60)
        expires_days = data.get('expires_days', 30)
        permissions = data.get('permissions', ['read'])
        
        if not user_id or not name:
            return jsonify({
                "status": "error",
                "message": "user_id and name are required",
                "error_code": 400
            }), 400
        
        api_key_data = create_api_key(user_id, name, rate_limit, expires_days, permissions)
        
        return jsonify({
            "status": "success",
            "data": api_key_data
        })
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error creating API key: {str(e)}",
            "error_code": 500
        }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({
        "status": "error",
        "message": f"Server error: {str(e)}",
        "error_code": 500
    }), 500

##########################
# IMPLEMENTAÇÃO FASTAPI
##########################
# Note: Esta implementação FastAPI está disponível mas não está sendo servida pelo Gunicorn
# Para utilizar, use o script workflow_fastapi.sh ou run_fastapi.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional as OptionalType

# Modelos Pydantic para FastAPI
class OCRLanguage(str, Enum):
    PORTUGUESE = "por"
    ENGLISH = "eng"
    SPANISH = "spa"
    AUTO = "auto"

class DocumentType(str, Enum):
    RG = "rg"
    CPF = "cpf"
    CNH = "cnh"
    GENERIC = "generic"

class FastAPIResponse(BaseModel):
    text: List[str] = []
    status: str = ""
    processing_time_ms: OptionalType[float] = None
    language_detected: OptionalType[str] = None
    document_type: OptionalType[str] = None

class FastAPIErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_code: OptionalType[int] = None

class FastAPICameraRequest(BaseModel):
    image_data: str
    language: OptionalType[OCRLanguage] = OCRLanguage.PORTUGUESE
    document_type: OptionalType[DocumentType] = DocumentType.GENERIC
    enhanced_processing: bool = True

class OCRSettings(BaseModel):
    language: OCRLanguage = OCRLanguage.PORTUGUESE
    document_type: DocumentType = DocumentType.GENERIC
    enhanced_processing: bool = True
    confidence_threshold: float = Field(0.0, ge=0.0, le=100.0)

class OCRStatistics(BaseModel):
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_processing_time_ms: float = 0.0

# Armazenar estatísticas em memória
ocr_stats = OCRStatistics()

# Inicializar FastAPI app 
fastapi_app = FastAPI(
    title="OCR Document API",
    description="API para extração de texto de documentos usando OCR",
    version="1.0.0"
)

# Configurar CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar arquivos estáticos
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Função para obter configurações de OCR
def get_ocr_settings(
    language: OCRLanguage = Query(OCRLanguage.PORTUGUESE, description="Idioma para OCR"),
    document_type: DocumentType = Query(DocumentType.GENERIC, description="Tipo de documento"),
    enhanced_processing: bool = Query(True, description="Usar processamento avançado"),
    confidence_threshold: float = Query(0.0, ge=0.0, le=100.0, description="Limite de confiança (0-100)")
) -> OCRSettings:
    return OCRSettings(
        language=language,
        document_type=document_type,
        enhanced_processing=enhanced_processing,
        confidence_threshold=confidence_threshold
    )

# Rota raiz - servir a interface web
@fastapi_app.get("/", response_class=HTMLResponse)
async def fastapi_read_root(request: Request):
    """Serve a interface web para o serviço OCR"""
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint de upload de imagem OCR
@fastapi_app.post("/ocr/upload", response_model=FastAPIResponse, 
                 responses={400: {"model": FastAPIErrorResponse}, 500: {"model": FastAPIErrorResponse}})
async def fastapi_ocr_upload(
    file: UploadFile = File(...),
    settings: OCRSettings = Depends(get_ocr_settings)
):
    """
    Processa OCR em uma imagem de documento enviada
    
    Args:
        file: Arquivo de imagem enviado
        settings: Configurações para o processamento OCR
    
    Returns:
        FastAPIResponse: Texto extraído e status
    """
    import time
    start_time = time.time()
    
    logger.info(f"FastAPI: Recebeu upload de arquivo: {file.filename}")
    logger.info(f"FastAPI: Configurações: idioma={settings.language}, tipo={settings.document_type}, avançado={settings.enhanced_processing}")
    
    try:
        # Ler o conteúdo do arquivo
        file_bytes = await file.read()
        
        # Converter para Image usando PIL
        image_pil = Image.open(BytesIO(file_bytes))
        
        # Converter para RGB se necessário
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
            
        # Processar a imagem com OCR
        extracted_text = process_image_ocr(image_pil)
        
        # Calcular tempo de processamento
        processing_time = (time.time() - start_time) * 1000  # em milissegundos
        
        # Atualizar estatísticas
        ocr_stats.total_requests += 1
        ocr_stats.successful_requests += 1
        ocr_stats.average_processing_time_ms = (
            (ocr_stats.average_processing_time_ms * (ocr_stats.successful_requests - 1) + processing_time) / 
            ocr_stats.successful_requests
        )
        
        return FastAPIResponse(
            text=extracted_text,
            status="success",
            processing_time_ms=processing_time,
            language_detected=str(settings.language),
            document_type=str(settings.document_type)
        )
    
    except Exception as e:
        logger.error(f"FastAPI: Erro ao processar upload: {str(e)}")
        
        # Atualizar estatísticas
        ocr_stats.total_requests += 1
        ocr_stats.failed_requests += 1
        
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")

# Endpoint de imagem de câmera OCR
@fastapi_app.post("/ocr/camera", response_model=FastAPIResponse, 
                 responses={400: {"model": FastAPIErrorResponse}, 500: {"model": FastAPIErrorResponse}})
async def fastapi_ocr_camera(request: FastAPICameraRequest):
    """
    Processa OCR em uma imagem capturada da câmera
    
    Args:
        request: Solicitação de captura de câmera contendo dados de imagem base64
    
    Returns:
        FastAPIResponse: Texto extraído e status
    """
    import time
    start_time = time.time()
    
    logger.info("FastAPI: Recebeu solicitação de captura de câmera")
    logger.info(f"FastAPI: Configurações: idioma={request.language}, tipo={request.document_type}, avançado={request.enhanced_processing}")
    
    try:
        # Processar a imagem da câmera
        image = process_camera_image(request.image_data)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid camera image")
        
        # Processar a imagem com OCR
        extracted_text = process_image_ocr(image)
        
        # Calcular tempo de processamento
        processing_time = (time.time() - start_time) * 1000  # em milissegundos
        
        # Atualizar estatísticas
        ocr_stats.total_requests += 1
        ocr_stats.successful_requests += 1
        ocr_stats.average_processing_time_ms = (
            (ocr_stats.average_processing_time_ms * (ocr_stats.successful_requests - 1) + processing_time) / 
            ocr_stats.successful_requests
        )
        
        return FastAPIResponse(
            text=extracted_text,
            status="success",
            processing_time_ms=processing_time,
            language_detected=str(request.language),
            document_type=str(request.document_type)
        )
    
    except Exception as e:
        logger.error(f"FastAPI: Erro ao processar imagem da câmera: {str(e)}")
        
        # Atualizar estatísticas
        ocr_stats.total_requests += 1
        ocr_stats.failed_requests += 1
        
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")

# Manipulador de exceções
@fastapi_app.exception_handler(Exception)
async def fastapi_global_exception_handler(request: Request, exc: Exception):
    """Manipulador global de exceções"""
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc), "error_code": 500}
    )

# Endpoint para obter estatísticas
@fastapi_app.get("/api/stats", response_model=OCRStatistics)
async def get_stats():
    """
    Retorna estatísticas sobre o uso da API OCR
    
    Returns:
        OCRStatistics: Estatísticas de uso da API
    """
    return ocr_stats

# Endpoint de saúde da API
@fastapi_app.get("/api/health")
async def health_check():
    """
    Endpoint de verificação de saúde da API
    
    Returns:
        dict: Status da API
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "api_type": "FastAPI",
        "endpoints": [
            {"path": "/", "methods": ["GET"], "description": "Interface web"},
            {"path": "/ocr/upload", "methods": ["POST"], "description": "OCR por upload de arquivo"},
            {"path": "/ocr/camera", "methods": ["POST"], "description": "OCR por captura de câmera"},
            {"path": "/api/stats", "methods": ["GET"], "description": "Estatísticas da API"},
            {"path": "/api/health", "methods": ["GET"], "description": "Verificação de saúde"},
            {"path": "/docs", "methods": ["GET"], "description": "Documentação Swagger"},
            {"path": "/redoc", "methods": ["GET"], "description": "Documentação ReDoc"}
        ]
    }

if __name__ == "__main__":
    # Executar o aplicativo Flask
    app.run(host="0.0.0.0", port=5000, debug=True)