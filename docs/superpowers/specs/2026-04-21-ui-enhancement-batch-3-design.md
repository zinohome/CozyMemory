# CozyMemory UI Enhancement — Batch 3 Design

**Date**: 2026-04-21
**Scope**: 3 polish/power-user features — Playground session persistence,
Sparkline hover tooltip, keyboard shortcuts.

## Items

### 1. Playground session persistence

Problem: Reloading Playground loses chat history. No way to switch sessions.

Solution: Zustand `persist` store, schema:
```ts
interface PlaygroundSession {
  id: string; title: string; userId: string;
  messages: ChatMsg[]; createdAt: number; updatedAt: number;
}
```
Cap 20 sessions (drop oldest). Playground UI adds session dropdown +
"New chat" button. Title auto-derived from first user message (40 chars).

### 2. Sparkline hover tooltip

Problem: Dashboard sparklines show shape only.

Solution: Sparkline takes optional `timestamps: number[]` prop. Mousemove
finds nearest point, renders absolute-positioned tooltip with value + ts.
Vertical guide line on hover. Pure SVG + CSS.

### 3. Keyboard shortcuts

Problem: No keyboard nav.

Solution: `useHotkeys` hook in `lib/use-hotkeys.ts`. Gmail-style `g x`
sequences + `?` for help dialog. Disabled when focus on input/textarea.

| Key | Route |
|-----|-------|
| `g d`/`g m`/`g p`/`g k`/`g c`/`g y`/`g u`/`g b`/`g s` | Dashboard/Memory/Profiles/Knowledge/Context/Playground/Users/Backup/Settings |
| `?` | Shortcut help dialog |

## Non-goals

- Cmd+K command palette
- User-editable shortcuts

## Files

New: `lib/playground-sessions-store.ts`, `lib/use-hotkeys.ts`,
`components/shortcut-help-dialog.tsx`, `components/hotkeys-provider.tsx`

Modified: `playground/page.tsx`, `components/sparkline.tsx`,
`dashboard/page.tsx`, `app/(app)/layout.tsx`

## Acceptance

- [ ] Playground messages persist across reload; session dropdown works
- [ ] Dashboard sparkline shows tooltip on hover
- [ ] `g d` and other sequences navigate; `?` opens dialog
- [ ] Shortcuts disabled when typing
- [ ] Playwright 8 pages 0 errors
