# Kafka Routing Architecture

## Overview

This document explains how Kafka's native routing capabilities handle message distribution in the Loom v2 pipeline, eliminating the need for complex routing logic in the application layer.

## Core Concepts

### 1. Topics as Entry Points

Each Kafka topic serves as an entry point to a processing pipeline. The topic itself determines which consumers will process the message.

```
Message Type → Topic → Consumer Group(s) → Processing
```

### 2. Consumer Groups for Distribution

Kafka consumer groups determine how messages are distributed:

- **Different consumer groups** = Each group gets ALL messages (duplication)
- **Same consumer group** = Messages distributed among members (load balancing)

## Processing Patterns

### Pattern 1: Direct Storage (No Processing)

```
Mobile App → [screenshot] → device.video.screen.raw → kafka-to-db-consumer → Database
```

**Consumer Groups:**
- `generic-kafka-to-db-consumer` (stores to database)

### Pattern 2: Single Processing Stage

```
Mobile App → [twitter_screenshot] → external.twitter.images.raw → Moondream OCR → media.image.analysis.moondream_results → Database
```

**Consumer Groups:**
- `moondream-ocr-consumer` (processes images)
- `generic-kafka-to-db-consumer` (stores results)

### Pattern 3: Multi-Stage Pipeline

```
Mobile App → [audio_chunk] → device.audio.raw → VAD Filter → media.audio.vad_filtered → STT → media.text.transcribed.words → Database
```

**Consumer Groups:**
- `silero-vad-consumer` (filters voice activity)
- `kyutai-stt-consumer` (transcribes speech)
- `generic-kafka-to-db-consumer` (stores transcripts)

## Multiple Consumer Example

If you want both Moondream and MiniCPM to process the same images:

```
                                    ┌─→ [moondream-ocr-consumer] → moondream_results
external.twitter.images.raw ────────┤
                                    └─→ [minicpm-ocr-consumer] → minicpm_results
```

Both consumers receive ALL messages because they use different consumer groups.

## Scaling Example

To scale Moondream OCR horizontally:

```
external.twitter.images.raw ──→ [moondream-ocr-consumer]
                                 ├─→ Moondream Instance 1 (processes ~50%)
                                 └─→ Moondream Instance 2 (processes ~50%)
```

Messages are load-balanced because instances share the same consumer group.

## Pipeline Hints

While Kafka handles routing, messages can include hints to help consumers understand processing intent:

```json
{
    "message_type": "twitter_screenshot",
    "pipeline_hint": "ocr_extraction",  // Helps consumer understand the goal
    "data": {...}
}
```

## Configuration Examples

### Moondream Consumer
```python
consumer = KafkaConsumer(
    "external.twitter.images.raw",  # Input topic
    group_id="moondream-ocr-consumer",  # Unique consumer group
    ...
)

# Process and forward to next stage
producer.send("media.image.analysis.moondream_results", processed_data)
```

### Database Consumer
```yaml
# topic_mappings.yml
topics:
  media.image.analysis.moondream_results:
    table: "media_image_analysis_moondream_results"
    description: "OCR results from Moondream"
```

## Benefits

1. **No Central Router**: Topics themselves are the routing mechanism
2. **Automatic Scaling**: Just add more instances with same consumer group
3. **Fault Tolerance**: If one consumer fails, others continue processing
4. **Simple Configuration**: Just configure topic and consumer group
5. **Flexible Processing**: Easy to add new consumers without changing producers

## Best Practices

1. **One Topic Per Processing Stage**: Keep topics focused on a single purpose
2. **Descriptive Consumer Groups**: Use names like `service-function-consumer`
3. **Forward Processing Results**: Consumers should produce to next stage topic
4. **Preserve Original Data**: Add results to message rather than replacing
5. **Use Pipeline Hints**: Help consumers understand processing goals

## Adding New Processing Pipelines

To add a new processing pipeline:

1. **Define Entry Topic**: Add to `MESSAGE_TYPE_MAPPINGS` in unified API
2. **Create Consumer**: Implement with unique consumer group
3. **Define Output Topic**: Where processed results go
4. **Update Database Mappings**: Add to `topic_mappings.yml` if storing results

Example: Adding sentiment analysis
```python
# 1. Add message type
"customer_feedback": "external.feedback.raw"

# 2. Create consumer
consumer = KafkaConsumer(
    "external.feedback.raw",
    group_id="sentiment-analyzer-consumer"
)

# 3. Process and forward
result = analyze_sentiment(message)
producer.send("analysis.sentiment.results", result)
```

This architecture leverages Kafka's strengths while keeping the application layer simple and focused on data processing rather than routing logic.