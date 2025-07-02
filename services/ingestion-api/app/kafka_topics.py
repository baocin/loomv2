"""Kafka topic management for automatic topic creation."""

import structlog
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.admin.config_resource import ConfigResource, ConfigResourceType
from aiokafka.admin.new_topic import NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from .config import settings

logger = structlog.get_logger(__name__)


class KafkaTopicManager:
    """Manages Kafka topic creation and configuration."""

    def __init__(self):
        self.admin_client: AIOKafkaAdminClient = None
        self.required_topics = self._get_required_topics()

    def _get_required_topics(self) -> dict[str, dict]:
        """Get list of required topics with their configurations."""
        return {
            # Audio topics
            settings.topic_device_audio_raw: {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                    "segment.ms": "86400000",  # 1 day
                },
            },
            # Sensor topics
            "device.sensor.gps.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "device.sensor.accelerometer.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            # Health topics
            "device.health.heartrate.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "5184000000",  # 60 days
                    "compression.type": "producer",
                },
            },
            # State topics
            "device.state.power.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            # Network topics
            "device.network.wifi.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                },
            },
            "device.network.bluetooth.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                },
            },
            # Environmental sensors
            "device.sensor.temperature.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "device.sensor.barometer.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            # New Sprint 4 topics
            settings.topic_device_system_apps_macos: {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            settings.topic_device_system_apps_android: {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            settings.topic_device_metadata: {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
            # Android app usage statistics (pre-aggregated)
            "device.app_usage.android.aggregated": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
            # Sprint 5.5: New data ingestion topics
            "digital.notes.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days (documents, markdown files)
                    "compression.type": "producer",
                },
            },
            "device.image.camera.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "1296000000",  # 15 days (images are large)
                    "compression.type": "producer",
                },
            },
            "device.video.screen.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days (screenshots)
                    "compression.type": "producer",
                },
            },
            # External data topics for scheduled consumers
            "external.email.events.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
            "external.calendar.events.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "31536000000",  # 365 days
                    "compression.type": "producer",
                },
            },
            "external.twitter.liked.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "31536000000",  # 365 days
                    "compression.type": "producer",
                },
            },
            "external.hackernews.activity.raw": {
                "partitions": 2,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "15552000000",  # 180 days
                    "compression.type": "producer",
                },
            },
            "external.web.visits.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "internal.scheduled.jobs.status": {
                "partitions": 1,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                    "cleanup.policy": "compact",  # Keep latest status per job
                },
            },
            # URL Processing Tasks
            "task.url.ingest": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days (processing queue)
                    "compression.type": "producer",
                },
            },
            # AI Processing Intermediate Topics
            "media.audio.vad_filtered": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                },
            },
            # AI Processing Result Topics (renamed from *_results)
            "media.audio.voice_segments": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "compression.type": "producer",
                },
            },
            "media.text.word_timestamps": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "1296000000",  # 15 days
                    "compression.type": "producer",
                },
            },
            "media.image.vision_annotations": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "1296000000",  # 15 days
                    "compression.type": "producer",
                },
            },
            "analysis.audio.emotion_scores": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "analysis.image.face_emotions": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "analysis.context.reasoning_chains": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
            "task.url.processed_content": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "15552000000",  # 180 days
                    "compression.type": "producer",
                },
            },
            # OS Event Topics (Sprint 5)
            "os.events.app_lifecycle.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "os.events.system.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            "os.events.notifications.raw": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "2592000000",  # 30 days
                    "compression.type": "producer",
                },
            },
            # Location Processing Topics
            "location.address.geocoded": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
            "location.georegion.detected": {
                "partitions": settings.kafka_default_partitions,
                "replication_factor": settings.kafka_default_replication_factor,
                "config": {
                    "retention.ms": "7776000000",  # 90 days
                    "compression.type": "producer",
                },
            },
        }

    async def start(self) -> None:
        """Initialize the Kafka admin client."""
        try:
            self.admin_client = AIOKafkaAdminClient(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                client_id=f"{settings.kafka_client_id}-admin",
                request_timeout_ms=30000,
                connections_max_idle_ms=300000,
            )
            await self.admin_client.start()
            logger.info(
                "Kafka admin client started",
                bootstrap_servers=settings.kafka_bootstrap_servers,
            )

            # Create topics if enabled
            if settings.kafka_auto_create_topics:
                await self.ensure_topics_exist()

        except Exception as e:
            logger.error("Failed to start Kafka admin client", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka admin client."""
        if self.admin_client:
            try:
                await self.admin_client.close()
                logger.info("Kafka admin client stopped")
            except Exception as e:
                logger.error("Error stopping Kafka admin client", error=str(e))

    async def ensure_topics_exist(self) -> None:
        """Ensure all required topics exist, creating them if necessary."""
        try:
            # Get existing topics
            existing_topics = await self.get_existing_topics()
            logger.info(
                "Found existing topics",
                count=len(existing_topics),
                topics=list(existing_topics),
            )

            # Determine which topics need to be created
            topics_to_create = []
            for topic_name, config in self.required_topics.items():
                if topic_name not in existing_topics:
                    topics_to_create.append(
                        NewTopic(
                            name=topic_name,
                            num_partitions=config["partitions"],
                            replication_factor=config["replication_factor"],
                            topic_configs=config.get("config", {}),
                        ),
                    )

            if not topics_to_create:
                logger.info("All required topics already exist")
                return

            # Create missing topics
            logger.info(
                "Creating missing topics",
                count=len(topics_to_create),
                topics=[t.name for t in topics_to_create],
            )

            create_result = await self.admin_client.create_topics(topics_to_create)

            # Check results
            successful_topics = []
            failed_topics = []

            # Handle different response types from create_topics
            if hasattr(create_result, "items"):
                # Dictionary-like response
                for topic_name, future in create_result.items():
                    try:
                        await future
                        successful_topics.append(topic_name)
                        logger.info("Successfully created topic", topic=topic_name)
                    except TopicAlreadyExistsError:
                        # Topic was created between our check and creation attempt
                        successful_topics.append(topic_name)
                        logger.info(
                            "Topic already exists (concurrent creation)",
                            topic=topic_name,
                        )
                    except Exception as e:
                        failed_topics.append((topic_name, str(e)))
                        logger.error(
                            "Failed to create topic",
                            topic=topic_name,
                            error=str(e),
                        )
            else:
                # Assume all topics were created successfully if no detailed response
                successful_topics = [t.name for t in topics_to_create]
                logger.info("Topics created (no detailed response available)")

            # Report results
            if successful_topics:
                logger.info(
                    "Topic creation completed",
                    successful=len(successful_topics),
                    failed=len(failed_topics),
                    successful_topics=successful_topics,
                )

            if failed_topics:
                logger.error(
                    "Some topics failed to create",
                    failed_topics=failed_topics,
                )
                # Don't raise exception - service can still function with manual topic creation

        except Exception as e:
            logger.error("Error during topic creation", error=str(e))
            # Don't raise exception - service can still function with manual topic creation

    async def get_existing_topics(self) -> list[str]:
        """Get list of existing topic names."""
        try:
            metadata = await self.admin_client.list_topics()
            # Handle different return types from list_topics
            if isinstance(metadata, list):
                return metadata
            if hasattr(metadata, "topics"):
                return list(metadata.topics.keys())
            logger.warning(
                "Unexpected metadata format",
                metadata_type=type(metadata),
            )
            return []
        except Exception as e:
            logger.error("Failed to list existing topics", error=str(e))
            return []

    async def create_topic_if_not_exists(
        self,
        topic_name: str,
        partitions: int = None,
        replication_factor: int = None,
    ) -> bool:
        """Create a single topic if it doesn't exist.

        Args:
        ----
            topic_name: Name of the topic to create
            partitions: Number of partitions (uses default if None)
            replication_factor: Replication factor (uses default if None)

        Returns:
        -------
            True if topic was created or already exists, False if creation failed

        """
        try:
            existing_topics = await self.get_existing_topics()

            if topic_name in existing_topics:
                logger.debug("Topic already exists", topic=topic_name)
                return True

            # Use provided values or defaults
            num_partitions = partitions or settings.kafka_default_partitions
            repl_factor = (
                replication_factor or settings.kafka_default_replication_factor
            )

            new_topic = NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=repl_factor,
            )

            create_result = await self.admin_client.create_topics([new_topic])
            await create_result[topic_name]

            logger.info(
                "Successfully created topic",
                topic=topic_name,
                partitions=num_partitions,
                replication_factor=repl_factor,
            )
            return True

        except TopicAlreadyExistsError:
            logger.info("Topic already exists (concurrent creation)", topic=topic_name)
            return True
        except Exception as e:
            logger.error("Failed to create topic", topic=topic_name, error=str(e))
            return False

    async def validate_topic_config(self, topic_name: str) -> dict:
        """Validate configuration of an existing topic.

        Args:
        ----
            topic_name: Name of the topic to validate

        Returns:
        -------
            Dictionary with topic configuration details

        """
        try:
            # Get topic metadata
            metadata = await self.admin_client.describe_topics([topic_name])
            topic_metadata = metadata[topic_name]

            # Get topic configuration
            config_resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
            configs = await self.admin_client.describe_configs([config_resource])
            topic_config = configs[config_resource]

            return {
                "name": topic_name,
                "partitions": len(topic_metadata.partitions),
                "replication_factor": (
                    len(topic_metadata.partitions[0].replicas)
                    if topic_metadata.partitions
                    else 0
                ),
                "config": {name: entry.value for name, entry in topic_config.items()},
                "exists": True,
            }

        except Exception as e:
            logger.error(
                "Failed to validate topic config",
                topic=topic_name,
                error=str(e),
            )
            return {"name": topic_name, "exists": False, "error": str(e)}


# Global topic manager instance
topic_manager = KafkaTopicManager()
