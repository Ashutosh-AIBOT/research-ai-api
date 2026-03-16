import logging
from aiokafka import AIOKafkaProducer
import json
import asyncio
from app.config import config

logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self):
        self.producer = None
    
    async def connect_producer(self):
        """Connect Kafka producer using service name NOT localhost"""
        # CRITICAL FIX: Use kafka:9092 (service name) NOT localhost!
        bootstrap_servers = "kafka:9092"  # Hardcode for now
        
        try:
            logger.info(f"🔄 Connecting Kafka to {bootstrap_servers}")
            self.producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=10000,
                max_request_size=1048576
            )
            await self.producer.start()
            logger.info(f"✅ Kafka producer connected to {bootstrap_servers}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            self.producer = None
            return False
    
    async def close(self):
        if self.producer:
            await self.producer.stop()
    
    async def send_response_chunk(self, request_id: str, chunk: str, is_last: bool = False):
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