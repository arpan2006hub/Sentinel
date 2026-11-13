# =============================================================================
# Sentinel Backend — Docker image (CPU-only)
# Build context MUST be the project root (the API imports the ai/ package):
#     docker build -f backend/Dockerfile -t sentinel-backend .
#     docker compose --profile app up backend
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STORAGE_PATH=/data/evidence-store \
    ARTIFACTS_DIR=/data/artifacts \
    TIMESFORMER_CACHE_DIR=/data/models/timesformer

# libglib2.0-0 / libgl1: runtime libs for OpenCV video decoding; ffmpeg: fallback decoder
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch first (avoids pulling ~2 GB of CUDA wheels).
ARG INSTALL_TORCH=true
RUN if [ "$INSTALL_TORCH" = "true" ]; then \
        pip install torch --index-url https://download.pytorch.org/whl/cpu ; \
    fi

COPY backend/requirements.txt backend/requirements.txt
COPY requirements-ml.txt requirements-ml.txt
RUN if [ "$INSTALL_TORCH" = "true" ]; then \
        pip install -r backend/requirements.txt -r requirements-ml.txt ; \
    else \
        grep -v -E '^(torch|transformers)' requirements-ml.txt > /tmp/ml-notorch.txt && \
        pip install -r backend/requirements.txt -r /tmp/ml-notorch.txt ; \
    fi

COPY ai ./ai
COPY backend ./backend
COPY scripts ./scripts
COPY data/schemas ./data/schemas

RUN useradd --create-home --uid 1000 sentinel \
    && mkdir -p /data/evidence-store /data/artifacts /data/models/timesformer \
    && chown -R sentinel:sentinel /data /app
USER sentinel

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
