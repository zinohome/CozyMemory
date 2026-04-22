"use client";

/**
 * Server API Keys panel — 调 /api/v1/admin/api-keys CRUD 管理动态 key。
 *
 * 仅在当前 client key 是 bootstrap（env COZY_API_KEYS 里的）时能访问；
 * 如果用的是自身动态 key，admin list 会返回 401 → 面板显示
 * "bootstrap key required" 提示。
 *
 * 从 settings/page.tsx 抽出，解耦 Client Key 和 Server Keys 两块关注点。
 */

import { useState, useEffect, useCallback } from "react";
import { useAppStore, getApiKey } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { toast } from "sonner";
import {
  KeyRound,
  Loader2,
  Plus,
  RotateCw,
  Trash2,
  Copy,
  Ban,
  CheckCircle,
  History,
} from "lucide-react";
import { useT } from "@/lib/i18n";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiKeyRecord {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  disabled: boolean;
}

interface ApiKeyCreateResponse {
  record: ApiKeyRecord;
  key: string;
}

interface ApiKeyLogEntry {
  ts: string;
  method: string;
  path: string;
  status: number;
}

function authHeaders(): Record<string, string> {
  const k = getApiKey();
  return k ? { "X-Cozy-API-Key": k } : {};
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}/api/v1/admin${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const err: Error & { status?: number } = new Error(body.detail ?? body.error ?? `HTTP ${resp.status}`);
    err.status = resp.status;
    throw err;
  }
  return resp.json() as Promise<T>;
}

function useFmtDate() {
  const t = useT();
  return (s: string | null): string => {
    if (!s) return t("settings.server.time.never");
    const d = new Date(s);
    const now = Date.now();
    const diff = (now - d.getTime()) / 1000;
    if (diff < 60) return t("settings.server.time.justNow");
    if (diff < 3600) return t("settings.server.time.minAgo", { n: Math.floor(diff / 60) });
    if (diff < 86400) return t("settings.server.time.hourAgo", { n: Math.floor(diff / 3600) });
    return d.toLocaleDateString();
  };
}

