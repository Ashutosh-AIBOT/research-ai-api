import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # API
    API_KEY = os.getenv("API_KEY", "mypassword123")
    
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_MAX_MEMORY = os.getenv("REDIS_MAX_MEMORY", "512mb")
    REDIS_TTL = int(os.getenv("REDIS_TTL", 3600))
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_REQUESTS = os.getenv("KAFKA_TOPIC_REQUESTS", "ai-requests")
    KAFKA_TOPIC_RESPONSES = os.getenv("KAFKA_TOPIC_RESPONSES", "ai-responses")
    KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "ai-group")
    
    # Models - All will load on-demand!
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
    CHAT_MODEL = os.getenv("CHAT_MODEL", "phi3:mini")
    CODE_MODEL = os.getenv("CODE_MODEL", "deepseek-coder:1.3b")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "moondream")
    TRANSLATOR_MODEL = os.getenv("TRANSLATOR_MODEL", "Helsinki-NLP/opus-mt-hi-en")
    
    # Paths
    MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
    WHISPER_CACHE_DIR = os.getenv("WHISPER_CACHE_DIR", "/app/models/whisper")
    TRANSLATOR_CACHE_DIR = os.getenv("TRANSLATOR_CACHE_DIR", "/app/models/translator")
    
    # Performance
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 120))
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    STREAMING_ENABLED = os.getenv("STREAMING_ENABLED", "true").lower() == "true"

config = Config()