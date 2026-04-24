# cozymemory — CozyMemory Python SDK

Thin, typed client for the [CozyMemory](../..) unified memory REST API
(conversation memory, user profile, knowledge graph).

## Install

```bash
pip install cozymemory
```

From source:

```bash
pip install -e path/to/CozyMemory/sdks/python
```

## Quickstart (sync)

```python
from cozymemory import CozyMemoryClient

with CozyMemoryClient(
    api_key="cozy_live_<your-key>",
    base_url="http://localhost:8000",
) as c:
    c.conversations.add(
        user_id="alice",
        messages=[
            {"role": "user", "content": "I love hiking"},
            {"role": "assistant", "content": "Got it."},
        ],
    )

    ctx = c.context.get_unified(user_id="alice", query="outdoor activity")
    print(ctx["conversations"], ctx["profile_context"], ctx["knowledge"])
```

## Quickstart (async)

```python
import asyncio
from cozymemory import CozyMemoryAsyncClient


async def main() -> None:
    async with CozyMemoryAsyncClient(
        api_key="cozy_live_<your-key>",
        base_url="http://localhost:8000",
    ) as c:
        await c.conversations.add(
            "alice",
            [{"role": "user", "content": "hello"}],
        )
        ctx = await c.context.get_unified("alice", query="anything")
        print(ctx)


asyncio.run(main())
```

## API Reference

### Client

```python
CozyMemoryClient(api_key: str, base_url: str = "http://localhost:8000")
CozyMemoryAsyncClient(api_key: str, base_url: str = "http://localhost:8000")
```

Both support context manager (`with` / `async with`) for connection lifecycle.

### `client.conversations`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `add` | `user_id: str, messages: list[dict]` | Add conversation, extract memories |
| `list` | `user_id: str` | List all memories for a user |
| `search` | `user_id: str, query: str, limit: int = 10` | Semantic search over memories |
| `get` | `memory_id: str` | Get a single memory |
| `delete` | `memory_id: str` | Delete a single memory |
| `delete_all` | `user_id: str` | Delete all memories for a user |

### `client.profiles`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `insert` | `user_id: str, messages: list[dict], sync: bool = False` | Insert conversation into Memobase buffer |
| `flush` | `user_id: str` | Trigger buffer processing |
| `get` | `user_id: str` | Get structured user profile |
| `get_context` | `user_id: str, max_token_size: int \| None = None` | Get LLM-ready context prompt |
| `add_item` | `user_id: str, topic: str, sub_topic: str, content: str` | Manually add a profile topic |
| `delete_item` | `user_id: str, profile_id: str` | Delete a profile topic |

### `client.knowledge`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `list_datasets` | _(none)_ | List all datasets |
| `create_dataset` | `name: str` | Create a new dataset |
| `delete_dataset` | `dataset_id: str` | Delete a dataset |
| `add` | `data: str, dataset: str` | Add document to knowledge base |
| `cognify` | `datasets: list[str] \| None = None, run_in_background: bool = False` | Trigger knowledge graph build |
| `search` | `query: str, dataset: str \| None = None, search_type: str \| None = None, top_k: int \| None = None` | Search knowledge graph |

`search_type` valid values: `"CHUNKS"`, `"SUMMARIES"`, `"RAG_COMPLETION"`, `"GRAPH_COMPLETION"`.

### `client.context`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `get_unified` | `user_id: str, query: str \| None = None` | Concurrently fetch all 3 memory types |

### `client.health()`

Liveness check — no authentication required. Returns the health status dict.

## Error handling

```python
from cozymemory import APIError, AuthError, CozyMemoryError

try:
    c.conversations.add(user_id="alice", messages=[...])
except AuthError:
    # 401 — invalid or missing X-Cozy-API-Key
    ...
except APIError as e:
    print(e.status_code, e.detail, e.body)
except CozyMemoryError:
    # Base class for all SDK errors
    ...
```

| Exception | When |
|-----------|------|
| `AuthError` | 401 Unauthorized — API key invalid or missing |
| `APIError` | Any other non-2xx response (has `.status_code`, `.detail`, `.body`) |
| `CozyMemoryError` | Base class; network errors, timeouts |

## Auth

Obtain `cozy_live_...` keys from the CozyMemory Dashboard (Apps → Keys).
They are sent via `X-Cozy-API-Key` automatically.

## License

MIT. See the main repo for details.
