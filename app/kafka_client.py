import json
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app.config import config
import logging

logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self):
        self.producer = None
        self.consumers = {}
        self.enabled = config.STREAMING_ENABLED
        
    async def connect_producer(self):
        """Connect Kafka producer"""
        if not self.enabled:
            logger.info("Kafka streaming is disabled")
            return
            
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type="gzip"
            )
            await self.producer.start()
            logger.info("✅ Connected to Kafka producer")
        except Exception as e:
            logger.error(f"❌ Kafka producer connection failed: {e}")
            self.enabled = False
    
    async def send_request(self, request_id: str, data: dict):
        """Send request to Kafka"""
        if not self.enabled or not self.producer:
            return False
        try:
            await self.producer.send(
                config.KAFKA_TOPIC_REQUESTS,
                key=request_id.encode(),
                value=data
            )
            return True
        except Exception as e:
            logger.error(f"Kafka send error: {e}")
            return False
    
    async def send_response_chunk(self, request_id: str, chunk: str, is_last: bool = False):
        """Send response chunk to Kafka"""
        if not self.enabled or not self.producer:
            return False
        try:
            await self.producer.send(
                config.KAFKA_TOPIC_RESPONSES,
                key=request_id.encode(),
                value={"chunk": chunk, "last": is_last, "request_id": request_id}
            )
            return True
        except Exception as e:
            logger.error(f"Kafka send chunk error: {e}")
            return False
    
    async def create_consumer(self, group_id: str, topic: str):
        """Create a new consumer"""
        if not self.enabled:
            return None
            
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset="latest",
            enable_auto_commit=True
        )
        await consumer.start()
        self.consumers[group_id] = consumer
        return consumer
    
    async def close(self):
        """Close all connections"""
        if self.producer:
            await self.producer.stop()
        
        for consumer in self.consumers.values():
            await consumer.stop()
        
        logger.info("Kafka connections closed")

# Global Kafka instance
kafka_client = KafkaClient()
