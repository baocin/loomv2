"""
Kafka utilities and base classes
"""

from loom_common.kafka.consumer import BaseKafkaConsumer
from loom_common.kafka.producer import BaseKafkaProducer

__all__ = ["BaseKafkaProducer", "BaseKafkaConsumer"]
