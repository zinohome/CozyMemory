# Changelog

## 0.1.0 (2026-04-24)

Initial release.

- `CozyMemoryClient` with sync and async support (`httpx`)
- Four resource classes: `conversations`, `profiles`, `knowledge`, `context`
- `X-Cozy-API-Key` authentication
- Three-tier error hierarchy: `CozyMemoryError` > `APIError` / `AuthError`
- Context manager support for connection lifecycle
