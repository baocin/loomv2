#!/bin/bash
# Setup k3s in multipass VM for local development
# Real Ubuntu VM with real k3s - perfect for macOS!

set -e

VM_NAME="k3s"
VM_IP=""

echo "🐄 Setting up k3s in multipass VM"
echo "================================="

# Check if multipass is installed
if ! command -v multipass &> /dev/null; then
    echo "📦 Installing multipass..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install --cask multipass
        else
            echo "❌ Please install multipass manually:"
            echo "   brew install --cask multipass"
            exit 1
        fi
    else
        echo "❌ Please install multipass for your OS:"
        echo "   https://multipass.run/install"
        exit 1
    fi
    echo "✅ Multipass installed!"
fi

# Check if VM exists
if multipass list | grep -q "$VM_NAME"; then
    echo "✅ VM $VM_NAME already exists"
    multipass start "$VM_NAME" 2>/dev/null || true
else
    echo "🚀 Creating multipass VM..."
    multipass launch --name "$VM_NAME" --mem 4G --disk 40G --cpus 2
    echo "✅ VM created!"
fi

# Get VM IP
echo "🔍 Getting VM IP address..."
VM_IP=$(multipass info "$VM_NAME" | grep IPv4 | awk '{print $2}')
echo "📍 VM IP: $VM_IP"

# Install k3s in VM
echo "📦 Installing k3s in VM..."
multipass exec "$VM_NAME" -- bash -c "
    if ! command -v k3s &> /dev/null; then
        echo 'Installing k3s...'
        curl -sfL https://get.k3s.io | sh -
        echo 'Waiting for k3s to start...'
        sleep 10
    else
        echo 'k3s already installed'
    fi
"

# Get kubeconfig from VM
echo "🔧 Setting up kubectl access..."
mkdir -p ~/.kube
multipass exec "$VM_NAME" -- sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config-k3s-multipass

# Update server IP in kubeconfig
sed "s/127.0.0.1/$VM_IP/g" ~/.kube/config-k3s-multipass > ~/.kube/config
chmod 600 ~/.kube/config

# Test connection
echo "🧪 Testing connection..."
if kubectl get nodes; then
    echo "✅ k3s cluster is ready!"
    echo ""
    echo "📊 Cluster info:"
    kubectl cluster-info
    echo ""
    echo "🎯 VM Details:"
    echo "  Name: $VM_NAME"
    echo "  IP: $VM_IP"
    echo "  Memory: 4GB"
    echo "  Disk: 40GB"
    echo ""
    echo "🚀 Next steps:"
    echo "  1. Deploy: ./scripts/deploy-k3s.sh"
    echo ""
    echo "🧹 VM Commands:"
    echo "  Shell into VM: multipass shell $VM_NAME"
    echo "  Stop VM: multipass stop $VM_NAME"
    echo "  Delete VM: multipass delete $VM_NAME && multipass purge"
else
    echo "❌ Failed to connect to k3s cluster"
    exit 1
fi 