# Overall System Architecture

**System Goal:** A unified personal informatics engine to create a richly queryable timeline of all personal events, device interactions, and digital footprints, enabling advanced AI-driven context inference and analysis.

**Core Architectural Pattern:** Event-driven microservices architecture with a strong emphasis on asynchronous processing, scalability, and modularity.

**API Gateway:** **Kong** will serve as the central API gateway. It's excellent for managing diverse API paths, routing traffic (REST, WebSockets), enforcing rate limits, handling authentication/authorization (if you add users beyond yourself), and providing observability.

**Ingestion Service:** A **FastAPI** application, leveraging **WebSockets** for real-time streaming data (audio chunks, accelerometer, screen recording keyframes) and **REST** for batch or less frequent data (periodic photos, app lifecycle events, metadata). This will be the primary entry point for all raw data from your devices.

**Message Bus:** **Apache Kafka** is the backbone for data ingestion, decoupling, and inter-service communication. Its publish-subscribe model naturally supports your need for hierarchical processing pipelines and backpressure management.

**Model Storage (Local):** All pre-trained model weights (HF, ONNX, etc.) live in a top-level `models/` directory that is **git-ignored**. Kubernetes mounts this directory read-only into every consumer pod at `/models`, ensuring a single cache is shared across services while keeping containers stateless.

**Processing:** A suite of specialized consumer microservices (Python scripts, often using Hugging Face models) responsible for specific data transformations, filtering, and analysis. Each consumer reads from one or more Kafka topics and writes to new, more processed topics.

**State Store:** **Redis** for fast, ephemeral data access. This is crucial for managing chunking logic (associating audio/video chunks with a `file_id`), buffering intermediate processing states, and potentially caching model weights or frequently accessed metadata.

**Primary Datastore:** **TimescaleDB** (PostgreSQL with time-series extensions) is the ideal choice for storing all your granular, event-driven, time-series data. Its capabilities for handling high ingest rates and complex time-series queries will be invaluable.

**Federated Querying:** **Trino** (formerly PrestoSQL) will be used to provide a unified query interface across your TimescaleDB instance and external data sources like your UseMemos SQLite database. This allows you to join and query data from disparate sources seamlessly.

**Infrastructure and DevOps:**
*   **Orchestration Platform:** **k3s** (Lightweight Kubernetes) on your devices/servers for managing containerized services.
*   **Deployment Methodology:** **GitOps** using **Flux** for managing and deploying Helm charts. This provides automated, declarative deployments, ensuring your infrastructure and application states are version-controlled and synchronized with your Git repository. Helm charts will define your Kafka topics, consumer deployments, database instances, and other services.
*   **Monitoring:** For **Kafka backpressure**, you'll need tools that can monitor consumer lag (the difference between the latest offset written to a topic and the latest offset consumed by a consumer group).
    *   **Prometheus + Grafana:** Standard solution. Kafka Exporter (or similar) can expose consumer lag metrics for Prometheus, which Grafana can visualize.
    *   **Kafka's built-in consumer group commands:** `kafka-consumer-groups.sh` can manually check lag.
    *   **Confluent Control Center (if using Confluent Platform):** Provides excellent built-in monitoring.
    *   **Third-party tools:** Datadog, Splunk, etc.

---

# Data Sources

1.  **Device Sensors (Real-time & Periodic):**
    *   **Audio:** Microphone chunks (WebSocket).
    *   **Video:** Screen recording keyframes (WebSocket), periodic webcam frames (front/rear, REST/upload), screenshots (REST/upload).
    *   **Motion:** Accelerometer (WebSocket), GPS (REST/upload), Step Count (REST/upload).
    *   **Environment:** Barometer, Device Temperature, Light Sensor, Humidity, Air Quality (REST/upload or WebSocket if high frequency).
    *   **Vitals:** Heart Rate (REST/upload or WebSocket).
    *   **Power:** Battery level, charging state (REST/upload).
    *   **Network:** Wi-Fi state (connected SSID, signal strength), nearby Bluetooth devices (REST/upload).
2.  **OS & App Events:**
    *   Android app lifecycle events (REST/upload).
    *   Notifications (REST/upload).
    *   Clipboard content (REST/upload).
    *   User input: Keyboard/mouse activity, opened applications (from desktop agents, REST/upload).
