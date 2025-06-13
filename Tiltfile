# Tiltfile for Loom v2 local development

# Load Kubernetes YAML
k8s_yaml([
    'deploy/dev/namespace.yaml',
    'deploy/dev/kafka.yaml',
    'deploy/dev/postgres.yaml',
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
    ]
))

# Build and deploy kafka-infra
k8s_yaml(helm(
    'deploy/helm/kafka-infra',
    values=['deploy/helm/kafka-infra/values.yaml'],
))

# Port forwards for local development
k8s_resource('ingestion-api', port_forwards='8000:8000')
k8s_resource('kafka', port_forwards=['9092:9092', '9093:9093'])
k8s_resource('postgres', port_forwards='5432:5432')

# Resource dependencies
k8s_resource('ingestion-api', resource_deps=['kafka', 'postgres'])

# Custom commands
local_resource(
    'create-kafka-topics',
    cmd='python scripts/create_kafka_topics.py --bootstrap-servers localhost:9092',
    resource_deps=['kafka'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

local_resource(
    'test-ingestion-api',
    cmd='cd services/ingestion-api && make test',
    resource_deps=['ingestion-api'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL,
)

# Watch for changes in shared schemas
watch_file('shared/schemas/')

print("""
🚀 Loom v2 Development Environment

Available services:
- Ingestion API: http://localhost:8000
- Kafka: localhost:9092
- PostgreSQL: localhost:5432

Manual commands:
- Create Kafka topics: `tilt trigger create-kafka-topics`
- Run tests: `tilt trigger test-ingestion-api`

Logs: `tilt logs <service-name>`
""")
