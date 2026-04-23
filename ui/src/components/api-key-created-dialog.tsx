"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Copy, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";

interface Props {
  keyValue: string | null;
  open: boolean;
  onClose: () => void;
}

export function ApiKeyCreatedDialog({ keyValue, open, onClose }: Props) {
  const t = useT();
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!keyValue) return;
    await navigator.clipboard.writeText(keyValue);
    setCopied(true);
    toast.success(t("keys.copied"));
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("keys.created_once")}</DialogTitle>
          <DialogDescription>{t("keys.created_warning")}</DialogDescription>
        </DialogHeader>
        <div className="rounded border bg-muted p-3 font-mono text-sm break-all">
          {keyValue}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={copy}>
            {copied ? (
              <CheckCircle2 className="size-4 mr-2" />
            ) : (
              <Copy className="size-4 mr-2" />
            )}
            {t("keys.copy")}
          </Button>
          <Button onClick={onClose}>{t("keys.saved_ack")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