3.  **Digital Interactions:**
    *   Website analytics (e.g., browser extension, REST/upload).
4.  **External Integrations:**
    *   Scraped liked Twitter/X posts (from a dedicated script, REST/upload or directly to Kafka).
    *   Synced Email and Calendar events (from dedicated scripts, REST/upload or directly to Kafka).
    *   Arbitrary URLs (from clipboard, browser extension, etc., REST/upload).
5.  **Existing Databases:**
    *   UseMemos SQLite database (accessed via Trino).

---

# Kafka Topic Hierarchy (Hierarchical Naming Convention)

The best way to achieve hierarchical Kafka channels is through a consistent naming convention, often using dot-separated segments. This clearly indicates the data's origin and processing stage.

**Pattern:** `<category>.<source>.<datatype>.<processing_stage>`

**Raw Data Ingestion Topics:**
*   `device.audio.raw`: For raw microphone audio chunks.
*   `device.video.screen.raw`: Keyframes from screen recordings.
*   `device.image.camera.raw`: One-off periodic photos from front/rear cameras, and screenshots.
*   `device.sensor.accelerometer.raw`: Accelerometer data.
*   `device.sensor.gps.raw`: GPS coordinates.
*   `device.sensor.barometer.raw`: Barometer data.
*   `device.sensor.temperature.raw`: Device temperature.
*   `device.health.heartrate.raw`: Heart rate data.
*   `device.health.steps.raw`: Step count.
*   `device.state.power.raw`: Power states (battery, charging).
*   `device.network.wifi.raw`: Wi-Fi state.
*   `device.network.bluetooth.raw`: Nearby Bluetooth devices.
*   `os.events.app_lifecycle.raw`: Android app lifecycle events.
*   `os.events.notifications.raw`: System notifications.
*   `digital.clipboard.raw`: Clipboard content.
*   `digital.web_analytics.raw`: Website analytics.
*   `external.twitter.liked.raw`: Scraped liked Twitter/X posts.
*   `external.calendar.events.raw`: Calendar events.
*   `external.email.events.raw`: Email events.
*   `task.url.ingest`: For arbitrary URLs (Twitter links, PDFs, general web links).

**Processed Data Topics (Examples):**
*   `media.audio.vad_filtered`: Audio chunks identified as speech.
*   `media.text.transcribed.words`: Word-by-word transcripts from speech.
*   `media.image.analysis.moondream_results`: Moondream outputs (captions, gaze, objects) for snapshots.
*   `media.video.analysis.yolo_results`: Object detection/tracking from video streams.
*   `analysis.3d_reconstruction.dustr_results`: 3D environment data.
*   `analysis.inferred_context.qwen_results`: High-level context inferences (location, food, people).
*   `task.url.processed.twitter_archived`: Results from Twitter archiving.
*   `task.url.processed.pdf_extracted`: Extracted content/summary from PDFs.

---

# Processing Pipelines and Models

Each pipeline will be a consumer service reading from specific Kafka topics, performing processing, and publishing results to new Kafka topics.

