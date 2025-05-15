import base64
import logging
from PIL import Image
from io import BytesIO
import numpy as np
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

def process_camera_image(image_data: str) -> Optional[np.ndarray]:
    """
    Process a base64 encoded image from camera
    
    Args:
        image_data: Base64-encoded image string
    
    Returns:
        numpy.ndarray: Image array or None if processing fails
    """
    try:
        # Remove data URL prefix if present
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Use PIL to open the image
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        if image_array is None or image_array.size == 0:
            logger.error("Failed to decode camera image")
            return None
        
        logger.debug(f"Successfully processed camera image with shape {image_array.shape}")
        return image_array
    
    except Exception as e:
        logger.error(f"Error processing camera image: {str(e)}")
        return None
