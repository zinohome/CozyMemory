"use client";

/**
 * Developer 主页 —— 登录后默认落点。显示跨 App 汇总统计：
 *   - Apps 数 / 总 External Users / 最近活跃 App
 *   - 快捷跳转卡片（新建 App / 文档 / Playground）
 *
 * 各 App 的 user 计数独立用 useAppUsers 拉，fan-out 少量请求，
 * 可接受（典型一个 org 下 Apps 个位数）。
 */

import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { Database, LayoutGrid, Plus, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dashboardFetch } from "@/lib/api";
import { useApps, type AppRow } from "@/lib/hooks/use-apps";
import { useT } from "@/lib/i18n";

interface AppUserListEnvelope {
  total: number;
  data: unknown[];
}

function StatCard({
  label,
  value,
  icon: Icon,
  hint,
}: {
  label: string;
  value: string | number;
  icon: typeof LayoutGrid;
  hint?: string;
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
        {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function HomePage() {
  const t = useT();
  const { data: apps } = useApps();
  const appList: AppRow[] = apps ?? [];

  // 并发拉每个 App 的 user 总数（仅 total 字段）
  const userCountQueries = useQueries({
    queries: appList.map((a) => ({
      queryKey: ["apps", a.id, "users", "count"],
      queryFn: () =>
        dashboardFetch<AppUserListEnvelope>(
          `/dashboard/apps/${a.id}/users?limit=1&offset=0`,
        ),
      staleTime: 60_000,
    })),
  });

  const totalUsers = userCountQueries.reduce(
    (sum, q) => sum + (q.data?.total ?? 0),
    0,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("home.title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("home.subtitle")}</p>
      </div>

      {/* 三个核心统计 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label={t("home.stat.apps")}
          value={appList.length}
          icon={LayoutGrid}
        />
        <StatCard
          label={t("home.stat.users")}
          value={totalUsers}
          icon={Users}
          hint={t("home.stat.users_hint")}
        />
        <StatCard
          label={t("home.stat.engines")}
          value={3}
          icon={Database}
          hint={t("home.stat.engines_hint")}
        />
      </div>

      {/* 快捷操作 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("home.quick.title")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button render={<Link href="/apps" />}>
            <Plus className="h-4 w-4 mr-2" />
            {t("home.quick.new_app")}
          </Button>
          <Button variant="outline" render={<Link href="/apps" />}>
            <LayoutGrid className="h-4 w-4 mr-2" />
            {t("home.quick.browse_apps")}
          </Button>
        </CardContent>
      </Card>

      {/* 最近 App */}
      {appList.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("home.recent_apps")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {appList.slice(0, 6).map((app, idx) => {
                const userTotal = userCountQueries[idx]?.data?.total ?? 0;
                return (
                  <Link
                    key={app.id}
                    href={`/apps/${app.id}`}
                    className="rounded-md border p-3 hover:bg-accent transition-colors"
                  >
                    <div className="font-medium">{app.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">/{app.slug}</div>
                    <div className="text-xs text-muted-foreground mt-2">
                      {userTotal} {t("home.app_card.users")}
                    </div>
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
