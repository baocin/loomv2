# Loom Local Development Scripts

Local development and testing using **k3d** - k3s in Docker containers!

## 🚀 Quick Start

**One-time setup:**
```bash
# 1. Setup k3d cluster (installs k3d if needed)
./scripts/setup-k3s-local.sh

# 2. Deploy everything to k3d
./scripts/deploy-k3s.sh

# 3. Test directly
curl http://localhost:8000/healthz
```

## 📁 Scripts

| Script | Purpose |
|--------|---------|
| `setup-k3s-local.sh` | Install k3d + create cluster (one-time) |
| `deploy-k3s.sh` | Deploy to k3d cluster |
| `test-simple.sh` | Quick Docker-only API test |
| `test-api.sh` | API testing with health checks |

## 🎯 Development Workflow

1. **Setup** (once): `./scripts/setup-k3s-local.sh`
2. **Code** → **Deploy**: `./scripts/deploy-k3s.sh`
3. **Test**: `curl http://localhost:8000/healthz`
4. **Debug**: `kubectl logs -f` or `docker ps`

## ✅ Why k3d?

- ✅ **Fast startup** - containers start in seconds
- ✅ **Real k3s** - exactly like production k3s
- ✅ **Port mapping** - direct localhost access
- ✅ **Easy debugging** - standard Docker tools
- ✅ **Lightweight** - no VM overhead
- ✅ **Simple cleanup** - delete cluster instantly

## 🔧 Requirements

- **Docker** (for building images and k3d)
- **k3d** (auto-installed by setup script)
- **kubectl** (for deployment)
- **curl** (for testing)

## 🌐 Access Methods

**Direct via localhost (k3d port mapping):**
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/docs
```

**Kafka access:**
```bash
# Connect to Kafka at localhost:9092
```

## 🧹 Cleanup Options

```bash
# Just remove our apps
kubectl delete namespace loom-dev

# Remove entire cluster (instant reset)
k3d cluster delete loom-local

# Stop cluster (keep for later)
k3d cluster stop loom-local
```

## 🐞 Debugging

```bash
# Check cluster status
k3d cluster list

# Check Docker containers
docker ps | grep k3d

# Kubernetes debugging
kubectl get pods -n loom-dev
kubectl logs -f deployment/ingestion-api -n loom-dev
kubectl describe pod <pod-name> -n loom-dev

# Access cluster nodes
docker exec -it k3d-loom-local-server-0 sh
``` 