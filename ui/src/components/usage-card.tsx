"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, CheckCircle2, Clock } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dashboardFetch } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface UsageResponse {
  total: number;
  success: number;
  errors: number;
  avg_latency_ms: number;
  per_route: { route: string; count: number }[];
  daily: { date: string; count: number }[];
  since: string;
  days: number;
}

export function UsageCard({ appId }: { appId: string }) {
  const t = useT();
  const { data, isLoading } = useQuery<UsageResponse>({
    queryKey: ["apps", appId, "usage", 7],
    queryFn: () => dashboardFetch<UsageResponse>(`/dashboard/apps/${appId}/usage?days=7`),
    staleTime: 30_000,
  });
  if (isLoading || !data) return null;

  const maxDaily = Math.max(1, ...data.daily.map((d) => d.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Activity className="h-4 w-4" />
          {t("usage.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 4 indicators */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">{t("usage.total")}</p>
            <p className="text-xl font-semibold">{data.total}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> {t("usage.success")}
            </p>
            <p className="text-xl font-semibold">{data.success}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <AlertCircle className="h-3 w-3" /> {t("usage.errors")}
            </p>
            <p className="text-xl font-semibold">{data.errors}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" /> {t("usage.avg_latency")}
            </p>
            <p className="text-xl font-semibold">
              {data.avg_latency_ms.toFixed(1)}<span className="text-xs ml-0.5">ms</span>
            </p>
          </div>
        </div>

        {/* daily bars */}
        {data.daily.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1.5">{t("usage.daily")}</p>
            <div className="flex items-end gap-1 h-16">
              {data.daily.map((d) => (
                <div
                  key={d.date}
                  className="flex-1 bg-primary/70 rounded-sm"
                  style={{ height: `${(d.count / maxDaily) * 100}%` }}
                  title={`${d.date}: ${d.count}`}
                />
              ))}
            </div>
          </div>
        )}

        {/* per-route */}
        {data.per_route.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1.5">{t("usage.per_route")}</p>
            <div className="space-y-1 text-xs">
              {data.per_route.slice(0, 6).map((r) => (
                <div key={r.route} className="flex items-center justify-between">
                  <code className="text-muted-foreground">{r.route}</code>
                  <span>{r.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
