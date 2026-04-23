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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerApiKeysPanel } from "@/components/server-api-keys-panel";
import { KeyRound, Eye, EyeOff, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useT } from "@/lib/i18n";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SettingsPage() {
  const t = useT();
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
        setProbeMsg(t("settings.client.probe.unauthorized"));
      } else if (resp.ok) {
        setProbe("ok");
        setProbeMsg(draft.trim()
          ? t("settings.client.probe.okWithKey")
          : t("settings.client.probe.okNoAuth"));
      } else {
        setProbe("fail");
        setProbeMsg(t("settings.client.probe.http", { code: resp.status }));
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
        <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("settings.subtitle")}
        </p>
      </div>

      {/* ── Client API Key ── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> {t("settings.client.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {t("settings.client.desc2")}
          </p>

          <div className="space-y-1.5">
            <Label htmlFor="api-key">{t("settings.client.keyLabel")}</Label>
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
                aria-label={reveal ? t("settings.client.hideAria") : t("settings.client.revealAria")}
                title={reveal ? t("settings.client.hide") : t("settings.client.show")}
              >
                {reveal ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={save} disabled={!dirty}>{t("settings.client.save")}</Button>
            <Button variant="outline" onClick={test} disabled={probe === "probing"}>
              {probe === "probing" ? <Loader2 className="h-4 w-4 animate-spin" /> : t("settings.client.test")}
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

      {/* ── Legacy Bootstrap Keys (pre multi-tenant) ── */}
      <Card className="opacity-80">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {t("settings.legacy_bootstrap_title")}
          </CardTitle>
          <CardDescription>
            {t("settings.legacy_bootstrap_desc")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ServerApiKeysPanel />
        </CardContent>
      </Card>
    </div>
  );
}
