import os
import logging
import re
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from typing import List, Optional

# Configure logging
logger = logging.getLogger(__name__)

def preprocess_image(image):
    """
    Preprocess the image to improve OCR accuracy using Pillow
    
    Args:
        image: Input PIL Image
    
    Returns:
        PIL.Image: Preprocessed image
    """
    # Use PIL Image directly
    if not isinstance(image, Image.Image):
        try:
            # If somehow we received something else, try to convert to PIL Image
            image = Image.open(BytesIO(image))
        except Exception as e:
            logger.error(f"Error converting to PIL Image: {str(e)}")
            return image
    
    # Convert to grayscale
    gray = image.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(2.0)
    
    # Apply sharpening
    sharpened = enhanced.filter(ImageFilter.SHARPEN)
    
    # Apply noise reduction
    smoothed = sharpened.filter(ImageFilter.SMOOTH_MORE)
    
    return smoothed

def extract_text_from_image(image):
    """
    Extract text from image using Tesseract OCR
    
    Args:
        image: PIL Image
    
    Returns:
        List[str]: List of extracted text lines
    """
    try:
        # Configure Tesseract for Portuguese language
        custom_config = r'--oem 3 --psm 6 -l por'
        
        # Extract text using pytesseract
        extracted_text = pytesseract.image_to_string(image, config=custom_config)
        
        # Split text into lines and remove empty lines
        text_lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        
        if not text_lines:
            logger.warning("No text detected in the image")
            return ["Nenhum texto detectado na imagem. Tente uma imagem com texto mais claro."]
        
        return text_lines
        
    except Exception as e:
        logger.error(f"Error extracting text with Tesseract: {str(e)}")
        return [f"Erro ao processar a imagem: {str(e)}"]

def process_image_ocr(image) -> List[str]:
    """
    Process an image to extract text
    
    Args:
        image: PIL Image object or numpy array
    
    Returns:
        List[str]: List of extracted text lines
    """
    logger.debug("Processing image with OCR")
    
    try:
        # Preprocess the image
        processed_image = preprocess_image(image)
        
        # Extract text from the processed image
        text_lines = extract_text_from_image(processed_image)
        
        logger.info(f"OCR processing complete, extracted {len(text_lines)} text lines")
        return text_lines
        
    except Exception as e:
        logger.error(f"Error during OCR processing: {str(e)}")
        return [f"Erro ao processar imagem: {str(e)}. Tente novamente com uma imagem mais clara."]
