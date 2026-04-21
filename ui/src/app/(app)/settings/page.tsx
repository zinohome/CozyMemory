"use client";

/**
 * Settings — CozyMemory 客户端偏好 + 服务端 API Key 管理。
 *
 * 两个板块：
 *  1. Client API Key — 持久化在 localStorage，用于每个 request 的
 *     X-Cozy-API-Key header。
 *  2. Server API Keys — 调 /api/v1/admin/api-keys CRUD 管理动态 key。
 *     仅在当前 client key 是 bootstrap（env COZY_API_KEYS 里的）时
 *     能访问；如果用的是自身动态 key，admin list 会返回 401 → 面板
 *     显示 "bootstrap key required" 提示。
 */

import { useState, useEffect, useCallback } from "react";
import { useAppStore, getApiKey } from "@/lib/store";
import { healthApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  Loader2,
  Plus,
  RotateCw,
  Trash2,
  Copy,
  Ban,
  CheckCircle,
  History,
} from "lucide-react";

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

function fmtDate(s: string | null): string {
  if (!s) return "never";
  const d = new Date(s);
  const now = Date.now();
  const diff = (now - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

export default function SettingsPage() {
  const { apiKey, setApiKey } = useAppStore();
  const [draft, setDraft] = useState(apiKey);
  const [reveal, setReveal] = useState(false);
  const [probe, setProbe] = useState<"idle" | "probing" | "ok" | "fail">("idle");
  const [probeMsg, setProbeMsg] = useState("");

  useEffect(() => setDraft(apiKey), [apiKey]);
  const dirty = draft !== apiKey;

  function save() {
    setApiKey(draft.trim());
  }

  async function test() {
    setProbe("probing");
    setProbeMsg("");
    const prev = apiKey;
    setApiKey(draft.trim());
    try {
      await new Promise((r) => setTimeout(r, 0));
      await healthApi.check();
      const resp = await fetch(`${BASE_URL}/api/v1/users`, {
        headers: draft.trim() ? { "X-Cozy-API-Key": draft.trim() } : {},
      });
      if (resp.status === 401) {
        setProbe("fail");
        setProbeMsg("401 Unauthorized — key rejected by server");
      } else if (resp.ok) {
        setProbe("ok");
        setProbeMsg(`200 OK — ${draft.trim() ? "key accepted" : "server has no auth enabled"}`);
      } else {
        setProbe("fail");
        setProbeMsg(`HTTP ${resp.status}`);
      }
    } catch (e) {
      setProbe("fail");
      setProbeMsg((e as Error).message);
    } finally {
      if (!dirty) setApiKey(prev);
    }
  }

  // ── Server API Keys panel ───────────────────────────────────────────────
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
      setLoadErr((e as Error).message);
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
        setLoadErr("Bootstrap key required — current client key is either missing or is a dynamic key. Server auth management only accepts keys defined in COZY_API_KEYS env var.");
      } else {
        setLoadErr(err.message);
      }
      setKeys(null);
    } finally {
      setLoading(false);
    }
  }, []);

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
    } catch (e) {
      setLoadErr((e as Error).message);
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
    } catch (e) {
      setLoadErr((e as Error).message);
    }
  }

  async function handleToggleDisabled(rec: ApiKeyRecord) {
    try {
      await adminFetch(`/api-keys/${rec.id}`, {
        method: "PATCH",
        body: JSON.stringify({ disabled: !rec.disabled }),
      });
      await refresh();
    } catch (e) {
      setLoadErr((e as Error).message);
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
    } catch (e) {
      setLoadErr((e as Error).message);
    }
  }

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

  function copyToClipboard(text: string) {
    navigator.clipboard?.writeText(text);
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Client-side preferences + server-side API key management.
        </p>
      </div>

      {/* ── Client API Key ── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> Client API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Sent as <code className="font-mono">X-Cozy-API-Key</code> on every request. Stored in
            this browser&apos;s localStorage. Use the server panel below to create/rotate keys.
          </p>

          <div className="space-y-1.5">
            <Label htmlFor="api-key">Key</Label>
            <div className="flex gap-2">
              <Input
                id="api-key"
                type={reveal ? "text" : "password"}
                placeholder="cozy_..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                autoComplete="off"
                className="font-mono"
              />
              <Button variant="outline" size="icon" onClick={() => setReveal((r) => !r)}>
                {reveal ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={save} disabled={!dirty}>Save</Button>
            <Button variant="outline" onClick={test} disabled={probe === "probing"}>
              {probe === "probing" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Test"}
            </Button>
            {probe === "ok" && (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> {probeMsg}
              </span>
            )}
            {probe === "fail" && (
              <span className="text-xs text-destructive flex items-center gap-1">
                <XCircle className="h-3.5 w-3.5" /> {probeMsg}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ── Server-side API Keys ── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> Server API Keys
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Dynamic keys stored in Redis. Requires a <strong>bootstrap key</strong> (one of{" "}
            <code>COZY_API_KEYS</code> env values) in the client field above.
          </p>

          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading keys…
            </div>
          )}

          {!loading && isBootstrap === false && loadErr && (
            <p className="text-sm text-destructive">{loadErr}</p>
          )}

          {revealedKey && (
            <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <CheckCircle className="h-4 w-4 text-amber-600" />
                Key {revealedKey.action} — save it now, it won&apos;t be shown again
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
                  title="Copy"
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => setRevealedKey(null)}>
                  Dismiss
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
                  <Label htmlFor="new-name" className="text-xs">New key name</Label>
                  <Input
                    id="new-name"
                    placeholder="e.g. production-backend"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  />
                </div>
                <Button onClick={handleCreate} disabled={!newName.trim() || creating}>
                  {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  <span className="ml-1">Create</span>
                </Button>
              </div>

              {/* List */}
              {keys && keys.length === 0 && (
                <p className="text-sm text-muted-foreground py-3">
                  No dynamic keys yet — create one above.
                </p>
              )}
              {keys && keys.length > 0 && (
                <div className="space-y-1.5">
                  {keys.map((k) => (
                    <div key={k.id} className="space-y-0">
                    <div
                      className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                    >
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
                          <span>· used {fmtDate(k.last_used_at)}</span>
                          {k.disabled && (
                            <Badge variant="destructive" className="text-[10px] h-4">
                              disabled
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Button
                        size="icon"
                        variant="ghost"
                        title={k.disabled ? "Enable" : "Disable"}
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
                        title={logsId === k.id ? "Hide logs" : "View logs"}
                        onClick={() => toggleLogs(k.id)}
                      >
                        <History className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        title="Rotate"
                        onClick={() => handleRotate(k.id)}
                      >
                        <RotateCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        title="Delete"
                        onClick={() => handleDelete(k.id, k.name)}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </div>
                    {logsId === k.id && (
                      <div className="rounded-md border border-t-0 rounded-t-none bg-muted/30 px-3 py-2 text-xs">
                        {logsLoading ? (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
                          </div>
                        ) : logs.length === 0 ? (
                          <p className="text-muted-foreground">No recent usage.</p>
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
            ? "Rotate this key?"
            : confirmState?.kind === "delete"
              ? `Delete key "${confirmState.name}"?`
              : ""
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
    </div>
  );
}
