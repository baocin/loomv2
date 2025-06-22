# Loom Kubernetes Deployment

This directory contains Kubernetes manifests for local development using **k3d**.

> **Note**: For local development, use the scripts in `/scripts/` instead of deploying manually.

## 📁 Directory Structure

```
deploy/
└── dev/
    ├── namespace.yaml        # loom-dev namespace
    ├── kafka.yaml           # Zookeeper + Kafka
    ├── postgres.yaml        # PostgreSQL database
    └── ingestion-api.yaml   # FastAPI service
```

## 🚀 Quick Deploy (via scripts)

```bash
# 1. Setup k3d cluster
./scripts/setup-k3s-local.sh

# 2. Deploy everything
./scripts/deploy-k3s.sh
```

## 📦 Manual Deployment (if needed)

```bash
# Deploy to existing k3d cluster
kubectl apply -f deploy/dev/namespace.yaml
kubectl apply -f deploy/dev/kafka.yaml
kubectl apply -f deploy/dev/postgres.yaml
kubectl apply -f deploy/dev/ingestion-api.yaml

# Check status
kubectl get pods -n loom-dev
```

## 🌐 Services Deployed

- **Namespace**: `loom-dev`
- **Zookeeper**: Kafka coordination (internal)
- **Kafka**: Message broker (mapped to localhost:9092)
- **PostgreSQL**: Relational database (mapped to localhost:5432)
- **Ingestion API**: FastAPI service (mapped to localhost:8000)

## 🧪 Testing

```bash
# Direct access via k3d port mapping
curl http://localhost:8000/healthz
curl http://localhost:8000/docs

# Test Kafka
# (Available at localhost:9092)
```

## 🔍 Debugging

```bash
# Check all resources
kubectl get all -n loom-dev

# View logs
kubectl logs -f deployment/ingestion-api -n loom-dev
kubectl logs -f deployment/kafka -n loom-dev
kubectl logs -f deployment/postgres -n loom-dev

# Describe problematic pods
kubectl describe pod <pod-name> -n loom-dev

# Check Kafka topics
kubectl exec -it deployment/kafka -n loom-dev -- kafka-topics --list --bootstrap-server localhost:9092

# Connect to PostgreSQL
kubectl exec -it deployment/postgres -n loom-dev -- psql -U loom -d loom

# Check k3d cluster
k3d cluster list
docker ps | grep k3d
```

## 🧹 Cleanup

```bash
# Remove just our apps
kubectl delete namespace loom-dev

# Remove entire cluster (instant reset)
k3d cluster delete loom-local
```

## 🎯 Next Steps

- **Sprint 2**: Replace with proper Kafka Helm chart
- **Sprint 6**: Add PostgreSQL for persistence
- **Sprint 7**: Add monitoring and GitOps with Flux
