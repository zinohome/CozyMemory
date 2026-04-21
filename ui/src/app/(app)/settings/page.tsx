"use client";

/**
 * Settings — CozyMemory 客户端偏好 + 服务端 API Key 管理。
 *
 * 两个板块：
 *  1. Client API Key — 持久化在 localStorage，用于每个 request 的
 *     X-Cozy-API-Key header。
 *  2. <ServerApiKeysPanel /> — 调 /api/v1/admin/api-keys CRUD 管理动态 key。
 */

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { healthApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerApiKeysPanel } from "@/components/server-api-keys-panel";
import { KeyRound, Eye, EyeOff, CheckCircle2, XCircle, Loader2 } from "lucide-react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
              <Button
                variant="outline"
                size="icon"
                onClick={() => setReveal((r) => !r)}
                aria-label={reveal ? "Hide key" : "Reveal key"}
                title={reveal ? "Hide" : "Reveal"}
              >
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
      <ServerApiKeysPanel />
    </div>
  );
}
