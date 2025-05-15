import os
import logging
import base64
from typing import List
from io import BytesIO
from PIL import Image

from flask import Flask, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename

from models import OCRResponse, CameraRequest
from ocr_service import process_image_ocr
from camera_service import process_camera_image

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
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

if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)