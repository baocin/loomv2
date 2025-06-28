# Loom v2 Data Workflows

This document describes all data flows and processing pipelines in the Loom v2 system, mapping out how data moves from ingestion through various AI processing stages to final storage.

## Overview

The Loom v2 system processes multiple types of data through specialized AI pipelines:

1. **Audio Processing Pipeline** - Voice activity detection, speech-to-text, emotion analysis
2. **Vision Processing Pipeline** - Image analysis, OCR, face emotion detection
3. **Text Processing Pipeline** - Text embedding, summarization, analysis
4. **High-Level Reasoning Pipeline** - Context understanding and inference
5. **External Data Pipeline** - Social media, email, calendar synchronization
6. **Storage Pipeline** - All processed data stored in TimescaleDB

## Data Flow Architecture

```
                    ┌─────────────────┐
                    │  Ingestion API  │
                    │   (Port 8000)   │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │     Kafka       │
                    │  Message Bus    │
                    └─────────┬───────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼─────────┐ ┌──▼──┐ ┌─────────▼─────────┐
    │  Audio Pipeline   │ │ ... │ │  Vision Pipeline  │
    └─────────┬─────────┘ └─────┘ └─────────┬─────────┘
              │                             │
              └──────────┬──────────────────┘
                         │
               ┌─────────▼─────────┐
               │   TimescaleDB     │
               │    (Storage)      │
               └───────────────────┘
```

## 1. Audio Processing Pipeline

### Flow Overview
```
device.audio.raw
    ↓ (silero-vad-consumer)
media.audio.vad_filtered
    ↓ (parakeet-tdt-consumer)
media.text.transcribed.words + media.text.word_timestamps
    ↓ (bud-e-emotion-consumer)
analysis.audio.emotion_scores
    ↓ (kafka-to-db-consumer)
TimescaleDB
```

### Services and Topics

| Service | Consumer Group | Input Topic | Output Topic | Description |
|---------|----------------|-------------|--------------|-------------|
| Silero VAD | `silero-vad-consumer` | `device.audio.raw` | `media.audio.vad_filtered` | Detects voice activity in audio |
| Parakeet TDT | `parakeet-tdt-consumer` | `media.audio.vad_filtered` | `media.text.transcribed.words`<br>`media.text.word_timestamps` | Speech-to-text transcription |
| BUD-E Emotion | `bud-e-emotion-consumer` | `media.audio.vad_filtered` | `analysis.audio.emotion_scores` | Audio emotion detection |

### Data Schema Evolution
- **Raw Audio**: Base64 encoded chunks with metadata
- **VAD Filtered**: Audio segments with speech detected
- **Transcribed Text**: Word-level transcripts with timestamps
- **Emotion Scores**: Confidence scores for detected emotions

## 2. Vision Processing Pipeline

### Flow Overview
```
device.image.camera.raw + device.video.screen.raw
    ↓ (minicpm-vision-consumer)
media.image.vision_annotations
    ↓ (face-emotion-consumer)
analysis.image.face_emotions
    ↓ (kafka-to-db-consumer)
TimescaleDB

device.image.camera.raw
    ↓ (moondream-ocr-consumer)
media.image.analysis.moondream_results
    ↓ (kafka-to-db-consumer)
TimescaleDB
```

### Services and Topics

| Service | Consumer Group | Input Topic | Output Topic | Description |
|---------|----------------|-------------|--------------|-------------|
| MiniCPM Vision | `minicpm-vision-consumer` | `device.image.camera.raw`<br>`device.video.screen.raw` | `media.image.vision_annotations` | Image analysis and captioning |
| Face Emotion | `face-emotion-consumer` | `media.image.vision_annotations` | `analysis.image.face_emotions` | Facial emotion detection |
| Moondream OCR | `moondream-ocr-consumer` | `device.image.camera.raw`<br>`task.url.screenshot` | `media.image.analysis.moondream_results` | OCR text extraction |

## 3. Text Processing Pipeline

### Flow Overview
```
Multiple Text Sources → Embedding Services → Analysis Storage

external.email.events.raw ┐
external.twitter.liked.raw │    ↓ (text-embedder-consumer)
media.text.transcribed.words │  analysis.text.embedded.*
task.url.processed.content ┘

device.text.notes.raw ┐
media.text.transcribed.words │    ↓ (nomic-embed-consumer)
task.url.processed.content │      analysis.embeddings.nomic
task.github.processed.content │
task.document.processed.content ┘
```

### Services and Topics

| Service | Consumer Group | Input Topics | Output Topics | Description |
|---------|----------------|--------------|---------------|-------------|
| Text Embedder | `text-embedder-consumer` | `external.email.events.raw`<br>`external.twitter.liked.raw`<br>`media.text.transcribed.words`<br>`task.url.processed.content` | `analysis.text.embedded.emails`<br>`analysis.text.embedded.twitter`<br>`analysis.text.embedded.general` | Sentence transformer embeddings |
| Nomic Embed | `nomic-embed-consumer` | `device.text.notes.raw`<br>`media.text.transcribed.words`<br>`task.url.processed.content`<br>`task.github.processed.content`<br>`task.document.processed.content` | `analysis.embeddings.nomic` | Multimodal embeddings |

## 4. High-Level Reasoning Pipeline

### Flow Overview
```
Multiple Analysis Sources → Reasoning Engine → Context Understanding

media.text.word_timestamps ┐
task.url.processed.content │   ↓ (mistral-reasoning-consumer)
analysis.audio.emotion_scores │ analysis.context.reasoning_chains
analysis.image.face_emotions ┘

device.text.notes.raw ┐    ↓ (onefilellm-consumer)
media.text.transcribed.words ┘  analysis.text.summaries
```

