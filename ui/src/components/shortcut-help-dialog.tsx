"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { HotkeyBinding } from "@/lib/use-hotkeys";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  bindings: HotkeyBinding[];
}

function renderKey(keys: string) {
  return keys.split(" ").map((k, i) => (
    <kbd
      key={i}
      className="inline-flex items-center justify-center rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] shadow-sm mr-1"
    >
      {k === "?" ? "?" : k}
    </kbd>
  ));
}

export function ShortcutHelpDialog({ open, onOpenChange, bindings }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Press <kbd className="px-1 border rounded text-[10px] bg-muted">?</kbd> anytime (outside
            text fields) to reopen this list.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5 text-sm">
          {bindings.map((b) => (
            <div key={b.keys} className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">{b.description}</span>
              <span className="flex items-center">{renderKey(b.keys)}</span>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
