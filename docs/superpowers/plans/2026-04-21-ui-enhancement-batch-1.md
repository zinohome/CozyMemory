# UI Enhancement Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade CozyMemory UI user-facing quality in 4 independent areas — Dialog, Toast, Optimistic delete, Knowledge dataset filter.

**Architecture:** Each area lands as its own commit behind a focused change. New UI primitives land in `components/ui/`, wrapper helpers in `components/`, and per-page migrations touch the page files directly. No backend change.

**Tech Stack:** Next.js 16 App Router, TypeScript, TanStack Query v5, shadcn primitives, Radix Dialog, sonner.

---

## Task 1: Dialog primitive + ConfirmDialog wrapper

**Files:**
- Create: `ui/src/components/ui/dialog.tsx`
- Create: `ui/src/components/confirm-dialog.tsx`
- Modify: `ui/package.json` (add `@radix-ui/react-dialog`)

- [ ] **Step 1: Install Radix Dialog**

Run from `ui/`:
```bash
npm install @radix-ui/react-dialog
```

Expected: `package.json` updated, no errors.

- [ ] **Step 2: Create `ui/src/components/ui/dialog.tsx`**

Standard shadcn Dialog primitive (Radix wrapper). Exports `Dialog`,
`DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogFooter`,
`DialogTitle`, `DialogDescription`, `DialogClose`.

```tsx
"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg rounded-lg data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col space-y-1.5 text-left", className)}
    {...props}
  />
);
DialogHeader.displayName = "DialogHeader";

const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
);
DialogFooter.displayName = "DialogFooter";

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none", className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
};
```

- [ ] **Step 3: Create `ui/src/components/confirm-dialog.tsx`**

Controlled wrapper for destructive confirmations.

```tsx
"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
}: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Replace `confirm()` in settings/page.tsx**

In `ui/src/app/(app)/settings/page.tsx`:

Import at top:
```tsx
import { ConfirmDialog } from "@/components/confirm-dialog";
```

Add state near other hooks:
```tsx
const [confirmState, setConfirmState] = useState<
  | { kind: "rotate"; id: string }
  | { kind: "delete"; id: string; name: string }
  | null
>(null);
```

Replace `handleRotate` body:
```tsx
async function handleRotate(id: string) {
  setConfirmState({ kind: "rotate", id });
}

async function doRotate(id: string) {
  try {
    const r = await adminFetch<ApiKeyCreateResponse>(`/api-keys/${id}/rotate`, { method: "POST" });
    setRevealedKey({ id, key: r.key, action: "rotated" });
    await refresh();
  } catch (e) {
    setLoadErr((e as Error).message);
  }
}
```

Replace `handleDelete` body similarly:
```tsx
function handleDelete(id: string, name: string) {
  setConfirmState({ kind: "delete", id, name });
}

async function doDelete(id: string) {
  try {
    await adminFetch(`/api-keys/${id}`, { method: "DELETE" });
    await refresh();
  } catch (e) {
    setLoadErr((e as Error).message);
  }
}
```

Render the dialog at the end of the outer `<div>`:
```tsx
<ConfirmDialog
  open={!!confirmState}
  onOpenChange={(o) => !o && setConfirmState(null)}
  title={
    confirmState?.kind === "rotate"
      ? "Rotate this key?"
      : `Delete key "${confirmState?.kind === "delete" ? confirmState.name : ""}"?`
  }
  description={
    confirmState?.kind === "rotate"
      ? "The old key will stop working immediately."
      : "This is immediate and irreversible."
  }
  confirmLabel={confirmState?.kind === "rotate" ? "Rotate" : "Delete"}
  destructive={confirmState?.kind === "delete"}
  onConfirm={() => {
    if (!confirmState) return;
    if (confirmState.kind === "rotate") doRotate(confirmState.id);
    else doDelete(confirmState.id);
  }}
