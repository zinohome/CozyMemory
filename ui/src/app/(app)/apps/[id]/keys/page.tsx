"use client";

import { use, useState } from "react";
import { toast } from "sonner";
import { Plus, RotateCw, Trash2 } from "lucide-react";

import { ApiKeyCreatedDialog } from "@/components/api-key-created-dialog";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAppKeys,
  useCreateKey,
  useDeleteKey,
  useRotateKey,
  type KeyCreated,
} from "@/lib/hooks/use-app-keys";
import { useT } from "@/lib/i18n";

export default function KeysPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useT();
  const { data: keys, isLoading } = useAppKeys(id);
  const createM = useCreateKey(id);
  const rotateM = useRotateKey(id);
  const deleteM = useDeleteKey(id);

  const [name, setName] = useState("");
  const [revealed, setRevealed] = useState<KeyCreated | null>(null);
  const [rotateTarget, setRotateTarget] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  async function create() {
    try {
      const r = await createM.mutateAsync({ name: name.trim() || "key" });
      setRevealed(r);
      setName("");
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function doRotate() {
    if (!rotateTarget) return;
    try {
      const r = await rotateM.mutateAsync(rotateTarget);
      setRevealed(r);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setRotateTarget(null);
    }
  }

  async function doDelete() {
    if (!deleteTarget) return;
    try {
      await deleteM.mutateAsync(deleteTarget);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setDeleteTarget(null);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{t("keys.title")}</h1>

      <div className="flex gap-2">
        <Input
          placeholder={t("keys.name_placeholder")}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button onClick={create} disabled={createM.isPending}>
          <Plus className="size-4 mr-2" />
          {t("keys.create")}
        </Button>
      </div>

      <div className="rounded border">
        <div className="grid grid-cols-[2fr_2fr_1fr_1.5fr_auto] gap-2 px-4 py-2 border-b bg-muted/50 text-xs font-medium text-muted-foreground">
          <div>{t("keys.name")}</div>
          <div>{t("keys.prefix")}</div>
          <div>{t("keys.status")}</div>
          <div>{t("keys.last_used")}</div>
          <div />
        </div>
        {isLoading ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            {t("common.loading")}
          </div>
        ) : !keys || keys.length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            {t("common.noResults")}
          </div>
        ) : (
          keys.map((k) => (
            <div
              key={k.id}
              className="grid grid-cols-[2fr_2fr_1fr_1.5fr_auto] gap-2 px-4 py-3 border-b last:border-b-0 items-center text-sm"
            >
              <div className="truncate">{k.name}</div>
              <div className="font-mono text-xs truncate">{k.prefix}…</div>
              <div>
                <Badge variant={k.disabled ? "secondary" : "default"}>
                  {k.disabled
                    ? t("settings.server.disabledBadge")
                    : t("keys.status_active")}
                </Badge>
              </div>
              <div className="text-muted-foreground">
                {k.last_used_at
                  ? new Date(k.last_used_at).toLocaleString()
                  : "—"}
              </div>
              <div className="flex gap-1 justify-end">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t("keys.rotate")}
                  onClick={() => setRotateTarget(k.id)}
                >
                  <RotateCw className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t("common.delete")}
                  onClick={() => setDeleteTarget(k.id)}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      <ApiKeyCreatedDialog
        keyValue={revealed?.key ?? null}
        open={!!revealed}
        onClose={() => setRevealed(null)}
      />

      <ConfirmDialog
        open={!!rotateTarget}
        onOpenChange={(v) => !v && setRotateTarget(null)}
        title={t("keys.rotate_confirm_title")}
        description={t("keys.rotate_confirm_desc")}
        confirmLabel={t("keys.rotate")}
        onConfirm={doRotate}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title={t("keys.delete_confirm_title")}
        description={t("keys.delete_confirm_desc")}
        confirmLabel={t("common.delete")}
        destructive
        onConfirm={doDelete}
      />
    </div>
  );
}
