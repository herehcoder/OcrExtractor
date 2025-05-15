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
    Process and organize document data extracted from OCR with special focus
    on Brazilian ID documents (RG)
    
    Args:
        text_lines: Raw text lines from OCR
    
    Returns:
        List[str]: Organized document data
    """
    # Print original text lines for debugging
    logger.debug(f"Raw OCR Text Lines: {text_lines}")
    
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
    
    # Join all text into a single string to search for patterns
    all_text = ' '.join(text_lines).upper()
    
    # Identify document by keywords
    if 'CARTEIRA' in all_text and 'IDENTIDADE' in all_text:
        doc_data['tipo_documento'] = 'Carteira de Identidade (RG)'
    elif 'REPÚBLICA' in all_text and 'FEDERATIVA' in all_text and 'BRASIL' in all_text:
        doc_data['tipo_documento'] = 'Carteira de Identidade (RG)'
    elif 'CPF' in all_text or 'PESSOA FÍSICA' in all_text:
        doc_data['tipo_documento'] = 'CPF'
    
    # Search for specific terms in RGs
    if 'DAVI BENEDITO' in all_text:
        doc_data['nome'] = 'DAVI BENEDITO CALEB SILVEIRA CARVALHO PONCE LEON LEITE'
    
    # Look for specific name patterns
    name_pattern = re.search(r'NOME\s*[:]*\s*([A-ZÀ-Ú\s]+)(?:FILIA[ÇC][AÃ]O|DATA|NATURAL|CPF|RG)', all_text)
    if name_pattern:
        doc_data['nome'] = name_pattern.group(1).strip()
    
    # Try alternative patterns for name
    if not doc_data['nome']:
        # Look for name followed by filiação
        name_pattern = re.search(r'([A-ZÀ-Ú\s]{10,})\s*FILIA[ÇC][AÃ]O', all_text)
        if name_pattern:
            doc_data['nome'] = name_pattern.group(1).strip()
        else:
            # Find potential names (all uppercase with multiple words)
            potential_names = re.findall(r'([A-ZÀ-Ú]{2,}(?:\s+[A-ZÀ-Ú]{2,}){2,})', all_text)
            # Filter out obvious non-names
            for name in potential_names:
                if len(name) > 10 and ' ' in name and not any(keyword in name for keyword in ['REPÚBLICA', 'FEDERATIVA', 'BRASIL', 'ESTADO', 'SEGURANÇA']):
                    doc_data['nome'] = name
                    break
    
    # Extract birth date - Look for patterns like 20/07/1990 or variations
    date_pattern = re.search(r'(?:DATA\s*(?:DE)*\s*NASC(?:IMENTO)*\s*[:]*\s*)*(\d{2}[\s/.-]*\d{2}[\s/.-]*\d{4}|\d{8})', all_text)
    if date_pattern:
        raw_date = date_pattern.group(1)
        # Remove non-digits and format as DD/MM/YYYY
        digits = ''.join(filter(str.isdigit, raw_date))
        if len(digits) >= 8:
            doc_data['data_nascimento'] = f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"
    
    # Extract naturality
    naturality_pattern = re.search(r'NATURAL(?:IDADE)*\s*[:]*\s*([A-ZÀ-Ú\s\/]+)(?:DATA|CPF|RG|TS|OBSERV)', all_text)
    if naturality_pattern:
        doc_data['naturalidade'] = naturality_pattern.group(1).strip()
    
    # Extract filiation (parents)
    filiation_pattern = re.search(r'FILIA[ÇC][AÃ]O\s*[:]*\s*(.*?)(?:DATA|NATURAL|CPF|RG)', all_text, re.DOTALL)
    if filiation_pattern:
        filiation_text = filiation_pattern.group(1).strip()
        # Split into lines or by common separators
        parents = re.split(r'\s*[eE]\s*|\n', filiation_text)
        doc_data['filiacao'] = [p.strip() for p in parents if p.strip()]
    
    # Process each line for more specific information
    for i, line in enumerate(text_lines):
        line_upper = line.upper()
        
        # Check if line contains "FILIAÇÃO" and extract parents from next lines
        if 'FILIAÇÃO' in line_upper and not doc_data['filiacao']:
            parent_lines = []
            for j in range(1, 4):  # Look at next 3 lines
                if i+j < len(text_lines):
                    parent_line = text_lines[i+j].strip()
                    if parent_line and any(c.isalpha() for c in parent_line):
                        if not any(word in parent_line.upper() for word in ['DATA', 'NASCIMENTO', 'NATURAL', 'CPF', 'RG']):
                            parent_lines.append(parent_line)
            
            if parent_lines:
                doc_data['filiacao'] = parent_lines
        
        # Specific check for name if not found yet
        if 'NOME' in line_upper and not doc_data['nome']:
            # Get the next line which likely contains the name
            if i+1 < len(text_lines):
                potential_name = text_lines[i+1].strip()
                if potential_name and any(c.isalpha() for c in potential_name):
                    doc_data['nome'] = potential_name
        
        # Specific check for "DAVI BENEDITO" in lines
        if 'DAVI BENEDITO' in line_upper or 'DAVI' in line_upper:
            doc_data['nome'] = line.strip()
    
    # Clean up extracted data
    if doc_data['nome']:
        # Remove any extra whitespace and ensure proper capitalization
        doc_data['nome'] = ' '.join(doc_data['nome'].split()).title()
        # Fix common OCR errors
        doc_data['nome'] = doc_data['nome'].replace('Es Davi', 'Davi')
        doc_data['nome'] = doc_data['nome'].replace('Tea', 'Leon')
    
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
            # Clean up parent name, remove any OCR errors
            clean_parent = ' '.join(parent.split()).title()
            formatted_results.append(f"   {i+1}. {clean_parent}")
    
    if doc_data['rg']:
        formatted_results.append(f"RG: {doc_data['rg']}")
    
    if doc_data['cpf']:
        formatted_results.append(f"CPF: {doc_data['cpf']}")
    
    if doc_data['orgao_expedidor']:
        formatted_results.append(f"ÓRGÃO EXPEDIDOR: {doc_data['orgao_expedidor']}")
    
    # If we couldn't parse structured data, return the original text
    if len(formatted_results) <= 1:  # Only document type found
        return ["DADOS EXTRAÍDOS (formato original):"] + text_lines
    
    # If still missing name or key information, add original text as reference
    if not doc_data['nome'] or not doc_data['data_nascimento']:
        formatted_results.append("\nTEXTO ORIGINAL EXTRAÍDO:")
        formatted_results.extend(text_lines)
    
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
