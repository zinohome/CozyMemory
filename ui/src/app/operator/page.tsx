"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  ArrowRight,
  Brain,
  Building2,
  Database,
  FileText,
  HardDrive,
  Heart,
  KeyRound,
  Shield,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { operatorApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useOperatorStore } from "@/lib/store";

/* ═══ Key Gate (login) ═══ */
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
      if (!r.ok) { toast.error(t("operator.key_invalid")); return; }
      setStoreKey(key);
    } catch {
      toast.error(t("operator.key_invalid"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout fixed inset-0 z-50">
      {/* 左侧：Key 输入 */}
      <div className="auth-left bg-background">
        <div className="w-full max-w-sm space-y-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">CozyMemory</h1>
            <p className="text-sm text-muted-foreground">Operator 管理入口</p>
          </div>
          <form onSubmit={submit} className="space-y-5">
            <h2 className="text-lg font-semibold">{t("operator.bootstrap_key")}</h2>
            <div className="space-y-1.5">
              <Label htmlFor="op-key">Bootstrap Key</Label>
              <Input
                id="op-key"
                type="password"
                autoComplete="off"
                placeholder="输入 COZY_API_KEYS 中的密钥"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                {t("operator.bootstrap_key_hint")}
              </p>
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("common.loading") : t("operator.enter")}
            </Button>
            <p className="text-sm text-muted-foreground text-center">
              <a href="/login" className="hover:text-primary transition-colors">
                Developer 登录 →
              </a>
            </p>
          </form>
        </div>
      </div>

      {/* 右侧：品牌 + 说明 */}
      <div className="auth-right">
        <div className="relative z-10 max-w-md space-y-8">
          <div className="space-y-3">
            <h2 className="text-3xl font-bold tracking-tight">平台管理</h2>
            <p className="text-white/70 text-sm leading-relaxed">
              Operator 模式提供跨组织的全局管理视图，包括用户映射、原始数据查看、引擎健康监控和数据备份。
            </p>
          </div>
          <div className="space-y-3">
            <div className="auth-feature">
              <Building2 className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">组织管理</div>
                <div className="text-xs text-white/50 mt-0.5">查看所有注册组织和 App 概览</div>
              </div>
            </div>
            <div className="auth-feature">
              <Heart className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">引擎健康</div>
                <div className="text-xs text-white/50 mt-0.5">实时监控 Mem0/Memobase/Cognee 三引擎状态</div>
              </div>
            </div>
            <div className="auth-feature">
              <HardDrive className="size-5 text-white/80 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-sm">数据备份</div>
                <div className="text-xs text-white/50 mt-0.5">导出导入用户记忆和画像数据</div>
              </div>
            </div>
          </div>
          <div className="text-xs text-white/30 pt-4">
            Bootstrap Key 仅存于 sessionStorage · 关闭浏览器即清除
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══ Stat Card (with color bar) ═══ */
function StatCard({
  label,
  value,
  icon: Icon,
  barColor = "stat-bar-blue",
}: {
  label: string;
  value: string | number;
  icon: typeof Activity;
  barColor?: string;
}) {
  return (
    <Card className={barColor}>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-extrabold tracking-tight" style={{ fontVariantNumeric: "tabular-nums" }}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

/* ═══ Dashboard ═══ */
function Dashboard() {
  const t = useT();
  const { data: orgs } = useQuery({ queryKey: ["operator", "orgs"], queryFn: operatorApi.orgs });
  const { data: users } = useQuery({ queryKey: ["operator", "users"], queryFn: operatorApi.listUsers });
  const { data: datasets } = useQuery({ queryKey: ["operator", "datasets"], queryFn: operatorApi.listDatasets });
  const { data: health } = useQuery({ queryKey: ["operator", "health"], queryFn: operatorApi.health, refetchInterval: 10_000 });

  const totalOrgs = orgs?.total ?? 0;
  const totalUsers = users?.total ?? users?.data?.length ?? 0;
  const totalDatasets = datasets?.data?.length ?? 0;
  const engines = health?.engines ?? {};
  const engineEntries = Object.entries(engines);

  const quickLinks = [
    { href: "/operator/orgs", label: t("operator.orgs"), icon: Building2, desc: "查看所有组织和 App" },
    { href: "/operator/users-mapping", label: t("operator.users_mapping"), icon: Users, desc: "用户 ID 映射管理" },
    { href: "/operator/memory-raw", label: t("operator.memory_raw"), icon: Brain, desc: "查看原始对话记忆" },
    { href: "/operator/profiles-raw", label: t("operator.profiles_raw") || "画像数据", icon: FileText, desc: "查看原始用户画像" },
    { href: "/operator/knowledge-raw", label: t("operator.knowledge_raw"), icon: Database, desc: "查看知识库数据" },
    { href: "/operator/health", label: t("operator.health"), icon: Activity, desc: "引擎健康监控详情" },
    { href: "/operator/backup", label: t("operator.backup") || "备份", icon: HardDrive, desc: "数据导出和导入" },
    { href: "/operator/settings", label: t("operator.settings") || "设置", icon: KeyRound, desc: "API Key 管理" },
  ];

  return (
    <div className="space-y-6 w-full">
      <div>
        <h1 className="text-2xl font-bold">{t("operator.dashboard_title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("operator.dashboard_subtitle")}</p>
      </div>

      {/* 统计指标 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard label={t("operator.stat.orgs")} value={totalOrgs} icon={Building2} barColor="stat-bar-blue" />
        <StatCard label={t("operator.stat.users")} value={totalUsers} icon={Users} barColor="stat-bar-amber" />
        <StatCard label={t("operator.stat.datasets")} value={totalDatasets} icon={Database} barColor="stat-bar-emerald" />
        <StatCard label={t("operator.stat.api_status")} value={health?.status ?? "…"} icon={Activity} barColor="stat-bar-violet" />
      </div>

      {/* 引擎健康 */}
      {engineEntries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {engineEntries.map(([key, eng]) => (
            <Card key={key} className="flex items-center gap-4 p-4">
              <div className={`size-3 rounded-full shrink-0 ${eng.status === "healthy" ? "bg-green-500" : "bg-destructive"}`} />
              <div className="flex-1 min-w-0">
                <div className="font-medium capitalize">{eng.name || key}</div>
                <div className="text-xs text-muted-foreground">
                  {eng.latency_ms != null ? `${eng.latency_ms.toFixed(1)} ms` : "—"}
                </div>
              </div>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-sm ${
                eng.status === "healthy"
                  ? "bg-green-500/10 text-green-600 dark:text-green-400"
                  : "bg-destructive/10 text-destructive"
              }`}>
                {eng.status}
              </span>
            </Card>
          ))}
        </div>
      )}

      {/* 快捷入口 */}
      <div>
        <h2 className="text-base font-semibold mb-3">管理功能</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {quickLinks.map((l) => (
            <Link key={l.href} href={l.href}>
              <Card className="hover:border-primary/40 hover:shadow-md transition-all h-full">
                <CardContent className="p-4 flex items-start gap-3">
                  <div className="p-2 rounded-md bg-primary/5">
                    <l.icon className="size-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium text-sm">{l.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{l.desc}</div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function OperatorLanding() {
  const operatorKey = useOperatorStore((s) => s.operatorKey);
  if (!operatorKey) return <KeyGate />;
  return <Dashboard />;
}
