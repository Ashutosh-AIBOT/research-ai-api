# Dockerfile - COMPLETE with Redis, Kafka & WebSockets
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (including Redis and Kafka)
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
    redis-server \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && echo "✅ System dependencies installed"

# Install Kafka
RUN wget https://downloads.apache.org/kafka/3.9.0/kafka_2.13-3.9.0.tgz && \
    tar -xzf kafka_2.13-3.9.0.tgz && \
    mv kafka_2.13-3.9.0 /opt/kafka && \
    rm kafka_2.13-3.9.0.tgz && \
    echo "✅ Kafka installed"

# Install uv (100x faster than pip)
RUN pip install uv==0.5.0 \
    && echo "✅ uv installed"

# Create directories for ALL models and services
RUN mkdir -p /app/models/whisper \
             /app/models/translator \
             /app/models/ollama \
             /app/models/transformers \
             /app/voices \
             /app/models/torch \
             /app/cache \
             /app/data/redis \
             /app/data/kafka \
             /app/logs \
    && echo "✅ Directories created"

# Copy requirements
COPY requirements.txt .

# ========== FIXED: Install setuptools system-wide FIRST ==========
RUN pip install --no-cache-dir --upgrade pip setuptools==69.5.1 wheel==0.43.0

# ========== FIXED: Install numpy before whisper ==========
RUN pip install --no-cache-dir numpy==1.24.3

# ========== FIXED: Install whisper with no-build-isolation ==========
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117 \
    && echo "✅ Whisper installed"

# ========== Install remaining dependencies with uv ==========
RUN uv pip install --system --no-cache \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    pydantic==2.4.2 \
    httpx==0.25.1 \
    websockets==12.0 \
    aiohttp==3.9.1 \
    aiofiles==23.2.1 \
    transformers==4.35.0 \
    torch==2.1.0 \
    torchaudio==2.1.0 \
    ollama==0.1.6 \
    redis==5.0.1 \
    aiokafka==0.8.1 \
    python-dotenv==1.0.0 \
    pyyaml==6.0.1 \
    psutil==5.9.6 \
    aioredis==2.0.1 \
    kafka-python==2.0.2 \
    && echo "✅ Python dependencies installed with uv"

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh \
    && echo "✅ Ollama installed"

# ========== DOWNLOAD ALL MODELS ==========

# 1. Download Whisper model
RUN python -c "\
import whisper; \
print('📥 Downloading Whisper tiny...'); \
whisper.load_model('tiny', download_root='/app/models/whisper'); \
print('✅ Whisper downloaded'); \
" || echo "⚠️ Whisper download failed"

# 2. Download Translator model
RUN python -c "\
from transformers import MarianMTModel, MarianTokenizer; \
print('📥 Downloading Hindi-English translator...'); \
MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-hi-en', cache_dir='/app/models/translator'); \
print('✅ Translator downloaded'); \
" || echo "⚠️ Translator download failed"

# 3. Download Piper voice
RUN wget -q -O /app/voices/en_US-lessac-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    echo "✅ Piper voice downloaded" || echo "⚠️ Piper download failed"

# 4. Download Ollama models
RUN ollama serve & \
    sleep 10 && \
    ollama pull phi3:mini && \
    ollama pull deepseek-coder:1.3b && \
    ollama pull moondream && \
    pkill ollama && \
    echo "✅ Ollama models downloaded" || echo "⚠️ Ollama pulls failed"

# 5. Download sentiment model (optional)
RUN python -c "\
try: \
    from transformers import pipeline; \
    print('📥 Downloading sentiment model...'); \
    pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english', cache_dir='/app/models/transformers'); \
    print('✅ Sentiment model downloaded'); \
except Exception as e: \
    print(f'⚠️ Sentiment model download failed: {e}'); \
" || echo "⚠️ Sentiment download failed"

# ========== SET ENVIRONMENT VARIABLES ==========
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
ENV KAFKA_PORT=9092
ENV WEBSOCKET_PORT=7860
ENV WEBSOCKET_ENABLED=true
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV UV_SYSTEM_PYTHON=1

# Copy application code
COPY app/ ./app/
COPY start.sh ./
COPY docker/ ./docker/
COPY scripts/ ./scripts/

RUN chmod +x start.sh

# Create Redis config
RUN echo "port 6379\nsave 60 1\nrdbcompression yes\ndbfilename dump.rdb\ndir /app/data/redis" > /etc/redis/redis.conf

# Install Kafka (FIXED URL)
RUN wget https://archive.apache.org/dist/kafka/3.9.0/kafka_2.13-3.9.0.tgz && \
    tar -xzf kafka_2.13-3.9.0.tgz && \
    mv kafka_2.13-3.9.0 /opt/kafka && \
    rm kafka_2.13-3.9.0.tgz && \
    echo "✅ Kafka installed"
    
# Show directory structure
RUN echo "📁 Directory structure:" && ls -la && \
    echo "📁 App directory:" && ls -la app/ || true

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /opt/kafka && \
    chown -R appuser:appuser /etc/redis
USER appuser

# Show disk usage
RUN du -sh /app/models/* 2>/dev/null || echo "⚠️ No models found"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Expose ports for all services
EXPOSE 7860 6379 9092 2181

CMD ["./start.sh"]