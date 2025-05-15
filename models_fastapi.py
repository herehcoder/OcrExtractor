from typing import List, Optional
from pydantic import BaseModel

class OCRResponse(BaseModel):
    """
    Response model for OCR results
    
    Attributes:
        text: List of text strings extracted from the document
        status: Processing status (success or error)
    """
    text: List[str] = []
    status: str = ""

class ErrorResponse(BaseModel):
    """
    Response model for error messages
    
    Attributes:
        status: Error status
        message: Error message details
    """
    status: str = "error"
    message: str

class CameraRequest(BaseModel):
    """
    Request model for camera capture
    
    Attributes:
        image_data: Base64 encoded image data from camera
    """
    image_data: str