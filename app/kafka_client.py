from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
import logging
from app.config import config

logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self):
        self.producer = None
        self.consumer = None
    
    async def connect_producer(self):
        """Connect Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                request_timeout_ms=3000
            )
            await self.producer.start()
            logger.info("✅ Kafka producer connected")
        except Exception as e:
            logger.warning(f"⚠️ Kafka connection failed: {e}")
            self.producer = None
    
    async def close(self):
        if self.producer:
            await self.producer.stop()
    
    async def send_response_chunk(self, request_id: str, chunk: str, is_last: bool = False):
        """Send response chunk to Kafka"""
        if not self.producer:
            return
        
        try:
            await self.producer.send(
                config.KAFKA_TOPIC_RESPONSES,
                json.dumps({
                    "request_id": request_id,
                    "chunk": chunk,
                    "is_last": is_last,
                    "timestamp": asyncio.get_event_loop().time()
                }).encode()
            )
        except Exception as e:
            logger.warning(f"Kafka send error: {e}")

kafka_client = KafkaClient()