/>
```

- [ ] **Step 5: Add confirmation in knowledge/page.tsx dataset delete**

Find `deleteDatasetMutation.mutate(ds.id)` trigger. Wrap it:

```tsx
const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; name: string } | null>(null);

// ... change onDelete prop in DatasetRow click handler to:
onDelete={() => setDeleteConfirm({ id: ds.id, name: ds.name })}

// At component bottom:
<ConfirmDialog
  open={!!deleteConfirm}
  onOpenChange={(o) => !o && setDeleteConfirm(null)}
  title={`Delete dataset "${deleteConfirm?.name}"?`}
  description="Also removes all graph data. Irreversible."
  confirmLabel="Delete"
  destructive
  onConfirm={() => {
    if (deleteConfirm) deleteDatasetMutation.mutate(deleteConfirm.id);
  }}
/>
```

- [ ] **Step 6: Type-check**

```bash
cd ui && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add ui/package.json ui/package-lock.json \
  ui/src/components/ui/dialog.tsx \
  ui/src/components/confirm-dialog.tsx \
  "ui/src/app/(app)/settings/page.tsx" \
  "ui/src/app/(app)/knowledge/page.tsx"
git commit -m "feat(ui): Dialog + ConfirmDialog replacing native confirm()"
```

---

## Task 2: Sonner Toast notifications

**Files:**
- Modify: `ui/package.json`
- Modify: `ui/src/app/layout.tsx`
- Modify: 6 page files

- [ ] **Step 1: Install sonner**

```bash
cd ui && npm install sonner
```

- [ ] **Step 2: Mount Toaster in root layout**

In `ui/src/app/layout.tsx`, import and place at end of body:

```tsx
import { Toaster } from "sonner";

