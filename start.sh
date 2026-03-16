#!/bin/bash
# start.sh - ZERO downloads at runtime, just load from disk

echo "🚀 Starting Research AI API..."

# Set paths to pre-downloaded models
export WHISPER_MODEL_PATH=/app/models/whisper
export TRANSFORMERS_CACHE=/app/models/transformers
export HF_HOME=/app/models
export PIPER_VOICE=/app/voices/en_US-lessac-medium.onnx
export OLLAMA_MODELS=/app/models/ollama

# Function to handle shutdown
cleanup() {
    echo "🛑 Shutting down..."
    kill $OLLAMA_PID 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

# Start Ollama with pre-downloaded models
echo "📦 Starting Ollama from local models..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama..."
sleep 5

if kill -0 $OLLAMA_PID 2>/dev/null; then
    echo "✅ Ollama ready (using local models)"
else
    echo "❌ Ollama failed to start"
    exit 1
fi

# Show loaded models (verify no downloads)
echo "📋 Available models:"
curl -s http://localhost:11434/api/tags | python -m json.tool || echo "No models loaded"

# Start FastAPI
echo "🚀 Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 7860