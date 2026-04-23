"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useT } from "@/lib/i18n";
import { useOperatorStore } from "@/lib/store";

export default function OperatorLanding() {
  const t = useT();
  const router = useRouter();
  const setStoreKey = useOperatorStore((s) => s.setOperatorKey);
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    try {
      // 用提交的 key 试探 /operator/orgs，401/403 → key 无效
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const r = await fetch(`${base}/api/v1/operator/orgs`, {
        headers: { "X-Cozy-API-Key": key },
      });
      if (!r.ok) {
        toast.error(t("operator.key_invalid"));
        return;
      }
      setStoreKey(key);
      router.replace("/operator/orgs");
    } catch {
      toast.error(t("operator.key_invalid"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Operator Mode</CardTitle>
          <CardDescription>{t("operator.landing_desc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="op-key">{t("operator.bootstrap_key")}</Label>
              <Input
                id="op-key"
                type="password"
                autoComplete="off"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t("operator.bootstrap_key_hint")}
              </p>
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("common.loading") : t("operator.enter")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
