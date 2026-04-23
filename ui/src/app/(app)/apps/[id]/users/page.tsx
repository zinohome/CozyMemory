"use client";

import { use, useState } from "react";
import { toast } from "sonner";
import { Trash2, ChevronLeft, ChevronRight } from "lucide-react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { useAppUsers, useDeleteAppUser } from "@/lib/hooks/use-app-users";
import { useT } from "@/lib/i18n";

const PAGE = 20;

export default function UsersPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useT();
  const [offset, setOffset] = useState(0);
  const { data } = useAppUsers(id, PAGE, offset);
  const del = useDeleteAppUser(id);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  async function doDelete() {
    if (!deleteTarget) return;
    try {
      await del.mutateAsync(deleteTarget);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setDeleteTarget(null);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{t("users.ext_title")}</h1>

      <div className="rounded-md border">
        <div className="grid grid-cols-[2fr_3fr_1fr_auto] gap-2 px-3 py-2 text-sm font-medium border-b bg-muted/30">
          <div>{t("users.external_id")}</div>
          <div>{t("users.internal_uuid")}</div>
          <div>{t("users.created_at")}</div>
          <div />
        </div>
        {data?.data.map((u) => (
          <div
            key={u.external_user_id}
            className="grid grid-cols-[2fr_3fr_1fr_auto] gap-2 px-3 py-2 text-sm items-center border-b last:border-b-0"
          >
            <div className="truncate">{u.external_user_id}</div>
            <div className="font-mono text-xs truncate">{u.internal_uuid}</div>
            <div className="text-muted-foreground text-xs">
              {new Date(u.created_at).toLocaleString()}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setDeleteTarget(u.external_user_id)}
              aria-label={t("users.delete_gdpr")}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        ))}
        {(!data || data.data.length === 0) && (
          <div className="px-3 py-8 text-center text-sm text-muted-foreground">
            {t("users.none")}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t("users.pagination", { page, pages, total })}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE))}
            aria-label="prev"
          >
            <ChevronLeft className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            disabled={offset + PAGE >= total}
            onClick={() => setOffset(offset + PAGE)}
            aria-label="next"
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => {
          if (!v) setDeleteTarget(null);
        }}
        title={t("users.delete_gdpr")}
        description={t("users.delete_gdpr_desc")}
        destructive
        onConfirm={doDelete}
      />
    </div>
  );
}