1.  **Audio Processing Pipeline:**
    *   **Input:** `device.audio.raw`
    *   **1a. VAD Filtering (Silero VAD Consumer):**
        *   **Purpose:** Identify speech segments and filter out non-speech.
        *   **Output:** `media.audio.vad_filtered` (only speech chunks).
    *   **1b. Transcription (Parakeet Consumer):**
        *   **Model:** NVIDIA Parakeet TDT (https://huggingface.co/spaces/nvidia/parakeet-tdt-0.6b-v2)
        *   **Purpose:** Transcribe speech audio to text, word-by-word, including timestamps for each word.
        *   **Output:** `media.text.transcribed.words`
2.  **One-Off Image Analysis Pipeline:**
    *   **Input:** `device.image.camera.raw` (screenshots, periodic webcam photos).
    *   **Consumer (Moondream/Object Detection):**
        *   **Model:** Moondream (https://huggingface.co/moondream/moondream-2b-2025-04-14-4bit) for captions, gaze, common objects.
        *   **Purpose:** Extract high-level visual context.
        *   **Output:** `media.image.analysis.moondream_results`
3.  **Streaming Video Analysis Pipeline:**
    *   **Input:** `device.video.screen.raw` (keyframes from screen recordings).
    *   **Consumer (YOLO/Optical Flow):**
        *   **Models:** Ultralytics YOLO (https://github.com/ultralytics/ultralytics) for object detection, Optical Flow for motion analysis.
        *   **Purpose:** Analyze motion and objects within continuous video streams.
        *   **Output:** `media.video.analysis.yolo_results`
4.  **3D Reconstruction Pipeline:**
    *   **Input:** `device.image.camera.raw` (specifically paired front and rear camera photos).
    *   **Consumer (DUST-R):**
        *   **Model:** dust3r (https://github.com/naver/dust3r - or similar models for 3D reconstruction like DUST-R or Instant-NGP variants).
        *   **Redis Usage:** This consumer will likely use Redis to temporarily store and correlate incoming front/rear frames by timestamp and device ID until a complete pair is available for processing.
        *   **Purpose:** Reconstruct 3D environments from simultaneous camera views.
        *   **Output:** `analysis.3d_reconstruction.dustr_results`
5.  **Speculative Context Inference Pipeline:**
    *   **Input:** Samples from `device.audio.raw`, `device.image.camera.raw`.
    *   **Consumer (Qwen2.5-Omni-7B Sampler):**
        *   **Model:** Qwen2.5-Omni-7B (https://huggingface.co/Qwen/Qwen2.5-Omni-7B)
        *   **Purpose:** Run on *raw, unprocessed* samples to infer high-level context (e.g., guess location from background audio, identify if a photo is of food/people before specific object detection). This adds a valuable "sense-making" layer early in the process.
        *   **Output:** `analysis.inferred_context.qwen_results`
6.  **Generic URL Task Processing Pipeline:**
    *   **Input:** `task.url.ingest`
    *   **Consumer (Twitter Archiver):**
        *   **Purpose:** Scrape and archive details of liked Twitter/X posts.
        *   **Output:** `task.url.processed.twitter_archived`
    *   **Consumer (PDF Processor - onefilellm):**
        *   **Model:** onefilellm (https://github.com/jimmc414/onefilellm)
        *   **Purpose:** Extract text, summarize, or analyze content from PDF URLs (including base64 encoded).
        *   **Output:** `task.url.processed.pdf_extracted`
7.  **Unified Persistence Consumer(s):**
    *   **Input:** All final processed topics (e.g., `media.text.transcribed.words`, `media.image.analysis.moondream_results`, `analysis.inferred_context.qwen_results`, etc.) and some raw topics that don't need complex processing (e.g., `device.sensor.gps.raw`, `device.health.heartrate.raw`).
    *   **Purpose:** Ingest data into **TimescaleDB**. Design your TimescaleDB schema to be flexible and highly granular, leveraging hypertable capabilities for efficient time-series storage and querying. Each data type will likely have its own table (e.g., `transcripts`, `image_analyses`, `gps_data`, `device_states`).

---

# Data Persistence and Querying

*   **Redis:** For transient data like `file_id` association with audio/video chunks, and possibly buffering for 3D reconstruction. It acts as a fast cache and temporary state store.
*   **TimescaleDB:** The ultimate destination for all your structured time-series event data. Its ability to handle vast amounts of chronologically ordered data and perform complex queries efficiently is perfect for your "timeline UI."
*   **Trino:**
    *   **Purpose:** Enable federated queries. You can write SQL queries in Trino that join data from your TimescaleDB (e.g., `device_states`) with data from your UseMemos SQLite database (e.g., `notes`).
    *   **Integration:** Trino connects to TimescaleDB as a PostgreSQL connector and to SQLite files using its dedicated connector (though you'll need to expose the SQLite file to Trino, perhaps via a shared volume or a small service that proxies access to it).

---

# Data Flow Diagram (Mermaid.js)

```mermaid
graph TD
    %% Class Definitions for Styling
    classDef kafka_topic fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#333
    classDef consumer_service fill:#e0f7fa,stroke:#00796b,stroke-width:1px
    classDef storage_service fill:#ede7f6,stroke:#512da8,stroke-width:2px
    classDef ingestion_service fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px
    classDef source_group fill:#fffde7,stroke:#f57f17,stroke-width:1px
    classDef query_engine fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef api_gateway fill:#f3e5f5,stroke:#9c27b0,stroke-width:1px

    %% Sources Subgraph
    subgraph Data_Sources
        direction LR
        PERSONAL_DEVICES["Personal Devices<br>(Phone, Laptop, Edge)"]
        EXTERNAL_SERVICES["External Services<br>(Email, Calendar, Twitter)"]
        EXISTING_DBS["Existing Local DBs<br>(UseMemos SQLite)"]
    end
    class PERSONAL_DEVICES,EXTERNAL_SERVICES,EXISTING_DBS source_group

    %% Ingestion Layer
    subgraph Ingestion_Layer
        KONG["API Gateway<br>Kong"]
        FASTAPI["Ingestion API<br>FastAPI (REST & WebSockets)"]
    end
    class KONG api_gateway
    class FASTAPI ingestion_service

    %% Kafka Topics Hub
    subgraph Kafka_Topics_The_Central_Message_Bus
        direction TB

        subgraph Raw_Data_Topics
            direction LR
            T_AUDIO_RAW["device.audio.raw"]:::kafka_topic
            T_VIDEO_SCREEN_RAW["device.video.screen.raw"]:::kafka_topic
            T_IMAGE_CAMERA_RAW["device.image.camera.raw"]:::kafka_topic
            T_SENSOR_ACCEL_RAW["device.sensor.accelerometer.raw"]:::kafka_topic
            T_SENSOR_GPS_RAW["device.sensor.gps.raw"]:::kafka_topic
            T_DEVICE_STATE_RAW["device.state.power.raw<br>Temp, Barometer"]:::kafka_topic
            T_OS_EVENTS_RAW["os.events.app_lifecycle.raw<br>Notifications"]:::kafka_topic
            T_NETWORK_EVENTS_RAW["device.network.wifi.raw<br>Bluetooth"]:::kafka_topic
            T_HEALTH_VITALS_RAW["device.health.heartrate.raw<br>Steps"]:::kafka_topic
            T_DIGITAL_INPUTS_RAW["digital.clipboard.raw<br>Web_Analytics"]:::kafka_topic
            T_EXTERNAL_SYNC_RAW["external.twitter.liked.raw<br>Email, Calendar"]:::kafka_topic
            T_TASK_URL_INGEST["task.url.ingest"]:::kafka_topic
        end

        subgraph Processed_Data_Topics
            direction LR
            T_AUDIO_VAD["media.audio.vad_filtered"]:::kafka_topic
            T_TEXT_TRANSCRIBED["media.text.transcribed.words"]:::kafka_topic
            T_IMAGE_ANALYSIS_MOONDREAM["media.image.analysis.moondream_results"]:::kafka_topic
            T_VIDEO_ANALYSIS_YOLO["media.video.analysis.yolo_results"]:::kafka_topic
            T_3D_RECONSTRUCTION["analysis.3d_reconstruction.dustr_results"]:::kafka_topic
            T_INFERRED_CONTEXT_QWEN["analysis.inferred_context.qwen_results"]:::kafka_topic
            T_TASK_URL_PROCESSED["task.url.processed.twitter_archived<br>pdf_extracted"]:::kafka_topic
        end
    end

    %% Processing Services
    subgraph Processing_Services
        VAD_CONS["VAD Consumer<br>(Silero VAD)"]:::consumer_service
        PARAKEET_CONS["Transcription Consumer<br>(NVIDIA Parakeet)"]:::consumer_service
        MOONDREAM_CONS["Image Analysis Consumer<br>(Moondream)"]:::consumer_service
        DUSTR_CONS["3D Reconstruction Consumer<br>(dust3r)"]:::consumer_service
        YOLO_CONS["Video Analysis Consumer<br>(Ultralytics YOLO<br>+ Optical Flow)"]:::consumer_service
        QWEN_OMNI_CONS["Omni-Modal Speculative Consumer<br>(Qwen2.5-Omni-7B)"]:::consumer_service
        URL_TASK_CONS["URL Task Consumer<br>(Twitter Archiver, onefilellm)"]:::consumer_service
        PERSISTENCE_CONS["Unified Persistence Consumer"]:::consumer_service
    end

    %% Storage & Querying Layer
    subgraph Storage_and_Querying_Layer
        REDIS_STORE["State Store<br>(Redis)"]:::storage_service
        TIMESCALEDB_STORE["Primary Datastore<br>(TimescaleDB)"]:::storage_service
        MEMOS_SQLITE_DB["UseMemos DB<br>(SQLite File)"]:::storage_service
        TRINO_ENGINE["Federated Query Engine<br>(Trino)"]:::query_engine
    end

    %% Data Flows
    PERSONAL_DEVICES --> KONG
    EXTERNAL_SERVICES --> KONG
    KONG --> FASTAPI

    FASTAPI --Streams & Uploads--> T_AUDIO_RAW
    FASTAPI --> T_VIDEO_SCREEN_RAW
    FASTAPI --> T_IMAGE_CAMERA_RAW
    FASTAPI --> T_SENSOR_ACCEL_RAW
    FASTAPI --> T_SENSOR_GPS_RAW
    FASTAPI --> T_DEVICE_STATE_RAW
    FASTAPI --> T_OS_EVENTS_RAW
    FASTAPI --> T_NETWORK_EVENTS_RAW
    FASTAPI --> T_HEALTH_VITALS_RAW
    FASTAPI --> T_DIGITAL_INPUTS_RAW
    FASTAPI --> T_EXTERNAL_SYNC_RAW
    FASTAPI --> T_TASK_URL_INGEST

    %% Audio Pipeline
    T_AUDIO_RAW --> VAD_CONS
    VAD_CONS --> T_AUDIO_VAD
    T_AUDIO_VAD --> PARAKEET_CONS
    PARAKEET_CONS --> T_TEXT_TRANSCRIBED

    %% Image & 3D Pipelines
    T_IMAGE_CAMERA_RAW --> MOONDREAM_CONS
    MOONDREAM_CONS --> T_IMAGE_ANALYSIS_MOONDREAM
    T_IMAGE_CAMERA_RAW --(Paired Frames)--> DUSTR_CONS
    DUSTR_CONS -.-> REDIS_STORE
    DUSTR_CONS --> T_3D_RECONSTRUCTION

    %% Video Pipeline
    T_VIDEO_SCREEN_RAW --> YOLO_CONS
    YOLO_CONS --> T_VIDEO_ANALYSIS_YOLO

    %% Speculative Qwen
    T_AUDIO_RAW --(Sample)--> QWEN_OMNI_CONS
    T_IMAGE_CAMERA_RAW --(Sample)--> QWEN_OMNI_CONS
    QWEN_OMNI_CONS --> T_INFERRED_CONTEXT_QWEN

    %% URL Task Processing
    T_TASK_URL_INGEST --> URL_TASK_CONS
    URL_TASK_CONS --> T_TASK_URL_PROCESSED

    %% Persistence
    T_TEXT_TRANSCRIBED --> PERSISTENCE_CONS
    T_IMAGE_ANALYSIS_MOONDREAM --> PERSISTENCE_CONS
    T_VIDEO_ANALYSIS_YOLO --> PERSISTENCE_CONS
    T_3D_RECONSTRUCTION --> PERSISTENCE_CONS
    T_INFERRED_CONTEXT_QWEN --> PERSISTENCE_CONS
    T_TASK_URL_PROCESSED --> PERSISTENCE_CONS
    T_SENSOR_GPS_RAW --> PERSISTENCE_CONS %% GPS is simple, can go direct
    T_SENSOR_ACCEL_RAW --> PERSISTENCE_CONS
    T_DEVICE_STATE_RAW --> PERSISTENCE_CONS
    T_OS_EVENTS_RAW --> PERSISTENCE_CONS
    T_NETWORK_EVENTS_RAW --> PERSISTENCE_CONS
    T_HEALTH_VITALS_RAW --> PERSISTENCE_CONS
    T_DIGITAL_INPUTS_RAW --> PERSISTENCE_CONS
    T_EXTERNAL_SYNC_RAW --> PERSISTENCE_CONS

    PERSISTENCE_CONS --> TIMESCALEDB_STORE

    %% Querying
    TRINO_ENGINE --> TIMESCALEDB_STORE
    TRINO_ENGINE --> MEMOS_SQLITE_DB
    EXISTING_DBS --> MEMOS_SQLITE_DB %% Memos is a file, Trino connects to it
```

---