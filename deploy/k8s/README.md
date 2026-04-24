# Kubernetes Deployment Example

This directory contains example K8s manifests for deploying the CozyMemory API.
Infrastructure services (PostgreSQL, Redis, Neo4j, etc.) are assumed to be
managed separately (e.g., via Helm charts or managed cloud services).

## Quick Start

```bash
# Create namespace and secrets
kubectl create namespace cozymemory
kubectl apply -f secret.yaml      # edit first!

# Deploy
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Verify
kubectl -n cozymemory get pods
kubectl -n cozymemory logs -f deployment/cozymemory-api
```

## Files

| File | Description |
|------|-------------|
| `secret.yaml` | Template for environment secrets |
| `deployment.yaml` | API deployment (REST + gRPC in one pod) |
| `service.yaml` | ClusterIP service exposing ports 8000 and 50051 |
