# Kubernetes Single-Node Deployment Guide for Loom v2

This guide provides exhaustive instructions for deploying Loom v2 to a production Kubernetes single-node cluster. It covers all components including PostgreSQL with TimescaleDB, Kafka, microservices, and AI model deployments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cluster Setup](#cluster-setup)
3. [Storage Configuration](#storage-configuration)
4. [Certificate Management](#certificate-management)
5. [Database Deployment (PostgreSQL + TimescaleDB)](#database-deployment-postgresql--timescaledb)
6. [Kafka Deployment](#kafka-deployment)
7. [Core Services Deployment](#core-services-deployment)
8. [AI Model Services Deployment](#ai-model-services-deployment)
9. [CronJob Services Deployment](#cronjob-services-deployment)
10. [Remote Control Infrastructure](#remote-control-infrastructure)
11. [Web UI Deployment](#web-ui-deployment)
12. [Ingress and Load Balancing](#ingress-and-load-balancing)
13. [Monitoring and Observability](#monitoring-and-observability)
14. [Resource Management](#resource-management)
15. [Backup and Recovery](#backup-and-recovery)
16. [Security Hardening](#security-hardening)
17. [Troubleshooting](#troubleshooting)
18. [Production Checklist](#production-checklist)

## Prerequisites

### Hardware Requirements

**Minimum for Single-Node Cluster:**
- CPU: 16 cores (24+ recommended for AI workloads)
- RAM: 32GB (64GB+ recommended)
- Storage: 500GB SSD (1TB+ recommended)
- GPU: NVIDIA GPU with 8GB+ VRAM (optional but recommended for AI models)

### Software Requirements

```bash
# Operating System
- Ubuntu 22.04 LTS or RHEL 8.x

# Container Runtime
- containerd 1.7+ or Docker 24+

# Kubernetes
- Kubernetes 1.28+ (1.29 recommended)

# CLI Tools Required
- kubectl 1.28+
- helm 3.13+
- git
- jq
- yq
- docker or podman (for building images)
- make
- python 3.11+ with uv
```

### Install Required Tools

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://get.helm.sh/helm-v3.13.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Install jq and yq
sudo apt-get update && sudo apt-get install -y jq
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Python and uv
sudo apt-get install -y python3.11 python3.11-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Install make and git
sudo apt-get install -y make git build-essential
```

## Cluster Setup

### Option 1: K3s (Recommended for Single-Node)

```bash
# Install K3s with specific configurations
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --kubelet-arg="max-pods=250" \
  --kube-apiserver-arg="enable-admission-plugins=PodSecurityPolicy"

# Export kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Verify installation
kubectl get nodes
kubectl get pods -A
```

### Option 2: Kubeadm

```bash
# Initialize cluster with custom pod network CIDR
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --apiserver-advertise-address=$(hostname -I | awk '{print $1}')

# Configure kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install Flannel CNI
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Allow scheduling on control plane (single-node)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

### GPU Support (if applicable)

```bash
# Install NVIDIA device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU availability
kubectl get nodes -o json | jq '.items[].status.capacity."nvidia.com/gpu"'
```

## Storage Configuration

### Local Storage Class

```bash
# Create local-storage.yaml
cat <<EOF > local-storage.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF

kubectl apply -f local-storage.yaml
```

### Create Storage Directories

```bash
# Create directories for persistent volumes
sudo mkdir -p /mnt/loom/{postgres,kafka,ai-models}
sudo chmod 755 /mnt/loom
```

### Persistent Volumes

```bash
# Create persistent-volumes.yaml
cat <<EOF > persistent-volumes.yaml
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
spec:
  capacity:
    storage: 200Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/loom/postgres
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - $(hostname)
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: kafka-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/loom/kafka
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - $(hostname)
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ai-models-pv
spec:
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/loom/ai-models
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - $(hostname)
EOF

kubectl apply -f persistent-volumes.yaml
```

## Certificate Management

### Install cert-manager

```bash
# Install cert-manager for automatic TLS certificate management
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s
```

### Configure Let's Encrypt Issuer

```bash
# Create letsencrypt-issuer.yaml
cat <<EOF > letsencrypt-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com  # Change this
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com  # Change this
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

kubectl apply -f letsencrypt-issuer.yaml
```

### Self-Signed Certificates (for internal services)

```bash
# Create self-signed-issuer.yaml
cat <<EOF > self-signed-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: loom-internal-ca
  namespace: loom-prod
spec:
  isCA: true
  commonName: loom-internal-ca
  secretName: loom-internal-ca-secret
  issuerRef:
    name: selfsigned-issuer
    kind: ClusterIssuer
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: loom-internal-issuer
  namespace: loom-prod
spec:
  ca:
    secretName: loom-internal-ca-secret
EOF

kubectl apply -f self-signed-issuer.yaml
```

## Database Deployment (PostgreSQL + TimescaleDB)

### Create Namespace

```bash
kubectl create namespace loom-prod
kubectl config set-context --current --namespace=loom-prod
```

### Create All Required Secrets

```bash
# Generate secure passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REPLICATION_PASSWORD=$(openssl rand -base64 32)
LOOM_PASSWORD=$(openssl rand -base64 32)

# Create PostgreSQL secrets
kubectl create secret generic postgres-secrets \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=replication-password=$REPLICATION_PASSWORD \
  --from-literal=loom-password=$LOOM_PASSWORD \
  --from-literal=database-url="postgresql://loom:$LOOM_PASSWORD@postgres-timescale:5432/loom"

# Create Twitter API secrets (replace with your actual values)
kubectl create secret generic twitter-secrets \
  --from-literal=bearer-token="your-twitter-bearer-token" \
  --from-literal=api-key="your-twitter-api-key" \
  --from-literal=api-secret="your-twitter-api-secret" \
  --from-literal=access-token="your-twitter-access-token" \
  --from-literal=access-token-secret="your-twitter-access-token-secret"

# Create encryption keys for sensitive data
ENCRYPTION_KEY=$(openssl rand -base64 32)
kubectl create secret generic encryption-keys \
  --from-literal=data-encryption-key=$ENCRYPTION_KEY

# Create API keys for external services
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="your-openai-key" \
  --from-literal=anthropic-api-key="your-anthropic-key" \
  --from-literal=huggingface-token="your-hf-token"

# Create Docker registry credentials (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email@example.com
```

### TimescaleDB StatefulSet

```bash
# Create timescaledb.yaml
cat <<EOF > timescaledb.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
data:
  postgresql.conf: |
    # Connection settings
    listen_addresses = '*'
    max_connections = 200

    # Memory settings
    shared_buffers = 8GB
    effective_cache_size = 24GB
    maintenance_work_mem = 2GB
    work_mem = 40MB

    # WAL settings
    wal_level = replica
    max_wal_size = 4GB
    min_wal_size = 1GB
    checkpoint_completion_target = 0.9

    # TimescaleDB settings
    shared_preload_libraries = 'timescaledb'
    timescaledb.max_background_workers = 8

    # Performance settings
    random_page_cost = 1.1
    effective_io_concurrency = 200

  init.sql: |
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    CREATE DATABASE loom;
    \c loom
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE USER loom WITH ENCRYPTED PASSWORD :'LOOM_PASSWORD';
    GRANT ALL PRIVILEGES ON DATABASE loom TO loom;
    GRANT ALL ON SCHEMA public TO loom;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO loom;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO loom;
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-timescale
spec:
  ports:
  - port: 5432
    targetPort: 5432
  selector:
    app: postgres-timescale
  type: ClusterIP
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-timescale
spec:
  serviceName: postgres-timescale
  replicas: 1
  selector:
    matchLabels:
      app: postgres-timescale
  template:
    metadata:
      labels:
        app: postgres-timescale
    spec:
      containers:
      - name: postgres
        image: timescale/timescaledb:latest-pg15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: postgres-password
        - name: LOOM_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: loom-password
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_DB
          value: postgres
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
          subPath: postgres
        - name: postgres-config
          mountPath: /docker-entrypoint-initdb.d/init.sql
          subPath: init.sql
        - name: postgres-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-config
        configMap:
          name: postgres-config
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: local-storage
      resources:
        requests:
          storage: 200Gi
EOF

kubectl apply -f timescaledb.yaml
```

### Initialize Database Schema

```bash
# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres-timescale --timeout=300s

# Create loom database and user
kubectl exec -it postgres-timescale-0 -- psql -U postgres <<EOF
CREATE DATABASE loom;
\c loom
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE USER loom WITH ENCRYPTED PASSWORD '$LOOM_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE loom TO loom;
GRANT ALL ON SCHEMA public TO loom;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO loom;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO loom;
EOF

# Run migrations
kubectl exec -it postgres-timescale-0 -- psql -U postgres -d loom -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);"

# Copy and run migration files
kubectl cp services/ingestion-api/migrations postgres-timescale-0:/tmp/migrations
kubectl exec -it postgres-timescale-0 -- bash -c "
  for file in /tmp/migrations/*.sql; do
    echo \"Running migration: \$file\"
    psql -U postgres -d loom -f \$file
  done
"

# Create TimescaleDB hypertables for time-series data
kubectl exec -it postgres-timescale-0 -- psql -U postgres -d loom <<EOF
-- Convert time-series tables to hypertables
SELECT create_hypertable('device_audio_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_gps_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_accelerometer_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_heartrate_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_state_power_raw', 'timestamp', if_not_exists => TRUE);

-- Add compression policies (compress data older than 7 days)
SELECT add_compression_policy('device_audio_raw', INTERVAL '7 days');
SELECT add_compression_policy('device_sensor_gps_raw', INTERVAL '7 days');
SELECT add_compression_policy('device_sensor_accelerometer_raw', INTERVAL '7 days');
SELECT add_compression_policy('device_health_heartrate_raw', INTERVAL '7 days');
SELECT add_compression_policy('device_state_power_raw', INTERVAL '7 days');

-- Add retention policies
SELECT add_retention_policy('device_audio_raw', INTERVAL '30 days');
SELECT add_retention_policy('device_sensor_gps_raw', INTERVAL '90 days');
SELECT add_retention_policy('device_sensor_accelerometer_raw', INTERVAL '60 days');
SELECT add_retention_policy('device_health_heartrate_raw', INTERVAL '180 days');
SELECT add_retention_policy('device_state_power_raw', INTERVAL '30 days');

-- Create continuous aggregates for common queries
CREATE MATERIALIZED VIEW device_gps_hourly
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  time_bucket('1 hour', timestamp) AS hour,
  avg(latitude) as avg_lat,
  avg(longitude) as avg_lon,
  avg(accuracy) as avg_accuracy,
  count(*) as sample_count
FROM device_sensor_gps_raw
GROUP BY device_id, hour
WITH NO DATA;

-- Refresh continuous aggregate
SELECT add_continuous_aggregate_policy('device_gps_hourly',
  start_offset => INTERVAL '3 hours',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour');
EOF
```

## Kafka Deployment

### Kafka Configuration

```bash
# Create kafka-config.yaml
cat <<EOF > kafka-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-config
data:
  server.properties: |
    # Broker settings
    broker.id=0
    listeners=PLAINTEXT://:9092
    advertised.listeners=PLAINTEXT://kafka-0.kafka-headless.loom-prod.svc.cluster.local:9092

    # Log settings
    log.dirs=/var/lib/kafka/data
    log.retention.hours=168
    log.segment.bytes=1073741824
    log.retention.check.interval.ms=300000

    # Replication settings
    default.replication.factor=1
    min.insync.replicas=1

    # Performance settings
    num.network.threads=8
    num.io.threads=8
    socket.send.buffer.bytes=102400
    socket.receive.buffer.bytes=102400
    socket.request.max.bytes=104857600

    # Compression
    compression.type=lz4

    # Topic creation
    auto.create.topics.enable=false

  create-topics.sh: |
    #!/bin/bash
    # Wait for Kafka to be ready
    until kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
      echo "Waiting for Kafka to be ready..."
      sleep 5
    done

    # Create all topics with proper configuration

    # Device Audio/Video/Image Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.audio.raw --partitions 3 --replication-factor 1 \
      --config retention.ms=604800000 --config compression.type=lz4

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.video.screen.raw --partitions 3 --replication-factor 1 \
      --config retention.ms=604800000 --config compression.type=lz4

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.image.camera.raw --partitions 3 --replication-factor 1 \
      --config retention.ms=604800000 --config compression.type=lz4

    # Device Sensor Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sensor.gps.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sensor.accelerometer.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sensor.barometer.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sensor.temperature.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sensor.generic.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    # Device Health Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.health.heartrate.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=5184000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.health.steps.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=5184000000

    # Device State Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.state.power.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    # System and Network Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.system.apps.macos.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.system.apps.android.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.metadata.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.network.wifi.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.network.bluetooth.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    # OS Events Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic os.events.app_lifecycle.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic os.events.notifications.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    # Digital Data Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic digital.clipboard.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=604800000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic digital.web_analytics.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=2592000000

    # External Sources Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic external.twitter.liked.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic external.calendar.events.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic external.email.events.raw --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    # Task Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic task.url.ingest --partitions 3 --replication-factor 1 \
      --config retention.ms=604800000

    # Processing Result Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic media.audio.vad_filtered --partitions 3 --replication-factor 1 \
      --config retention.ms=604800000 --config compression.type=lz4

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic media.text.transcribed.words --partitions 3 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic media.image.analysis.moondream_results --partitions 3 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic media.image.analysis.minicpm_results --partitions 3 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic media.video.analysis.yolo_results --partitions 3 --replication-factor 1 \
      --config retention.ms=2592000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic analysis.3d_reconstruction.dustr_results --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic analysis.inferred_context.mistral_results --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic analysis.text.embeddings --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    # Processed Task Results
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic task.url.processed.twitter_archived --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic task.url.processed.hackernews_archived --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic task.url.processed.pdf_extracted --partitions 2 --replication-factor 1 \
      --config retention.ms=7776000000

    # Remote Control Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.keystroke.send --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.mouse.send --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.clipboard.send --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.file.transfer --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.screen.capture --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.audio.send --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.shell.execute --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.app.launch --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.command.app.close --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    # Response Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.response.command.status --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.response.file.transfer --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.response.screen.capture --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.response.shell.output --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.response.error --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    # Cross-Device Sync Topics
    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sync.clipboard.broadcast --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sync.files.broadcast --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    kafka-topics.sh --create --if-not-exists --bootstrap-server localhost:9092 \
      --topic device.sync.state.broadcast --partitions 2 --replication-factor 1 \
      --config retention.ms=86400000

    echo "All Kafka topics created successfully!"
EOF

kubectl apply -f kafka-config.yaml
```

### Kafka StatefulSet

```bash
# Create kafka.yaml
cat <<EOF > kafka.yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka-headless
spec:
  ports:
  - port: 9092
    name: broker
  - port: 9093
    name: controller
  clusterIP: None
  selector:
    app: kafka
---
apiVersion: v1
kind: Service
metadata:
  name: kafka
spec:
  ports:
  - port: 9092
    targetPort: 9092
  selector:
    app: kafka
  type: ClusterIP
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
spec:
  serviceName: kafka-headless
  replicas: 1
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
      - name: kafka
        image: confluentinc/cp-kafka:7.5.0
        ports:
        - containerPort: 9092
          name: broker
        - containerPort: 9093
          name: controller
        env:
        - name: KAFKA_NODE_ID
          value: "1"
        - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
          value: "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT"
        - name: KAFKA_ADVERTISED_LISTENERS
          value: "PLAINTEXT://kafka-0.kafka-headless.loom-prod.svc.cluster.local:9092,PLAINTEXT_HOST://localhost:29092"
        - name: KAFKA_PROCESS_ROLES
          value: "broker,controller"
        - name: KAFKA_CONTROLLER_QUORUM_VOTERS
          value: "1@kafka-0.kafka-headless.loom-prod.svc.cluster.local:9093"
        - name: KAFKA_LISTENERS
          value: "PLAINTEXT://:9092,CONTROLLER://:9093,PLAINTEXT_HOST://:29092"
        - name: KAFKA_INTER_BROKER_LISTENER_NAME
          value: "PLAINTEXT"
        - name: KAFKA_CONTROLLER_LISTENER_NAMES
          value: "CONTROLLER"
        - name: KAFKA_LOG_DIRS
          value: "/var/lib/kafka/data"
        - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
          value: "1"
        - name: KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
          value: "1"
        - name: KAFKA_TRANSACTION_STATE_LOG_MIN_ISR
          value: "1"
        - name: KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS
          value: "0"
        - name: KAFKA_JMX_PORT
          value: "9999"
        - name: KAFKA_JMX_HOSTNAME
          value: "localhost"
        - name: CLUSTER_ID
          value: "MkU3OEVBNTcwNTJENDM2Qk"
        resources:
          requests:
            memory: "4Gi"
            cpu: "1"
          limits:
            memory: "8Gi"
            cpu: "2"
        volumeMounts:
        - name: kafka-storage
          mountPath: /var/lib/kafka/data
        - name: kafka-config
          mountPath: /etc/kafka/create-topics.sh
          subPath: create-topics.sh
        lifecycle:
          postStart:
            exec:
              command: ["/bin/bash", "/etc/kafka/create-topics.sh"]
        livenessProbe:
          exec:
            command:
            - kafka-broker-api-versions.sh
            - --bootstrap-server
            - localhost:9092
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - kafka-broker-api-versions.sh
            - --bootstrap-server
            - localhost:9092
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: kafka-config
        configMap:
          name: kafka-config
          defaultMode: 0755
  volumeClaimTemplates:
  - metadata:
      name: kafka-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: local-storage
      resources:
        requests:
          storage: 100Gi
EOF

kubectl apply -f kafka.yaml
```

### Kafka UI (Optional but Recommended)

```bash
# Create kafka-ui.yaml
cat <<EOF > kafka-ui.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-ui-config
data:
  config.yml: |
    kafka:
      clusters:
        - name: loom-kafka
          bootstrapServers: kafka:9092
          metrics:
            port: 9999
            type: JMX
    server:
      servlet:
        context-path: /
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kafka-ui
  template:
    metadata:
      labels:
        app: kafka-ui
    spec:
      containers:
      - name: kafka-ui
        image: provectuslabs/kafka-ui:latest
        ports:
        - containerPort: 8080
        env:
        - name: KAFKA_CLUSTERS_0_NAME
          value: loom-kafka
        - name: KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS
          value: kafka:9092
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: kafka-ui
spec:
  ports:
  - port: 8080
    targetPort: 8080
  selector:
    app: kafka-ui
  type: ClusterIP
EOF

kubectl apply -f kafka-ui.yaml
```

## Core Services Deployment

### Ingestion API Service

```bash
# Create ingestion-api.yaml
cat <<EOF > ingestion-api.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingestion-api-config
data:
  config.yaml: |
    kafka:
      bootstrap_servers: kafka:9092
      producer:
        compression_type: lz4
        batch_size: 16384
        linger_ms: 10
    cors:
      origins:
        - "*"
      allow_credentials: true
      allow_methods:
        - GET
        - POST
        - PUT
        - DELETE
      allow_headers:
        - "*"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingestion-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ingestion-api
  template:
    metadata:
      labels:
        app: ingestion-api
    spec:
      containers:
      - name: ingestion-api
        image: loom/ingestion-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: LOOM_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        - name: LOOM_KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: LOOM_HOST
          value: "0.0.0.0"
        - name: LOOM_PORT
          value: "8000"
        - name: LOOM_LOG_LEVEL
          value: "INFO"
        - name: LOOM_ENVIRONMENT
          value: "production"
        - name: LOOM_CORS_ORIGINS
          value: "*"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: ingestion-api-config
---
apiVersion: v1
kind: Service
metadata:
  name: ingestion-api
spec:
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: ingestion-api
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ingestion-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ingestion-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF

kubectl apply -f ingestion-api.yaml
```

### Kafka to DB Consumer

```bash
# Create kafka-to-db-consumer.yaml
cat <<EOF > kafka-to-db-consumer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka-to-db-consumer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kafka-to-db-consumer
  template:
    metadata:
      labels:
        app: kafka-to-db-consumer
    spec:
      containers:
      - name: consumer
        image: loom/kafka-to-db-consumer:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_GROUP_ID
          value: "kafka-to-db-consumer"
        - name: KAFKA_AUTO_OFFSET_RESET
          value: "earliest"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
EOF

kubectl apply -f kafka-to-db-consumer.yaml
```

## AI Model Services Deployment

### Shared Model Storage

```bash
# Create model-storage.yaml
cat <<EOF > model-storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ai-models-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: local-storage
  resources:
    requests:
      storage: 50Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: download-models
spec:
  template:
    spec:
      containers:
      - name: downloader
        image: python:3.11-slim
        command:
        - bash
        - -c
        - |
          pip install huggingface-hub
          python -c "
          from huggingface_hub import snapshot_download
          import os

          models = [
              'snakers4/silero-vad',
              'nvidia/parakeet-tdt_ctc-1.1b',
              'laion/BUD-E_Whisper',
              'openbmb/MiniCPM-Llama3-V-2_5',
              'laion/Empathic-Insight-Face',
              'mistralai/Mistral-Small-3.2',
              'geneing/Kokoro'
          ]

          for model in models:
              print(f'Downloading {model}...')
              snapshot_download(
                  repo_id=model,
                  cache_dir='/models/cache',
                  local_dir=f'/models/{model.replace("/", "_")}'
              )
          "
        volumeMounts:
        - name: models
          mountPath: /models
      restartPolicy: OnFailure
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
EOF

kubectl apply -f model-storage.yaml
```

### Silero VAD Service

```bash
# Create silero-vad.yaml
cat <<EOF > silero-vad.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: silero-vad
spec:
  replicas: 2
  selector:
    matchLabels:
      app: silero-vad
  template:
    metadata:
      labels:
        app: silero-vad
    spec:
      containers:
      - name: vad
        image: loom/silero-vad:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPIC
          value: device.audio.raw
        - name: KAFKA_OUTPUT_TOPIC
          value: media.audio.vad_filtered
        - name: KAFKA_GROUP_ID
          value: silero-vad-consumer
        - name: MODEL_PATH
          value: /models/snakers4_silero-vad
        - name: VAD_THRESHOLD
          value: "0.5"
        - name: MIN_SPEECH_DURATION_MS
          value: "250"
        - name: MAX_SPEECH_DURATION_S
          value: "30"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "2Gi"
            cpu: "2"
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
EOF

kubectl apply -f silero-vad.yaml
```

### MiniCPM Vision Service

```bash
# Create minicpm-vision.yaml
cat <<EOF > minicpm-vision.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minicpm-vision
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minicpm-vision
  template:
    metadata:
      labels:
        app: minicpm-vision
    spec:
      containers:
      - name: vision
        image: loom/minicpm-vision:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPICS
          value: "device.image.camera.raw,device.video.screen.raw"
        - name: KAFKA_OUTPUT_TOPIC
          value: media.image.analysis.minicpm_results
        - name: KAFKA_GROUP_ID
          value: minicpm-vision-consumer
        - name: MODEL_PATH
          value: /models/openbmb_MiniCPM-Llama3-V-2_5
        - name: DEVICE
          value: "cuda"  # Change to "cpu" if no GPU
        - name: BATCH_SIZE
          value: "4"
        - name: MAX_SEQUENCE_LENGTH
          value: "2048"
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
            nvidia.com/gpu: "1"  # Remove if no GPU
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"  # Remove if no GPU
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
      nodeSelector:
        nvidia.com/gpu: "true"  # Remove if no GPU
EOF

kubectl apply -f minicpm-vision.yaml
```

### Mistral Reasoning Service

```bash
# Create mistral-reasoning.yaml
cat <<EOF > mistral-reasoning.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mistral-config
data:
  ollama-modelfile: |
    FROM /models/mistralai_Mistral-Small-3.2
    PARAMETER temperature 0.7
    PARAMETER top_p 0.9
    PARAMETER max_tokens 4096
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-server
  template:
    metadata:
      labels:
        app: ollama-server
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        env:
        - name: OLLAMA_MODELS
          value: /models
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"  # Remove if no GPU
          limits:
            memory: "32Gi"
            cpu: "8"
            nvidia.com/gpu: "1"  # Remove if no GPU
        volumeMounts:
        - name: models
          mountPath: /models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
      nodeSelector:
        nvidia.com/gpu: "true"  # Remove if no GPU
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-server
spec:
  ports:
  - port: 11434
    targetPort: 11434
  selector:
    app: ollama-server
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mistral-reasoning
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mistral-reasoning
  template:
    metadata:
      labels:
        app: mistral-reasoning
    spec:
      containers:
      - name: reasoning
        image: loom/mistral-reasoning:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPICS
          value: "media.text.transcribed.words,task.url.processed.*"
        - name: KAFKA_OUTPUT_TOPIC
          value: analysis.inferred_context.mistral_results
        - name: KAFKA_GROUP_ID
          value: mistral-reasoning-consumer
        - name: OLLAMA_HOST
          value: http://ollama-server:11434
        - name: MODEL_NAME
          value: mistral-small
        - name: SCHEMA_PATH
          value: /app/schemas/analysis/context/v1.json
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
      initContainers:
      - name: wait-for-ollama
        image: busybox
        command: ['sh', '-c', 'until nc -z ollama-server 11434; do sleep 1; done']
EOF

kubectl apply -f mistral-reasoning.yaml
```

### Moondream OCR Service

```bash
# Create moondream-ocr.yaml
cat <<EOF > moondream-ocr.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moondream-ocr
spec:
  replicas: 2
  selector:
    matchLabels:
      app: moondream-ocr
  template:
    metadata:
      labels:
        app: moondream-ocr
    spec:
      containers:
      - name: ocr
        image: loom/moondream-ocr:latest
        ports:
        - containerPort: 8000
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPIC
          value: device.image.camera.raw
        - name: KAFKA_OUTPUT_TOPIC
          value: media.image.analysis.moondream_results
        - name: KAFKA_GROUP_ID
          value: moondream-ocr-consumer
        - name: MODEL_PATH
          value: /models/vikhyatk_moondream2
        - name: DEVICE
          value: "cuda"  # Change to "cpu" if no GPU
        - name: BATCH_SIZE
          value: "8"
        - name: MAX_WORKERS
          value: "4"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
            nvidia.com/gpu: "1"  # Remove if no GPU
          limits:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: "1"  # Remove if no GPU
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
      nodeSelector:
        nvidia.com/gpu: "true"  # Remove if no GPU
---
apiVersion: v1
kind: Service
metadata:
  name: moondream-ocr
spec:
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: moondream-ocr
  type: ClusterIP
EOF

kubectl apply -f moondream-ocr.yaml
```

### Twitter OCR Processor

```bash
# Create twitter-ocr-processor.yaml
cat <<EOF > twitter-ocr-processor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twitter-ocr-processor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: twitter-ocr-processor
  template:
    metadata:
      labels:
        app: twitter-ocr-processor
    spec:
      containers:
      - name: processor
        image: loom/twitter-ocr-processor:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPIC
          value: external.twitter.screenshots.raw
        - name: KAFKA_OUTPUT_TOPIC
          value: task.url.processed.twitter_archived
        - name: KAFKA_GROUP_ID
          value: twitter-ocr-processor
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        - name: OCR_SERVICE_URL
          value: http://moondream-ocr:8000
        - name: PROCESSING_BATCH_SIZE
          value: "10"
        - name: MAX_RETRIES
          value: "3"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
EOF

kubectl apply -f twitter-ocr-processor.yaml
```

## CronJob Services Deployment

### External Data Scrapers

```bash
# Create x-likes-fetcher-cronjob.yaml
cat <<EOF > x-likes-fetcher-cronjob.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: x-likes-fetcher-config
data:
  config.yaml: |
    kafka:
      bootstrap_servers: kafka:9092
      topic: external.twitter.liked.raw
    twitter:
      rate_limit_delay: 2
      max_tweets_per_run: 100
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: x-likes-fetcher
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: fetcher
            image: loom/x-likes-fetcher:latest
            env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: kafka:9092
            - name: KAFKA_TOPIC
              value: external.twitter.liked.raw
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: database-url
            - name: TWITTER_BEARER_TOKEN
              valueFrom:
                secretKeyRef:
                  name: twitter-secrets
                  key: bearer-token
            - name: TWITTER_USERNAME
              value: "your_username"  # Change this
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
            volumeMounts:
            - name: config
              mountPath: /app/config
          volumes:
          - name: config
            configMap:
              name: x-likes-fetcher-config
EOF

kubectl apply -f x-likes-fetcher-cronjob.yaml
```

### HackerNews Fetcher

```bash
# Create hackernews-fetcher-cronjob.yaml
cat <<EOF > hackernews-fetcher-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hackernews-fetcher
spec:
  schedule: "*/30 * * * *"  # Every 30 minutes
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: fetcher
            image: loom/hackernews-fetcher:latest
            env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: kafka:9092
            - name: KAFKA_TOPIC
              value: task.url.ingest
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: database-url
            - name: FETCH_TOP_STORIES
              value: "true"
            - name: FETCH_NEW_STORIES
              value: "true"
            - name: STORIES_LIMIT
              value: "50"
            - name: COMMENTS_DEPTH
              value: "3"
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "250m"
EOF

kubectl apply -f hackernews-fetcher-cronjob.yaml
```

### Database Maintenance Jobs

```bash
# Create db-maintenance-cronjob.yaml
cat <<EOF > db-maintenance-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: timescaledb-maintenance
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: maintenance
            image: timescale/timescaledb:latest-pg15
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: postgres-password
            command:
            - bash
            - -c
            - |
              # Run compression job
              psql -h postgres-timescale -U postgres -d loom -c "
                SELECT run_job((
                  SELECT job_id FROM timescaledb_information.jobs
                  WHERE proc_name = 'policy_compression'
                ));
              "

              # Run retention policy
              psql -h postgres-timescale -U postgres -d loom -c "
                SELECT run_job((
                  SELECT job_id FROM timescaledb_information.jobs
                  WHERE proc_name = 'policy_retention'
                ));
              "

              # Vacuum and analyze
              psql -h postgres-timescale -U postgres -d loom -c "VACUUM ANALYZE;"

              # Update table statistics
              psql -h postgres-timescale -U postgres -d loom -c "
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname = 'public'
              " | while read schema table; do
                psql -h postgres-timescale -U postgres -d loom -c "ANALYZE \$schema.\$table;"
              done
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"
EOF

kubectl apply -f db-maintenance-cronjob.yaml
```

## Remote Control Infrastructure

### Command Router Service

```bash
# Create command-router.yaml
cat <<EOF > command-router.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: command-router
spec:
  replicas: 2
  selector:
    matchLabels:
      app: command-router
  template:
    metadata:
      labels:
        app: command-router
    spec:
      containers:
      - name: router
        image: loom/command-router:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPICS
          value: "device.command.keystroke.send,device.command.mouse.send,device.command.clipboard.send,device.command.file.transfer,device.command.screen.capture,device.command.audio.send,device.command.shell.execute,device.command.app.launch,device.command.app.close"
        - name: KAFKA_GROUP_ID
          value: command-router
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        - name: DEVICE_REGISTRY_URL
          value: http://device-registry:8000
        - name: COMMAND_TIMEOUT_SECONDS
          value: "30"
        - name: MAX_RETRIES
          value: "3"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 10
          periodSeconds: 30
EOF

kubectl apply -f command-router.yaml
```

### Device Registry Service

```bash
# Create device-registry.yaml
cat <<EOF > device-registry.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: device-registry
spec:
  replicas: 2
  selector:
    matchLabels:
      app: device-registry
  template:
    metadata:
      labels:
        app: device-registry
    spec:
      containers:
      - name: registry
        image: loom/device-registry:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        - name: REDIS_URL
          value: redis://redis:6379
        - name: DEVICE_HEARTBEAT_INTERVAL
          value: "30"
        - name: DEVICE_OFFLINE_THRESHOLD
          value: "120"
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: device-registry
spec:
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: device-registry
  type: ClusterIP
---
# Redis for device state caching
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  ports:
  - port: 6379
    targetPort: 6379
  selector:
    app: redis
  type: ClusterIP
EOF

kubectl apply -f device-registry.yaml
```

## Web UI Deployment

### Pipeline Monitor UI

```bash
# Create pipeline-monitor.yaml
cat <<EOF > pipeline-monitor.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-monitor-config
data:
  config.json: |
    {
      "api": {
        "baseUrl": "https://api.loom.example.com",
        "wsUrl": "wss://ws.loom.example.com"
      },
      "kafka": {
        "uiUrl": "https://kafka-ui.loom.example.com"
      },
      "features": {
        "testMode": false,
        "debugMode": false
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipeline-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pipeline-monitor
  template:
    metadata:
      labels:
        app: pipeline-monitor
    spec:
      containers:
      - name: monitor
        image: loom/pipeline-monitor:latest
        ports:
        - containerPort: 80
        env:
        - name: REACT_APP_API_URL
          value: https://api.loom.example.com
        - name: REACT_APP_WS_URL
          value: wss://ws.loom.example.com
        - name: REACT_APP_KAFKA_UI_URL
          value: https://kafka-ui.loom.example.com
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "100m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: config
          mountPath: /usr/share/nginx/html/config.json
          subPath: config.json
      volumes:
      - name: config
        configMap:
          name: pipeline-monitor-config
---
apiVersion: v1
kind: Service
metadata:
  name: pipeline-monitor
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: pipeline-monitor
  type: ClusterIP
EOF

kubectl apply -f pipeline-monitor.yaml
```

## Ingress and Load Balancing

### Install NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Wait for controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

### Configure Ingress

```bash
# Create ingress.yaml
cat <<EOF > ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: loom-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.loom.example.com
    secretName: api-loom-tls
  - hosts:
    - kafka-ui.loom.example.com
    secretName: kafka-ui-loom-tls
  - hosts:
    - monitor.loom.example.com
    secretName: monitor-loom-tls
  rules:
  - host: api.loom.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ingestion-api
            port:
              number: 8000
  - host: kafka-ui.loom.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kafka-ui
            port:
              number: 8080
  - host: monitor.loom.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pipeline-monitor
            port:
              number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: loom-websocket-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/websocket-services: "ingestion-api"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - ws.loom.example.com
    secretName: ws-loom-tls
  rules:
  - host: ws.loom.example.com
    http:
      paths:
      - path: /audio/stream
        pathType: Prefix
        backend:
          service:
            name: ingestion-api
            port:
              number: 8000
EOF

kubectl apply -f ingress.yaml
```

## Monitoring and Observability

### Deploy Prometheus

```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create prometheus-values.yaml
cat <<EOF > prometheus-values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: local-storage
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    resources:
      requests:
        memory: 2Gi
        cpu: 1
      limits:
        memory: 4Gi
        cpu: 2
  additionalScrapeConfigs:
    - job_name: 'loom-services'
      kubernetes_sd_configs:
        - role: pod
          namespaces:
            names:
              - loom-prod
      relabel_configs:
        - source_labels: [__meta_kubernetes_pod_container_port_name]
          action: keep
          regex: metrics
grafana:
  enabled: true
  adminPassword: $(openssl rand -base64 32)
  persistence:
    enabled: true
    storageClassName: local-storage
    size: 10Gi
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'loom'
        orgId: 1
        folder: 'Loom'
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/loom
alertmanager:
  enabled: true
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'default'
    receivers:
    - name: 'default'
      # Configure your notification channels here
EOF

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f prometheus-values.yaml
```

### Deploy Loki for Log Aggregation

```bash
# Add Grafana Helm repository
helm repo add grafana https://grafana.github.io/helm-charts

# Create loki-values.yaml
cat <<EOF > loki-values.yaml
loki:
  persistence:
    enabled: true
    storageClassName: local-storage
    size: 50Gi
  config:
    table_manager:
      retention_deletes_enabled: true
      retention_period: 720h
promtail:
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push
EOF

# Install Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  -f loki-values.yaml
```

### Application Metrics

```bash
# Create servicemonitor.yaml
cat <<EOF > servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: loom-services
  namespace: loom-prod
spec:
  selector:
    matchLabels:
      monitoring: "true"
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
---
apiVersion: v1
kind: Service
metadata:
  name: ingestion-api-metrics
  labels:
    monitoring: "true"
spec:
  ports:
  - name: metrics
    port: 8000
    targetPort: 8000
  selector:
    app: ingestion-api
EOF

kubectl apply -f servicemonitor.yaml
```

## Resource Management

### Resource Quotas

```bash
# Create resource-quotas.yaml
cat <<EOF > resource-quotas.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: loom-compute-quota
  namespace: loom-prod
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
    requests.nvidia.com/gpu: "4"
    persistentvolumeclaims: "20"
    services.loadbalancers: "2"
    services.nodeports: "0"  # Discourage NodePort usage
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: loom-object-quota
  namespace: loom-prod
spec:
  hard:
    configmaps: "50"
    persistentvolumeclaims: "20"
    replicationcontrollers: "0"  # Discourage old controllers
    secrets: "50"
    services: "30"
    pods: "200"
EOF

kubectl apply -f resource-quotas.yaml
```

### Limit Ranges

```bash
# Create limit-ranges.yaml
cat <<EOF > limit-ranges.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: loom-limit-range
  namespace: loom-prod
spec:
  limits:
  - max:
      cpu: "8"
      memory: 32Gi
      nvidia.com/gpu: "1"
    min:
      cpu: 50m
      memory: 64Mi
    default:
      cpu: 250m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
  - max:
      storage: 200Gi
    min:
      storage: 1Gi
    type: PersistentVolumeClaim
EOF

kubectl apply -f limit-ranges.yaml
```

### Priority Classes

```bash
# Create priority-classes.yaml
cat <<EOF > priority-classes.yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: loom-critical
value: 1000
globalDefault: false
description: "Critical Loom services (database, kafka)"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: loom-high
value: 900
globalDefault: false
description: "High priority services (ingestion-api, core consumers)"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: loom-medium
value: 800
globalDefault: true
description: "Default priority for most services"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: loom-low
value: 700
globalDefault: false
description: "Low priority services (batch jobs, scrapers)"
EOF

kubectl apply -f priority-classes.yaml

# Update critical deployments to use priority classes
kubectl patch statefulset postgres-timescale -n loom-prod --type merge -p '{"spec":{"template":{"spec":{"priorityClassName":"loom-critical"}}}}'
kubectl patch statefulset kafka -n loom-prod --type merge -p '{"spec":{"template":{"spec":{"priorityClassName":"loom-critical"}}}}'
kubectl patch deployment ingestion-api -n loom-prod --type merge -p '{"spec":{"template":{"spec":{"priorityClassName":"loom-high"}}}}'
```

## Backup and Recovery

### PostgreSQL Backup

```bash
# Create backup-cronjob.yaml
cat <<EOF > backup-cronjob.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-backup-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-storage
  resources:
    requests:
      storage: 100Gi
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: postgres-password
            command:
            - bash
            - -c
            - |
              DATE=$(date +%Y%m%d_%H%M%S)
              pg_dump -h postgres-timescale -U postgres -d loom | gzip > /backup/loom_\${DATE}.sql.gz
              # Keep only last 7 days of backups
              find /backup -name "loom_*.sql.gz" -mtime +7 -delete
            volumeMounts:
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
EOF

kubectl apply -f backup-cronjob.yaml
```

### Kafka Backup

```bash
# Create kafka-backup-cronjob.yaml
cat <<EOF > kafka-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: kafka-offset-backup
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kafka-backup
            image: confluentinc/cp-kafka:7.5.0
            command:
            - bash
            - -c
            - |
              # Export consumer group offsets
              kafka-consumer-groups.sh --bootstrap-server kafka:9092 --all-groups --describe > /backup/consumer-offsets-$(date +%Y%m%d_%H%M%S).txt

              # Export topic configurations
              for topic in $(kafka-topics.sh --bootstrap-server kafka:9092 --list); do
                kafka-configs.sh --bootstrap-server kafka:9092 --entity-type topics --entity-name \$topic --describe > /backup/topic-config-\$topic-$(date +%Y%m%d_%H%M%S).txt
              done
            volumeMounts:
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: kafka-backup-pvc
EOF

kubectl apply -f kafka-backup-cronjob.yaml
```

## Security Hardening

### Network Policies

```bash
# Create network-policies.yaml
cat <<EOF > network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres-network-policy
spec:
  podSelector:
    matchLabels:
      app: postgres-timescale
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingestion-api
    - podSelector:
        matchLabels:
          app: kafka-to-db-consumer
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kafka-network-policy
spec:
  podSelector:
    matchLabels:
      app: kafka
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: loom-prod
    ports:
    - protocol: TCP
      port: 9092
    - protocol: TCP
      port: 9093
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
EOF

kubectl apply -f network-policies.yaml
```

### Pod Security Policies

```bash
# Create pod-security.yaml
cat <<EOF > pod-security.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: loom-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: loom-restricted-psp-user
rules:
- apiGroups: ['policy']
  resources: ['podsecuritypolicies']
  verbs: ['use']
  resourceNames:
  - loom-restricted
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: loom-restricted-psp-all-serviceaccounts
roleRef:
  kind: ClusterRole
  name: loom-restricted-psp-user
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: Group
  name: system:serviceaccounts:loom-prod
  apiGroup: rbac.authorization.k8s.io
EOF

kubectl apply -f pod-security.yaml
```

### Secrets Management

```bash
# Install Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret example
echo -n "your-secret-value" | kubectl create secret generic example-secret \
  --dry-run=client --from-file=password=/dev/stdin -o yaml | \
  kubeseal -o yaml > example-sealed-secret.yaml
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Crashes or Restarts

```bash
# Check pod status
kubectl get pods -n loom-prod

# Describe pod for events
kubectl describe pod <pod-name> -n loom-prod

# Check logs
kubectl logs <pod-name> -n loom-prod --previous

# Check resource usage
kubectl top pod <pod-name> -n loom-prod
```

#### 2. Database Connection Issues

```bash
# Test database connection
kubectl run -it --rm psql-test --image=postgres:15 --restart=Never -- \
  psql -h postgres-timescale -U postgres -d loom -c "SELECT 1"

# Check database logs
kubectl logs postgres-timescale-0 -n loom-prod

# Verify secrets
kubectl get secret postgres-secrets -n loom-prod -o yaml
```

#### 3. Kafka Issues

```bash
# Check Kafka broker status
kubectl exec -it kafka-0 -n loom-prod -- \
  kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# List topics
kubectl exec -it kafka-0 -n loom-prod -- \
  kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check consumer group status
kubectl exec -it kafka-0 -n loom-prod -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 --all-groups --describe

# View Kafka logs
kubectl logs kafka-0 -n loom-prod
```

#### 4. Storage Issues

```bash
# Check PVC status
kubectl get pvc -n loom-prod

# Check PV status
kubectl get pv

# Check disk usage
kubectl exec -it <pod-name> -n loom-prod -- df -h

# Check node disk usage
df -h /mnt/loom
```

#### 5. Network Issues

```bash
# Test service connectivity
kubectl run -it --rm curl-test --image=curlimages/curl --restart=Never -- \
  curl http://ingestion-api:8000/healthz

# Check service endpoints
kubectl get endpoints -n loom-prod

# Test DNS resolution
kubectl run -it --rm dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 --restart=Never -- \
  nslookup ingestion-api.loom-prod.svc.cluster.local
```

### Debug Commands

```bash
# Enable debug logging for a deployment
kubectl set env deployment/ingestion-api LOOM_LOG_LEVEL=DEBUG -n loom-prod

# Port forward for local debugging
kubectl port-forward service/ingestion-api 8000:8000 -n loom-prod
kubectl port-forward service/kafka-ui 8080:8080 -n loom-prod

# Execute commands in running container
kubectl exec -it deployment/ingestion-api -n loom-prod -- /bin/bash

# Copy files from container
kubectl cp loom-prod/<pod-name>:/path/to/file ./local-file

# View recent events
kubectl get events -n loom-prod --sort-by='.lastTimestamp'
```

## Production Checklist

### Pre-Deployment

- [ ] **Hardware Requirements Met**
  - [ ] CPU cores ≥ 16 (24+ for AI workloads)
  - [ ] RAM ≥ 32GB (64GB+ recommended)
  - [ ] SSD storage ≥ 500GB (1TB+ recommended)
  - [ ] GPU available (if using GPU-accelerated AI models)

- [ ] **Security Hardening**
  - [ ] All secrets stored in Kubernetes secrets
  - [ ] Network policies configured
  - [ ] Pod security policies enabled
  - [ ] RBAC configured with least privilege
  - [ ] Ingress TLS/SSL certificates configured

- [ ] **Storage Configuration**
  - [ ] Persistent volumes created and bound
  - [ ] Backup locations configured
  - [ ] Retention policies defined

- [ ] **Resource Limits**
  - [ ] All deployments have resource requests/limits
  - [ ] HPA configured for scalable services
  - [ ] Node resources monitored

### Post-Deployment

- [ ] **Health Checks**
  - [ ] All pods running and ready
  - [ ] All services have endpoints
  - [ ] Health endpoints responding
  - [ ] Kafka topics created
  - [ ] Database migrations completed

- [ ] **Monitoring**
  - [ ] Prometheus scraping metrics
  - [ ] Grafana dashboards configured
  - [ ] Alerts configured
  - [ ] Log aggregation working

- [ ] **Testing**
  - [ ] End-to-end data flow tested
  - [ ] WebSocket connections tested
  - [ ] AI model inference tested
  - [ ] Backup/restore procedures tested

- [ ] **Documentation**
  - [ ] Runbooks created
  - [ ] Disaster recovery plan documented
  - [ ] Contact information updated
  - [ ] Architecture diagrams current

### Maintenance

- [ ] **Regular Tasks**
  - [ ] Monitor disk usage (weekly)
  - [ ] Review logs for errors (daily)
  - [ ] Check backup status (daily)
  - [ ] Update dependencies (monthly)
  - [ ] Security patches (as needed)

- [ ] **Performance Tuning**
  - [ ] Analyze Prometheus metrics
  - [ ] Optimize slow queries
  - [ ] Adjust resource limits
  - [ ] Scale replicas as needed

- [ ] **Capacity Planning**
  - [ ] Monitor growth trends
  - [ ] Plan storage expansion
  - [ ] Evaluate scaling needs
  - [ ] Budget for resources

## Additional Services

### Text Embedder Service

```bash
# Create text-embedder.yaml
cat <<EOF > text-embedder.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: text-embedder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: text-embedder
  template:
    metadata:
      labels:
        app: text-embedder
    spec:
      containers:
      - name: embedder
        image: loom/text-embedder:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPICS
          value: "media.text.transcribed.words,task.url.processed.twitter_archived,task.url.processed.hackernews_archived"
        - name: KAFKA_OUTPUT_TOPIC
          value: analysis.text.embeddings
        - name: KAFKA_GROUP_ID
          value: text-embedder
        - name: MODEL_NAME
          value: "sentence-transformers/all-MiniLM-L6-v2"
        - name: BATCH_SIZE
          value: "32"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database-url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
EOF

kubectl apply -f text-embedder.yaml
```

### Speech to Text Service (Parakeet)

```bash
# Create parakeet-stt.yaml
cat <<EOF > parakeet-stt.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: parakeet-stt
spec:
  replicas: 2
  selector:
    matchLabels:
      app: parakeet-stt
  template:
    metadata:
      labels:
        app: parakeet-stt
    spec:
      containers:
      - name: stt
        image: loom/parakeet-stt:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka:9092
        - name: KAFKA_INPUT_TOPIC
          value: media.audio.vad_filtered
        - name: KAFKA_OUTPUT_TOPIC
          value: media.text.transcribed.words
        - name: KAFKA_GROUP_ID
          value: parakeet-stt-consumer
        - name: MODEL_PATH
          value: /models/nvidia_parakeet-tdt_ctc-1.1b
        - name: DEVICE
          value: "cuda"  # Change to "cpu" if no GPU
        - name: BATCH_SIZE
          value: "16"
        - name: MAX_AUDIO_LENGTH
          value: "30"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
            nvidia.com/gpu: "1"  # Remove if no GPU
          limits:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: "1"  # Remove if no GPU
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-models-pvc
      nodeSelector:
        nvidia.com/gpu: "true"  # Remove if no GPU
EOF

kubectl apply -f parakeet-stt.yaml
```

## Building Docker Images

Before deployment, build all required Docker images:

```bash
# Clone the repository
git clone https://github.com/yourusername/loomv2.git
cd loomv2

# Set your Docker registry (use Docker Hub, GitHub Container Registry, etc.)
export DOCKER_REGISTRY="your-registry.com"
export DOCKER_NAMESPACE="loom"

# Build all service images
make docker-build-all

# Or build individual services
cd services/ingestion-api && make docker && cd ../..
cd services/kafka-to-db-consumer && make docker && cd ../..
cd services/moondream-ocr && make docker && cd ../..
cd services/twitter-ocr-processor && make docker && cd ../..
cd services/pipeline-monitor && make docker && cd ../..
cd services/x-likes-fetcher && make docker && cd ../..
cd services/hackernews-fetcher && make docker && cd ../..

# Build AI service images
cd services/silero-vad && make docker && cd ../..
cd services/parakeet-stt && make docker && cd ../..
cd services/minicpm-vision && make docker && cd ../..
cd services/mistral-reasoning && make docker && cd ../..
cd services/text-embedder && make docker && cd ../..
cd services/command-router && make docker && cd ../..
cd services/device-registry && make docker && cd ../..

# Tag images for your registry
docker tag loom/ingestion-api:latest $DOCKER_REGISTRY/$DOCKER_NAMESPACE/ingestion-api:latest
docker tag loom/kafka-to-db-consumer:latest $DOCKER_REGISTRY/$DOCKER_NAMESPACE/kafka-to-db-consumer:latest
# ... repeat for all images

# Push images to registry
docker push $DOCKER_REGISTRY/$DOCKER_NAMESPACE/ingestion-api:latest
docker push $DOCKER_REGISTRY/$DOCKER_NAMESPACE/kafka-to-db-consumer:latest
# ... repeat for all images

# Or use the convenience script
./scripts/push-all-images.sh $DOCKER_REGISTRY/$DOCKER_NAMESPACE
```

### Update Image References

After pushing images, update all Kubernetes manifests to use your registry:

```bash
# Replace image references in all YAML files
find . -name "*.yaml" -type f -exec sed -i "s|loom/|$DOCKER_REGISTRY/$DOCKER_NAMESPACE/|g" {} +

# Or manually update each deployment file
sed -i "s|image: loom/|image: $DOCKER_REGISTRY/$DOCKER_NAMESPACE/|g" ingestion-api.yaml
sed -i "s|image: loom/|image: $DOCKER_REGISTRY/$DOCKER_NAMESPACE/|g" kafka-to-db-consumer.yaml
# ... repeat for all deployment files
```

## Deployment Order

For a successful deployment, follow this order:

1. **Infrastructure Setup**
   ```bash
   # 1. Create namespace
   kubectl create namespace loom-prod
   kubectl config set-context --current --namespace=loom-prod

   # 2. Storage configuration
   kubectl apply -f local-storage.yaml
   kubectl apply -f persistent-volumes.yaml

   # 3. Certificate management
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   kubectl apply -f letsencrypt-issuer.yaml
   kubectl apply -f self-signed-issuer.yaml
   ```

2. **Core Services**
   ```bash
   # 4. Secrets
   kubectl apply -f postgres-secrets.yaml
   kubectl apply -f twitter-secrets.yaml  # If using Twitter scraper

   # 5. Database
   kubectl apply -f timescaledb.yaml
   kubectl wait --for=condition=ready pod -l app=postgres-timescale --timeout=300s

   # 6. Run database migrations
   kubectl cp services/ingestion-api/migrations postgres-timescale-0:/tmp/migrations
   kubectl exec -it postgres-timescale-0 -- bash -c "for file in /tmp/migrations/*.sql; do psql -U postgres -d loom -f \$file; done"

   # 7. Kafka
   kubectl apply -f kafka.yaml
   kubectl wait --for=condition=ready pod -l app=kafka --timeout=300s

   # 8. Redis (for device registry)
   kubectl apply -f device-registry.yaml
   ```

3. **Application Services**
   ```bash
   # 9. Core services
   kubectl apply -f ingestion-api.yaml
   kubectl apply -f kafka-to-db-consumer.yaml
   kubectl apply -f kafka-ui.yaml

   # 10. AI model storage
   kubectl apply -f model-storage.yaml
   kubectl wait --for=condition=complete job/download-models --timeout=3600s

   # 11. AI services
   kubectl apply -f silero-vad.yaml
   kubectl apply -f parakeet-stt.yaml
   kubectl apply -f minicpm-vision.yaml
   kubectl apply -f moondream-ocr.yaml
   kubectl apply -f mistral-reasoning.yaml
   kubectl apply -f text-embedder.yaml

   # 12. Processing services
   kubectl apply -f twitter-ocr-processor.yaml
   kubectl apply -f command-router.yaml

   # 13. Web UI
   kubectl apply -f pipeline-monitor.yaml
   ```

4. **Scheduled Jobs & Monitoring**
   ```bash
   # 14. CronJobs
   kubectl apply -f x-likes-fetcher-cronjob.yaml
   kubectl apply -f hackernews-fetcher-cronjob.yaml
   kubectl apply -f db-maintenance-cronjob.yaml
   kubectl apply -f backup-cronjob.yaml
   kubectl apply -f kafka-backup-cronjob.yaml

   # 15. Ingress
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
   kubectl apply -f ingress.yaml

   # 16. Monitoring
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo add grafana https://grafana.github.io/helm-charts
   helm repo update
   helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace -f prometheus-values.yaml
   helm install loki grafana/loki-stack --namespace monitoring -f loki-values.yaml
   kubectl apply -f servicemonitor.yaml

   # 17. Resource management
   kubectl apply -f resource-quotas.yaml
   kubectl apply -f limit-ranges.yaml
   kubectl apply -f priority-classes.yaml

   # 18. Security policies
   kubectl apply -f network-policies.yaml
   kubectl apply -f pod-security.yaml
   ```

## Post-Deployment Configuration

### Configure Grafana Dashboards

```bash
# Get Grafana admin password
GRAFANA_PASSWORD=$(kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d)

# Port forward to Grafana
kubectl port-forward -n monitoring service/prometheus-grafana 3000:80 &
GRAFANA_PID=$!

# Wait for port forward
sleep 5

# Import Loom dashboards
curl -X POST -H "Content-Type: application/json" \
  -u "admin:$GRAFANA_PASSWORD" \
  -d @deploy/monitoring/dashboards/loom-overview.json \
  http://localhost:3000/api/dashboards/db

curl -X POST -H "Content-Type: application/json" \
  -u "admin:$GRAFANA_PASSWORD" \
  -d @deploy/monitoring/dashboards/kafka-metrics.json \
  http://localhost:3000/api/dashboards/db

curl -X POST -H "Content-Type: application/json" \
  -u "admin:$GRAFANA_PASSWORD" \
  -d @deploy/monitoring/dashboards/ai-services.json \
  http://localhost:3000/api/dashboards/db

# Kill port forward
kill $GRAFANA_PID
```

### Initialize Device Registry

```bash
# Create initial device registrations
kubectl exec -it deployment/device-registry -- python -c "
from app.models import Device
from app.database import get_db

# Register your devices
devices = [
    {'id': 'macos-laptop', 'name': 'MacBook Pro', 'type': 'macos', 'capabilities': ['audio', 'screen', 'keyboard']},
    {'id': 'android-phone', 'name': 'Pixel Phone', 'type': 'android', 'capabilities': ['audio', 'camera', 'sensors']},
    {'id': 'linux-server', 'name': 'Processing Server', 'type': 'linux', 'capabilities': ['compute']}
]

db = next(get_db())
for device in devices:
    db_device = Device(**device)
    db.add(db_device)
db.commit()
print('Devices registered successfully')
"
```

### Configure AI Model Optimization

```bash
# Optimize models for inference
kubectl exec -it job/download-models -- python -c "
import torch
from transformers import AutoModel

# Optimize models for deployment
models = [
    'nvidia/parakeet-tdt_ctc-1.1b',
    'openbmb/MiniCPM-Llama3-V-2_5'
]

for model_name in models:
    model_path = f'/models/{model_name.replace("/", "_")}'
    print(f'Optimizing {model_name}...')

    # Load and optimize model
    model = AutoModel.from_pretrained(model_path)
    model.eval()

    # Convert to TorchScript if possible
    try:
        traced = torch.jit.trace(model, example_inputs)
        torch.jit.save(traced, f'{model_path}/model_traced.pt')
        print(f'Saved optimized model for {model_name}')
    except:
        print(f'Could not trace {model_name}, using original')
"
```

## Verification Steps

After deployment, verify all components:

```bash
# Check all pods are running
kubectl get pods -n loom-prod

# Check services
kubectl get svc -n loom-prod

# Check ingress
kubectl get ingress -n loom-prod

# Test API endpoint
curl https://api.loom.example.com/healthz

# Check Kafka topics
kubectl exec -it kafka-0 -- kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check database connection
kubectl exec -it postgres-timescale-0 -- psql -U postgres -d loom -c "SELECT 1"

# View logs
kubectl logs -f deployment/ingestion-api
kubectl logs -f deployment/silero-vad

# Check metrics
kubectl port-forward service/ingestion-api 8000:8000 &
sleep 5
curl http://localhost:8000/metrics
kill %1  # Stop port-forward

# Check Grafana dashboard
kubectl port-forward -n monitoring service/prometheus-grafana 3000:80 &
echo "Grafana available at http://localhost:3000"
echo "Default username: admin"
echo "Password: $(kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d)"

# Access Kafka UI
kubectl port-forward service/kafka-ui 8081:8080 &
echo "Kafka UI available at http://localhost:8081"

# Check Pipeline Monitor UI
kubectl port-forward service/pipeline-monitor 8082:80 &
echo "Pipeline Monitor available at http://localhost:8082"
```

## Conclusion

This deployment guide provides a comprehensive approach to deploying Loom v2 on a single-node Kubernetes cluster. The configuration includes all components from the evolved architecture including:

- TimescaleDB for time-series data storage
- Kafka for event streaming
- Core ingestion and processing services
- AI model services for audio, vision, and reasoning
- CronJob-based scrapers for external data
- Remote control infrastructure for cross-device communication
- Web UI for pipeline monitoring
- Comprehensive monitoring and observability
- Security hardening and resource management

Key considerations:
- Start with the minimum configuration and scale up as needed
- Monitor resource usage closely in the first weeks
- Implement proper backup and disaster recovery procedures
- Keep security as a top priority
- Document any customizations for future reference
- Follow the deployment order to ensure dependencies are met
- Verify each component before proceeding to the next

For multi-node clusters:
- Adjust replica counts for high availability
- Add pod anti-affinity rules to spread pods across nodes
- Consider distributed storage solutions like Rook/Ceph
- Implement cross-node networking policies
- Use external load balancers for ingress
