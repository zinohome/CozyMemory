---
name: Unified Deployment Specification
description: Specification for merging Mem0, Memobase, and Cognee into a single production-ready environment.
type: project
date: 2026-04-14
status: approved
---

# Unified Deployment Specification: CozyMemory Stack

## 1. Overview
This document specifies the architecture and configuration for deploying the unified CozyMemory memory service platform. It merges three independent engine environments into a single, resource-optimized Docker Compose stack.

## 2. System Requirements
- **OS**: Linux (Ubuntu 22.04+ recommended)
- **Docker**: 24.0+ with Docker Compose v2
- **Minimum Hardware**: 
  - CPU: 4 Cores
  - RAM: 16GB (Critical due to Neo4j and Cognee memory requirements)
  - Disk: 50GB+ (SSD recommended for vector DB performance)
- **External Network**: `1panel-network` must be pre-created.

## 3. Architecture Design

### 3.1 Shared Infrastructure Layer
To minimize overhead, the stack shares core database components:
- **PostgreSQL (pgvector)**: Single instance handling both `cognee_db` and `memobase` databases.
- **Redis**: Single instance using DB 0 (Cognee) and DB 1 (Memobase) for isolation.
- **Dedicated Stores**: Qdrant (Mem0), Neo4j (Cognee), and MinIO (Cognee) remain independent.

### 3.2 Traffic Routing
- **Gateway Strategy**: All services are internal to `1panel-network`.
- **Port Mapping**:
  - Mem0 API: `8888` $\rightarrow$ `8000`
  - Memobase API: `8019` $\rightarrow$ `8000`
  - Cognee API: `8000` $\rightarrow$ `8000` (Change to `8080` or similar recommended if conflict occurs)
  - WebUIs: 3000, 3001 as configured.

## 4. Configuration Management

### 4.1 Environment Variables (`.env`)
All sensitive data is extracted to a `.env` file.

```env
# --- Global Settings ---
DATA_PATH=/data/cozy-memory
POSTGRES_ROOT_PASSWORD=cozy_root_password
REDIS_PASSWORD=cozy_redis_password

# --- Mem0 Settings ---
MEM0_OPENAI_API_KEY=sk-...
MEM0_OPENAI_BASE_URL=https://api.openai.com/v1
MEM0_OPENAI_MODEL=gpt-4o-mini

# --- Memobase Settings ---
MEMOBASE_LLM_API_KEY=sk-...
MEMOBASE_EMBEDDING_API_KEY=sk-...

# --- Cognee Settings ---
COGNEE_LLM_API_KEY=sk-...
COGNEE_EMBEDDING_API_KEY=sk-...
S3_ROOT_USER=minioadmin
S3_ROOT_PASSWORD=minioadmin
```

### 4.2 Resource Constraints
Limits are enforced to prevent OOM crashes:
- **Neo4j**: Heap initial 512MB, Max 2GB.
- **APIs**: Memory limit 2GB, Reservation 512MB.

## 5. Deployment Workflow

### 5.1 Pre-deployment
1. Create root directory: `mkdir -p /data/cozy-memory`
2. Upload `init.sql` to `unified_deployment/sql/`
3. Create `.env` file in the root of the deployment folder.

### 5.2 Execution
```bash
docker compose -f docker-compose.1panel.yml up -d
```

### 5.3 Verification (Post-Deployment)
Run a health check script to verify connectivity:
- [ ] Postgres: Port 5432 $\rightarrow$ Check if `cognee_db` and `memobase` exist.
- [ ] Mem0: `curl http://localhost:8888/api/v1/` $\rightarrow$ Expect 200/404 (not 502).
- [ ] Memobase: `curl http://localhost:8019/` $\rightarrow$ Expect 200.
- [ ] Cognee: `curl http://localhost:8000/` $\rightarrow$ Expect 200.

## 6. Backup & Recovery
- **Database**: Dump `postgres` and `qdrant` volumes.
- **Volumes**: Periodically backup `/data/cozy-memory` using tar or rsync.
