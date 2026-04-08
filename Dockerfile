FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy essential codebase
COPY server.py .
COPY tasks.py .
COPY inference.py .
COPY server/ ./server/

# Copy OpenEnv metadata
COPY openenv.yaml .
COPY pyproject.toml .
COPY README.md .

ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["python", "server/app.py"]