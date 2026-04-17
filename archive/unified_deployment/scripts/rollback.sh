#!/bin/bash
echo "Rolling back deployment..."
# Stop and remove all containers
docker compose -f unified_deployment/docker-compose.1panel.yml down

# Optional: Backup existing data before wiping if this is a re-deployment
# tar -cvzf /data/cozy-memory-backup-$(date +%F).tar.gz /data/cozy-memory

echo "Stack stopped. Please check logs with 'docker compose logs' before re-deploying."
