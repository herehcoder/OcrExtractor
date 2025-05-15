from app_fastapi import app

# Este arquivo serve como ponto de entrada ASGI para o Uvicorn
# Usado por: uvicorn asgi:app ou gunicorn -k uvicorn.workers.UvicornWorker asgi:app