import os
import logging
import base64
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from io import BytesIO

from models_fastapi import OCRResponse, ErrorResponse, CameraRequest
from ocr_service import process_image_ocr
from camera_service import process_camera_image

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OCR Document API",
    description="API for extracting text from documents with OCR",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Home route - serve the web interface
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the web interface for the OCR service"""
    return templates.TemplateResponse("index.html", {"request": request})

# OCR image upload endpoint
@app.post("/ocr/upload", response_model=OCRResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def ocr_upload(file: UploadFile = File(...)):
    """
    Process OCR on an uploaded document image
    
    Args:
        file: Uploaded image file
    
    Returns:
        OCRResponse: Extracted text and status
    """
    logger.info(f"Received file upload: {file.filename}")
    
    try:
        # Read the file content
        file_bytes = await file.read()
        
        # Convert to Image using PIL
        image_pil = Image.open(BytesIO(file_bytes))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
            
        # Process the image with OCR
        extracted_text = process_image_ocr(image_pil)
        
        return OCRResponse(
            text=extracted_text,
            status="success"
        )
    
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")

# OCR camera image endpoint
@app.post("/ocr/camera", response_model=OCRResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def ocr_camera(request: CameraRequest):
    """
    Process OCR on an image captured from camera
    
    Args:
        request: Camera capture request containing base64 image data
    
    Returns:
        OCRResponse: Extracted text and status
    """
    logger.info("Received camera capture request")
    
    try:
        # Process the camera image
        image = process_camera_image(request.image_data)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid camera image")
        
        # Process the image with OCR
        extracted_text = process_image_ocr(image)
        
        return OCRResponse(
            text=extracted_text,
            status="success"
        )
    
    except Exception as e:
        logger.error(f"Error processing camera image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )