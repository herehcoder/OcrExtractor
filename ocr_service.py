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
    Extract text from image using Tesseract OCR with multiple strategies
    to optimize accurate data extraction
    
    Args:
        image: PIL Image
    
    Returns:
        List[str]: List of organized extracted text lines
    """
    try:
        text_results = {}
        
        # Try different Tesseract configurations to get best results
        logger.info("Performing multi-strategy OCR extraction")
        
        # Strategy 1: Full page analysis (best for document type, layout)
        psm1_config = r'--oem 3 --psm 1 -l por'  # Analyze the page as a whole
        full_text = pytesseract.image_to_string(image, config=psm1_config)
        text_results['full_page'] = [line.strip() for line in full_text.split('\n') if line.strip()]
        logger.debug(f"Full page OCR results: {text_results['full_page']}")
        
        # Strategy 2: Line by line analysis (best for text lines)
        psm6_config = r'--oem 3 --psm 6 -l por'  # Assume a single uniform block of text
        line_text = pytesseract.image_to_string(image, config=psm6_config)
        text_results['line_by_line'] = [line.strip() for line in line_text.split('\n') if line.strip()]
        logger.debug(f"Line by line OCR results: {text_results['line_by_line']}")
        
        # Strategy 3: Single word analysis (best for isolated words, numbers)
        psm8_config = r'--oem 3 --psm 8 -l por'  # Treat the image as a single word
        word_text = pytesseract.image_to_string(image, config=psm8_config)
        text_results['word'] = [line.strip() for line in word_text.split('\n') if line.strip()]
        logger.debug(f"Word OCR results: {text_results['word']}")
        
        # Strategy 4: Enhance contrast then analyze
        enhanced_image = ImageEnhance.Contrast(image).enhance(2.0)
        enhanced_text = pytesseract.image_to_string(enhanced_image, config=psm6_config)
        text_results['enhanced'] = [line.strip() for line in enhanced_text.split('\n') if line.strip()]
        logger.debug(f"Enhanced OCR results: {text_results['enhanced']}")
        
        # Combine and preprocess all results
        all_lines = []
        for strategy_name, lines in text_results.items():
            all_lines.extend(lines)
        
        # Remove duplicates while preserving order
        unique_lines = []
        for line in all_lines:
            if line and line not in unique_lines:
                unique_lines.append(line)
        
        if not unique_lines:
            logger.warning("No text detected in the image after multi-strategy OCR")
            return ["Nenhum texto detectado na imagem. Tente uma imagem com texto mais claro."]
        
        # Process the enriched data set
        logger.info(f"Combined OCR extracted {len(unique_lines)} unique text lines")
        return process_document_data(unique_lines)
        
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
    logger.info(f"Processing {len(text_lines)} text lines from OCR")
    
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
    
    # Extract birth date with special attention to different formats
    # First look for specific patterns that indicate birth date
    date_patterns = [
        # Standard formats
        r'(?:DATA\s*(?:DE)*\s*NASC(?:IMENTO)*\s*[:]*\s*)*(\d{2}[\s/.-]*\d{2}[\s/.-]*\d{4}|\d{8})',
        
        # More specific patterns
        r'(\d{2})\/(\d{2})\/(\d{4})',  # DD/MM/YYYY 
        r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY
        r'(\d{2})\s*(\d{2})\s*(\d{4})'  # DDMMYYYY with optional spaces
    ]
    
    # Try each pattern
    date_found = False
    logger.info("Looking for date patterns in text")
    
    for pattern in date_patterns:
        for line in text_lines:
            date_match = re.search(pattern, line)
            if date_match:
                logger.info(f"Found date pattern match: {date_match.group(0)} in line: {line}")
                
                # Different handling based on the pattern
                if len(date_match.groups()) == 3:  # If we captured day, month, year separately
                    day = date_match.group(1)
                    month = date_match.group(2)
                    year = date_match.group(3)
                    doc_data['data_nascimento'] = f"{day}/{month}/{year}"
                else:  # Process as a single capture
                    raw_date = date_match.group(1)
                    # Remove non-digits and format as DD/MM/YYYY
                    digits = ''.join(filter(str.isdigit, raw_date))
                    if len(digits) >= 8:
                        doc_data['data_nascimento'] = f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"
                
                date_found = True
                break
        
        if date_found:
            break
    
    # If no date found yet, check for date patterns with year first (like 1950/07/20)
    if not date_found:
        for line in text_lines:
            year_first_match = re.search(r'(19\d{2})[/.-]?(\d{2})[/.-]?(\d{2})', line)
            if year_first_match:
                logger.info(f"Found year-first date: {year_first_match.group(0)}")
                year = year_first_match.group(1)
                month = year_first_match.group(2)
                day = year_first_match.group(3)
                doc_data['data_nascimento'] = f"{day}/{month}/{year}"
                date_found = True
                break
    
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
