# Loom Common

Shared utilities and base classes for Loom v2 microservices.

## Features

- **Kafka Integration**: Base producer and consumer classes with standard error handling
- **Configuration**: Common settings and environment variable patterns
- **Logging**: Structured logging setup with correlation IDs
- **Health Checks**: Standard health check endpoints for Kubernetes
- **Models**: Common Pydantic models and validators
- **Deduplication**: Content hashing utilities for data deduplication

## Installation

```bash
pip install -e /app/loom-common
```

Or in your `pyproject.toml`:

```toml
dependencies = [
    "loom-common @ file:///app/loom-common",
    # ... other dependencies
]
```

## Usage

### Kafka Producer

```python
from loom_common.kafka import BaseKafkaProducer

class MyProducer(BaseKafkaProducer):
    async def process_data(self, data):
        await self.send_message("my.topic", data, key=data.get("id"))
```

### Kafka Consumer

```python
from loom_common.kafka import BaseKafkaConsumer

class MyConsumer(BaseKafkaConsumer):
    def __init__(self):
        super().__init__(
            topics=["input.topic"],
            group_id="my-consumer-group"
        )

    async def process_message(self, message):
        # Process your message here
        result = transform(message.value)
        await self.send_to_topic("output.topic", result)
```

### Configuration

```python
from loom_common.config import BaseSettings

class Settings(BaseSettings):
    # Your service-specific settings
    my_custom_setting: str = "default"

settings = Settings()
```

### Logging

```python
from loom_common.logging import setup_logging

logger = setup_logging("my-service")
logger.info("Service started", extra={"version": "1.0.0"})
```

### Health Checks

```python
from fastapi import FastAPI
from loom_common.health import create_health_router

app = FastAPI()
app.include_router(create_health_router())
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff --fix src/
```
