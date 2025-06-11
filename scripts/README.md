# Loom Testing Scripts

This directory contains scripts for testing and deploying the Loom services locally.

## 🚀 Quick Start Options

### Option 1: Local k3s (Recommended)

**Simplest approach** - runs everything locally with k3s:

```bash
# 1. Setup k3s locally
./scripts/setup-k3s-local.sh

# 2. Deploy everything
./scripts/deploy-k3s.sh

# 3. Test
kubectl port-forward svc/ingestion-api-external 8000:8000 -n loom-dev &
curl http://localhost:8000/healthz
```

### Option 2: Docker Only

**Quick API testing** without Kubernetes:

```bash
# Simple test (no Kafka)
./scripts/test-simple.sh

# Full stack test (with Kafka)
./scripts/test-docker.sh
```

### Option 3: Remote k8s Cluster

**For your existing cluster at 10.0.0.148**:

```bash
# Setup kubectl access
./deploy/scripts/setup-kubectl.sh

# Deploy to remote cluster
./deploy/scripts/deploy.sh
```

## 📁 Scripts Overview

| Script | Purpose | Use Case |
|--------|---------|----------|
| `test-simple.sh` | Quick API test | Fast development iteration |
| `test-docker.sh` | Full Docker stack | Local integration testing |
| `setup-k3s-local.sh` | Install k3s locally | One-time setup |
| `deploy-k3s.sh` | Deploy to local k3s | Kubernetes testing |

## 🎯 Recommended Workflow

1. **Development**: Use `test-simple.sh` for quick iterations
2. **Testing**: Use `deploy-k3s.sh` for full k8s testing
3. **Production**: Use remote cluster deployment

## ✅ Benefits of Local k3s

- ✅ **No SSH/SCP** - images stay local
- ✅ **Fast deployment** - no network transfers
- ✅ **Real Kubernetes** - same as production
- ✅ **Simple cleanup** - just restart k3s
- ✅ **Port forwarding** - easy access to services

## 🔧 Dependencies

- **Docker** (all approaches)
- **kubectl** (k8s approaches)  
- **curl** (testing)
- **jq** (optional, for JSON formatting)

## 🧹 Cleanup

```bash
# Stop Docker containers
docker stop $(docker ps -q --filter name=loom)
docker rm $(docker ps -aq --filter name=loom)

# Reset k3s
sudo k3s-uninstall.sh  # Remove k3s completely
# or
kubectl delete namespace loom-dev  # Just remove our stuff
``` 