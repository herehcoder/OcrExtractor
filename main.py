import os
import logging
import base64
from typing import List
from io import BytesIO
from PIL import Image

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Importar modelos e serviços
from models import OCRResponse, CameraRequest
from ocr_service import process_image_ocr
from camera_service import process_camera_image

##########################
# IMPLEMENTAÇÃO FLASK
##########################
from flask import Flask, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename

# Inicializar Flask app
app = Flask(__name__,
    static_folder='static',
    template_folder='templates'
)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

@app.route('/')
def read_root():
    """Serve the web interface for the OCR service"""
    return render_template("index.html")

@app.route('/ocr/upload', methods=['POST'])
def ocr_upload():
    """
    Process OCR on an uploaded document image
    
    Returns:
        JSON: Extracted text and status
    """
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    logger.info(f"Received file upload: {file.filename}")
    
    try:
        # Read the file content
        file_bytes = file.read()
        
        # Convert to Image using PIL
        image_pil = Image.open(BytesIO(file_bytes))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
            
        # Use the image directly
        image = image_pil
        
        if image is None:
            return jsonify({"status": "error", "message": "Invalid image file"}), 400
        
        # Process the image with OCR
        extracted_text = process_image_ocr(image)
        
        return jsonify({
            "text": extracted_text,
            "status": "success"
        })
    
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({"status": "error", "message": f"OCR processing error: {str(e)}"}), 500

@app.route('/ocr/camera', methods=['POST'])
def ocr_camera():
    """
    Process OCR on an image captured from camera
    
    Returns:
        JSON: Extracted text and status
    """
    logger.info("Received camera capture request")
    
    try:
        # Get JSON data from request
        data = request.json
        if not data or 'image_data' not in data:
            return jsonify({"status": "error", "message": "Missing image data"}), 400
        
        # Process the camera image
        image = process_camera_image(data['image_data'])
        
        if image is None:
            return jsonify({"status": "error", "message": "Invalid camera image"}), 400
        
        # Process the image with OCR
        extracted_text = process_image_ocr(image)
        
        return jsonify({
            "text": extracted_text,
            "status": "success"
        })
    
    except Exception as e:
        logger.error(f"Error processing camera image: {str(e)}")
        return jsonify({"status": "error", "message": f"OCR processing error: {str(e)}"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    return jsonify({
        "status": "error",
        "message": str(e)
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