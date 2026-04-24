# Changelog

## 0.2.0 (2026-04-24)

- Full TypeScript types for all API responses (no more `<unknown>`)
- Full API reference documentation in README
- License changed to AGPL-3.0-or-later
- npm publish workflow (`sdk-v*` tag trigger)

## 0.1.0 (2026-04-24)

Initial release.

- `CozyMemory` client class with native `fetch`
- Four resource classes: `conversations`, `profiles`, `knowledge`, `context`
- `X-Cozy-API-Key` authentication
- Full TypeScript types for all API responses
- Three-tier error hierarchy: `CozyMemoryError` > `APIError` / `AuthError`
