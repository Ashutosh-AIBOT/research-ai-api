# Dockerfile - COMPLETE VERSION with all models and features
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    curl \
    wget \
    gcc \
    g++ \
    make \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && echo "✅ System dependencies installed"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools==69.5.1 wheel==0.43.0 \
    && echo "✅ Build tools installed"

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt \
    && pip install redis==5.0.1 aiokafka==0.8.1 \
    && echo "✅ Python dependencies installed"

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh \
    && echo "✅ Ollama installed"

# Create directories for ALL models
RUN mkdir -p /app/models/whisper \
             /app/models/translator \
             /app/models/ollama \
             /app/models/transformers \
             /app/voices \
             /app/models/torch \
             /app/cache \
             /app/models \
    && echo "✅ Model directories created"

# ========== DOWNLOAD ALL MODELS AT BUILD TIME ==========

# 1. Download Whisper model
RUN python -c "\
import whisper; \
print('📥 Downloading Whisper tiny...'); \
whisper.load_model('tiny', download_root='/app/models/whisper'); \
print('✅ Whisper downloaded'); \
" || echo "⚠️ Whisper download failed but continuing"

# 2. Download Translator model (Helsinki-NLP)
RUN python -c "\
from transformers import MarianMTModel, MarianTokenizer; \
print('📥 Downloading Hindi-English translator...'); \
MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-hi-en', cache_dir='/app/models/translator'); \
print('✅ Translator downloaded'); \
" || echo "⚠️ Translator download failed but continuing"

# 3. Download Piper voice
RUN wget -q --timeout=30 --tries=3 -O /app/voices/en_US-lessac-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget -q --timeout=30 --tries=3 -O /app/voices/en_US-lessac-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json && \
    echo "✅ Piper voice downloaded" || echo "⚠️ Piper download failed but continuing"

# 4. Download ALL Ollama models
RUN ollama serve & \
    sleep 10 && \
    echo "📥 Pulling phi3:mini (2.2GB)..." && \
    ollama pull phi3:mini && \
    echo "📥 Pulling deepseek-coder:1.3b (0.8GB)..." && \
    ollama pull deepseek-coder:1.3b && \
    echo "📥 Pulling moondream (1.7GB)..." && \
    ollama pull moondream && \
    pkill ollama && \
    echo "✅ All Ollama models downloaded" || echo "⚠️ Ollama pulls failed but continuing"

# 5. Download sentiment model (optional but included)
RUN python -c "\
try: \
    from transformers import pipeline; \
    print('📥 Downloading sentiment model...'); \
    pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english', cache_dir='/app/models/transformers'); \
    print('✅ Sentiment model downloaded'); \
except Exception as e: \
    print(f'⚠️ Sentiment model download failed: {e}'); \
" || echo "⚠️ Sentiment download failed but continuing"

# ========== SET ALL ENVIRONMENT VARIABLES ==========
ENV WHISPER_MODEL_PATH=/app/models/whisper
ENV TRANSFORMERS_CACHE=/app/models/transformers
ENV HF_HOME=/app/models
ENV TORCH_HOME=/app/models/torch
ENV PIPER_VOICE=/app/voices/en_US-lessac-medium.onnx
ENV OLLAMA_MODELS=/app/models/ollama
ENV XDG_CACHE_HOME=/app/models/cache
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV KAFKA_BROKER=localhost:9092
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# ========== COPY APPLICATION CODE ==========

# Copy entire app folder (includes all routes, utils, etc.)
COPY app/ ./app/

# Copy start script
COPY start.sh ./

# Copy docker and scripts folders if needed
COPY docker/ ./docker/
COPY scripts/ ./scripts/

# Make start.sh executable
RUN chmod +x start.sh

# Show directory structure for debugging
RUN echo "📁 Directory structure:" && ls -la && \
    echo "📁 App directory:" && ls -la app/ && \
    echo "📁 Routes directory:" && ls -la app/routes/ || true

# Create non-root user
RUN useradd -m -u 1000 appuser 2>/dev/null || true && \
    chown -R appuser:appuser /app 2>/dev/null || true
USER appuser

# Show disk usage to verify models are downloaded
RUN du -sh /app/models/* 2>/dev/null || echo "⚠️ No models found in /app/models/"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Hugging Face port
EXPOSE 7860

# Start command
CMD ["./start.sh"]