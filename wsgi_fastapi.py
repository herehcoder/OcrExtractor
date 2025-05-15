from main import fastapi_app
import uvicorn

# Ponto de entrada para gunicorn usando o Uvicorn worker
# Para executar: gunicorn -k uvicorn.workers.UvicornWorker wsgi_fastapi:fastapi_app

if __name__ == "__main__":
    uvicorn.run("wsgi_fastapi:fastapi_app", host="0.0.0.0", port=8000, reload=True)