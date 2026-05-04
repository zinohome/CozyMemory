"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { dashboardFetch } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export function RegisterForm() {
  const t = useT();
  const router = useRouter();
  const setJwt = useAppStore((s) => s.setJwt);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await dashboardFetch<{ access_token: string }>(
        "/auth/register",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            org_name: orgName,
            org_slug: orgSlug,
          }),
        },
      );
      setJwt(r.access_token);
      document.cookie = "cm_auth=1; Path=/; SameSite=Lax";
      router.replace("/home");
    } catch (err) {
      // 后端 422 的 err.message 是 JSON.stringify 的 detail 数组；尝试
      // 解析出第一条字段级错误给用户具体提示。
      const raw = err instanceof Error ? err.message : String(err);
      let shown = t("auth.register_failed");
      try {
        const m = raw.match(/\[.*\]/);
        if (m) {
          const arr = JSON.parse(m[0]) as Array<{ loc?: string[]; msg?: string }>;
          if (arr[0]?.loc && arr[0]?.msg) {
            shown = `${arr[0].loc.slice(-1)[0]}: ${arr[0].msg}`;
          }
        }
      } catch {
        /* 降级回通用文案 */
      }
      toast.error(shown);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("auth.register")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t("auth.password_hint")}
            </p>
          </div>
          <div>
            <Label htmlFor="org_name">{t("auth.org_name")}</Label>
            <Input
              id="org_name"
              type="text"
              autoComplete="organization"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="org_slug">{t("auth.org_slug")}</Label>
            <Input
              id="org_slug"
              type="text"
              pattern="^[a-z0-9][a-z0-9\-]*[a-z0-9]$"
              minLength={2}
              maxLength={64}
              value={orgSlug}
              onChange={(e) => setOrgSlug(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t("auth.org_slug_hint")}
            </p>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {t("auth.register_submit")}
          </Button>
          <p className="text-sm text-muted-foreground text-center">
            <a href="/login" className="underline">
              {t("auth.go_login")}
            </a>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
