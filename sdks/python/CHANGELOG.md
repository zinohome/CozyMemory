# Changelog

## 0.2.0 (2026-04-24)

- Full API reference documentation in README
- License changed to AGPL-3.0-or-later
- PyPI publish workflow (`sdk-v*` tag trigger)

## 0.1.0 (2026-04-24)

Initial release.

- `CozyMemoryClient` with sync and async support (`httpx`)
- Four resource classes: `conversations`, `profiles`, `knowledge`, `context`
- `X-Cozy-API-Key` authentication
- Three-tier error hierarchy: `CozyMemoryError` > `APIError` / `AuthError`
- Context manager support for connection lifecycle
