#!/bin/bash
# Script para executar a aplicação FastAPI em uma porta diferente
uvicorn asgi:app --host 0.0.0.0 --port 8000 --reload