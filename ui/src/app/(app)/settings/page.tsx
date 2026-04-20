"use client";

/**
 * Settings — 管理 CozyMemory 客户端配置。
 *
 * 当前只有一项：API Key。存在 Zustand persist，localStorage 持久化。
 * 后端开启 COZY_API_KEYS 鉴权后，未填 key 或 key 错误会全站 401。
 */

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { healthApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyRound, Eye, EyeOff, CheckCircle2, XCircle, Loader2 } from "lucide-react";

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
    // 临时应用当前 draft 的 key 做一次 /users 访问（health 免鉴权不能验证）
    const prev = apiKey;
    setApiKey(draft.trim());
    try {
      // 等下一个 tick，让 zustand setState 生效，再发请求
      await new Promise((r) => setTimeout(r, 0));
      await healthApi.check(); // 先确认 API 可达
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/users`, {
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
      // 如果用户还没保存 draft，把存的 key 恢复成原 apiKey
      if (!dirty) setApiKey(prev);
    }
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Client-side preferences. Values persist in localStorage of this browser only.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <KeyRound className="h-4 w-4" /> API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Sent as <code className="font-mono">X-Cozy-API-Key</code> header on every request. Leave
            empty if the server has auth disabled (no <code>COZY_API_KEYS</code> env var).
          </p>

          <div className="space-y-1.5">
            <Label htmlFor="api-key">Key</Label>
            <div className="flex gap-2">
              <Input
                id="api-key"
                type={reveal ? "text" : "password"}
                placeholder="sk-..."
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
            <Button onClick={save} disabled={!dirty}>
              Save
            </Button>
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
    </div>
  );
}
