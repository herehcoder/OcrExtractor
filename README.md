# OCR Document Extraction API

Sistema avançado de extração de documentos OCR especializado em processar documentos de identidade brasileiros usando Tesseract e análise de dados personalizada.

## Visão Geral

Este projeto oferece uma API para extração de texto de documentos usando OCR (Reconhecimento Óptico de Caracteres) com foco especial em documentos de identidade brasileiros (RG, CPF).

## Tecnologias

O projeto está implementado em duas versões:

### 1. API Flask (Padrão)
- Implementação atual em produção
- Endpoints RESTful
- Interface web para upload de arquivos e captura de câmera

### 2. API FastAPI (Nova Implementação)
- Implementação moderna usando FastAPI
- Documentação automática da API (Swagger/OpenAPI)
- Verificação de tipo com Pydantic
- Suporte assíncrono

## Recursos

- Extração de texto de documentos usando OCR
- Processamento de imagens via upload de arquivo
- Processamento de imagens via captura de câmera
- Interface web amigável
- Pré-processamento de imagem para melhorar a precisão do OCR
- Estratégias múltiplas de OCR para otimizar a extração de dados
- Processamento específico para documentos de identidade brasileiros

## Endpoints da API

### Endpoint Raiz
- URL: `/`
- Método: `GET`
- Descrição: Interface web para o serviço OCR

### Processamento OCR de Upload de Arquivo
- URL: `/ocr/upload`
- Método: `POST`
- Parâmetros: Arquivo de imagem via formulário multipart
- Retorno: Texto extraído e status

### Processamento OCR de Imagem de Câmera
- URL: `/ocr/camera`
- Método: `POST`
- Corpo: JSON com dados de imagem em base64
- Retorno: Texto extraído e status

## Como Usar

### Usando a API Flask (Padrão)
```
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Usando a API FastAPI (Nova)
```
uvicorn run_fastapi:app --host 0.0.0.0 --port 8000 --reload
```

### Interface Web
Acesse a interface web na URL raiz para:
- Fazer upload de arquivo de imagem para OCR
- Capturar imagem com a câmera para OCR

### Documentação da API FastAPI
Quando usando FastAPI, acesse a documentação automática da API em:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Estrutura do Projeto

- `main.py`: Aplicação Flask (em produção)
- `fastapi_app.py`: Aplicação FastAPI
- `models.py`: Modelos Flask
- `models_fastapi.py`: Modelos Pydantic para FastAPI
- `ocr_service.py`: Serviço de OCR e processamento de texto
- `camera_service.py`: Processamento de imagens de câmera