export function ServerApiKeysPanel() {
  const t = useT();
  const fmtDate = useFmtDate();
  const { apiKey } = useAppStore();

  const [keys, setKeys] = useState<ApiKeyRecord[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [isBootstrap, setIsBootstrap] = useState<boolean | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [revealedKey, setRevealedKey] = useState<{ id: string; key: string; action: "created" | "rotated" } | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [logsId, setLogsId] = useState<string | null>(null);
  const [logs, setLogs] = useState<ApiKeyLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [confirmState, setConfirmState] = useState<
    | { kind: "rotate"; id: string }
    | { kind: "delete"; id: string; name: string }
    | null
  >(null);

  async function toggleLogs(id: string) {
    if (logsId === id) {
      setLogsId(null);
      setLogs([]);
      return;
    }
    setLogsId(id);
    setLogsLoading(true);
    try {
      const r = await adminFetch<{ data: ApiKeyLogEntry[] }>(`/api-keys/${id}/logs?limit=50`);
      setLogs(r.data);
    } catch (e) {
      toast.error((e as Error).message);
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadErr(null);
    try {
      const data = await adminFetch<{ data: ApiKeyRecord[] }>("/api-keys");
      setKeys(data.data);
      setIsBootstrap(true);
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 401) {
        setIsBootstrap(false);
        setLoadErr(t("settings.server.notBootstrap"));
      } else {
        setLoadErr(err.message);
      }
      setKeys(null);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    refresh();
  }, [refresh, apiKey]); // apiKey 变了重新探测

  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const r = await adminFetch<ApiKeyCreateResponse>("/api-keys", {
        method: "POST",
        body: JSON.stringify({ name: newName.trim() }),
      });
      setRevealedKey({ id: r.record.id, key: r.key, action: "created" });
      setNewName("");
      await refresh();
      toast.success(t("settings.server.toast.created", { name: r.record.name }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  function handleRotate(id: string) {
    setConfirmState({ kind: "rotate", id });
  }

  async function doRotate(id: string) {
    try {
      const r = await adminFetch<ApiKeyCreateResponse>(`/api-keys/${id}/rotate`, { method: "POST" });
      setRevealedKey({ id, key: r.key, action: "rotated" });
      await refresh();
      toast.success(t("settings.server.toast.rotated"));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function handleToggleDisabled(rec: ApiKeyRecord) {
    try {
      await adminFetch(`/api-keys/${rec.id}`, {
        method: "PATCH",
        body: JSON.stringify({ disabled: !rec.disabled }),
      });
      await refresh();
      toast.success(rec.disabled ? t("settings.server.toast.enabled") : t("settings.server.toast.disabled"));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function handleRename(id: string) {
    if (!editName.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await adminFetch(`/api-keys/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: editName.trim() }),
      });
      setEditingId(null);
      await refresh();
      toast.success(t("settings.server.toast.renamed"));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  function handleDelete(id: string, name: string) {
    setConfirmState({ kind: "delete", id, name });
  }

  async function doDelete(id: string) {
    try {
      await adminFetch(`/api-keys/${id}`, { method: "DELETE" });
      await refresh();
      toast.success(t("settings.server.toast.deleted"));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard?.writeText(text);
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> {t("settings.server.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {t("settings.server.desc2")}
          </p>

          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> {t("settings.server.loading")}
            </div>
          )}

          {!loading && isBootstrap === false && loadErr && (
            <p className="text-sm text-destructive">{loadErr}</p>
          )}

          {revealedKey && (
            <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <CheckCircle className="h-4 w-4 text-amber-600" />
                {revealedKey.action === "created"
                  ? t("settings.server.reveal.created")
                  : t("settings.server.reveal.rotated")}
              </div>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={revealedKey.key}
                  className="font-mono text-xs"
                  onFocus={(e) => e.currentTarget.select()}
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => copyToClipboard(revealedKey.key)}
                  title={t("settings.server.reveal.copy")}
                  aria-label={t("settings.server.reveal.copyAria")}
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => setRevealedKey(null)}>
                  {t("settings.server.reveal.dismiss")}
                </Button>
              </div>
            </div>
          )}

          {isBootstrap && (
            <>
              <Separator />
              {/* Create row */}
              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-1">
                  <Label htmlFor="new-name" className="text-xs">{t("settings.server.newName")}</Label>
                  <Input
                    id="new-name"
                    placeholder={t("settings.server.newName.placeholder")}
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  />
                </div>
                <Button onClick={handleCreate} disabled={!newName.trim() || creating}>
                  {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  <span className="ml-1">{t("settings.server.createBtn")}</span>
                </Button>
              </div>

              {/* List */}
              {keys && keys.length === 0 && (
                <p className="text-sm text-muted-foreground py-3">
                  {t("settings.server.emptyList")}
                </p>
              )}
              {keys && keys.length > 0 && (
                <div className="space-y-1.5">
                  {keys.map((k) => (
                    <div key={k.id} className="space-y-0">
                      <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                        <div className="flex-1 min-w-0 space-y-0.5">
                          {editingId === k.id ? (
                            <Input
                              autoFocus
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onBlur={() => handleRename(k.id)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleRename(k.id);
                                if (e.key === "Escape") setEditingId(null);
                              }}
                              className="h-7 text-sm"
                            />
                          ) : (
                            <button
                              type="button"
                              className="font-medium truncate text-left hover:underline"
                              onClick={() => {
                                setEditingId(k.id);
                                setEditName(k.name);
                              }}
                            >
                              {k.name}
                            </button>
                          )}
                          <div className="flex gap-2 items-center text-xs text-muted-foreground">
                            <code className="font-mono">{k.prefix}…</code>
                            <span>{t("settings.server.usedAgo", { when: fmtDate(k.last_used_at) })}</span>
                            {k.disabled && (
                              <Badge variant="destructive" className="text-[10px] h-4">
                                {t("settings.server.disabledBadge")}
                              </Badge>
                            )}
                          </div>
                        </div>
                        <Button
                          size="icon"
                          variant="ghost"
                          title={k.disabled ? t("settings.server.action.enable") : t("settings.server.action.disable")}
                          aria-label={
                            k.disabled
                              ? t("settings.server.action.enableAria", { name: k.name })
                              : t("settings.server.action.disableAria", { name: k.name })
                          }
                          onClick={() => handleToggleDisabled(k)}
                        >
                          {k.disabled ? (
                            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                          ) : (
                            <Ban className="h-3.5 w-3.5 text-amber-500" />
                          )}
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          title={logsId === k.id ? t("settings.server.action.hideLogs") : t("settings.server.action.viewLogs")}
                          aria-label={
                            logsId === k.id
                              ? t("settings.server.action.hideLogsAria", { name: k.name })
                              : t("settings.server.action.viewLogsAria", { name: k.name })
                          }
                          onClick={() => toggleLogs(k.id)}
                        >
                          <History className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          title={t("settings.server.action.rotateTitle")}
                          aria-label={t("settings.server.action.rotateAria", { name: k.name })}
                          onClick={() => handleRotate(k.id)}
                        >
                          <RotateCw className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          title={t("settings.server.action.deleteTitle")}
                          aria-label={t("settings.server.action.deleteAria", { name: k.name })}
                          onClick={() => handleDelete(k.id, k.name)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                      {logsId === k.id && (
                        <div className="rounded-md border border-t-0 rounded-t-none bg-muted/30 px-3 py-2 text-xs">
                          {logsLoading ? (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("settings.server.logs.loading")}
                            </div>
                          ) : logs.length === 0 ? (
                            <p className="text-muted-foreground">{t("settings.server.logs.empty")}</p>
                          ) : (
                            <div className="space-y-0.5 max-h-60 overflow-auto">
                              {logs.map((e, i) => (
                                <div
                                  key={i}
                                  className="flex items-center gap-3 font-mono text-[11px]"
                                >
                                  <span className="text-muted-foreground shrink-0">
                                    {fmtDate(e.ts)}
                                  </span>
                                  <span
                                    className={
                                      e.status >= 400
                                        ? "text-destructive"
                                        : "text-green-600 dark:text-green-400"
                                    }
                                  >
                                    {e.status}
                                  </span>
                                  <span className="text-muted-foreground shrink-0">{e.method}</span>
                                  <span className="truncate">{e.path}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {loadErr && isBootstrap && (
                <p className="text-xs text-destructive">{loadErr}</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!confirmState}
        onOpenChange={(o) => !o && setConfirmState(null)}
        title={
          confirmState?.kind === "rotate"
            ? t("settings.server.confirm.rotateTitle")
            : confirmState?.kind === "delete"
              ? t("settings.server.confirm.deleteTitle", { name: confirmState.name })
              : ""
        }
        description={
          confirmState?.kind === "rotate"
            ? t("settings.server.confirm.rotateDesc")
            : t("settings.server.confirm.deleteDesc")
        }
        confirmLabel={
          confirmState?.kind === "rotate"
            ? t("settings.server.confirm.rotateBtn")
            : t("settings.server.confirm.deleteBtn")
        }
        destructive={confirmState?.kind === "delete"}
        onConfirm={() => {
          if (!confirmState) return;
          if (confirmState.kind === "rotate") doRotate(confirmState.id);
          else doDelete(confirmState.id);
        }}
      />
    </>
  );
}
