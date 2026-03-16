# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg espeak curl wget gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create model directories
RUN mkdir -p /app/models/whisper /app/models/translator

# Download models at BUILD TIME
RUN python -c "\
import whisper; \
print('Downloading Whisper...'); \
whisper.load_model('tiny', download_root='/app/models/whisper'); \
"

RUN python -c "\
from transformers import MarianMTModel, MarianTokenizer; \
print('Downloading Translator...'); \
MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-hi-en', cache_dir='/app/models/translator'); \
"

# Pull Ollama models
RUN ollama serve & sleep 5 && \
    ollama pull phi3:mini && \
    ollama pull deepseek-coder:1.3b && \
    ollama pull moondream && \
    pkill ollama

# Copy application code
COPY . .

# Hugging Face port
EXPOSE 7860

# Start command
CMD ollama serve & uvicorn main:app --host 0.0.0.0 --port 7860