### Services and Topics

| Service | Consumer Group | Input Topics | Output Topic | Description |
|---------|----------------|--------------|--------------|-------------|
| Mistral Reasoning | `mistral-reasoning-consumer` | `media.text.word_timestamps`<br>`task.url.processed.content`<br>`analysis.audio.emotion_scores`<br>`analysis.image.face_emotions` | `analysis.context.reasoning_chains` | High-level context understanding |
| OneFile LLM | `onefilellm-consumer` | `device.text.notes.raw`<br>`media.text.transcribed.words` | `analysis.text.summaries` | Document summarization |

## 5. External Data Pipeline

### Flow Overview
```
Scheduled Fetchers → Raw Data → Processors → Archived Content

┌─ x-likes-fetcher → external.twitter.liked.raw
│                       ↓ (twitter-ocr-processor-consumer)
│                   task.url.screenshot + media.text.ocr_extracted
│
├─ hackernews-fetcher → external.hackernews.activity.raw
├─ email-fetcher → external.email.events.raw  
└─ calendar-fetcher → external.calendar.events.raw

task.url.ingest
    ↓ (x-url-processor-consumer)
task.url.processed.twitter_archived

task.url.ingest
    ↓ (hackernews-url-processor-consumer)
task.url.processed.hackernews_archived
```

### Services and Topics

| Service | Type | Input Topic | Output Topic | Description |
|---------|------|-------------|--------------|-------------|
| Twitter Fetcher | Producer | - | `external.twitter.liked.raw` | Fetches liked tweets |
| HackerNews Fetcher | Producer | - | `external.hackernews.activity.raw` | Monitors HackerNews |
| Email Fetcher | Producer | - | `external.email.events.raw` | Syncs email events |
| Calendar Fetcher | Producer | - | `external.calendar.events.raw` | Syncs calendar events |
| Twitter URL Processor | Consumer | `task.url.ingest` | `task.url.processed.twitter_archived` | Archives Twitter content |
| HackerNews URL Processor | Consumer | `task.url.ingest` | `task.url.processed.hackernews_archived` | Archives HackerNews content |
| Twitter OCR Processor | Consumer | `external.twitter.liked.raw` | `task.url.screenshot`<br>`media.text.ocr_extracted` | OCR for Twitter images |

## 6. Storage Pipeline

### Flow Overview
```
All Topics → Database Consumer → TimescaleDB

Raw Device Data:
- device.audio.raw
- device.image.camera.raw
- device.video.screen.raw
- device.sensor.gps.raw
- device.sensor.accelerometer.raw
- device.health.heartrate.raw
- device.state.power.raw
- device.system.apps.*

Processed Media:
- media.audio.vad_filtered
- media.text.transcribed.words
- media.image.vision_annotations

Analysis Results:
- analysis.audio.emotion_scores
- analysis.image.face_emotions
- analysis.context.reasoning_chains
- analysis.text.embedded.*

External Data:
- external.twitter.liked.raw
- external.hackernews.activity.raw
- external.email.events.raw
- external.calendar.events.raw

Task Results:
- task.url.processed.*
```

### Database Consumer

| Service | Consumer Group | Input Topics | Output | Description |
|---------|----------------|--------------|--------|-------------|
| Kafka to DB Consumer | `kafka-to-db-consumer` | All topics listed above | TimescaleDB tables | Persists all data with proper schema mapping |

## Cross-Pipeline Data Flows

### Multi-Modal Fusion
The Mistral Reasoning service combines data from multiple pipelines:
- **Audio emotion** from audio pipeline
- **Face emotion** from vision pipeline  
- **Transcribed text** with timestamps
- **URL content** from external data

### Text Enhancement Chain
Text data flows through multiple enhancement stages:
1. **Raw text** → Speech transcription or direct input
2. **Embeddings** → Multiple embedding services (text-embedder, nomic-embed)
3. **Analysis** → Reasoning and summarization services
4. **Storage** → All stages stored for retrieval

### External Data Enrichment
External data is processed and cross-referenced:
1. **Twitter likes** → OCR processing → Text extraction
2. **URLs** → Content archiving → Text analysis
3. **Email/Calendar** → Event correlation → Context building

## Performance Characteristics

### Throughput Expectations
- **Audio pipeline**: ~10 MB/min raw audio → ~1000 words/min transcription
- **Vision pipeline**: ~100 images/min → ~50 annotations/min  
- **Text pipeline**: ~10,000 tokens/min → ~1000 embeddings/min
- **Reasoning pipeline**: ~100 contexts/min → ~50 insights/min

### Latency Targets
- **Real-time services** (VAD, OCR): <500ms
- **Transcription services**: <5s per minute of audio
- **Analysis services**: <10s per input
- **Reasoning services**: <30s per context window

## Error Handling and Recovery

### Circuit Breaker Patterns
- Services automatically disable when error rates exceed 50%
- Health monitoring detects unhealthy services within 30s
- Failed messages are retried up to 3 times with exponential backoff

### Data Consistency
- All messages include `trace_id` for end-to-end tracking
- Database consumer handles duplicate detection via upsert strategies
- Schema validation ensures data quality at each stage

## Monitoring and Observability

### Key Metrics
- **Consumer lag** per service
- **Processing latency** per pipeline stage
- **Error rates** and **success rates**
- **Throughput** (messages/second)

### Health Indicators
- **Service health** via /healthz endpoints
- **Kafka connectivity** status
- **Database connectivity** status
- **Model loading** status for AI services

This comprehensive workflow documentation ensures the pipeline monitor can accurately display all connections and provide meaningful insights into system health and performance.