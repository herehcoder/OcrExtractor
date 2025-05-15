import requests
import json
import base64
from pathlib import Path
import sys

# Exemplo de utilização da API FastAPI

def upload_file_ocr(url, image_path, language="por", doc_type="generic", enhanced=True):
    """
    Envia um arquivo para processamento OCR usando a API FastAPI
    
    Args:
        url: URL base da API
        image_path: Caminho para a imagem a ser processada
        language: Idioma para OCR (por, eng, spa, auto)
        doc_type: Tipo de documento (rg, cpf, cnh, generic)
        enhanced: Usar processamento avançado
    
    Returns:
        dict: Resposta da API
    """
    # Configurar URL com parâmetros
    api_url = f"{url}/ocr/upload?language={language}&document_type={doc_type}&enhanced_processing={enhanced}"
    
    # Preparar arquivo
    files = {'file': (Path(image_path).name, open(image_path, 'rb'), 'image/jpeg')}
    
    # Enviar requisição
    response = requests.post(api_url, files=files)
    
    # Processar resposta
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro: {response.status_code} - {response.text}")
        return None

def process_camera_image(url, image_path, language="por", doc_type="generic", enhanced=True):
    """
    Envia uma imagem de câmera para processamento OCR usando a API FastAPI
    
    Args:
        url: URL base da API
        image_path: Caminho para a imagem a ser processada como se fosse da câmera
        language: Idioma para OCR (por, eng, spa, auto)
        doc_type: Tipo de documento (rg, cpf, cnh, generic)
        enhanced: Usar processamento avançado
    
    Returns:
        dict: Resposta da API
    """
    # Ler imagem e converter para base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
    
    # Preparar dados da requisição
    request_data = {
        "image_data": f"data:image/jpeg;base64,{encoded_image}",
        "language": language,
        "document_type": doc_type,
        "enhanced_processing": enhanced
    }
    
    # Enviar requisição
    response = requests.post(
        f"{url}/ocr/camera",
        headers={"Content-Type": "application/json"},
        data=json.dumps(request_data)
    )
    
    # Processar resposta
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro: {response.status_code} - {response.text}")
        return None

def get_api_stats(url):
    """
    Obter estatísticas da API
    
    Args:
        url: URL base da API
    
    Returns:
        dict: Estatísticas da API
    """
    response = requests.get(f"{url}/api/stats")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro: {response.status_code} - {response.text}")
        return None

def get_api_health(url):
    """
    Verificar a saúde da API
    
    Args:
        url: URL base da API
    
    Returns:
        dict: Status da API
    """
    response = requests.get(f"{url}/api/health")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro: {response.status_code} - {response.text}")
        return None

def main():
    # Configuração
    base_url = "http://localhost:8000"  # URL da API FastAPI
    
    # Verificar se uma imagem foi fornecida como argumento da linha de comando
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("Uso: python fastapi_client.py <caminho_da_imagem>")
        return
    
    print(f"=== Cliente FastAPI OCR ===")
    print(f"API URL: {base_url}")
    print(f"Imagem: {image_path}")
    
    # Verificar saúde da API
    print("\n1. Verificando saúde da API...")
    health = get_api_health(base_url)
    if health:
        print(f"  Status: {health['status']}")
        print(f"  Versão: {health['version']}")
        print(f"  Tipo: {health['api_type']}")
    
    # Testar endpoint de upload
    print("\n2. Testando endpoint de upload...")
    result = upload_file_ocr(base_url, image_path, language="por", doc_type="rg", enhanced=True)
    if result:
        print(f"  Status: {result['status']}")
        print(f"  Tempo de processamento: {result['processing_time_ms']:.2f} ms")
        print(f"  Idioma detectado: {result['language_detected']}")
        print(f"  Tipo de documento: {result['document_type']}")
        print(f"  Linhas de texto extraídas: {len(result['text'])}")
        for i, line in enumerate(result['text']):
            print(f"    {i+1}. {line}")
    
    # Testar endpoint de câmera
    print("\n3. Testando endpoint de câmera...")
    result = process_camera_image(base_url, image_path, language="por", doc_type="rg", enhanced=True)
    if result:
        print(f"  Status: {result['status']}")
        print(f"  Tempo de processamento: {result['processing_time_ms']:.2f} ms")
        print(f"  Idioma detectado: {result['language_detected']}")
        print(f"  Tipo de documento: {result['document_type']}")
        print(f"  Linhas de texto extraídas: {len(result['text'])}")
        for i, line in enumerate(result['text']):
            print(f"    {i+1}. {line}")
    
    # Obter estatísticas
    print("\n4. Obtendo estatísticas da API...")
    stats = get_api_stats(base_url)
    if stats:
        print(f"  Total de requisições: {stats['total_requests']}")
        print(f"  Requisições bem-sucedidas: {stats['successful_requests']}")
        print(f"  Requisições com falha: {stats['failed_requests']}")
        print(f"  Tempo médio de processamento: {stats['average_processing_time_ms']:.2f} ms")

if __name__ == "__main__":
    main()