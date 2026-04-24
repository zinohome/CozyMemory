# @cozymemory/sdk — CozyMemory JS/TS SDK

Thin TypeScript client for the [CozyMemory](../..) unified memory REST API
(conversation memory, user profile, knowledge graph). Works in Node 18+ and
modern browsers (native `fetch`).

## Install

From source (until published on npm):

```bash
cd sdks/js && npm install && npm run build
# then in your project:
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
```

## Resources

| Property | Methods |
|---|---|
| `client.conversations` | `add`, `list`, `search`, `get`, `delete`, `deleteAll` |
| `client.profiles` | `insert`, `flush`, `get`, `getContext`, `addItem`, `deleteItem` |
| `client.knowledge` | `listDatasets`, `createDataset`, `deleteDataset`, `add`, `cognify`, `search` |
| `client.context` | `getUnified` |
| `client.health()` | Liveness check (no auth). |

All methods return `Promise<unknown>` — cast to your own types in userland.

## Error handling

```ts
import { APIError, AuthError, CozyMemoryError } from "@cozymemory/sdk";

try {
  await client.conversations.add("alice", [...]);
} catch (e) {
  if (e instanceof AuthError) {
    // 401 — check X-Cozy-API-Key
  } else if (e instanceof APIError) {
    console.error(e.statusCode, e.detail, e.body);
  } else if (e instanceof CozyMemoryError) {
    // base class
  }
}
```

## Auth

Grab `cozy_live_...` keys from the CozyMemory Dashboard (Apps → Keys). The
SDK sends them via the `X-Cozy-API-Key` header automatically.

## Notes

- ESM-only (MVP). Use Node 18+ or any bundler that supports ESM.
- No runtime dependencies; uses native `fetch` + `AbortController`.

## License

Apache-2.0. See the main repo.
