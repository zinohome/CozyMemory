# cozymemory — CozyMemory Python SDK

Thin, typed client for the [CozyMemory](../..) unified memory REST API
(conversation memory, user profile, knowledge graph).

## Install

From source (until published on PyPI):

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

## Resources

| Attribute | Methods |
|---|---|
| `client.conversations` | `add`, `list`, `search`, `get`, `delete`, `delete_all` |
| `client.profiles` | `insert`, `flush`, `get`, `get_context`, `add_item`, `delete_item` |
| `client.knowledge` | `list_datasets`, `create_dataset`, `delete_dataset`, `add`, `cognify`, `search` |
| `client.context` | `get_unified` |
| `client.health()` | Liveness check (no auth). |

The async client mirrors the same attribute tree; call the methods with
`await`.

## Error handling

```python
from cozymemory import APIError, AuthError, CozyMemoryError

try:
    c.conversations.add(user_id="alice", messages=[...])
except AuthError:
    # 401 — check X-Cozy-API-Key
    ...
except APIError as e:
    # Any other non-2xx. e.status_code / e.detail / e.body
    ...
except CozyMemoryError:
    # Base class
    ...
```

## Auth

Obtain `cozy_live_...` keys from the CozyMemory Dashboard (Apps → Keys).
They are sent via `X-Cozy-API-Key` automatically.

## License

Apache-2.0. See the main repo for details.
