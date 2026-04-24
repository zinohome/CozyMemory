# Changelog

## 0.1.0 (2026-04-24)

Initial release.

- `CozyMemory` client class with native `fetch`
- Four resource classes: `conversations`, `profiles`, `knowledge`, `context`
- `X-Cozy-API-Key` authentication
- Full TypeScript types for all API responses
- Three-tier error hierarchy: `CozyMemoryError` > `APIError` / `AuthError`
