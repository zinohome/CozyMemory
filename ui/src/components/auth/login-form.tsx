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

export function LoginForm() {
  const t = useT();
  const router = useRouter();
  const setJwt = useAppStore((s) => s.setJwt);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await dashboardFetch<{ access_token: string }>(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      setJwt(r.access_token);
      document.cookie = "cm_auth=1; Path=/; SameSite=Lax";
      router.replace("/home");
    } catch {
      toast.error(t("auth.login_failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <h2 className="text-lg font-semibold">{t("auth.login")}</h2>
      <div className="space-y-1.5">
        <Label htmlFor="email">{t("auth.email")}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="password">{t("auth.password")}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? t("common.loading") : t("auth.login_submit")}
      </Button>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <a href="/register" className="hover:text-primary transition-colors">
          {t("auth.go_register")}
        </a>
        <a href="/operator" className="hover:text-primary transition-colors">
          {t("auth.go_operator")}
        </a>
      </div>
    </form>
  );
}
