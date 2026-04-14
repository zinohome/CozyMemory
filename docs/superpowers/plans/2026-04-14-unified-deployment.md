# Unified Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a unified, resource-optimized production stack integrating Mem0, Memobase, and Cognee into a single Docker Compose environment on a remote server.

**Architecture:** A shared-infrastructure model utilizing a single pgvector PostgreSQL instance and a single Redis instance, with dedicated storage for Neo4j, Qdrant, and MinIO. Configuration is centralized via a `.env` file and orchestration is handled by Docker Compose.

**Tech Stack:** Docker Compose, PostgreSQL (pgvector), Redis, Neo4j, Qdrant, MinIO, Bash.

---

## File Mapping
- Create: `unified_deployment/.env.example` (Template for environment variables)
- Modify: `unified_deployment/docker-compose.1panel.yml` (Optimized for resource limits and .env variables)
- Create: `unified_deployment/scripts/health_check.sh` (Verification script)
- Create: `unified_deployment/scripts/rollback.sh` (Recovery script)

---

### Task 1: Configuration Templating

**Files:**
- Create: `unified_deployment/.env.example`

- [ ] **Step 1: Create the .env template with all necessary variables**

```env
# --- Global Settings ---
# Root directory for all Docker volumes
DATA_PATH=/data/cozy-memory
# Root password for PostgreSQL (used by init.sql)
POSTGRES_ROOT_PASSWORD=cozy_root_password
# Password for the shared Redis instance
REDIS_PASSWORD=cozy_redis_password

# --- Mem0 Settings ---
MEM0_OPENAI_API_KEY=sk-your-key-here
MEM0_OPENAI_BASE_URL=https://api.openai.com/v1
MEM0_OPENAI_MODEL=gpt-4o-mini

# --- Memobase Settings ---
MEMOBASE_LLM_API_KEY=sk-your-key-here
MEMOBASE_EMBEDDING_API_KEY=sk-your-key-here

# --- Cognee Settings ---
COGNEE_LLM_API_KEY=sk-your-key-here
COGNEE_EMBEDDING_API_KEY=sk-your-key-here
S3_ROOT_USER=minioadmin
S3_ROOT_PASSWORD=minioadmin
```

- [ ] **Step 2: Commit the template**
```bash
git add unified_deployment/.env.example
git commit -m "deploy: add .env template for unified deployment"
```

---

### Task 2: Optimized Docker Compose Orchestration

**Files:**
- Modify: `unified_deployment/docker-compose.1panel.yml`

- [ ] **Step 1: Update volume paths to use ${DATA_PATH} variable**
Replace all hardcoded `/data/cozy-memory/` with `${DATA_PATH}/`.

- [ ] **Step 2: Replace hardcoded passwords/keys with .env variables**
- Replace `POSTGRES_PASSWORD=cozy_root_password` with `${POSTGRES_ROOT_PASSWORD}`
- Replace `REDIS_PASSWORD=cozy_redis_password` with `${REDIS_PASSWORD}`
- Replace Cognee/Mem0 API keys with `${COGNEE_LLM_API_KEY}`, etc.

- [ ] **Step 3: Apply Resource Limits (RAM)**
Update the following service limits:
- `postgres`: `mem_limit: 2g`, `mem_reservation: 1g`
- `neo4j`: `mem_limit: 2g`, `mem_reservation: 512m` (Ensure `NEO4J_dbms_memory_heap_max__size=1G`)
- `cognee`: `mem_limit: 2g`, `mem_reservation: 512m`
- `mem0-api`: `mem_limit: 1g`, `mem_reservation: 256m`
- `memobase-server-api`: `mem_limit: 1g`, `mem_reservation: 256m`

- [ ] **Step 4: Commit the optimized compose file**
```bash
git add unified_deployment/docker-compose.1panel.yml
git commit -m "deploy: optimize compose with .env variables and resource limits"
```

---

### Task 3: Server Preparation & Deployment Sequence

**Files:**
- No files created here, purely operational steps.

- [ ] **Step 1: Prepare Server Directories**
Run on server:
```bash
mkdir -p /data/cozy-memory/postgres /data/cozy-memory/redis /data/cozy-memory/qdrant /data/cozy-memory/minio /data/cozy-memory/neo4j
chmod -R 755 /data/cozy-memory
```

- [ ] **Step 2: Deploy Environment Files**
1. Upload `unified_deployment/.env.example` as `.env` and fill in real keys.
2. Upload `unified_deployment/sql/init.sql` to the server.

- [ ] **Step 3: Execute Deployment**
```bash
docker compose -f unified_deployment/docker-compose.1panel.yml up -d
```

- [ ] **Step 4: Verify Container Status**
```bash
docker compose -f unified_deployment/docker-compose.1panel.yml ps
```
Expected: All containers should be `Up (healthy)` or `Up`.

---

### Task 4: Verification & Health Check System

**Files:**
- Create: `unified_deployment/scripts/health_check.sh`

- [ ] **Step 1: Write the health check script**

```bash
#!/bin/bash
echo "Checking CozyMemory Stack Health..."

# 1. Check Postgres
docker exec cozy_postgres pg_isready -U postgres
if [ $? -eq 0 ]; then echo "✅ Postgres: READY"; else echo "❌ Postgres: FAILED"; fi

# 2. Check Mem0 API
curl -s --head http://localhost:8888/api/v1/ | grep "200\|404" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Mem0 API: READY"; else echo "❌ Mem0 API: FAILED"; fi

# 3. Check Memobase API
curl -s --head http://localhost:8019/ | grep "200" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Memobase API: READY"; else echo "❌ Memobase API: FAILED"; fi

# 4. Check Cognee API
curl -s --head http://localhost:8000/ | grep "200" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Cognee API: READY"; else echo "❌ Cognee API: FAILED"; fi

echo "Health check complete."
```

- [ ] **Step 2: Make script executable and commit**
```bash
chmod +x unified_deployment/scripts/health_check.sh
git add unified_deployment/scripts/health_check.sh
git commit -m "deploy: add health check script"
```

---

### Task 5: Rollback Strategy

**Files:**
- Create: `unified_deployment/scripts/rollback.sh`

- [ ] **Step 1: Write the rollback script**

```bash
#!/bin/bash
echo "Rolling back deployment..."
# Stop and remove all containers
docker compose -f unified_deployment/docker-compose.1panel.yml down

# Optional: Backup existing data before wiping if this is a re-deployment
# tar -cvzf /data/cozy-memory-backup-$(date +%F).tar.gz /data/cozy-memory

echo "Stack stopped. Please check logs with 'docker compose logs' before re-deploying."
```

- [ ] **Step 2: Make script executable and commit**
```bash
chmod +x unified_deployment/scripts/rollback.sh
git add unified_deployment/scripts/rollback.sh
git commit -m "deploy: add rollback script"
```
