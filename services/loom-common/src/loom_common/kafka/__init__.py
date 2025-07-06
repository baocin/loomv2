"""
Kafka utilities and base classes
"""

from loom_common.kafka.consumer import BaseKafkaConsumer
from loom_common.kafka.consumer_config_loader import (
    ConsumerConfiguration,
    KafkaConsumerConfigLoader,
    ProcessingRecommendation,
    create_optimized_consumer,
)
from loom_common.kafka.producer import BaseKafkaProducer

__all__ = [
    "BaseKafkaProducer",
    "BaseKafkaConsumer",
    "KafkaConsumerConfigLoader",
    "ConsumerConfiguration",
    "ProcessingRecommendation",
    "create_optimized_consumer",
]
