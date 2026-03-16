import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
from app.config import config

logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self):
        self.producer = None
        self.consumer = None
    
    async def connect_producer(self):
        """Connect Kafka producer with correct broker address"""
        # The correct broker is 'kafka:9092' (Docker service name), not localhost!
        bootstrap_servers = config.KAFKA_BOOTSTRAP_SERVERS  # This should be "kafka:9092"
        
        try:
            logger.info(f"🔄 Connecting Kafka to {bootstrap_servers}")
            self.producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=10000,
                connection_max_idle_ms=300000,
                max_request_size=1048576,
                acks='all'
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
            if is_last:
                logger.debug(f"✅ Sent final chunk for {request_id}")
        except Exception as e:
            logger.warning(f"Kafka send error: {e}")

kafka_client = KafkaClient()