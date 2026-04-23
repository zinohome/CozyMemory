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
      router.replace("/apps");
    } catch {
      toast.error(t("auth.register_failed"));
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="org_name">{t("auth.org_name")}</Label>
            <Input
              id="org_name"
              type="text"
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
              value={orgSlug}
              onChange={(e) => setOrgSlug(e.target.value)}
              required
            />
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
