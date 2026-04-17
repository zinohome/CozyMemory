# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CozyMemory is a unified AI memory service platform that integrates three memory engines: **Mem0** (conversation memory), **Memobase** (user profile), and **Cognee** (knowledge graph). It exposes both a REST API (FastAPI) and a gRPC API, with services that delegate to backend engine clients.

**Important**: The official `mem0ai` SDK is deliberately **not used**. All engine communication is via custom `httpx` HTTP clients against self-hosted engine backends.

## Commands

```bash
# Install (editable mode with dev dependencies)
pip install -e ".[dev]"

# Run REST API server
uvicorn cozymemory.app:create_app --factory --host 0.0.0.0 --port 8000

# Run gRPC server (registered as CLI entry point)
cozymemory-grpc

# Run tests
pytest tests/unit/ -v                           # Unit tests only
pytest tests/integration/ -v                     # Integration tests (need engine backends)
pytest tests/unit/ -v --cov=cozymemory           # With coverage
pytest tests/unit/test_conversation_service.py -v  # Single test file
pytest tests/unit/ -k "test_add" -v              # Tests matching name pattern

# Lint and format
ruff check src/ tests/
ruff format --check src/ tests/
ruff format src/ tests/                          # Auto-fix formatting

# Type checking
mypy src/cozymemory --ignore-missing-imports

# Backend engines (base_runtime)
cd base_runtime && ./build.sh all          # Build all custom images
cd base_runtime && ./build.sh cognee       # Build single image (cognee|mem0-api|mem0-webui|memobase|cognee-frontend)
docker compose -f base_runtime/docker-compose.1panel.yml up -d    # Start all engines
docker compose -f base_runtime/docker-compose.1panel.yml ps       # Check status
```

## Environment Configuration

Copy `.env.example` to `.env` and configure engine backends before running:

```
MEM0_API_URL=http://localhost:8888       # Default Mem0 port
MEMOBASE_API_URL=http://localhost:8019   # Default Memobase port
COGNEE_API_URL=http://localhost:8000     # Default Cognee port
MEM0_API_KEY=...
MEMOBASE_API_KEY=...
COGNEE_API_KEY=...
MEM0_ENABLED=true
MEMOBASE_ENABLED=true
COGNEE_ENABLED=true
APP_ENV=development   # Set to "production" to hide error details in responses
```

## Architecture

```
Request → FastAPI/gRPC → Service layer → Client (BaseClient subclass) → Backend engine
```

### Key layers

- **API layer** (`src/cozymemory/api/v1/`): FastAPI routers for REST; gRPC servicers in `grpc_server/server.py`. Both share the same service layer.
- **Service layer** (`src/cozymemory/services/`): Thin wrappers that translate client responses into Pydantic models. One service per domain: `ConversationService`, `ProfileService`, `KnowledgeService`.
- **Client layer** (`src/cozymemory/clients/`): `BaseClient` provides httpx async connection pooling, exponential backoff retry, and error handling. Each engine (`Mem0Client`, `MemobaseClient`, `CogneeClient`) extends it.
- **Models** (`src/cozymemory/models/`): Pydantic v2 models for request/response serialization. `common.py` has shared types (`Message`, `EngineStatus`, `HealthResponse`, `ErrorResponse`).
- **Config** (`src/cozymemory/config.py`): `pydantic-settings` based, reads from `.env` file and environment variables. All engine URLs and feature flags are configured here.

### Engine-to-domain mapping

| Domain | Service | Client | Backend Engine |
|--------|---------|--------|---------------|
| Conversation memory | `ConversationService` | `Mem0Client` | Mem0 |
| User profile | `ProfileService` | `MemobaseClient` | Memobase |
| Knowledge graph | `KnowledgeService` | `CogneeClient` | Cognee |

### Dependency injection

`api/deps.py` creates singleton client instances lazily and provides `get_*_service()` functions used as FastAPI `Depends()` injectors. gRPC servicers also use these same dependency functions.

### Protobuf / gRPC

Proto definitions live in `proto/`. Generated Python code (`*_pb2.py`, `*_pb2_grpc.py`) is checked into `src/cozymemory/grpc_server/` and excluded from ruff/mypy checks. To regenerate:

```bash
python -m grpc_tools.protoc -I proto --python_out=src/cozymemory/grpc_server --grpc_python_out=src/cozymemory/grpc_server proto/common.proto proto/conversation.proto proto/profile.proto proto/knowledge.proto
```

### Backend engine deployment (`base_runtime/`)

`base_runtime/docker-compose.1panel.yml` runs 10 services on `1panel-network`. Caddy exposes three ports: 8080 (Cognee), 8081 (Mem0), 8019 (Memobase). Custom images are built by `base_runtime/build.sh` from source in sibling `Cozy*` project directories. Before deploying, replace `YOUR_SERVER_IP` in the compose file with the actual server IP. Tiktoken cache must be pre-copied to `/data/CozyMemory/tiktoken/`.

## Conventions

- Python 3.11+, async-first (all client calls are async)
- Pydantic v2 models with `Field` descriptions
- Ruff for linting/formatting (config in `pyproject.toml`), replaces black/isort/flake8
- MyPy strict on `src/cozymemory/` except `grpc_server/` subpackage
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Engine errors raised as `EngineError` with engine name and status code; API layer converts to HTTP 400/502
- Mem0 uses `X-API-Key` header (not Bearer token) — see `Mem0Client._get_headers`; other engines use `Authorization: Bearer`
- All responses follow `{success: bool, data: ..., message: str}` pattern
- `DEBUG=True` (default) exposes full exception details in 500 responses; set `APP_ENV=production` / `DEBUG=False` to suppress
- `structlog` is listed as a dependency but not yet used; current code uses stdlib `logging`

## Project layout

- `src/cozymemory/` — main package (installed via pip -e)
- `tests/unit/` — unit tests (mocked, no engine backends needed)
- `tests/integration/` — integration tests (need running backends)
- `proto/` — protobuf definitions
- `base_runtime/` — **current active deployment** for the three backend engines (Mem0, Memobase, Cognee) and their infrastructure (PostgreSQL/pgvector, Redis, Qdrant, MinIO, Neo4j). This is what CozyMemory's service layer connects to. Ongoing development happens here.
- `archive/` — inactive code and superseded configs (previous v1 impl, old deploy/, old unified_deployment/); do not modify