# Tiltfile for Loom v2 local development

# Load Kubernetes YAML
k8s_yaml([
    'deploy/dev/namespace.yaml',
    # 'deploy/dev/kafka.yaml',  # Using Helm chart instead
    'deploy/dev/postgres.yaml',
    'deploy/dev/ai-services.yaml',
    'deploy/dev/cronjobs.yaml',
])

# Build and deploy ingestion-api
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

# Build and deploy AI model services
# Silero VAD service
docker_build(
    'loom/silero-vad',
    'services/silero-vad',
    dockerfile='services/silero-vad/Dockerfile',
    live_update=[
        sync('services/silero-vad/app', '/app/app'),
        run('pip install -e .', trigger=['services/silero-vad/pyproject.toml']),
    ]
)

# MiniCPM Vision service
docker_build(
    'loom/minicpm-vision',
    'services/minicpm-vision',
    dockerfile='services/minicpm-vision/Dockerfile',
    live_update=[
        sync('services/minicpm-vision/app', '/app/app'),
        run('pip install -e .', trigger=['services/minicpm-vision/pyproject.toml']),
    ]
)

# Parakeet TDT ASR service
docker_build(
    'loom/parakeet-tdt',
    'services/parakeet-tdt',
    dockerfile='services/parakeet-tdt/Dockerfile',
    live_update=[
        sync('services/parakeet-tdt/app', '/app/app'),
        run('pip install -e .', trigger=['services/parakeet-tdt/pyproject.toml']),
    ]
)

# Build and deploy external data fetchers
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

# Scheduled consumers service
docker_build(
    'loom/scheduled-consumers',
    'services/scheduled-consumers',
    dockerfile='services/scheduled-consumers/Dockerfile',
    live_update=[
        sync('services/scheduled-consumers/app', '/app/app'),
        run('pip install -e .', trigger=['services/scheduled-consumers/pyproject.toml']),
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

# Note: AI services run as Kafka consumers without external ports
# They can be monitored via their health endpoints through kubectl port-forward

# Resource dependencies
k8s_resource('chart-ingestion-api', resource_deps=['kafka-infra-chart', 'postgres'])
k8s_resource('chart-kafka-ui', resource_deps=['kafka-infra-chart'])

# AI services dependencies
k8s_resource('silero-vad', resource_deps=['kafka-infra-chart'])
k8s_resource('minicpm-vision', resource_deps=['kafka-infra-chart'])
k8s_resource('parakeet-tdt', resource_deps=['kafka-infra-chart'])

# Scheduled services dependencies
k8s_resource('scheduled-consumers', resource_deps=['kafka-infra-chart'])
k8s_resource('hackernews-fetcher', resource_deps=['kafka-infra-chart'])
k8s_resource('email-fetcher', resource_deps=['kafka-infra-chart'])
k8s_resource('calendar-fetcher', resource_deps=['kafka-infra-chart'])
k8s_resource('x-likes-fetcher', resource_deps=['kafka-infra-chart'])

# Custom commands
local_resource(
    'create-kafka-topics',
    cmd='python scripts/create_kafka_topics.py --bootstrap-servers localhost:9092',
    resource_deps=['kafka-infra-chart'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

local_resource(
    'test-ingestion-api',
    cmd='cd services/ingestion-api && make test',
    resource_deps=['chart-ingestion-api'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

local_resource(
    'test-pipeline-e2e',
    cmd='python scripts/test-pipeline-e2e.py',
    resource_deps=['chart-ingestion-api', 'kafka-infra-chart'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

# Watch for changes in shared schemas
watch_file('shared/schemas/')

print("""
🚀 Loom v2 Development Environment

Available services:
- Ingestion API: http://localhost:8000
- Kafka UI: http://localhost:8081
- Kafka: localhost:9092
- PostgreSQL: localhost:5432

AI Model Services (Kafka consumers):
- Silero VAD: Voice Activity Detection
- MiniCPM Vision: Image analysis and OCR
- Parakeet TDT: Speech-to-text transcription

External Data Services:
- HackerNews Fetcher: News aggregation
- Email Fetcher: Email monitoring
- Calendar Fetcher: Calendar integration
- Scheduled Consumers: Coordinated data collection

Manual commands:
- Create Kafka topics: `tilt trigger create-kafka-topics`
- Run unit tests: `tilt trigger test-ingestion-api`
- Run end-to-end pipeline test: `tilt trigger test-pipeline-e2e`

Logs: `tilt logs <service-name>`
Service status: `kubectl get pods -n loom-dev`
""")
