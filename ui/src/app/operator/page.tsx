"use client";

/**
 * Operator 主页 —— 登录状态决定渲染内容：
 *   - 无 operatorKey：显示 bootstrap key 输入表单
 *   - 有 operatorKey：显示 dashboard（跨 org / 引擎健康 / 全局统计）
 *
 * Step 8.12 合并了原 /operator/health 页的统计卡，/operator/orgs 的
 * org 列表入口作为卡片快捷操作。
 */

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  Building2,
  Database,
  Users,
  Brain,
  ArrowRight,
} from "lucide-react";

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
import { operatorApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useOperatorStore } from "@/lib/store";

function KeyGate() {
  const t = useT();
  const setStoreKey = useOperatorStore((s) => s.setOperatorKey);
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const r = await fetch(`${base}/api/v1/operator/orgs`, {
        headers: { "X-Cozy-API-Key": key },
      });
      if (!r.ok) {
        toast.error(t("operator.key_invalid"));
        return;
      }
      setStoreKey(key);
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

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: typeof Activity;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  const t = useT();
  const { data: orgs } = useQuery({
    queryKey: ["operator", "orgs"],
    queryFn: operatorApi.orgs,
  });
  const { data: users } = useQuery({
    queryKey: ["operator", "users"],
    queryFn: operatorApi.listUsers,
  });
  const { data: datasets } = useQuery({
    queryKey: ["operator", "datasets"],
    queryFn: operatorApi.listDatasets,
  });
  const { data: health } = useQuery({
    queryKey: ["operator", "health"],
    queryFn: operatorApi.health,
    refetchInterval: 10_000,
  });

  const totalOrgs = orgs?.total ?? 0;
  const totalUsers = users?.total ?? users?.data?.length ?? 0;
  const totalDatasets = datasets?.data?.length ?? 0;
  const engines = health?.engines ?? {};
  const engineEntries = Object.entries(engines);

  const quickLinks = [
    { href: "/operator/orgs",          label: t("operator.orgs"),          icon: Building2 },
    { href: "/operator/users-mapping", label: t("operator.users_mapping"), icon: Users },
    { href: "/operator/memory-raw",    label: t("operator.memory_raw"),    icon: Brain },
    { href: "/operator/knowledge-raw", label: t("operator.knowledge_raw"), icon: Database },
    { href: "/operator/health",        label: t("operator.health"),        icon: Activity },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("operator.dashboard_title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("operator.dashboard_subtitle")}
        </p>
      </div>

      {/* 四个全局指标 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("operator.stat.orgs")} value={totalOrgs} icon={Building2} />
        <StatCard label={t("operator.stat.users")} value={totalUsers} icon={Users} />
        <StatCard label={t("operator.stat.datasets")} value={totalDatasets} icon={Database} />
        <StatCard
          label={t("operator.stat.api_status")}
          value={health?.status ?? "…"}
          icon={Activity}
        />
      </div>

      {/* 引擎健康 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("operator.engine_health")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {engineEntries.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
            )}
            {engineEntries.map(([key, eng]) => (
              <div key={key} className="rounded-md border p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">{key}</span>
                  <span
                    className={
                      eng.status === "healthy"
                        ? "text-xs text-green-600"
                        : "text-xs text-destructive"
                    }
                  >
                    {eng.status}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {eng.latency_ms != null ? `${eng.latency_ms.toFixed(1)} ms` : "—"}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 快捷入口 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("operator.quick_links")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {quickLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="flex items-center justify-between rounded-md border p-3 hover:bg-accent transition-colors text-sm"
              >
                <span className="inline-flex items-center gap-2">
                  <l.icon className="h-4 w-4" />
                  {l.label}
                </span>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function OperatorLanding() {
  const operatorKey = useOperatorStore((s) => s.operatorKey);
  if (!operatorKey) return <KeyGate />;
  return <Dashboard />;
}
