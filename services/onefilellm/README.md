# OneFileLLM Service

This service processes GitHub repositories and documents using [OneFileLLM](https://github.com/raphaelsty/onefilellm) to aggregate and extract content for LLM context windows.

## Overview

The OneFileLLM service consumes tasks from Kafka topics and processes:

1. **GitHub Repositories**: Clones repositories and aggregates source code files into a single context-optimized format
2. **Documents**: Extracts text content from various document formats (PDF, DOCX, HTML, etc.)

All processed content is stored in the database and published back to Kafka for further processing by other services.

## Features

### GitHub Processing
- Clone repositories from GitHub URLs
- Filter files by include/exclude patterns
- Respect file size limits
- Extract README, code files, and documentation
- Generate summaries and metadata

### Document Processing
- Support for PDF, DOCX, HTML, TXT, Markdown
- Automatic text extraction
- Language detection
- Word and page counting
- Content summarization

### Processing Pipeline
- Asynchronous Kafka consumer/producer
- Database persistence with TimescaleDB optimization
- Error handling and retry logic
- Performance metrics and monitoring

## Configuration

Environment variables (see `config.py`):

```bash
# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
TOPIC_GITHUB_INGEST=task.github.ingest
TOPIC_DOCUMENT_INGEST=task.document.ingest
TOPIC_GITHUB_PARSED=processed.github.parsed
TOPIC_DOCUMENT_PARSED=processed.document.parsed

# Database
DATABASE_URL=postgresql://loom:loom@localhost:5432/loom

# Processing limits
MAX_FILE_SIZE_MB=100
MAX_REPO_FILES=1000
GITHUB_CLONE_TIMEOUT=300
PROCESSING_TIMEOUT=600

# GitHub (optional)
GITHUB_TOKEN=your_token_here
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Service Info
```bash
GET /
```

## Kafka Topics

### Input Topics (Consumed)
- `task.github.ingest`: GitHub repository processing requests
- `task.document.ingest`: Document processing requests

### Output Topics (Produced)
- `processed.github.parsed`: Processed GitHub content
- `processed.document.parsed`: Processed document content
- `*.errors`: Processing errors for retry handling

## Database Tables

### processed_github_parsed
Stores aggregated GitHub repository content:
- Repository metadata (name, type, URL)
- Aggregated content from OneFileLLM
- File processing statistics
- Performance metrics

### processed_document_parsed
Stores extracted document content:
- Original document metadata
- Extracted text content
- Language detection results
- Processing statistics

## Usage Examples

### Submit GitHub Repository
```bash
curl -X POST http://localhost:8000/github/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "url": "https://github.com/user/repo",
    "repository_type": "repository",
    "include_files": ["*.py", "*.md"],
    "exclude_files": ["*.pyc", "__pycache__/*"],
    "max_file_size": 1048576
  }'
```

### Submit Document
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "filename": "document.pdf",
    "file_data": "base64_encoded_content",
    "content_type": "application/pdf",
    "file_size": 102400,
    "document_type": "pdf"
  }'
```

## Development

### Local Setup
```bash
# Install dependencies
cd services/onefilellm
uv sync

# Run service
python -m app.main
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

### Docker Build
```bash
# Build image
docker build -t loom-onefilellm .

# Run container
docker run -p 8080:8080 \
  -e KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
  -e DATABASE_URL=postgresql://loom:loom@localhost:5432/loom \
  loom-onefilellm
```

## Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Logs
```bash
# Docker logs
docker logs loomv2-onefilellm-1 -f

# Container logs in development
docker-compose logs onefilellm -f
```

### Metrics
The service exposes processing metrics through:
- Structured logging with timing information
- Database statistics via `/health` endpoint
- Kafka message processing rates

## Troubleshooting

### Common Issues

**OneFileLLM Import Error**
```bash
# Ensure OneFileLLM is installed
pip install git+https://github.com/raphaelsty/onefilellm.git
```

**GitHub Clone Timeout**
```bash
# Increase timeout
export GITHUB_CLONE_TIMEOUT=600
```

**Memory Issues**
```bash
# Reduce batch sizes or increase container memory
export MAX_REPO_FILES=500
```

**File Processing Errors**
```bash
# Check file patterns and size limits
export MAX_FILE_SIZE_MB=50
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
```

## Architecture

```
GitHub URL → Kafka → OneFileLLM Service → Database
                         ↓
Documents → Kafka → Text Extraction → Kafka → Other Services
```

The service acts as a bridge between raw content sources and processed, LLM-ready text that can be consumed by downstream AI services for reasoning, summarization, and analysis.
