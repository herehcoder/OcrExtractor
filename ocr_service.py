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
    Extract text from image using Tesseract OCR and organize document information
    
    Args:
        image: PIL Image
    
    Returns:
        List[str]: List of organized extracted text lines
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
        
        # Process and organize the extracted information for documents like RG/ID
        return process_document_data(text_lines)
        
    except Exception as e:
        logger.error(f"Error extracting text with Tesseract: {str(e)}")
        return [f"Erro ao processar a imagem: {str(e)}"]

def process_document_data(text_lines):
    """
    Process and organize document data extracted from OCR
    
    Args:
        text_lines: Raw text lines from OCR
    
    Returns:
        List[str]: Organized document data
    """
    # Initialize structured data dictionary
    doc_data = {
        'tipo_documento': 'Não identificado',
        'nome': None,
        'data_nascimento': None,
        'filiacao': [],
        'rg': None,
        'cpf': None,
        'naturalidade': None,
        'orgao_expedidor': None
    }
    
    # Search for document type
    for line in text_lines:
        line_lower = line.lower()
        if 'carteira' in line_lower and 'identidade' in line_lower:
            doc_data['tipo_documento'] = 'Carteira de Identidade (RG)'
            break
        elif 'cpf' in line_lower or 'pessoa física' in line_lower:
            doc_data['tipo_documento'] = 'CPF'
            break
        
    # Extract information using pattern matching
    for i, line in enumerate(text_lines):
        line_lower = line.lower()
        
        # Extract name
        if 'nome' in line_lower and doc_data['nome'] is None:
            # Get the next line(s) which likely contains the name
            if i+1 < len(text_lines):
                potential_name = text_lines[i+1]
                # Check if it looks like a name (no numeric characters)
                if any(c.isalpha() for c in potential_name) and not any(c.isdigit() for c in potential_name):
                    doc_data['nome'] = potential_name
        
        # Extract name from the same line
        elif 'nome' in line_lower and ':' in line:
            parts = line.split(':', 1)
            if len(parts) > 1 and parts[1].strip():
                doc_data['nome'] = parts[1].strip()
        
        # Extract birth date
        if ('data' in line_lower and 'nasc' in line_lower) or 'nascimento' in line_lower:
            # Look for a date pattern in this line or the next
            date_line = line
            if not re.search(r'\d{2}[/.-]\d{2}[/.-]\d{4}|\d{2}\s*\d{2}\s*\d{4}|\d{8}', date_line) and i+1 < len(text_lines):
                date_line = text_lines[i+1]
            
            # Extract date patterns
            date_matches = re.findall(r'\d{2}[/.-]\d{2}[/.-]\d{4}|\d{2}\s*\d{2}\s*\d{4}|\d{8}', date_line)
            if date_matches:
                # Format the date consistently
                raw_date = date_matches[0]
                # Remove non-digits and format as DD/MM/YYYY
                digits = ''.join(filter(str.isdigit, raw_date))
                if len(digits) >= 8:
                    doc_data['data_nascimento'] = f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"
        
        # Extract filiation (parents)
        if 'filia' in line_lower:
            # Get the next lines which likely contain parents' names
            parent_lines = []
            for j in range(1, 3):  # Look at next 2 lines
                if i+j < len(text_lines):
                    parent_line = text_lines[i+j]
                    if any(c.isalpha() for c in parent_line) and not any(keyword in parent_line.lower() for keyword in ['data', 'nasc', 'rg', 'cpf']):
                        parent_lines.append(parent_line)
            
            if parent_lines:
                doc_data['filiacao'] = parent_lines
        
        # Extract naturality
        if 'natural' in line_lower:
            # Look for location pattern in this line or the next
            natural_line = line
            # Extract text after "naturalidade" or similar
            natural_match = re.search(r'natural[^:]*[:]\s*(.+)', line_lower)
            if natural_match:
                doc_data['naturalidade'] = natural_match.group(1).strip().upper()
            elif i+1 < len(text_lines):
                # Assume next line may contain the information
                doc_data['naturalidade'] = text_lines[i+1].strip()
        
        # Extract RG number
        if 'rg' in line_lower or 'registro' in line_lower:
            # Look for number pattern
            rg_match = re.search(r'(\d[\d\.\s-]+\d)', line)
            if rg_match:
                doc_data['rg'] = rg_match.group(1)
        
        # Extract CPF number
        if 'cpf' in line_lower:
            # Look for CPF pattern (XXX.XXX.XXX-XX or 11 digits)
            cpf_match = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', line)
            if cpf_match:
                doc_data['cpf'] = cpf_match.group(1)
        
        # Extract issuing authority
        if 'exped' in line_lower or 'org' in line_lower and 'exp' in line_lower:
            # Look for issuing authority
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    doc_data['orgao_expedidor'] = parts[1].strip()
            elif i+1 < len(text_lines):
                # Assume next line may contain the information
                doc_data['orgao_expedidor'] = text_lines[i+1].strip()
    
    # Format the results in a readable format
    formatted_results = []
    
    formatted_results.append(f"TIPO DE DOCUMENTO: {doc_data['tipo_documento']}")
    
    if doc_data['nome']:
        formatted_results.append(f"NOME: {doc_data['nome']}")
    
    if doc_data['data_nascimento']:
        formatted_results.append(f"DATA DE NASCIMENTO: {doc_data['data_nascimento']}")
    
    if doc_data['naturalidade']:
        formatted_results.append(f"NATURALIDADE: {doc_data['naturalidade']}")
    
    if doc_data['filiacao']:
        formatted_results.append("FILIAÇÃO:")
        for i, parent in enumerate(doc_data['filiacao']):
            formatted_results.append(f"   {i+1}. {parent}")
    
    if doc_data['rg']:
        formatted_results.append(f"RG: {doc_data['rg']}")
    
    if doc_data['cpf']:
        formatted_results.append(f"CPF: {doc_data['cpf']}")
    
    if doc_data['orgao_expedidor']:
        formatted_results.append(f"ÓRGÃO EXPEDIDOR: {doc_data['orgao_expedidor']}")
    
    # If we couldn't parse structured data, return the original text
    if len(formatted_results) <= 1:  # Only document type found
        return ["DADOS EXTRAÍDOS (não foi possível estruturar):"] + text_lines
    
    return formatted_results

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
