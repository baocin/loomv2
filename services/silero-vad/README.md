# Silero VAD Service

Voice Activity Detection service using Silero VAD model to filter audio streams.

## Features

- Consumes raw audio from Kafka topics
- Detects voice activity using Silero VAD
- Filters out non-speech audio segments
- Publishes voice-only audio to output topics

## Configuration

See the service's environment variables in docker-compose.local.yml for configuration options.
