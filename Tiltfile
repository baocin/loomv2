# Tiltfile for Loom v2 local development

# Load Kubernetes YAML - only load existing files
k8s_yaml([
    'deploy/dev/namespace.yaml',
    'deploy/dev/postgres.yaml',
    'deploy/dev/ai-services.yaml',
    'deploy/dev/kafka-to-db-consumer.yaml',
], allow_duplicates=True)

# Build and deploy ingestion-api (verified exists)
docker_build(
    'loom/ingestion-api',
    'services/ingestion-api',
    dockerfile='services/ingestion-api/Dockerfile',
    live_update=[
        sync('services/ingestion-api/app', '/app/app'),
        run('pip install -e .', trigger=['services/ingestion-api/pyproject.toml']),
    ]
)

k8s_yaml(helm(
    'deploy/helm/ingestion-api',
    values=['deploy/helm/ingestion-api/values.yaml'],
    set=[
        'image.repository=loom/ingestion-api',
        'image.tag=latest',
        'image.pullPolicy=Never',
    ],
    namespace='loom-dev'
))

# Build ONNX-based AI services
docker_build(
    'loom/onnx-vad',
    'services/onnx-vad',
    dockerfile='services/onnx-vad/Dockerfile',
    live_update=[
        sync('services/onnx-vad/app', '/app/app'),
        run('pip install -e .', trigger=['services/onnx-vad/pyproject.toml']),
    ]
)

docker_build(
    'loom/onnx-asr',
    'services/onnx-asr',
    dockerfile='services/onnx-asr/Dockerfile',
    live_update=[
        sync('services/onnx-asr/app', '/app/app'),
        run('pip install -e .', trigger=['services/onnx-asr/pyproject.toml']),
    ]
)

docker_build(
    'loom/minicpm-vision',
    'services/minicpm-vision',
    dockerfile='services/minicpm-vision/Dockerfile',
    live_update=[
        sync('services/minicpm-vision/app', '/app/app'),
        run('pip install -e .', trigger=['services/minicpm-vision/pyproject.toml']),
    ]
)

docker_build(
    'loom/moondream-ocr',
    'services/moondream-ocr',
    dockerfile='services/moondream-ocr/Dockerfile',
    live_update=[
        sync('services/moondream-ocr/app', '/app/app'),
        run('pip install -r requirements.txt', trigger=['services/moondream-ocr/requirements.txt']),
    ]
)

docker_build(
    'loom/hackernews-fetcher',
    'services/hackernews-fetcher',
    dockerfile='services/hackernews-fetcher/Dockerfile'
)

docker_build(
    'loom/email-fetcher',
    'services/email-fetcher',
    dockerfile='services/email-fetcher/Dockerfile'
)

docker_build(
    'loom/calendar-fetcher',
    'services/calendar-fetcher',
    dockerfile='services/calendar-fetcher/Dockerfile'
)

docker_build(
    'loom/scheduled-consumers',
    'services/scheduled-consumers',
    dockerfile='services/scheduled-consumers/Dockerfile',
    live_update=[
        sync('services/scheduled-consumers/app', '/app/app'),
        run('pip install -e .', trigger=['services/scheduled-consumers/pyproject.toml']),
    ]
)

docker_build(
    'loom/kafka-to-db-consumer',
    'services/kafka-to-db-consumer',
    dockerfile='services/kafka-to-db-consumer/Dockerfile',
    live_update=[
        sync('services/kafka-to-db-consumer/app', '/app/app'),
        run('pip install -e .', trigger=['services/kafka-to-db-consumer/pyproject.toml']),
    ]
)

# Build and deploy kafka-infra
k8s_yaml(helm(
    'deploy/helm/kafka-infra',
    values=['deploy/helm/kafka-infra/values.yaml'],
    namespace='loom-dev'
))

# Deploy kafka-ui for monitoring
k8s_yaml(helm(
    'deploy/helm/kafka-ui',
    values=['deploy/helm/kafka-ui/values.yaml'],
    namespace='loom-dev'
))

# Port forwards for local development
k8s_resource('chart-ingestion-api', port_forwards='8000:8000')
k8s_resource('kafka-infra-chart', port_forwards=['9092:9092', '9093:9093'])
k8s_resource('postgres', port_forwards='5432:5432')
k8s_resource('chart-kafka-ui', port_forwards='8081:8080')

# Resource dependencies
k8s_resource('chart-ingestion-api', resource_deps=['kafka-infra-chart', 'postgres'])
k8s_resource('chart-kafka-ui', resource_deps=['kafka-infra-chart'])

print("""
🚀 Loom v2 Development Environment (Minimal)

Available services:
- Ingestion API: http://localhost:8000
- Kafka UI: http://localhost:8081
- Kafka: localhost:9092
- PostgreSQL: localhost:5432

Logs: `tilt logs <service-name>`
Service status: `kubectl get pods -n loom-dev`
""")
