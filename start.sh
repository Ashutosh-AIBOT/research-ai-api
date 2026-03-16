#!/bin/bash
# start.sh - COMPLETE with all services

echo "🚀 Starting Research AI API with all services..."

# Set paths to pre-downloaded models
export WHISPER_MODEL_PATH=/app/models/whisper
export TRANSFORMERS_CACHE=/app/models/transformers
export HF_HOME=/app/models
export PIPER_VOICE=/app/voices/en_US-lessac-medium.onnx
export OLLAMA_MODELS=/app/models/ollama
export WEBSOCKET_ENABLED=true

# Function to check if service is running
check_service() {
    if pgrep -f "$1" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to cleanup all services
cleanup() {
    echo "🛑 Shutting down all services..."
    kill $OLLAMA_PID 2>/dev/null
    /opt/kafka/bin/kafka-server-stop.sh 2>/dev/null
    /opt/kafka/bin/zookeeper-server-stop.sh 2>/dev/null
    redis-cli shutdown 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}
trap cleanup SIGTERM SIGINT

# ========== START REDIS ==========
echo "📦 Starting Redis for caching..."
if command -v redis-server &> /dev/null; then
    redis-server --daemonize yes --port 6379 --save "" --appendonly no
    sleep 2
    if check_service "redis-server"; then
        echo "✅ Redis started on port 6379"
    else
        echo "⚠️ Redis failed to start - continuing without cache"
    fi
else
    echo "⚠️ Redis not installed - skipping"
fi

# ========== START ZOOKEEPER (for Kafka) ==========
if [ -f "/opt/kafka/bin/zookeeper-server-start.sh" ]; then
    echo "📦 Starting Zookeeper..."
    /opt/kafka/bin/zookeeper-server-start.sh -daemon /opt/kafka/config/zookeeper.properties 2>/dev/null
    sleep 5
    
    # Check if Zookeeper started
    if check_service "zookeeper"; then
        echo "✅ Zookeeper started"
        
        # ========== START KAFKA ==========
        echo "📦 Starting Kafka for streaming..."
        /opt/kafka/bin/kafka-server-start.sh -daemon /opt/kafka/config/server.properties 2>/dev/null
        sleep 8
        if check_service "kafka"; then
            echo "✅ Kafka started on port 9092"
        else
            echo "⚠️ Kafka failed to start - continuing without streaming"
        fi
    else
        echo "⚠️ Zookeeper failed to start - skipping Kafka"
    fi
else
    echo "⚠️ Kafka not installed - skipping"
fi

# ========== START OLLAMA ==========
echo "📦 Starting Ollama from local models..."
ollama serve &
OLLAMA_PID=$!

echo "⏳ Waiting for Ollama..."
sleep 8

if kill -0 $OLLAMA_PID 2>/dev/null; then
    echo "✅ Ollama ready (using local models)"
    
    # Show loaded models
    echo "📋 Available Ollama models:"
    curl -s http://localhost:11434/api/tags | python -m json.tool 2>/dev/null || echo "  ✓ Models will load on first request"
else
    echo "❌ Ollama failed to start"
    exit 1
fi

# ========== SHOW RUNNING SERVICES ==========
echo ""
echo "📊 ====== RUNNING SERVICES ======"
echo "🔹 FastAPI:   http://0.0.0.0:7860"
echo "🔹 Ollama:    http://localhost:11434"
if check_service "redis-server"; then
    echo "🔹 Redis:     port 6379 (caching)"
fi
if check_service "kafka"; then
    echo "🔹 Kafka:     port 9092 (streaming)"
fi
if check_service "zookeeper"; then
    echo "🔹 Zookeeper: port 2181"
fi
if [ "$WEBSOCKET_ENABLED" = "true" ]; then
    echo "🔹 WebSocket: ws://0.0.0.0:7860/ws"
fi
echo "================================"
echo ""

# ========== START FASTAPI with WebSockets ==========
echo "🚀 Starting FastAPI server with WebSocket support..."

# Check which main.py location exists
if [ -f "app/main.py" ]; then
    echo "📁 Using app/main.py"
    uvicorn app.main:app --host 0.0.0.0 --port 7860 --ws websockets --loop asyncio
elif [ -f "main.py" ]; then
    echo "📁 Using main.py"
    uvicorn main:app --host 0.0.0.0 --port 7860 --ws websockets --loop asyncio
else
    echo "❌ Could not find main.py"
    echo "🔍 Searching for main.py..."
    find . -name "main.py" -type f | head -5
    exit 1
fi

# Cleanup when FastAPI stops
cleanup