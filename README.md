---
title: Research AI API
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_file: main.py
pinned: false
---

# Research AI API - 7 Endpoints

## 🚀 Endpoints
1. `/chat` - phi3:mini (2.2GB)
2. `/code` - deepseek-coder (0.8GB)
3. `/stt` - Whisper tiny (75MB)
4. `/tts` - Piper/Espeak
5. `/translate` - Helsinki (300MB)
6. `/image` - moondream (1.7GB)
7. `/health` - Status check

## ⚡ Fast Response Technologies
- **Redis** - Response caching (5ms)
- **Kafka** - Token streaming
- **WebSockets** - Real-time
- **Build-time downloads** - No startup delay

## 🔑 Authentication
Use header: `X-API-Key: mypassword123`

## 🐳 Deploy on Hugging Face
1. Create new Space with Docker SDK
2. Connect GitHub repo
3. Add secrets in Settings:
   - `API_KEY=your_key_here`

Total size: ~5GB (optimized from 25GB+)
