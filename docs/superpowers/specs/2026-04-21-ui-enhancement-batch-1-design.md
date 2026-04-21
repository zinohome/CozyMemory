# CozyMemory UI Enhancement — Batch 1 Design

**Date**: 2026-04-21
**Target version**: next minor after v0.1.0
**Scope**: 4 high-impact, user-facing UI quality items

## Motivation

UI audit (9459 lines of TS/TSX) surfaced ~20 enhancement opportunities. This
first batch picks the 4 that users perceive on every session: modal
confirmations, centralised feedback, instant delete response, and searchable
dataset list.

## Items

### 1. Replace native `confirm()` with Dialog component

**Problem**: `settings/page.tsx` uses browser-native `confirm()` for rotate
and delete. Two UX issues: (a) style clash with the rest of the app, (b)
mobile browsers show it inconsistently, (c) cannot customise label or
destructive styling.

**Solution**:
- Add `components/ui/dialog.tsx` (Radix-based, shadcn pattern)
- Add `components/confirm-dialog.tsx` — a self-contained `<ConfirmDialog>`
  that wraps Dialog with `title`, `description`, `confirmLabel`,
  `destructive`, `onConfirm`, `open`, `onOpenChange`
- Replace 2 `confirm()` calls in Settings (rotate, delete)
- Add missing confirmation in Knowledge Base before deleting a dataset
  (currently no confirm — single-click destructive)

**Dependencies**: `@radix-ui/react-dialog`

### 2. Global Toast notifications

**Problem**: Each page maintains its own `errorMsg` / `loadErr` / `probeMsg`
state plus inline red/green text. Inconsistent layout, users may miss errors
that scroll off screen, no auto-dismiss.

**Solution**:
- Install `sonner` (lightweight, shadcn-recommended toast library)
- Mount `<Toaster />` in `app/layout.tsx` (root, not AppLayout, so it's
  reachable from auth/error pages too)
- Import `toast` from `sonner` where needed:
  `toast.success("Key saved")`, `toast.error(e.message)`, `toast.info(...)`
- Migrate error/success paths in: Settings, Backup, Memory Lab, User
  Profiles, Knowledge Base, Playground. Keep inline errors only where they
  describe a specific form field's state (e.g. "probe result" next to the
  Test button in Settings is contextual — keep that).

**Dependencies**: `sonner`

### 3. Optimistic delete for memory / profile / dataset

**Problem**: Deleting a memory in Memory Lab or a profile topic in Profiles
requires waiting for the HTTP round-trip before the row disappears. Feels
sluggish.

**Solution**: Use TanStack Query's `onMutate` / `onError` rollback pattern.

Scope:
- Memory Lab `deleteMutation` (for single memory)
- User Profiles `deleteMutation` (for single topic)
- Knowledge Base `deleteDatasetMutation`

Not in scope (non-destructive or already async-non-blocking):
- Playground "save to memory" — already fire-and-forget
- Conversation `deleteAll` — lower frequency, skip

### 4. Knowledge Base dataset search filter

**Problem**: Datasets sidebar shows all datasets. Even after integration
test cleanup, production use will grow this list. No way to filter.

**Solution**:
- Add `<Input placeholder="Filter datasets..." />` at top of Datasets
  sidebar, above the list
- Client-side `datasets.filter(d => d.name.toLowerCase().includes(q))`
- Show "No match for 'xxx'" empty state when filter active and 0 results

## Non-goals

- Dark-mode color hardcoding (separate cleanup)
- i18n layer (out of v0.1 scope)
- React Error Boundary (batch 2)
- Large-file refactors (batch 2)

## Architecture impact

- New UI primitives in `components/ui/dialog.tsx`
- New wrapper in `components/confirm-dialog.tsx`
- Root layout gets `<Toaster />`
- Per-page: replace `errorMsg` state with `toast.error()` calls; remove
  inline error JSX; use `onMutate` for optimistic cache updates

## Test strategy

- `npx tsc --noEmit` must pass
- Rebuild UI image, Playwright browse 8 pages — all should remain 0 console
  errors
- Manual spot-check:
  - Settings: click Delete key → Dialog appears, Cancel keeps key, Confirm
    removes it, toast.success fires
  - Memory Lab: click trash on a memory → row disappears immediately (before
    HTTP returns)
  - Knowledge Base: type "grpc" in filter → only grpc-* datasets visible

## Rollback plan

Each of the 4 items is in its own commit so any can be reverted
independently. Dialog/Toast dependencies stay in package.json; removing them
is trivial if we ever backtrack.

## Dependencies added

```
@radix-ui/react-dialog
sonner
```

Both ~5-10KB gzipped, acceptable size impact.

## Acceptance criteria

- [ ] No `confirm()` or `alert()` calls anywhere in `src/app` or
  `src/components`
- [ ] 10+ error/success paths migrated to `toast.*`
- [ ] Delete interactions in 3 pages produce sub-100ms UI response
- [ ] Knowledge Base has a working filter input
- [ ] Playwright smoke across 8 pages: 0 console errors
- [ ] All 329 unit tests still pass (no backend change)
