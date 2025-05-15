import requests
import json
import sys
import base64
from pathlib import Path

def test_root_endpoint(base_url):
    """Test the root endpoint that serves the web interface"""
    print(f"Testing root endpoint: {base_url}")
    
    response = requests.get(base_url)
    
    if response.status_code == 200:
        print("✓ Root endpoint is working")
        return True
    else:
        print(f"✗ Root endpoint failed with status code: {response.status_code}")
        return False

def test_upload_endpoint(base_url, image_path):
    """Test the OCR upload endpoint with a sample image"""
    upload_url = f"{base_url}/ocr/upload"
    print(f"Testing upload endpoint: {upload_url}")
    
    # Prepare the file
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (Path(image_path).name, f, 'image/jpeg')}
            
            # Send request
            response = requests.post(upload_url, files=files)
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Upload endpoint is working")
                print(f"  Status: {result.get('status')}")
                print(f"  Extracted text lines: {len(result.get('text', []))}")
                if result.get('text'):
                    print(f"  First text line: {result.get('text', [])[0]}")
                return True
            else:
                print(f"✗ Upload endpoint failed with status code: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Error testing upload endpoint: {str(e)}")
        return False

def test_camera_endpoint(base_url, image_path):
    """Test the OCR camera endpoint with a sample image as base64"""
    camera_url = f"{base_url}/ocr/camera"
    print(f"Testing camera endpoint: {camera_url}")
    
    try:
        # Read image and convert to base64
        with open(image_path, 'rb') as f:
            image_data = f.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request data
            request_data = {
                "image_data": f"data:image/jpeg;base64,{encoded_image}"
            }
            
            # Send request
            response = requests.post(
                camera_url, 
                headers={"Content-Type": "application/json"},
                data=json.dumps(request_data)
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Camera endpoint is working")
                print(f"  Status: {result.get('status')}")
                print(f"  Extracted text lines: {len(result.get('text', []))}")
                if result.get('text'):
                    print(f"  First text line: {result.get('text', [])[0]}")
                return True
            else:
                print(f"✗ Camera endpoint failed with status code: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Error testing camera endpoint: {str(e)}")
        return False

def run_tests():
    """Run all API tests"""
    print("=== FastAPI OCR API Test ===\n")
    
    # Configuration
    base_url = "http://localhost:8000"  # FastAPI port
    
    # Check if an image path was provided as a command-line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Use a default image path
        image_path = "test_image.jpg"
    
    print(f"Using image: {image_path}\n")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_root_endpoint(base_url):
        tests_passed += 1
    
    print()
    
    if test_upload_endpoint(base_url, image_path):
        tests_passed += 1
    
    print()
    
    if test_camera_endpoint(base_url, image_path):
        tests_passed += 1
    
    print(f"\nTests passed: {tests_passed}/{total_tests}")

if __name__ == "__main__":
    run_tests()