// inside the RootLayout return, after {children}:
<Toaster position="top-right" richColors closeButton />
```

- [ ] **Step 3: Migrate Settings page**

Replace `setLoadErr(e.message)` calls with `toast.error(e.message)`.
Replace probe success inline banner with `toast.success("Key accepted")`.
Keep the Test button's inline probe state (it's field-contextual).
Remove `loadErr` state variable and its inline JSX render.

Pattern per call site:
```tsx
// before:
setLoadErr((e as Error).message);
// after:
import { toast } from "sonner";
toast.error((e as Error).message);
```

Successful admin operations:
```tsx
// after create:
toast.success(`Key "${name}" created`);
// after rotate:
toast.success("Key rotated");
// after delete:
toast.success(`Key "${name}" deleted`);
// after rename:
toast.success("Key renamed");
// after disable/enable:
toast.success(rec.disabled ? "Key enabled" : "Key disabled");
```

- [ ] **Step 4: Migrate Backup page**

In `ui/src/app/(app)/backup/page.tsx`:
- `setExportErr` → `toast.error`
- `setImportErr` → `toast.error`
- Keep `importResult` state for the summary card (it's detailed data, not a flash notification)
- Add `toast.success("Bundle downloaded")` after successful export
- Add `toast.success("Bundle imported")` after successful import

- [ ] **Step 5: Migrate Memory Lab**

In `ui/src/app/(app)/memory/page.tsx`, onError for deleteMutation and searchMutation:

```tsx
const deleteMutation = useMutation({
  mutationFn: (id: string) => conversationsApi.delete(id),
  onSuccess: () => {
    toast.success("Memory deleted");
    qc.invalidateQueries({ queryKey: ["memories", userId] });
  },
  onError: (e) => toast.error((e as Error).message),
});
```

- [ ] **Step 6: Migrate Profiles page**

Same pattern as Memory Lab. `addMutation`, `deleteMutation` gain `onSuccess` + `onError` with toast calls.

- [ ] **Step 7: Migrate Playground**

Replace `setErrorMsg` / the red paragraph below the ScrollArea. Instead:
```tsx
// in catch:
toast.error((e as Error).message);
```
Remove `errorMsg` state and the `<p className="text-xs text-destructive">` JSX.

Keep `saveStatus` in-band since it's a persistent footer indicator, not a notification.

- [ ] **Step 8: Migrate Knowledge page**

Find the error display around `deleteDatasetMutation`, `searchMutation`, `cognifyMutation`, `createDatasetMutation`. Attach `onError: (e) => toast.error(...)` to each.

Add success toasts for:
- createDatasetMutation: `toast.success(\`Dataset "${name}" created\`)`
- deleteDatasetMutation: `toast.success("Dataset deleted")`
- cognifyMutation: `toast.info("Cognify started — search may return 0 results until it finishes")`

- [ ] **Step 9: Type-check**

```bash
cd ui && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 10: Commit**

```bash
git add ui/package.json ui/package-lock.json \
  ui/src/app/layout.tsx \
  "ui/src/app/(app)/settings/page.tsx" \
  "ui/src/app/(app)/backup/page.tsx" \
  "ui/src/app/(app)/memory/page.tsx" \
  "ui/src/app/(app)/profiles/page.tsx" \
  "ui/src/app/(app)/playground/page.tsx" \
  "ui/src/app/(app)/knowledge/page.tsx"
git commit -m "feat(ui): global toast notifications via sonner"
```

---

## Task 3: Optimistic delete mutations

**Files:**
- Modify: 3 page files

- [ ] **Step 1: Memory Lab optimistic delete**

In `ui/src/app/(app)/memory/page.tsx`, change `deleteMutation`:

```tsx
const deleteMutation = useMutation({
  mutationFn: (id: string) => conversationsApi.delete(id),
  onMutate: async (id) => {
    await qc.cancelQueries({ queryKey: ["memories", userId] });
    const previous = qc.getQueryData<ConversationListResponse>(["memories", userId]);
    qc.setQueryData<ConversationListResponse>(["memories", userId], (old) => {
      if (!old) return old;
      return { ...old, data: (old.data ?? []).filter((m) => m.id !== id) };
    });
    return { previous };
  },
  onError: (e, _id, ctx) => {
    if (ctx?.previous) qc.setQueryData(["memories", userId], ctx.previous);
    toast.error((e as Error).message);
  },
  onSuccess: () => toast.success("Memory deleted"),
  onSettled: () => qc.invalidateQueries({ queryKey: ["memories", userId] }),
});
```

- [ ] **Step 2: Profiles optimistic delete**

In `ui/src/app/(app)/profiles/page.tsx`, `deleteMutation`:

```tsx
const deleteMutation = useMutation({
  mutationFn: (profileId: string) => profilesApi.deleteItem(userId, profileId),
  onMutate: async (profileId) => {
    await qc.cancelQueries({ queryKey: ["profile", userId] });
    const previous = qc.getQueryData<ProfileResponse>(["profile", userId]);
    qc.setQueryData<ProfileResponse>(["profile", userId], (old) => {
      if (!old?.data) return old;
      return {
        ...old,
        data: {
          ...old.data,
          topics: (old.data.topics ?? []).filter((t) => t.id !== profileId),
        },
      };
    });
    return { previous };
  },
  onError: (e, _id, ctx) => {
    if (ctx?.previous) qc.setQueryData(["profile", userId], ctx.previous);
    toast.error((e as Error).message);
  },
  onSuccess: () => toast.success("Topic deleted"),
  onSettled: () => qc.invalidateQueries({ queryKey: ["profile", userId] }),
});
```

- [ ] **Step 3: Knowledge dataset optimistic delete**

In `ui/src/app/(app)/knowledge/page.tsx`, `deleteDatasetMutation`:

```tsx
const deleteDatasetMutation = useMutation({
  mutationFn: (id: string) => knowledgeApi.deleteDataset(id),
  onMutate: async (id) => {
    await qc.cancelQueries({ queryKey: ["datasets"] });
    const previous = qc.getQueryData<typeof datasetsQuery.data>(["datasets"]);
    qc.setQueryData<typeof datasetsQuery.data>(["datasets"], (old) => {
      if (!old) return old;
      return { ...old, data: (old.data ?? []).filter((d) => d.id !== id) };
    });
    // clear selectedDataset if it was the one deleted
    if (selectedDataset?.id === id) setSelectedDataset(null);
    return { previous };
  },
  onError: (e, _id, ctx) => {
    if (ctx?.previous) qc.setQueryData(["datasets"], ctx.previous);
    toast.error((e as Error).message);
  },
  onSuccess: () => toast.success("Dataset deleted"),
  onSettled: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
});
```

- [ ] **Step 4: Type-check**

```bash
cd ui && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add "ui/src/app/(app)/memory/page.tsx" \
  "ui/src/app/(app)/profiles/page.tsx" \
  "ui/src/app/(app)/knowledge/page.tsx"
git commit -m "feat(ui): optimistic delete for memory/profile/dataset"
```

---

## Task 4: Knowledge Base dataset filter

**Files:**
- Modify: `ui/src/app/(app)/knowledge/page.tsx`

- [ ] **Step 1: Add filter state and computed list**

Near other useState hooks in `KnowledgeBasePage`:

```tsx
const [datasetFilter, setDatasetFilter] = useState("");

const filteredDatasets = useMemo(() => {
  const all = datasetsQuery.data?.data ?? [];
  const q = datasetFilter.trim().toLowerCase();
  if (!q) return all;
  return all.filter((d) => d.name.toLowerCase().includes(q));
}, [datasetsQuery.data, datasetFilter]);
```

Make sure `useMemo` is imported from react. Replace references in the
dataset list render from `datasetsQuery.data?.data?.map(...)` to
`filteredDatasets.map(...)`.

- [ ] **Step 2: Add filter input UI**

Above the Datasets list (find the `<p>Datasets</p>` header and its refresh button), add below them and above the list:

```tsx
<Input
  placeholder="Filter datasets…"
  value={datasetFilter}
  onChange={(e) => setDatasetFilter(e.target.value)}
  className="h-8 text-xs"
/>
```

- [ ] **Step 3: Add filter-aware empty state**

In the dataset list area, after mapping filteredDatasets:

```tsx
{filteredDatasets.length === 0 && !datasetsQuery.isLoading && (
  <p className="text-xs text-muted-foreground text-center py-4">
    {datasetFilter ? `No match for "${datasetFilter}"` : "No datasets yet."}
  </p>
)}
```

Keep the existing "No datasets" logic replaced by this unified message.

- [ ] **Step 4: Type-check**

```bash
cd ui && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add "ui/src/app/(app)/knowledge/page.tsx"
git commit -m "feat(ui): Knowledge Base dataset name filter"
```

---

## Task 5: Rebuild image + Playwright smoke + push

- [ ] **Step 1: Rebuild UI image**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
sudo ./base_runtime/build.sh cozymemory-ui
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d --force-recreate cozymemory-ui
```

Wait until `docker ps` shows cozy_ui Up.

- [ ] **Step 2: Playwright page sweep**

Visit all 9 pages, confirm 0 console errors:
- /dashboard, /memory, /profiles, /knowledge, /context, /playground, /users, /backup, /settings

- [ ] **Step 3: Interaction spot checks**

- Settings: open a key row's Delete; Dialog appears; click Cancel → no change; click Delete → toast.success fires.
- Memory Lab: select user, click trash on a memory row; row disappears before the HTTP request returns.
- Knowledge Base: type "grpc" in the new filter input; only grpc-* datasets visible.

- [ ] **Step 4: Push all 4 commits**

```bash
git push origin main
```

---

## Post-implementation checks

- [ ] `ui/src/app/` and `ui/src/components/` contain no `confirm(` or `alert(` calls
- [ ] `grep -r "setErrorMsg\|setLoadErr\|setExportErr\|setImportErr" ui/src/app/ | wc -l` is near 0 (only contextual keeps allowed)
- [ ] CHANGELOG.md gets an "Unreleased" section entry (defer to final commit or separate release)
- [ ] Playwright smoke: 9 pages × 0 errors
