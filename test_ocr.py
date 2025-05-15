import sys
import requests
from io import BytesIO
from PIL import Image
import base64
import json

def test_upload(image_path):
    """Testa o OCR através do endpoint de upload"""
    print(f"Testando OCR com arquivo: {image_path}")
    url = "http://localhost:5000/ocr/upload"
    
    files = {'file': open(image_path, 'rb')}
    response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        print("\nRESULTADO OCR (UPLOAD):")
        print(f"Status: {result['status']}")
        print(f"Tempo de processamento: {result.get('processing_time_ms', 'N/A')} ms")
        print("\nTexto extraído:")
        for line in result['text']:
            print(f"  {line}")
    else:
        print(f"Erro: {response.status_code} - {response.text}")

def test_camera(image_path):
    """Testa o OCR através do endpoint de câmera"""
    print(f"Testando OCR com câmera: {image_path}")
    url = "http://localhost:5000/ocr/camera"
    
    # Ler imagem e codificar em base64
    with open(image_path, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Preparar dados para a requisição
    data = {
        "image_data": f"data:image/jpeg;base64,{encoded_string}"
    }
    
    # Enviar requisição
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(data)
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\nRESULTADO OCR (CÂMERA):")
        print(f"Status: {result['status']}")
        print(f"Tempo de processamento: {result.get('processing_time_ms', 'N/A')} ms")
        print("\nTexto extraído:")
        for line in result['text']:
            print(f"  {line}")
    else:
        print(f"Erro: {response.status_code} - {response.text}")

def main():
    if len(sys.argv) < 2:
        print("Uso: python test_ocr.py <caminho_da_imagem>")
        return
    
    image_path = sys.argv[1]
    
    print("=== TESTE DE OCR ===")
    test_upload(image_path)
    print("\n" + "="*30 + "\n")
    test_camera(image_path)

if __name__ == "__main__":
    main()