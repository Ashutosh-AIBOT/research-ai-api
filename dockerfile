# Dockerfile - ALL MODELS DOWNLOADED AT BUILD TIME
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
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools==69.5.1 wheel==0.43.0

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create directories for ALL models
RUN mkdir -p /app/models/whisper \
             /app/models/translator \
             /app/models/ollama \
             /app/models/transformers \
             /app/voices \
             /app/models/torch

# ========== DOWNLOAD ALL MODELS AT BUILD TIME ==========

# 1. Download Whisper model
RUN python -c "\
import whisper; \
print('📥 Downloading Whisper tiny...'); \
whisper.load_model('tiny', download_root='/app/models/whisper'); \
print('✅ Whisper downloaded'); \
"

# 2. Download Translator model (Helsinki-NLP)
RUN python -c "\
from transformers import MarianMTModel, MarianTokenizer; \
print('📥 Downloading Hindi-English translator...'); \
MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-hi-en', cache_dir='/app/models/translator'); \
print('✅ Translator downloaded'); \
"

# 3. Download Piper voice
RUN wget -q -O /app/voices/en_US-lessac-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
    wget -q -O /app/voices/en_US-lessac-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json && \
    echo "✅ Piper voice downloaded"

# 4. Download ALL Ollama models (pull and save to disk)
RUN ollama serve & \
    sleep 10 && \
    echo "📥 Pulling phi3:mini (2.2GB)..." && \
    ollama pull phi3:mini && \
    echo "📥 Pulling deepseek-coder:1.3b (0.8GB)..." && \
    ollama pull deepseek-coder:1.3b && \
    echo "📥 Pulling moondream (1.7GB)..." && \
    ollama pull moondream && \
    pkill ollama && \
    echo "✅ All Ollama models downloaded"

# 5. Download additional transformer models (for caching)
RUN python -c "\
from transformers import pipeline; \
print('📥 Downloading sentiment model...'); \
pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english', cache_dir='/app/models/transformers'); \
print('✅ Sentiment model downloaded'); \
"

# ========== SET ALL ENVIRONMENT VARIABLES ==========
ENV WHISPER_MODEL_PATH=/app/models/whisper
ENV TRANSFORMERS_CACHE=/app/models/transformers
ENV HF_HOME=/app/models
ENV TORCH_HOME=/app/models/torch
ENV PIPER_VOICE=/app/voices/en_US-lessac-medium.onnx
ENV OLLAMA_MODELS=/app/models/ollama
ENV XDG_CACHE_HOME=/app/models/cache

# Copy application code
COPY main.py config.py start.sh ./
RUN chmod +x start.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Show disk usage to verify models are downloaded (debug)
RUN du -sh /app/models/* || true

# Hugging Face port
EXPOSE 7860

# Start command
CMD ["./start.sh"]