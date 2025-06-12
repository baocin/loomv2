# Loom Kubernetes Deployment

This directory contains Kubernetes manifests for local development using **multipass**.

> **Note**: For local development, use the scripts in `/scripts/` instead of deploying manually.

## 📁 Directory Structure

```
deploy/
└── dev/
    ├── namespace.yaml        # loom-dev namespace
    ├── kafka.yaml           # Zookeeper + Kafka
    └── ingestion-api.yaml   # FastAPI service
```

## 🚀 Quick Deploy (via scripts)

```bash
# 1. Setup multipass VM with k3s
./scripts/setup-k3s-local.sh

# 2. Deploy everything
./scripts/deploy-k3s.sh
```

## 📦 Manual Deployment (if needed)

```bash
# Deploy to existing k3s cluster
kubectl apply -f deploy/dev/namespace.yaml
kubectl apply -f deploy/dev/kafka.yaml  
kubectl apply -f deploy/dev/ingestion-api.yaml

# Check status
kubectl get pods -n loom-dev
```

## 🌐 Services Deployed

- **Namespace**: `loom-dev`
- **Zookeeper**: Kafka coordination (internal)
- **Kafka**: Message broker (NodePort 32092)
- **Ingestion API**: FastAPI service (NodePort 32080)

## 🧪 Testing

```bash
# Via port-forward (recommended)
kubectl port-forward svc/ingestion-api-external 8000:8000 -n loom-dev &
curl http://localhost:8000/healthz

# Direct via VM IP
VM_IP=$(multipass info k3s | grep IPv4 | awk '{print $2}')
curl http://$VM_IP:32080/healthz
```

## 🔍 Debugging

```bash
# Check all resources
kubectl get all -n loom-dev

# View logs
kubectl logs -f deployment/ingestion-api -n loom-dev
kubectl logs -f deployment/kafka -n loom-dev

# Describe problematic pods
kubectl describe pod <pod-name> -n loom-dev

# Check Kafka topics
kubectl exec -it deployment/kafka -n loom-dev -- kafka-topics --list --bootstrap-server localhost:9092
```

## 🧹 Cleanup

```bash
# Remove just our apps
kubectl delete namespace loom-dev

# Remove entire VM (clean slate)
multipass delete k3s && multipass purge
```

## 🎯 Next Steps

- **Sprint 2**: Replace with proper Kafka Helm chart
- **Sprint 6**: Add TimescaleDB for persistence
- **Sprint 7**: Add monitoring and GitOps with Flux 