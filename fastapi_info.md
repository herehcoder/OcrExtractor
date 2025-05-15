# API OCR com FastAPI

## Visão Geral

Implementamos uma API OCR usando FastAPI, que oferece vários recursos avançados em relação à versão Flask:

1. **Documentação automática OpenAPI**: Acesse `/docs` ou `/redoc` para ver a documentação interativa da API
2. **Validação de tipos com Pydantic**: Garantia de tipos corretos para entradas e saídas
3. **Operações assíncronas**: Melhor performance em operações de I/O
4. **Endpoints adicionais**: Estatísticas, monitoramento de saúde, etc.

## Endpoints da API

### Interface web
- **URL**: `/`
- **Método**: `GET`
- **Descrição**: Interface web para o serviço OCR

### Upload de imagem para OCR
- **URL**: `/ocr/upload`
- **Método**: `POST`
- **Parâmetros de consulta**:
  - `language`: Idioma para OCR (por, eng, spa, auto)
  - `document_type`: Tipo de documento (rg, cpf, cnh, generic)
  - `enhanced_processing`: Usar processamento avançado (true/false)
  - `confidence_threshold`: Limite de confiança (0-100)
- **Corpo**: Arquivo de imagem (multipart/form-data)
- **Retorno**: Texto extraído, status, tempo de processamento, etc.

### Câmera para OCR
- **URL**: `/ocr/camera`
- **Método**: `POST`
- **Corpo**: JSON com campos:
  - `image_data`: Imagem em base64
  - `language`: Idioma para OCR (por, eng, spa, auto)
  - `document_type`: Tipo de documento (rg, cpf, cnh, generic)
  - `enhanced_processing`: Usar processamento avançado (true/false)
- **Retorno**: Texto extraído, status, tempo de processamento, etc.

### Estatísticas da API
- **URL**: `/api/stats`
- **Método**: `GET`
- **Retorno**: Estatísticas de uso da API (total de requisições, bem-sucedidas, falhas, tempo médio)

### Saúde da API
- **URL**: `/api/health`
- **Método**: `GET`
- **Retorno**: Status da API, versão, endpoints disponíveis

### Documentação OpenAPI
- **URL**: `/docs` (Swagger UI)
- **URL**: `/redoc` (ReDoc)
- **Método**: `GET`
- **Descrição**: Documentação interativa da API

## Como executar

```bash
# Executar a API FastAPI na porta 8000
./workflow_fastapi.sh

# Ou usando Python diretamente
python run_fastapi.py
```

## Testando a API

Você pode usar o cliente de exemplo em `examples/fastapi_client.py`:

```bash
# Instalar as dependências
pip install requests

# Executar o cliente (substitua por uma imagem real)
python examples/fastapi_client.py caminho/para/imagem.jpg
```

## Comparação com a API Flask (original)

| Recurso | Flask | FastAPI |
|---------|-------|---------|
| Documentação automática | ❌ | ✅ |
| Validação de tipos | ❌ | ✅ |
| Operações assíncronas | ❌ | ✅ |
| Estatísticas de uso | ❌ | ✅ |
| Verificação de saúde | ❌ | ✅ |
| Parâmetros de configuração OCR | ❌ | ✅ |
| Tempo de processamento | ❌ | ✅ |
| Detecção de idioma | ❌ | ✅ |
| Identificação de tipo de documento | ❌ | ✅ |