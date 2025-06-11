# Loom Deployment Guide

This directory contains Kubernetes deployment manifests for the Loom ingestion API.

## Quick Start

### Prerequisites

1. **Docker** installed locally
2. **kubectl** configured to access your k8s cluster at `10.0.0.148`
3. **SSH access** to the k8s cluster nodes (for image transfer)

### Option 1: Automated Deployment

```bash
# Run the automated deployment script
./deploy/scripts/deploy.sh
```

This script will:
1. Build the Docker image
2. Export it to a tar file
3. Guide you through copying it to the cluster
4. Deploy all services to k8s
5. Wait for everything to be ready

### Option 2: Manual Deployment

```bash
# 1. Build Docker image
cd services/ingestion-api
docker build -t loom-ingestion-api:latest .
cd ../..

# 2. Export and transfer image
docker save loom-ingestion-api:latest > /tmp/loom-ingestion-api.tar
scp /tmp/loom-ingestion-api.tar user@10.0.0.148:/tmp/
ssh user@10.0.0.148 'docker load < /tmp/loom-ingestion-api.tar'

# 3. Deploy to k8s
kubectl apply -f deploy/dev/namespace.yaml
kubectl apply -f deploy/dev/kafka.yaml
kubectl apply -f deploy/dev/ingestion-api.yaml

# 4. Check status
kubectl get pods -n loom-dev
```

## Services Deployed

- **Zookeeper**: Kafka coordination service
- **Kafka**: Message broker with external access on port 32092
- **Ingestion API**: FastAPI service with external access on port 32080

## Testing the Deployment

```bash
# Check if everything is running
kubectl get all -n loom-dev

# Test the API
curl http://10.0.0.148:32080/
curl http://10.0.0.148:32080/healthz

# View logs
kubectl logs -f deployment/ingestion-api -n loom-dev

# Check Kafka topics
kubectl exec -it deployment/kafka -n loom-dev -- kafka-topics --list --bootstrap-server localhost:9092
```

## Service URLs

- **Ingestion API**: http://10.0.0.148:32080
- **API Documentation**: http://10.0.0.148:32080/docs
- **Health Check**: http://10.0.0.148:32080/healthz
- **Kafka External**: 10.0.0.148:32092

## WebSocket Testing

```bash
# Using wscat (install with: npm install -g wscat)
wscat -c ws://10.0.0.148:32080/audio/stream/test-device
```

## Troubleshooting

```bash
# Pod not starting?
kubectl describe pod -l app.kubernetes.io/name=ingestion-api -n loom-dev

# Service not reachable?
kubectl get svc -n loom-dev

# Check logs
kubectl logs -f deployment/ingestion-api -n loom-dev
kubectl logs -f deployment/kafka -n loom-dev

# Port forward for local testing
kubectl port-forward svc/ingestion-api 8000:80 -n loom-dev
```

## Cleanup

```bash
# Delete everything
kubectl delete namespace loom-dev
```

## Next Steps

- **Sprint 2**: Replace this basic Kafka with proper Helm chart
- **Sprint 7**: Add proper GitOps with Flux overlays
- **Production**: Add TLS, authentication, and monitoring 