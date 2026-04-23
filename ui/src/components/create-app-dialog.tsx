"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateApp } from "@/lib/hooks/use-apps";
import { useT } from "@/lib/i18n";

export function CreateAppDialog({ trigger }: { trigger: React.ReactNode }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const m = useCreateApp();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await m.mutateAsync({ name, slug });
      toast.success(t("apps.created"));
      setOpen(false);
      setName("");
      setSlug("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("409")) toast.error(t("apps.slug_conflict"));
      else toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("apps.create")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label>{t("apps.name")}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label>{t("apps.slug")}</Label>
            <Input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              pattern="^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$"
              required
            />
          </div>
          <Button type="submit" disabled={m.isPending}>
            {t("apps.create_submit")}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
