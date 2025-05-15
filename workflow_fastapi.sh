#!/bin/bash
# Script para iniciar a API FastAPI usando Uvicorn
# Executa em uma porta diferente para não conflitar com a aplicação Flask

uvicorn wsgi_fastapi:fastapi_app --host 0.0.0.0 --port 8000 --reload