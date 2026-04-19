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
cd base_runtime && ./build.sh cognee       # Build single image (cognee|mem0-api|mem0-webui|memobase|cognee-frontend|cozymemory)
docker compose -f base_runtime/docker-compose.1panel.yml up -d    # Start all engines + CozyMemory API
docker compose -f base_runtime/docker-compose.1panel.yml ps       # Check status

# Quick API smoke tests (requires running base_runtime)
curl http://SERVER_IP:8000/api/v1/health                          # Health check (all 3 engines)
curl http://SERVER_IP:8000/api/v1/conversations?user_id=u1        # List memories
curl -X POST http://SERVER_IP:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","messages":[{"role":"user","content":"test"}]}'
curl -X POST http://SERVER_IP:8000/api/v1/profiles/insert \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<uuid-v4>","messages":[{"role":"user","content":"test"}],"sync":true}'
curl -X POST http://SERVER_IP:8000/api/v1/profiles/<uuid-v4>/items \
  -H "Content-Type: application/json" \
  -d '{"topic":"interest","sub_topic":"hobby","content":"reading"}'
curl -X DELETE http://SERVER_IP:8000/api/v1/profiles/<uuid-v4>/items/<profile-id>
curl http://SERVER_IP:8000/api/v1/knowledge/datasets
curl -X DELETE http://SERVER_IP:8000/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -d '{"data_id":"<data-id>","dataset_id":"<dataset-id>"}'

