# CozyMemory UI Enhancement — Batch 2 Design

**Date**: 2026-04-21
**Scope**: Code-quality foundation — extract over-grown components, unify
TanStack Query usage, add Error Boundary, audit icon-only buttons for a11y.

## Motivation

Batch 1 shipped user-visible polish (Dialog/Toast/Optimistic/Filter).
Batch 2 pays down internal debt uncovered during that work: two page files
crossed 550 LOC, 4 raw `fetch()` calls sit outside the Query layer, zero
Error Boundary means any render throw shows a white screen, and icon-only
buttons lack `aria-label`.

## Items

### 1. Split over-grown page files

**Problem**: Large single-file components become hard to navigate, test, and
edit without conflicts. Two files crossed the pain threshold (550+ LOC).

**Solution**:
- `settings/page.tsx` (577 LOC) → extract `ServerApiKeysPanel` to
  `components/server-api-keys-panel.tsx`. Settings page retains only the
  Client Key card and mounts `<ServerApiKeysPanel />`. This lets the two
  concerns evolve independently (client-side local state vs server CRUD).
- `playground/page.tsx` (547 LOC) → extract `ContextInspector` to
  `components/context-inspector.tsx`. The inspector takes the last-fetched
  `ContextResponse` and renders the right-side panel; Playground keeps the
  chat loop.
- Dashboard and Knowledge stay as-is. Their internal helper functions
  already provide a reasonable layering.

### 2. Unify TanStack Query usage

**Problem**: 4 raw `fetch()` calls in `settings/page.tsx` (admin API helper,
key probe) and `backup/page.tsx` (export, import). These manually track
loading state, don't benefit from retry/devtools, and duplicate auth header
logic.

**Solution**:
- Backup export: `useMutation` that fetches the bundle and triggers
  download. Returns `mutate` + `isPending`.
- Backup import: `useMutation` that POSTs to `/backup/import`. Returns the
  `ImportResult` through React Query cache.
- Settings admin CRUD: convert `adminFetch<T>` helper into 5 `useMutation`
  hooks (create, update, rotate, delete, logs). Query list with `useQuery`.
- Client key probe: convert Settings "Test" button logic from manual state
  to a `useMutation`.
- `/api/chat` streaming is left as raw fetch — TanStack Query's mutation
  model doesn't fit ReadableStream consumption.

### 3. Error Boundary

**Problem**: Next.js App Router uses its own error boundary pattern. We
have neither `error.tsx` nor `global-error.tsx`, so any uncaught render
error shows the default unstyled fallback or a blank page.

**Solution**:
- `ui/src/app/error.tsx` — nested error boundary for routed pages. Shows
  "Something went wrong" + Reset button + toast of the error message.
- `ui/src/app/global-error.tsx` — root-level error boundary. Uses plain
  `<html>/<body>` because it replaces RootLayout when fired. Simpler UI.
- Both respect `process.env.NODE_ENV !== "production"` to show the error
  message; in prod, show a generic copy only.

### 4. Icon button aria-label audit

**Problem**: `<Button size="icon">` with only a `<Trash2 />` icon child
presents no accessible name to screen readers. The existing `title="..."`
helps sighted users on hover but doesn't satisfy ARIA.

**Solution**:
- Add `aria-label="..."` to every icon-only button.
- Keep `title` for sighted hover tooltip parity.
- Also extend to: theme toggle, sidebar trigger, graph filter buttons,
  dashboard refresh.

Scope per file (estimates):
- Settings (~5 buttons)
- Memory Lab (1: Trash per row)
- Profiles (1: Trash per row)
- Knowledge Base (~4: delete row, refresh, create, graph refresh)
- Knowledge Graph component (type toggle pills)
- Theme toggle, sidebar trigger (1 each)
- Backup (copy button if any)
- Playground (~4: cancel, send, reset, copy)

Total: ~20 fixes.

## Non-goals

- i18n layer
- Responsive breakpoint sweep
- Hardcoded dark mode color cleanup
- Any feature additions

## Architecture impact

- New components: `components/server-api-keys-panel.tsx`,
  `components/context-inspector.tsx`
- New Next.js files: `app/error.tsx`, `app/global-error.tsx`
- `settings/page.tsx` and `playground/page.tsx` shrink substantially
- 4 raw `fetch` call sites replaced by `useQuery`/`useMutation`
- Icon buttons gain `aria-label` attribute

No runtime behaviour changes expected. Bundle size might shrink slightly
(shared error boundary vs per-page try/catch).

## Test strategy

- `npx tsc --noEmit` must pass.
- Rebuild UI image, Playwright sweep 8 pages — 0 console errors.
- Manual spot checks:
  - Throw in a page to confirm `error.tsx` renders.
  - Settings CRUD still works after mutation refactor.
  - Backup download/import still works.
  - Screen reader (or devtools accessibility tab) reports each icon button
    with a name.

## Rollback plan

Each item is one commit, independently revertable. Error boundary addition
is additive; Query migration keeps the same functional behaviour; file
extraction doesn't change semantics; aria-label is pure attribute addition.

## Acceptance criteria

- [ ] `settings/page.tsx` < 250 LOC
- [ ] `playground/page.tsx` < 400 LOC
- [ ] No `await fetch(` in `src/app/(app)/` except `playground` (stream)
- [ ] `app/error.tsx` and `app/global-error.tsx` exist
- [ ] Every `<Button size="icon">` has `aria-label`
- [ ] Playwright: 8 pages 0 console errors
