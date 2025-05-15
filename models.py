from typing import List, Optional, Dict

class OCRResponse:
    """
    Response model for OCR results
    
    Attributes:
        text: List of text strings extracted from the document
        status: Processing status (success or error)
    """
    def __init__(self, text: List[str] = [], status: str = ""):
        self.text = text
        self.status = status
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "status": self.status
        }

class CameraRequest:
    """
    Request model for camera capture
    
    Attributes:
        image_data: Base64 encoded image data from camera
    """
    def __init__(self, image_data: str = ""):
        self.image_data = image_data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CameraRequest':
        return cls(image_data=data.get("image_data", ""))