# Integration tests (requires running base_runtime)
COZY_TEST_URL=http://SERVER_IP:8000 pytest tests/integration/ -v          # All 39 tests
COZY_TEST_URL=http://SERVER_IP:8000 pytest tests/integration/ -k "health" # Subset
pytest tests/integration/test_api_error_handlers.py -v                    # Error handling (no server needed)
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
- **Service layer** (`src/cozymemory/services/`): Thin wrappers that translate client responses into Pydantic models. One service per domain: `ConversationService`, `ProfileService`, `KnowledgeService`. `ContextService` composes all three via `asyncio.gather` for the unified context endpoint.
- **Client layer** (`src/cozymemory/clients/`): `BaseClient` provides httpx async connection pooling, exponential backoff retry, error handling, and a circuit breaker (opens after `failure_threshold` consecutive 5xx/network failures; 4xx errors don't count). Each engine (`Mem0Client`, `MemobaseClient`, `CogneeClient`) extends it.
- **Models** (`src/cozymemory/models/`): Pydantic v2 models for request/response serialization. `common.py` has shared types (`Message`, `EngineStatus`, `HealthResponse`, `ErrorResponse`).
- **Config** (`src/cozymemory/config.py`): `pydantic-settings` based, reads from `.env` file and environment variables. All engine URLs and feature flags are configured here.

### Engine-to-domain mapping

| Domain | Service | Client | Backend Engine |
|--------|---------|--------|---------------|
| Conversation memory | `ConversationService` | `Mem0Client` | Mem0 |
| User profile | `ProfileService` | `MemobaseClient` | Memobase |
| Knowledge graph | `KnowledgeService` | `CogneeClient` | Cognee |

### REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check for all 3 engines |
| GET | `/api/v1/conversations?user_id=` | List all memories for a user |
| POST | `/api/v1/conversations` | Add conversation, extract memories |
| POST | `/api/v1/conversations/search` | Semantic search over memories |
| GET | `/api/v1/conversations/{id}` | Get single memory |
| DELETE | `/api/v1/conversations/{id}` | Delete single memory |
| DELETE | `/api/v1/conversations?user_id=` | Delete all memories for user |
| POST | `/api/v1/profiles/insert` | Insert conversation into Memobase buffer |
| POST | `/api/v1/profiles/flush` | Trigger buffer processing |
| GET | `/api/v1/profiles/{user_id}` | Get structured user profile |
| POST | `/api/v1/profiles/{user_id}/context` | Get LLM-ready context prompt |
| POST | `/api/v1/profiles/{user_id}/items` | Manually add a profile topic |
| DELETE | `/api/v1/profiles/{user_id}/items/{profile_id}` | Delete a profile topic |
| GET | `/api/v1/knowledge/datasets` | List datasets |
| POST | `/api/v1/knowledge/datasets?name=` | Create dataset |
| POST | `/api/v1/knowledge/add` | Add document to knowledge base |
| POST | `/api/v1/knowledge/cognify` | Trigger knowledge graph build |
| POST | `/api/v1/knowledge/search` | Search knowledge graph |
| DELETE | `/api/v1/knowledge` | Delete a document by data_id + dataset_id |
| POST | `/api/v1/context` | Concurrently fetch all 3 memory types in one call |

### Dependency injection

`api/deps.py` creates singleton client instances lazily and provides `get_*_service()` functions used as FastAPI `Depends()` injectors. gRPC servicers also use these same dependency functions. `close_all_clients()` is called by the lifespan shutdown hook to release HTTP connection pools.

### Protobuf / gRPC

Proto definitions live in `proto/`. Generated Python code (`*_pb2.py`, `*_pb2_grpc.py`) is checked into `src/cozymemory/grpc_server/` and excluded from ruff/mypy checks. Total: 18 gRPC methods mirroring the 19 REST endpoints (health is REST-only). To regenerate, prefer the wrapper script (it resolves paths regardless of CWD):

```bash
./scripts/generate_grpc.sh
# or the raw form:
python -m grpc_tools.protoc -I proto --python_out=src/cozymemory/grpc_server --grpc_python_out=src/cozymemory/grpc_server proto/common.proto proto/conversation.proto proto/profile.proto proto/knowledge.proto
```

### Backend engine deployment (`base_runtime/`)

`base_runtime/docker-compose.1panel.yml` runs 11 services on `1panel-network`. Caddy exposes four ports: 8000 (CozyMemory unified API), 8080 (Cognee), 8081 (Mem0), 8019 (Memobase). Custom images are built by `base_runtime/build.sh` from source in sibling `Cozy*` project directories. Before deploying, replace `YOUR_SERVER_IP` in the compose file with the actual server IP. Tiktoken cache must be pre-copied to `/data/CozyMemory/tiktoken/`.

The CozyMemory unified API (`cozymemory:latest`) is built from the root `Dockerfile` using `deploy/supervisord.conf` to run REST (port 8000) and gRPC (port 50051) in a single container.

### Frontend (`ui/`)

Next.js 16 / React 19 admin UI (App Router) using `@base-ui/react` + shadcn + Tailwind v4, with TanStack Query for server state and Zustand for client state. It consumes the REST API described above.

- **Critical**: `ui/AGENTS.md` warns that this Next.js version has breaking changes vs. typical training-data knowledge — consult `ui/node_modules/next/dist/docs/` before writing Next-specific code (routing, `use server`, caching semantics).
- **API base URL**: `ui/src/lib/api.ts` reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`). In the Docker image, `ui/entrypoint.sh` rewrites the baked-in URL at container start so the same image runs in any deployment.
- Dev: `cd ui && npm run dev` (port 3000). Lint: `npm run lint`. Build: `npm run build`.

## Engine API Quirks

These are non-obvious behaviors discovered during integration testing. Check here before touching client code.

### Mem0 (`Mem0Client`)

- **API prefix**: All endpoints are under `/api/v1/` — server is patched by `apply_server_fixes.py` to add this prefix via `APIRouter`. Without the prefix, all routes return 404.
- **`add()` response format**: `{"results": [{"id": "...", "memory": "...", "event": "ADD"}]}` — not a bare list. Parse with `data.get("results", [])`.
- **`search()` / `get_all()` entity params**: The mem0ai library requires entity identifiers in `filters={"user_id": "..."}`, not as top-level kwargs. The server is patched (Fix 8/9 in `apply_server_fixes.py`) to wrap them correctly.
- **No `/health` endpoint**: `health_check()` probes `GET /` which returns Swagger UI (HTTP 200 after redirect).
- **`get()` returns null for missing memory**: Mem0 returns JSON `null` (not 404) when a memory ID doesn't exist. `Mem0Client.get()` handles this by returning `None`.
- **Auth header**: `X-API-Key` (not `Authorization: Bearer`) — see `Mem0Client._get_headers`.

### Memobase (`MemobaseClient`)

- **user_id must be UUID v4**: Memobase enforces UUID v4 format at the path level. String IDs like `"user_01"` will return HTTP 422.
- **`insert()` payload format**: `{"blob_type": "chat", "blob_data": {"messages": [...]}}` — not a bare `{"messages": [...]}`. The `blob_type` field is required.
- **Auto-create user**: `insert()` detects `ForeignKeyViolation` in the response body (HTTP 200 + `errno != 0`) and automatically calls `add_user()` then retries. Callers don't need to create users manually.
- **`add_user()` upsert semantics**: Creating a user that already exists returns HTTP 200 + `errno: 500` + `UniqueViolation`. This is silently ignored.
- **Business errors use HTTP 200 + errno**: Unlike REST conventions, Memobase returns HTTP 200 for all responses and encodes errors in `{"errno": <int>, "errmsg": "..."}`. `EngineError` is only raised for real HTTP 4xx/5xx.
- **`profile()` response format**: `{"data": {"profiles": [{"id", "content", "attributes": {"topic", "sub_topic"}}]}, "errno": 0}`.
- **`context()` response format**: `{"data": {"context": "<prompt text>"}, "errno": 0}`.
- **`/api/v1/healthcheck`**: Health endpoint includes the API prefix.

### Cognee (`CogneeClient`)

- **`search_type` values**: Must be one of the Cognee enum values: `CHUNKS`, `SUMMARIES`, `RAG_COMPLETION`, `GRAPH_COMPLETION`, etc. `"insights"` is not valid.
- **Two-step add flow**: `add()` stages data; `cognify()` builds the knowledge graph. Search returns `NoDataError` if cognify hasn't run yet.
- **Slow health check**: Cognee health check (calls `/api/v1/datasets`) typically takes 1–4 seconds due to graph DB queries. This is normal.

## Conventions

- Python 3.11+, async-first (all client calls are async)
- Pydantic v2 models with `Field` descriptions
- Ruff for linting/formatting (config in `pyproject.toml`), replaces black/isort/flake8
- MyPy strict on `src/cozymemory/` except `grpc_server/` subpackage
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Engine errors raised as `EngineError` with engine name and status code; API layer converts to HTTP 400/502
- Mem0 uses `X-API-Key` header (not Bearer token) — see `Mem0Client._get_headers`; other engines use `Authorization: Bearer`
- All responses follow `{success: bool, data: ..., message: str}` pattern
- `DEBUG=False` (default) suppresses exception details in 500 responses; set `DEBUG=True` or `APP_ENV=development` to expose them
- `SearchType` — `Literal["CHUNKS","SUMMARIES","RAG_COMPLETION","GRAPH_COMPLETION"]` alias exported from `models/knowledge.py`; use it in service/client signatures instead of bare `str`
- **Unified context pattern**: new cross-engine operations should use `asyncio.gather(..., return_exceptions=True)` and populate an `errors: dict[str, str]` field rather than failing the whole request when one engine is down
- `structlog` for structured logging: `logging_config.py` configures it; `ConsoleRenderer` in development, `JSONRenderer` in production. Request middleware binds `request_id`, `method`, `path` to every log line via `contextvars`.

## Project layout

- `src/cozymemory/` — main package (installed via pip -e)
- `tests/unit/` — unit tests (mocked, no engine backends needed)
- `tests/integration/` — integration tests (need running backends)
- `proto/` — protobuf definitions
- `base_runtime/` — **current active deployment** for the three backend engines (Mem0, Memobase, Cognee) and their infrastructure (PostgreSQL/pgvector, Redis, Qdrant, MinIO, Neo4j). This is what CozyMemory's service layer connects to. Ongoing development happens here.
- `ui/` — Next.js 16 admin frontend; see the "Frontend" section above.
- `docs/` — reference docs checked into the repo: `api-reference.md`, `architecture.md`, `data-models.md`, `deployment.md`, `sdk-clients.md`. Consult these for deeper detail before exploring source.
- `archive/` — inactive code and superseded configs (previous v1 impl, old deploy/, old unified_deployment/); do not modify.
- The top-level `README.md` is stale (references an old `src.api.main:app` entry point and outdated test paths). Trust this file and `pyproject.toml` over `README.md`.