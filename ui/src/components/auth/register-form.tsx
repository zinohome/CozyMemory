"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
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
          body: JSON.stringify({ email, password, org_name: orgName, org_slug: orgSlug }),
        },
      );
      setJwt(r.access_token);
      document.cookie = "cm_auth=1; Path=/; SameSite=Lax";
      router.replace("/home");
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err);
      let shown = t("auth.register_failed");
      try {
        const m = raw.match(/\[.*\]/);
        if (m) {
          const arr = JSON.parse(m[0]) as Array<{ loc?: string[]; msg?: string }>;
          if (arr[0]?.loc && arr[0]?.msg) shown = `${arr[0].loc.slice(-1)[0]}: ${arr[0].msg}`;
        }
      } catch { /* fallback */ }
      toast.error(shown);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <h2 className="text-lg font-semibold">{t("auth.register")}</h2>
      <div className="space-y-1.5">
        <Label htmlFor="email">{t("auth.email")}</Label>
        <Input id="email" type="email" autoComplete="email" placeholder="you@company.com"
          value={email} onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="password">{t("auth.password")}</Label>
        <Input id="password" type="password" autoComplete="new-password" placeholder="••••••••"
          minLength={8} maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)} required />
        <p className="text-xs text-muted-foreground">{t("auth.password_hint")}</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="org_name">{t("auth.org_name")}</Label>
          <Input id="org_name" type="text" autoComplete="organization" placeholder="我的公司"
            value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="org_slug">{t("auth.org_slug")}</Label>
          <Input id="org_slug" type="text" pattern="^[a-z0-9][a-z0-9\-]*[a-z0-9]$" placeholder="my-company"
            minLength={2} maxLength={64} value={orgSlug} onChange={(e) => setOrgSlug(e.target.value)} required />
          <p className="text-xs text-muted-foreground">{t("auth.org_slug_hint")}</p>
        </div>
      </div>
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? t("common.loading") : t("auth.register_submit")}
      </Button>
      <p className="text-sm text-muted-foreground text-center">
        <a href="/login" className="hover:text-primary transition-colors">{t("auth.go_login")}</a>
      </p>
    </form>
  );
}
