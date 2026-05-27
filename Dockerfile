# API FastAPI do roulette_analyzer. Deploy como app no Easypanel (porta 8000).
FROM python:3.11-slim

WORKDIR /app

# lib de sistema que scipy/numpy as vezes precisam em imagem slim (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# dependencias (vem do pyproject; wheels binarios para scipy/numpy/pandas)
COPY pyproject.toml README.md ./
COPY core ./core
COPY analyze.py api.py ./
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
