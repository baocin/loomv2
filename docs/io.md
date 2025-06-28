# Loom v2 Input/Output Data Formats

This document describes the data formats for all Kafka consumers and producers in the Loom v2 system, including the new SMS/MMS endpoints and embedding flows.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Audio Processing Pipeline](#audio-processing-pipeline)
3. [Image/Video Processing Pipeline](#imagevideo-processing-pipeline)
4. [Text Processing Pipeline](#text-processing-pipeline)
5. [URL Processing Pipeline](#url-processing-pipeline)
6. [SMS/MMS Processing Pipeline (NEW)](#smsmms-processing-pipeline-new)
7. [Embedding Pipeline](#embedding-pipeline)
8. [Database Persistence](#database-persistence)
9. [Common Data Types](#common-data-types)

---

## Architecture Overview

The Loom v2 system follows an event-driven microservices architecture with the following key patterns:

### Data Flow Patterns

1. **Raw Data Ingestion** → **AI Processing** → **Analysis Results** → **Embeddings** → **Database Storage**

2. **Service Categories**:
   - **Ingestion Services**: REST/WebSocket endpoints that receive data and publish to Kafka
   - **Processing Services**: Consume raw data, apply AI models, produce enriched data
   - **Analysis Services**: Higher-level reasoning and cross-modal analysis
   - **Storage Services**: Generic database persistence via configurable mappings

3. **Topic Naming Convention**: `<category>.<source>.<datatype>.<stage>`
   - Example: `device.audio.raw`, `media.audio.vad_filtered`, `analysis.audio.emotion_results`

4. **Key Design Principles**:
   - Each AI model runs in its own microservice for independent scaling
   - All messages include `device_id`, `recorded_at`, and `schema_version`
   - Embeddings are generated for all text and image data for semantic search
   - The kafka-to-db-consumer provides generic persistence without code duplication

---

## Audio Processing Pipeline

### 1. Silero VAD (Voice Activity Detection)

**Service**: `silero-vad`

**Input Topic**: `device.audio.raw`
```json
{
  "device_id": "microphone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "data": "base64_encoded_audio_chunk",
  "format": "pcm",
  "sample_rate": 16000,
  "channels": 1,
  "duration_ms": 1000,
  "metadata": {
    "source": "mobile_app",
    "location": "office"
  },
  "schema_version": "v1"
}
```

**Output Topic**: `media.audio.vad_filtered`
```json
{
  "device_id": "microphone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "segment_start_ms": 250,
  "segment_end_ms": 950,
  "data": "base64_encoded_speech_segment",
  "format": "pcm",
  "sample_rate": 16000,
  "confidence": 0.95,
  "energy_level": 0.72,
  "processing_time_ms": 15,
  "model_version": "silero-vad-v4",
  "schema_version": "v1"
}
```

### 2. Parakeet TDT (Speech-to-Text)

**Service**: `parakeet-tdt`

**Input Topic**: `media.audio.vad_filtered`

**Output Topic**: `media.text.transcribed.words`
```json
{
  "device_id": "microphone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "segment_id": "seg_123abc",
  "words": [
    {
      "text": "Hello",
      "start_time": 0.25,
      "end_time": 0.45,
      "confidence": 0.98
    },
    {
      "text": "world",
      "start_time": 0.50,
      "end_time": 0.75,
      "confidence": 0.97
    }
  ],
  "full_text": "Hello world",
  "language": "en",
  "speaker_id": null,
  "processing_time_ms": 145,
  "model_version": "parakeet-tdt-1.1b",
  "schema_version": "v1"
}
```

### 3. BUD-E Emotion (Speech Emotion Recognition)

**Service**: `bud-e-emotion`

**Input Topic**: `media.audio.vad_filtered`

**Output Topic**: `analysis.audio.emotion_results`
```json
{
  "device_id": "microphone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "segment_id": "seg_123abc",
  "emotions": {
    "happy": 0.65,
    "sad": 0.10,
    "angry": 0.05,
    "neutral": 0.15,
    "surprised": 0.05
  },
  "dominant_emotion": "happy",
  "arousal": 0.7,
  "valence": 0.8,
  "confidence": 0.89,
  "processing_time_ms": 78,
  "model_version": "bud-e-whisper",
  "schema_version": "v1"
}
```

---

## Image/Video Processing Pipeline

### 4. MiniCPM Vision

**Service**: `minicpm-vision`

**Input Topics**: 
- `device.image.camera.raw`
- `device.video.screen.raw`

**Input Format**:
```json
{
  "device_id": "camera-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "data": "base64_encoded_image",
  "format": "jpeg",
  "width": 1920,
  "height": 1080,
  "metadata": {
    "camera": "front",
    "flash": false,
    "location": {
      "lat": 37.7749,
      "lon": -122.4194
    }
  },
  "schema_version": "v1"
}
```

**Output Topic**: `media.image.analysis.minicpm_results`
```json
{
  "device_id": "camera-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "scene_description": "An office desk with a laptop, coffee cup, and notebook",
  "scene_categories": ["indoor", "workplace", "technology"],
  "detected_objects": [
    {
      "label": "laptop",
      "confidence": 0.92,
      "bbox": [100, 200, 500, 400]
    },
    {
      "label": "coffee_cup",
      "confidence": 0.87,
      "bbox": [600, 300, 700, 450]
    }
  ],
  "ocr_results": [
    {
      "text": "Meeting Notes",
      "confidence": 0.95,
      "bbox": [800, 100, 1000, 150]
    }
  ],
  "full_text": "Meeting Notes",
  "dominant_colors": ["#FFFFFF", "#333333", "#8B4513"],
  "image_quality": {
    "brightness": 0.72,
    "contrast": 0.65,
    "sharpness": 0.88
  },
  "processing_time_ms": 234,
  "model_version": "MiniCPM-Llama3-V-2.5",
  "schema_version": "v1"
}
```

### 5. Moondream Station (Alternative Vision)

**Service**: `moondream-station`

**Input Topics**: Same as MiniCPM Vision

**Output Topic**: `media.image.analysis.moondream_results`
```json
{
  "device_id": "camera-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "caption": "A modern office workspace with electronic devices",
  "query_response": "There are 2 people in the background",
  "detected_objects": [
    {
      "label": "person",
      "confidence": 0.89,
      "bbox": [1200, 100, 1400, 600],
      "attributes": {
        "pose": "sitting",
        "activity": "working"
      }
    }
  ],
  "ocr_blocks": [
    {
      "text": "Deadline: Friday",
      "confidence": 0.93,
      "bbox": [850, 200, 1050, 250],
      "language": "en"
    }
  ],
  "scene_type": "office",
  "scene_attributes": ["professional", "modern", "organized"],
  "image_quality_score": 0.85,
  "processing_time_ms": 156,
  "model_version": "moondream-latest",
  "schema_version": "v1"
}
```

### 6. Face Emotion Recognition

**Service**: `face-emotion`

**Input Topic**: `media.image.analysis.minicpm_results` (requires face detection)

**Output Topic**: `analysis.image.face_emotions`
```json
{
  "device_id": "camera-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_analysis_id": "minicpm_result_123",
  "faces": [
    {
      "face_id": "face_001",
      "bbox": [300, 150, 450, 350],
      "emotions": {
        "happy": 0.75,
        "sad": 0.05,
        "angry": 0.02,
        "surprised": 0.10,
        "neutral": 0.08
      },
      "dominant_emotion": "happy",
      "age_estimate": "25-35",
      "gender_estimate": "female",
      "confidence": 0.91
    }
  ],
  "num_faces": 1,
  "processing_time_ms": 89,
  "model_version": "empathic-insight-face",
  "schema_version": "v1"
}
```

---

## Text Processing Pipeline

### 7. Text Embedder

**Service**: `text-embedder`

**Input Topics**:
- `external.email.events.raw`
- `external.twitter.liked.raw`
- `media.text.transcribed.words`
- `device.sms.received` (NEW)
- `device.mms.received` (NEW)

**Input Format (Email)**:
```json
{
  "device_id": "email-fetcher-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "email_id": "msg_123abc",
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "subject": "Project Update",
  "body_text": "Here's the latest update on the project...",
  "body_html": "<html>...</html>",
  "received_at": "2024-06-27T11:55:00Z",
  "metadata": {
    "folder": "inbox",
    "labels": ["work", "important"],
    "has_attachments": true
  },
  "schema_version": "v1"
}
```

**Output Topic**: `analysis.text.embedded.emails`
```json
{
  "device_id": "email-fetcher-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_id": "msg_123abc",
  "source_type": "email",
  "text": "Subject: Project Update. Here's the latest update...",
  "embedding": [0.123, -0.456, 0.789, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-text-v1.5",
  "metadata": {
    "from": "sender@example.com",
    "subject": "Project Update",
    "word_count": 245,
    "language": "en"
  },
  "processing_time_ms": 34,
  "schema_version": "v1"
}
```

### 8. Gemma 3N Processor (High-Level Reasoning)

**Service**: `gemma3n-processor`

**Input Topics**:
- `media.text.transcribed.words`
- `device.image.camera.raw`
- `device.video.screen.raw`
- `media.audio.vad_filtered`

**Output Topic**: `analysis.multimodal.gemma3n_results`
```json
{
  "device_id": "analysis-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "analysis_type": "multimodal_context",
  "primary_result": "User is in a work meeting discussing Q3 targets",
  "text_analysis": {
    "type": "text",
    "content": "Conversation focused on revenue goals and team expansion",
    "confidence": 0.87,
    "metadata": {
      "topics": ["business", "planning", "finance"],
      "sentiment": "positive"
    }
  },
  "image_analysis": {
    "type": "image",
    "content": "Conference room with presentation screen showing charts",
    "confidence": 0.92,
    "metadata": {
      "scene": "meeting_room",
      "participants": 5
    }
  },
  "multimodal_insights": [
    "Active business meeting in progress",
    "Positive team dynamics observed",
    "Focus on growth metrics"
  ],
  "entities": [
    {"type": "topic", "value": "Q3 targets", "confidence": 0.89},
    {"type": "activity", "value": "business_meeting", "confidence": 0.94}
  ],
  "processing_time_ms": 1234,
  "model_version": "gemma3n:e4b",
  "schema_version": "v1"
}
```

---

## URL Processing Pipeline

### 9. X/Twitter URL Processor

**Service**: `x-url-processor`

**Input Topic**: `task.url.ingest`
```json
{
  "device_id": "scheduler-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "url": "https://x.com/user/status/123456789",
  "source": "liked_tweets",
  "metadata": {
    "user_id": "twitter_user_123",
    "action": "archive"
  },
  "schema_version": "v1"
}
```

**Output Topics**:
1. `task.url.processed.twitter_archived`
```json
{
  "device_id": "x-processor-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "url": "https://x.com/user/status/123456789",
  "content": {
    "text": "Great insights on AI development! 🚀",
    "author": "@techuser",
    "timestamp": "2024-06-27T10:30:00Z",
    "likes": 1523,
    "retweets": 234,
    "replies": 45
  },
  "screenshot_path": "screenshots/twitter/123456789.png",
  "extracted_urls": [
    "https://example.com/ai-article"
  ],
  "processing_time_ms": 567,
  "schema_version": "v1"
}
```

2. `external.twitter.images.raw` (for OCR)
```json
{
  "device_id": "x-processor-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "data": "base64_encoded_screenshot",
  "format": "png",
  "source_url": "https://x.com/user/status/123456789",
  "metadata": {
    "type": "tweet_screenshot",
    "author": "@techuser"
  },
  "schema_version": "v1"
}
```

### 10. Twitter OCR Processor

**Service**: `twitter-ocr-processor`

**Input Topic**: `external.twitter.images.raw`

**Output Topic**: `media.text.extracted.twitter`

**Processing**: Uses Moondream OCR to extract text from Twitter screenshots

```json
{
  "device_id": "twitter-ocr-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_url": "https://x.com/user/status/123456789",
  "extracted_text": "Great insights on AI development! 🚀 The future is here.",
  "ocr_confidence": 0.94,
  "metadata": {
    "author": "@techuser",
    "contains_emoji": true,
    "language": "en"
  },
  "processing_time_ms": 156,
  "model_version": "moondream-ocr-v1",
  "schema_version": "v1"
}
```

### 11. HackerNews URL Processor

**Service**: `hackernews-url-processor`

**Input Topic**: `task.url.ingest` (filters for HN URLs)

**Output Topic**: `task.url.processed.hackernews_archived`
```json
{
  "device_id": "hn-processor-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "url": "https://news.ycombinator.com/item?id=123456",
  "content": {
    "title": "Show HN: My new AI project",
    "text": "I built this tool that helps with...",
    "author": "hnuser123",
    "points": 234,
    "comments": 89,
    "timestamp": "2024-06-27T09:00:00Z"
  },
  "comments_sample": [
    {
      "author": "commenter1",
      "text": "This is really interesting!",
      "points": 45
    }
  ],
  "extracted_urls": [
    "https://github.com/user/project"
  ],
  "processing_time_ms": 234,
  "schema_version": "v1"
}
```

### 12. Nomic Embed (Universal Embedding Service)

**Service**: `nomic-embed`

**Input Topics**: Multiple text and image topics
- `device.text.notes.raw`
- `media.text.transcribed.words`
- `task.url.processed.content`
- `device.image.camera.raw`
- `device.video.screen.raw`

**Output Topics**: 
- `embeddings.text.nomic` (for text embeddings)
- `embeddings.image.nomic` (for image embeddings)

**Text Embedding Output Format**:
```json
{
  "device_id": "nomic-embedder-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_topic": "media.text.transcribed.words",
  "source_id": "transcript_123",
  "text": "The embedded text content",
  "embedding": [0.123, -0.456, 0.789, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-text-v1.5",
  "metadata": {
    "text_length": 150,
    "token_count": 42,
    "language": "en"
  },
  "processing_time_ms": 23,
  "schema_version": "v1"
}
```

**Image Embedding Output Format**:
```json
{
  "device_id": "nomic-embedder-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_topic": "device.image.camera.raw",
  "source_id": "img_456",
  "embedding": [0.234, -0.567, 0.890, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-vision-v1.5",
  "metadata": {
    "image_dimensions": [1920, 1080],
    "format": "jpeg"
  },
  "processing_time_ms": 45,
  "schema_version": "v1"
}
```

---

## SMS/MMS Processing Pipeline (NEW)

### 13. SMS/MMS Ingestion

**Endpoint**: `POST /sms/received` and `POST /mms/received`

**Input Format (SMS)**:
```json
{
  "device_id": "phone-001",
  "phone_number": "+1234567890",
  "from": "+0987654321",
  "to": "+1234567890",
  "message": "Hey, are we still meeting at 3pm?",
  "received_at": "2024-06-27T12:00:00.123Z",
  "carrier": "verizon",
  "metadata": {
    "sim_id": "sim_1",
    "network_type": "5G",
    "signal_strength": -67
  }
}
```

**Output Topic**: `device.sms.received`
```json
{
  "device_id": "phone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "message_id": "sms_123abc",
  "from": "+0987654321",
  "to": "+1234567890",
  "content": "Hey, are we still meeting at 3pm?",
  "direction": "inbound",
  "carrier": "verizon",
  "metadata": {
    "sim_id": "sim_1",
    "network_type": "5G",
    "signal_strength": -67,
    "contact_name": "John Doe"
  },
  "schema_version": "v1"
}
```

**Input Format (MMS)**:
```json
{
  "device_id": "phone-001",
  "phone_number": "+1234567890",
  "from": "+0987654321",
  "to": "+1234567890",
  "message": "Check out this photo!",
  "media": [
    {
      "type": "image/jpeg",
      "data": "base64_encoded_image",
      "filename": "photo.jpg"
    }
  ],
  "received_at": "2024-06-27T12:00:00.123Z",
  "carrier": "att",
  "metadata": {
    "sim_id": "sim_1",
    "data_size_bytes": 524288
  }
}
```

**Output Topic**: `device.mms.received`
```json
{
  "device_id": "phone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "message_id": "mms_456def",
  "from": "+0987654321",
  "to": "+1234567890",
  "content": "Check out this photo!",
  "media": [
    {
      "media_id": "media_789ghi",
      "type": "image/jpeg",
      "data": "base64_encoded_image",
      "filename": "photo.jpg",
      "size_bytes": 524288
    }
  ],
  "direction": "inbound",
  "carrier": "att",
  "metadata": {
    "sim_id": "sim_1",
    "contact_name": "Jane Smith",
    "total_media_size": 524288
  },
  "schema_version": "v1"
}
```

### 14. SMS/MMS Embedding Flow

**Consumer**: `text-embedder` (enhanced)

**Additional Input Topics**:
- `device.sms.received`
- `device.mms.received`

**Output Topic**: `analysis.text.embedded.sms`
```json
{
  "device_id": "phone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_id": "sms_123abc",
  "source_type": "sms",
  "text": "Hey, are we still meeting at 3pm?",
  "embedding": [0.234, -0.567, 0.890, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-text-v1.5",
  "metadata": {
    "from": "+0987654321",
    "contact_name": "John Doe",
    "word_count": 8,
    "language": "en",
    "contains_time_reference": true,
    "sentiment": "neutral"
  },
  "processing_time_ms": 23,
  "schema_version": "v1"
}
```

**Output Topic**: `analysis.text.embedded.mms`
```json
{
  "device_id": "phone-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_id": "mms_456def",
  "source_type": "mms",
  "text": "Check out this photo! [Image: photo.jpg]",
  "embedding": [0.345, -0.678, 0.901, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-text-v1.5",
  "media_embeddings": [
    {
      "media_id": "media_789ghi",
      "type": "image",
      "embedding": [0.456, -0.789, 0.012, ...], // Image embedding
      "model": "clip-vit-base-patch32"
    }
  ],
  "metadata": {
    "from": "+0987654321",
    "contact_name": "Jane Smith",
    "has_media": true,
    "media_count": 1,
    "total_size_bytes": 524288
  },
  "processing_time_ms": 145,
  "schema_version": "v1"
}
```

---

## Embedding Pipeline

### 15. Embedding Service Details

**Service**: `nomic-embed`

**Input Topics**:
- `media.text.transcribed.words`
- `analysis.text.extracted.*`
- Any text-containing topics

**Output Topic**: `analysis.embeddings.generated`
```json
{
  "device_id": "embedder-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "source_topic": "media.text.transcribed.words",
  "source_id": "transcript_123",
  "text": "The quick brown fox jumps over the lazy dog",
  "embedding": [0.123, -0.456, 0.789, ...], // 768-dimensional vector
  "embedding_model": "nomic-embed-text-v1.5",
  "metadata": {
    "text_length": 44,
    "token_count": 9,
    "language": "en"
  },
  "processing_time_ms": 12,
  "schema_version": "v1"
}
```

### 16. Embedding Storage Flow

**Consumer**: `kafka-to-db-consumer` (enhanced)

**Database Table**: `embeddings`
```sql
CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    source_topic VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,  -- pgvector type
    embedding_model VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for similarity search
    INDEX idx_embedding_vector ON embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100),
    
    -- Indexes for filtering
    INDEX idx_device_recorded ON embeddings (device_id, recorded_at DESC),
    INDEX idx_source ON embeddings (source_topic, source_id),
    INDEX idx_metadata ON embeddings USING gin (metadata)
);
```

### 17. Alternative VAD Processor

**Service**: `vad-processor` (Alternative implementation with DB persistence)

**Input Topic**: `device.audio.raw`

**Output Topic**: `media.audio.vad_filtered`

**Additional Feature**: Direct database write to `media_audio_vad_filtered` table

**Database Schema**:
```sql
CREATE TABLE media_audio_vad_filtered (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    segment_start_ms INTEGER,
    segment_end_ms INTEGER,
    confidence REAL,
    energy_level REAL,
    audio_data BYTEA,
    format VARCHAR(50),
    sample_rate INTEGER,
    channels INTEGER,
    duration_ms INTEGER,
    model_version VARCHAR(100),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_vad_device_time ON media_audio_vad_filtered (device_id, timestamp DESC),
    INDEX idx_vad_trace ON media_audio_vad_filtered (trace_id)
);
```

---

## Database Persistence

### 18. Generic Kafka-to-DB Consumer

**Service**: `kafka-to-db-consumer`

**Configuration**: `config/topic_mappings.yml`
```yaml
topic_mappings:
  # Audio pipeline
  media.audio.vad_filtered:
    table: audio_segments
    columns:
      device_id: device_id
      recorded_at: recorded_at
      segment_start_ms: segment_start_ms
      segment_end_ms: segment_end_ms
      confidence: confidence
      energy_level: energy_level
      
  media.text.transcribed.words:
    table: transcriptions
    columns:
      device_id: device_id
      recorded_at: recorded_at
      words: words
      full_text: full_text
      language: language
      
  # SMS/MMS tables (NEW)
  device.sms.received:
    table: sms_messages
    columns:
      device_id: device_id
      recorded_at: recorded_at
      message_id: message_id
      from_number: from
      to_number: to
      content: content
      direction: direction
      carrier: carrier
      metadata: metadata
      
  device.mms.received:
    table: mms_messages
    columns:
      device_id: device_id
      recorded_at: recorded_at
      message_id: message_id
      from_number: from
      to_number: to
      content: content
      media: media
      direction: direction
      carrier: carrier
      metadata: metadata
      
  # Embeddings
  analysis.text.embedded.*:
    table: embeddings
    columns:
      device_id: device_id
      recorded_at: recorded_at
      source_id: source_id
      source_type: source_type
      text: text
      embedding: embedding
      embedding_model: embedding_model
      metadata: metadata
```

---

## Common Data Types

### Base Message Structure
All Kafka messages follow this base structure:
```json
{
  "device_id": "string - unique device identifier",
  "recorded_at": "ISO 8601 timestamp with milliseconds",
  "schema_version": "string - message schema version (e.g., 'v1')",
  // ... additional fields specific to message type
}
```

### Embedding Vectors
- Standard dimension: 768 (for Nomic Embed and similar models)
- Format: Array of float32 values
- Range: Typically normalized to [-1, 1]
- Storage: PostgreSQL `vector` type with pgvector extension

### Image Data
- Format: Base64 encoded string
- Supported formats: JPEG, PNG, WebP
- Maximum size: Configurable per service (default 10MB)
- Metadata includes: width, height, format, camera info

### Audio Data
- Format: Base64 encoded string
- Default format: PCM 16-bit mono
- Sample rate: 16000 Hz (standard for speech)
- Chunk duration: 1000ms (configurable)

### Timestamps
- All timestamps use ISO 8601 format with timezone
- Millisecond precision required
- UTC timezone preferred
- Example: `2024-06-27T12:00:00.123Z`

---

## Error Handling

All services implement standardized error messages:

```json
{
  "device_id": "service-001",
  "recorded_at": "2024-06-27T12:00:00.123Z",
  "error_type": "processing_failed",
  "error_message": "Failed to process image: invalid format",
  "original_topic": "device.image.camera.raw",
  "original_message_id": "msg_123",
  "retry_count": 2,
  "max_retries": 3,
  "schema_version": "v1"
}
```

Error topics follow the pattern: `{original_topic}.error`

---

## Notes on SMS/MMS Implementation

1. **Security**: All phone numbers should be hashed or encrypted before storage
2. **Privacy**: Implement data retention policies for SMS/MMS content
3. **Compliance**: Follow carrier and regulatory requirements for message storage
4. **Rate Limiting**: Implement rate limiting for SMS/MMS ingestion endpoints
5. **Deduplication**: Use message_id to prevent duplicate processing
6. **Media Storage**: Consider external object storage (S3) for MMS media files
7. **Contact Resolution**: Integrate with device contacts for name resolution
8. **Threading**: Implement conversation threading based on phone numbers

---

This document serves as the authoritative reference for all data formats in the Loom v2 system. Updates should be reflected here before implementation.