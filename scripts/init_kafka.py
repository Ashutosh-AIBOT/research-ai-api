#!/usr/bin/env python3
"""
Initialize Kafka topics
"""
import asyncio
from aiokafka import AIOKafkaAdminClient
from aiokafka.admin import NewTopic
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_topics():
    """Create Kafka topics if they don't exist"""
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers="kafka:9092"
    )
    
    try:
        await admin_client.start()
        
        topics = [
            NewTopic(name="ai-requests", num_partitions=3, replication_factor=1),
            NewTopic(name="ai-responses", num_partitions=3, replication_factor=1)
        ]
        
        try:
            await admin_client.create_topics(topics)
            logger.info("✅ Kafka topics created")
        except Exception as e:
            if "TOPIC_ALREADY_EXISTS" in str(e):
                logger.info("✅ Kafka topics already exist")
            else:
                logger.error(f"Error creating topics: {e}")
                
    finally:
        await admin_client.stop()

if __name__ == "__main__":
    logger.info("🚀 Initializing Kafka...")
    asyncio.run(create_topics())
    logger.info("✅ Kafka initialization complete")
