# Loom Local Development Scripts

Local development and testing using **multipass + k3s** - real Kubernetes in an Ubuntu VM!

## 🚀 Quick Start

**One-time setup:**
```bash
# 1. Setup k3s in multipass VM (installs multipass if needed)
./scripts/setup-k3s-local.sh

# 2. Deploy everything to k3s
./scripts/deploy-k3s.sh

# 3. Test via port-forward
kubectl port-forward svc/ingestion-api-external 8000:8000 -n loom-dev &
curl http://localhost:8000/healthz
```

## 📁 Scripts

| Script | Purpose |
|--------|---------|
| `setup-k3s-local.sh` | Install multipass VM + k3s (one-time) |
| `deploy-k3s.sh` | Deploy to k3s VM |
| `test-simple.sh` | Quick Docker-only API test |
| `test-api.sh` | API testing with health checks |

## 🎯 Development Workflow

1. **Setup** (once): `./scripts/setup-k3s-local.sh`
2. **Code** → **Deploy**: `./scripts/deploy-k3s.sh`
3. **Test**: `kubectl port-forward` + `curl`
4. **Debug**: `kubectl logs -f` or `multipass shell k3s`

## ✅ Why Multipass + k3s?

- ✅ **Real k3s** - exactly like production
- ✅ **Real Ubuntu** - proper systemd/Linux environment
- ✅ **Fast iteration** - local image import
- ✅ **Easy debugging** - shell into VM anytime
- ✅ **Clean isolation** - VM contains everything
- ✅ **Simple cleanup** - delete VM to reset

## 🔧 Requirements

- **Docker** (for building images)
- **multipass** (auto-installed by setup script)
- **kubectl** (for deployment)
- **curl** (for testing)

## 🌐 Access Methods

**Via port-forward (recommended):**
```bash
kubectl port-forward svc/ingestion-api-external 8000:8000 -n loom-dev &
curl http://localhost:8000/healthz
```

**Direct via VM IP:**
```bash
VM_IP=$(multipass info k3s | grep IPv4 | awk '{print $2}')
curl http://$VM_IP:32080/healthz
```

## 🧹 Cleanup Options

```bash
# Just remove our apps
kubectl delete namespace loom-dev

# Remove entire VM (clean slate)
multipass delete k3s && multipass purge

# Stop VM (keep for later)
multipass stop k3s
```

## 🐞 Debugging

```bash
# Shell into VM
multipass shell k3s

# View VM info
multipass info k3s

# Check VM logs
multipass logs k3s

# Kubernetes debugging
kubectl get pods -n loom-dev
kubectl logs -f deployment/ingestion-api -n loom-dev
kubectl describe pod <pod-name> -n loom-dev
``` 