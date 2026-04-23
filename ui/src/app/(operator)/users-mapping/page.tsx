"use client";

import { useState } from "react";
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query";
import { operatorApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, KeyRound, Trash2, Plus, Search, Copy, Check } from "lucide-react";
import { useT } from "@/lib/i18n";

// ── Copy-to-clipboard mini hook ───────────────────────────────────────────

function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  function copy(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(text);
      setTimeout(() => setCopied(null), 1500);
    });
  }
  return { copy, copied };
}

// ── Row-level delete confirmation ─────────────────────────────────────────

function DeleteCell({
  userId,
  onConfirm,
  isDeleting,
}: {
  userId: string;
  onConfirm: () => void;
  isDeleting: boolean;
}) {
  const t = useT();
  const [confirming, setConfirming] = useState(false);

  if (isDeleting) {
    return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
  }

  if (confirming) {
    return (
      <span className="flex items-center gap-1">
        <Button
          size="sm"
          variant="destructive"
          className="h-6 px-2 text-xs"
          onClick={() => { setConfirming(false); onConfirm(); }}
        >
          {t("common.yes")}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 px-2 text-xs"
          onClick={() => setConfirming(false)}
        >
          {t("common.no")}
        </Button>
      </span>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7 opacity-40 hover:opacity-100"
      title={t("common.delete")}
      aria-label={t("users.delete.aria", { id: userId })}
      onClick={() => setConfirming(true)}
    >
      <Trash2 className="h-3.5 w-3.5 text-destructive" />
    </Button>
  );
}

// ── UUID cell (fetched lazily per row) ────────────────────────────────────

function UuidCell({ uuid, loading, error }: {
  userId: string;
  uuid?: string | null;
  loading: boolean;
  error: boolean;
}) {
  const t = useT();
  const { copy, copied } = useCopy();

  if (loading) return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />;
  if (error) return <span className="text-xs text-muted-foreground">—</span>;
  if (!uuid) return <span className="text-xs text-muted-foreground italic">{t("users.table.noMapping")}</span>;

  return (
    <span className="flex items-center gap-1.5 font-mono text-xs">
      <span className="truncate max-w-[220px] hidden sm:block">{uuid}</span>
      <span className="sm:hidden text-muted-foreground">{uuid.slice(0, 8)}…</span>
      <button
        onClick={() => copy(uuid)}
        className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
        title={t("users.copy.tooltip")}
        aria-label={t("users.copy.tooltip")}
      >
        {copied === uuid ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
      </button>
    </span>
  );
}

// ── Create mapping panel ──────────────────────────────────────────────────

function CreateMappingPanel({ onCreated }: { onCreated: () => void }) {
  const t = useT();
  const [newId, setNewId] = useState("");

  const mutation = useMutation({
    mutationFn: () => operatorApi.getUserUuid(newId, true),  // create=true
    onSuccess: () => {
      setNewId("");
      onCreated();
    },
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Plus className="h-4 w-4" />
          {t("users.create.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          {t("users.create.desc")}
        </p>
        <div className="flex gap-2">
          <div className="flex-1 space-y-1">
            <Label htmlFor="new-uid">{t("common.userId")}</Label>
            <Input
              id="new-uid"
              placeholder={t("users.create.placeholder")}
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && newId && mutation.mutate()}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={() => mutation.mutate()} disabled={!newId || mutation.isPending}>
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t("users.create.btn")}
            </Button>
          </div>
        </div>
        {mutation.isSuccess && (
          <div className="rounded-md bg-muted px-3 py-2 text-xs space-y-0.5">
            <p className="font-medium">{mutation.data.user_id}</p>
            <p className="font-mono text-muted-foreground">{mutation.data.uuid}</p>
            <Badge variant="secondary" className="mt-1">
              {mutation.data.created ? t("users.create.result.new") : t("users.create.result.existing")}
            </Badge>
          </div>
        )}
        {mutation.isError && (
          <p className="text-xs text-destructive">{String(mutation.error)}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function UsersPage() {
  const t = useT();
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");

  // Full user list
  const usersQuery = useQuery({
    queryKey: ["operator", "users"],
    queryFn: operatorApi.listUsers,
    staleTime: 30_000,
  });

  const allIds = usersQuery.data?.data ?? [];
  const filtered = filter
    ? allIds.filter((u) => u.toLowerCase().includes(filter.toLowerCase()))
    : allIds;

  // Fetch UUIDs only for the visible (filtered) rows — avoids firing a request
  // for every user in the system when the filter is active.
  const uuidQueries = useQueries({
    queries: filtered.map((uid) => ({
      queryKey: ["operator", "uuid", uid],
      queryFn: () => operatorApi.getUserUuid(uid, false),
      staleTime: 120_000,
      retry: false,           // 404 = no mapping, don't retry
    })),
  });

  // Build a lookup map: userId → query result
  const uuidMap = Object.fromEntries(
    filtered.map((uid, i) => [uid, uuidQueries[i]])
  );

  const deleteMutation = useMutation({
    mutationFn: (uid: string) => operatorApi.deleteUserMapping(uid),
    onSuccess: (_, uid) => {
      qc.invalidateQueries({ queryKey: ["operator", "users"] });
      qc.removeQueries({ queryKey: ["operator", "uuid", uid] });
      qc.removeQueries({ queryKey: ["operator", "mem-count", uid] });
    },
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">{t("users.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("users.subtitle")}
        </p>
      </div>

      {/* ── Stats row ── */}
      <div className="flex items-center gap-3 text-sm">
        <KeyRound className="h-4 w-4 text-muted-foreground" />
        {usersQuery.isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : (
          <>
            <span className="font-semibold">{usersQuery.data?.total ?? 0}</span>
            <span className="text-muted-foreground">{t("users.stats.total")}</span>
          </>
        )}
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-6 items-start">
        {/* ── Left: table ── */}
        <div className="space-y-3">
          {/* Filter input */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              placeholder={t("users.filter.placeholder")}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-8"
            />
          </div>

          {filter && (
            <p className="text-xs text-muted-foreground">
              {t("users.filter.match", { n: filtered.length, total: allIds.length, q: filter })}
            </p>
          )}

          <ScrollArea className="h-[520px] rounded-md border">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-muted/90 backdrop-blur-sm z-10">
                <tr>
                  <th className="text-left px-3 py-2.5 font-medium text-xs text-foreground">
                    {t("users.table.userId")}
                  </th>
                  <th className="text-left px-3 py-2.5 font-medium text-xs text-foreground">
                    {t("users.table.uuid")}
                  </th>
                  <th className="px-3 py-2.5 w-10">
                    <span className="sr-only">{t("users.table.actions")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((uid) => {
                  const q = uuidMap[uid];
                  return (
                    <tr key={uid} className="border-t hover:bg-muted/30 transition-colors group">
                      <td className="px-3 py-2.5 font-mono text-xs align-middle">{uid}</td>
                      <td className="px-3 py-2.5 align-middle">
                        <UuidCell
                          userId={uid}
                          uuid={q?.data?.uuid}
                          loading={q?.isFetching ?? false}
                          error={q?.isError ?? false}
                        />
                      </td>
                      <td className="px-3 py-2.5 text-right align-middle">
                        <DeleteCell
                          userId={uid}
                          onConfirm={() => deleteMutation.mutate(uid)}
                          isDeleting={deleteMutation.isPending && deleteMutation.variables === uid}
                        />
                      </td>
                    </tr>
                  );
                })}

                {filtered.length === 0 && !usersQuery.isLoading && (
                  <tr>
                    <td colSpan={3} className="px-3 py-8 text-center text-xs text-muted-foreground">
                      {filter ? t("users.filter.empty") : t("users.empty")}
                    </td>
                  </tr>
                )}

                {usersQuery.isLoading && (
                  <tr>
                    <td colSpan={3} className="px-3 py-8 text-center">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </ScrollArea>

          {deleteMutation.isSuccess && deleteMutation.data?.warning && (
            <p className="text-xs text-amber-700 dark:text-amber-300 flex items-start gap-1.5">
              <span className="shrink-0">⚠</span>
              {deleteMutation.data.warning}
            </p>
          )}
        </div>

        {/* ── Right: create panel ── */}
        <div className="space-y-4">
          <CreateMappingPanel onCreated={() => {
            qc.invalidateQueries({ queryKey: ["operator", "users"] });
          }} />

          <Separator />

          <div className="rounded-md border p-3 space-y-2 text-xs text-muted-foreground">
            <p className="font-medium text-foreground text-sm">{t("users.howWorks.title")}</p>
            <p>{t("users.howWorks.body")}</p>
            <ul className="space-y-1 list-disc list-inside">
              <li><code className="text-xs">cm:uid:&#123;user_id&#125;</code> → UUID ({t("users.howWorks.forward")})</li>
              <li><code className="text-xs">cm:uuid:&#123;uuid&#125;</code> → user_id ({t("users.howWorks.reverse")})</li>
            </ul>
            <p className="pt-1 text-amber-700 dark:text-amber-300">
              {t("users.delete.warn")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
