# @cozymemory/sdk — CozyMemory JS/TS SDK

Thin TypeScript client for the [CozyMemory](../..) unified memory REST API
(conversation memory, user profile, knowledge graph). Works in Node 18+ and
modern browsers (native `fetch`).

## Install

```bash
npm install @cozymemory/sdk
```

From source:

```bash
cd sdks/js && npm install && npm run build
npm install file:/path/to/CozyMemory/sdks/js
```

## Quickstart

```ts
import { CozyMemory } from "@cozymemory/sdk";

const client = new CozyMemory({
  apiKey: "cozy_live_<your-key>",
  baseUrl: "http://localhost:8000",
});

await client.conversations.add("alice", [
  { role: "user", content: "I love hiking" },
  { role: "assistant", content: "Got it." },
]);

const ctx = await client.context.getUnified("alice", "outdoor activity");
console.log(ctx.conversations, ctx.profile_context, ctx.knowledge);
```

## API Reference

### Client

```ts
new CozyMemory({ apiKey: string; baseUrl?: string })
```

Default `baseUrl` is `http://localhost:8000`.

### `client.conversations`

| Method | Parameters | Return Type | Description |
|--------|-----------|-------------|-------------|
| `add` | `userId: string, messages: Message[]` | `ConversationMemoryListResponse` | Add conversation, extract memories |
| `list` | `userId: string` | `ConversationMemoryListResponse` | List all memories for a user |
| `search` | `userId: string, query: string, limit?: number` | `ConversationMemoryListResponse` | Semantic search over memories |
| `get` | `memoryId: string` | `ConversationMemory` | Get a single memory |
| `delete` | `memoryId: string` | `DeleteResponse` | Delete a single memory |
| `deleteAll` | `userId: string` | `DeleteResponse` | Delete all memories for a user |

### `client.profiles`

| Method | Parameters | Return Type | Description |
|--------|-----------|-------------|-------------|
| `insert` | `userId: string, messages: Message[], sync?: boolean` | `InsertResponse` | Insert conversation into Memobase buffer |
| `flush` | `userId: string` | `InsertResponse` | Trigger buffer processing |
| `get` | `userId: string` | `ProfileResponse` | Get structured user profile |
| `getContext` | `userId: string, maxTokenSize?: number` | `ProfileContextResponse` | Get LLM-ready context prompt |
| `addItem` | `userId: string, topic: string, subTopic: string, content: string` | `InsertResponse` | Manually add a profile topic |
| `deleteItem` | `userId: string, profileId: string` | `DeleteResponse` | Delete a profile topic |

### `client.knowledge`

| Method | Parameters | Return Type | Description |
|--------|-----------|-------------|-------------|
| `listDatasets` | _(none)_ | `DatasetListResponse` | List all datasets |
| `createDataset` | `name: string` | `DatasetInfo` | Create a new dataset |
| `deleteDataset` | `datasetId: string` | `DeleteResponse` | Delete a dataset |
| `add` | `data: string, dataset: string` | `AddKnowledgeResponse` | Add document to knowledge base |
| `cognify` | `datasets?: string[], runInBackground?: boolean` | `CognifyResponse` | Trigger knowledge graph build |
| `search` | `query: string, opts?: SearchOptions` | `KnowledgeSearchResponse` | Search knowledge graph |

`SearchOptions`: `{ dataset?: string; searchType?: string; topK?: number }`

`searchType` valid values: `"CHUNKS"`, `"SUMMARIES"`, `"RAG_COMPLETION"`, `"GRAPH_COMPLETION"`.

### `client.context`

| Method | Parameters | Return Type | Description |
|--------|-----------|-------------|-------------|
| `getUnified` | `userId: string, query?: string` | `UnifiedContextResponse` | Concurrently fetch all 3 memory types |

### `client.health()`

Liveness check — no authentication required.

## Error handling

```ts
import { APIError, AuthError, CozyMemoryError } from "@cozymemory/sdk";

try {
  await client.conversations.add("alice", [...]);
} catch (e) {
  if (e instanceof AuthError) {
    // 401 — invalid or missing X-Cozy-API-Key
  } else if (e instanceof APIError) {
    console.error(e.statusCode, e.detail, e.body);
  } else if (e instanceof CozyMemoryError) {
    // base class for all SDK errors
  }
}
```

| Exception | When |
|-----------|------|
| `AuthError` | 401 Unauthorized — API key invalid or missing |
| `APIError` | Any other non-2xx response (has `.statusCode`, `.detail`, `.body`) |
| `CozyMemoryError` | Base class; network errors, timeouts |

## Types

All response types are exported from the package:

```ts
import type {
  ConversationMemory,
  ConversationMemoryListResponse,
  ProfileResponse,
  ProfileContextResponse,
  UnifiedContextResponse,
  DatasetInfo,
  KnowledgeSearchResponse,
  Message,
} from "@cozymemory/sdk";
```

## Auth

Grab `cozy_live_...` keys from the CozyMemory Dashboard (Apps → Keys). The
SDK sends them via the `X-Cozy-API-Key` header automatically.

## Notes

- ESM-only. Use Node 18+ or any bundler that supports ESM.
- No runtime dependencies; uses native `fetch` + `AbortController`.

## License

MIT. See the main repo for details.
