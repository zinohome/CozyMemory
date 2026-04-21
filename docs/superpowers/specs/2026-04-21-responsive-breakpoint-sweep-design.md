# Responsive Breakpoint Sweep — Design

**Date**: 2026-04-21
**Scope**: Fix 7 narrow-viewport layout issues found in live 375px audit.

## Audit findings

Measured `main.scrollWidth = 395` vs `clientWidth = 375` on /knowledge at
375px viewport — the page horizontally scrolls because a long dataset name
stretches its containing card past the viewport. Controls around it get
clipped.

## Fixes

### Dashboard

1. Top stat cards: drop `col-span-2 sm:col-span-1` wrapper on API Status.
   Grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`.
2. Engine Health `<CardTitle>`: add `min-w-0` on name span, `shrink-0` on badge.

### Knowledge Base

3. DatasetRow: `min-w-0` on flex child; `truncate` on name/prefix `<p>`.
4. Datasets card content: `min-w-0` as needed.
5. Create-dataset row: `<Input>` gets `min-w-0 flex-1` so "+" stays visible.
6. Graph tab header row: `flex-wrap` so Refresh wraps at narrow width.
7. Type filter pill strip: verify `flex-wrap` already there; no change
   unless broken.

## Acceptance

- [ ] `main.scrollWidth === clientWidth` on /knowledge at 375px
- [ ] Long dataset names truncate with …
- [ ] Engine Health names + badges both visible
- [ ] 8 pages 0 console errors after fixes
