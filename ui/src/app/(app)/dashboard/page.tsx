"use client";

import { useState } from "react";
import { useQuery, useQueries, useQueryClient, useIsFetching } from "@tanstack/react-query";
import { healthApi, usersApi, knowledgeApi, conversationsApi, type EngineStatus, type KnowledgeDataset } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Brain, MessageSquare, User, BookOpen,
  Wifi, WifiOff, Loader2, Users, Database, MemoryStick, RefreshCw, Activity, TrendingUp,
} from "lucide-react";
import { useMetricsStore, WINDOW_PRESETS, type WindowMinutes } from "@/lib/metrics-store";
import { Sparkline } from "@/components/sparkline";

// ── Engine health card ────────────────────────────────────────────────────

const ENGINE_META: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  Mem0: { icon: MessageSquare, label: "Mem0", color: "text-blue-500" },
  Memobase: { icon: User, label: "Memobase", color: "text-green-500" },
  Cognee: { icon: BookOpen, label: "Cognee", color: "text-purple-500" },
};

function EngineCard({ engine }: { engine: EngineStatus }) {
  const meta = ENGINE_META[engine.name] ?? ENGINE_META[engine.name.toLowerCase()] ?? { icon: Brain, label: engine.name, color: "text-gray-500" };
  const Icon = meta.icon;
  const healthy = engine.status === "healthy";
  const disabled = engine.status === "disabled";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Icon className={`h-4 w-4 ${meta.color}`} />
          {meta.label}
        </CardTitle>
        <Badge variant={healthy ? "default" : disabled ? "secondary" : "destructive"}>
          {engine.status}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {healthy ? <Wifi className="h-3.5 w-3.5 text-green-500" /> : <WifiOff className="h-3.5 w-3.5 text-red-400" />}
          {engine.latency_ms != null ? (
            <span>{engine.latency_ms}ms</span>
          ) : engine.error ? (
            <span className="text-destructive truncate">{engine.error}</span>
          ) : (
            <span>—</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Observability panel ──────────────────────────────────────────────────
// 读 metrics-store 里的时序数据（由 MetricsPoller 填充），绘 sparkline。
// 页面只要在 AppLayout 下，跨导航切换 poller 都一直跑，历史窗口持续累积。

function fmtMs(v: number | null): string {
  if (v == null) return "—";
  return v >= 1000 ? `${(v / 1000).toFixed(2)}s` : `${v.toFixed(0)}ms`;
}

function stats(values: (number | null)[]): { min: number; avg: number; max: number } | null {
  const finite = values.filter((v): v is number => v != null);
  if (finite.length === 0) return null;
  const sum = finite.reduce((a, b) => a + b, 0);
  return { min: Math.min(...finite), avg: sum / finite.length, max: Math.max(...finite) };
}

function LatencyRow({
  label,
  values,
  color,
}: {
  label: string;
  values: (number | null)[];
  color: string;
}) {
  const s = stats(values);
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-20 text-muted-foreground truncate">{label}</div>
      <Sparkline values={values} stroke={color} className="shrink-0" />
      {s ? (
        <div className="flex-1 flex gap-3 text-muted-foreground font-mono">
          <span>min {fmtMs(s.min)}</span>
          <span>avg {fmtMs(s.avg)}</span>
          <span>max {fmtMs(s.max)}</span>
        </div>
      ) : (
        <div className="text-muted-foreground">no samples yet</div>
      )}
    </div>
  );
}

function ObservabilityPanel() {
  const latency = useMetricsStore((s) => s.latency);
  const counts = useMetricsStore((s) => s.counts);
  const [windowMinutes, setWindowMinutes] = useState<WindowMinutes>(10);

  // 按选中窗口裁剪出可视点。buffer 本身最多保留 6h；窗口只影响显示。
  const cutoff = Date.now() - windowMinutes * 60_000;
  const visibleLatency = latency.filter((p) => p.ts >= cutoff);
  const visibleCounts = counts.filter((p) => p.ts >= cutoff);

  const mem0Values = visibleLatency.map((p) => p.mem0);
  const memobaseValues = visibleLatency.map((p) => p.memobase);
  const cogneeValues = visibleLatency.map((p) => p.cognee);
  const userValues = visibleCounts.map((p) => p.users as number | null);
  const datasetValues = visibleCounts.map((p) => p.datasets as number | null);

  const firstTs = latency[0]?.ts ?? counts[0]?.ts;
  const elapsedMin = firstTs ? Math.max(0, Math.round((Date.now() - firstTs) / 60_000)) : 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold flex items-center gap-1.5">
          <Activity className="h-4 w-4" /> Observability
        </h3>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md border text-xs overflow-hidden">
            {WINDOW_PRESETS.map((p, i) => (
              <button
                key={p.minutes}
                onClick={() => setWindowMinutes(p.minutes)}
                className={
                  (windowMinutes === p.minutes
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted") +
                  " px-2 py-0.5" +
                  (i > 0 ? " border-l" : "")
                }
              >
                {p.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-muted-foreground">
            {visibleLatency.length} pts · buffer {elapsedMin}min · 10s cadence
          </span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" /> Engine latency
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <LatencyRow label="Mem0" values={mem0Values} color="#3b82f6" />
            <LatencyRow label="Memobase" values={memobaseValues} color="#10b981" />
            <LatencyRow label="Cognee" values={cogneeValues} color="#a855f7" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" /> Memory growth
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <LatencyRow label="Users" values={userValues} color="#2563eb" />
            <LatencyRow label="Datasets" values={datasetValues} color="#7c3aed" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Stat tile ─────────────────────────────────────────────────────────────

function StatTile({
  icon: Icon,
  label,
  value,
  loading,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number | undefined;
  loading?: boolean;
  color: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">{label}</p>
            <p className="text-3xl font-bold mt-1">
              {loading ? <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /> : (value ?? "—")}
            </p>
          </div>
          <div className={`rounded-full p-2.5 bg-muted ${color}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Users table with per-user memory counts ───────────────────────────────

const MAX_USERS_SHOWN = 30;

function UsersTable({ userIds }: { userIds: string[] }) {
  const shown = userIds.slice(0, MAX_USERS_SHOWN);

  // Fan-out parallel memory count queries — one per user
  const memQueries = useQueries({
    queries: shown.map((uid) => ({
      queryKey: ["mem-count", uid],
      queryFn: () => conversationsApi.list(uid).then((r) => r.total ?? r.data?.length ?? 0),
      staleTime: 60_000,
    })),
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          Users
        </h3>
        {userIds.length > MAX_USERS_SHOWN && (
          <span className="text-xs text-muted-foreground">
            showing {MAX_USERS_SHOWN} of {userIds.length}
          </span>
        )}
      </div>

      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground">User ID</th>
              <th className="text-right px-3 py-2 font-medium text-xs text-muted-foreground">Memories</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((uid, i) => {
              const q = memQueries[i];
              return (
                <tr key={uid} className="border-t hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2 font-mono text-xs">{uid}</td>
                  <td className="px-3 py-2 text-right">
                    {q.isFetching ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin inline text-muted-foreground" />
                    ) : q.isError ? (
                      <span className="text-destructive text-xs">err</span>
                    ) : (
                      <Badge variant="secondary">{q.data}</Badge>
                    )}
                  </td>
                </tr>
              );
            })}
            {shown.length === 0 && (
              <tr>
                <td colSpan={2} className="px-3 py-4 text-center text-xs text-muted-foreground">
                  No users yet — memories will appear after the first conversation is added.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Datasets table ────────────────────────────────────────────────────────

function DatasetsTable({ datasets }: { datasets: KnowledgeDataset[] }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        <Database className="h-4 w-4 text-muted-foreground" />
        Knowledge Datasets
      </h3>

      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground">Name</th>
              <th className="text-left px-3 py-2 font-medium text-xs text-muted-foreground hidden sm:table-cell">Dataset ID</th>
              <th className="text-right px-3 py-2 font-medium text-xs text-muted-foreground hidden md:table-cell">Created</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((ds) => (
              <tr key={ds.id} className="border-t hover:bg-muted/30 transition-colors">
                <td className="px-3 py-2 font-medium">{ds.name}</td>
                <td className="px-3 py-2 font-mono text-xs text-muted-foreground hidden sm:table-cell truncate max-w-[200px]">
                  {ds.id}
                </td>
                <td className="px-3 py-2 text-right text-xs text-muted-foreground hidden md:table-cell">
                  {ds.created_at ? new Date(ds.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
            {datasets.length === 0 && (
              <tr>
                <td colSpan={3} className="px-3 py-4 text-center text-xs text-muted-foreground">
                  No datasets yet — add data and run cognify to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Dashboard page ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const qc = useQueryClient();
  const fetchingCount = useIsFetching();
  const isRefreshing = fetchingCount > 0;
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  function handleRefresh() {
    qc.invalidateQueries({ queryKey: ["health"] });
    qc.invalidateQueries({ queryKey: ["users"] });
    qc.invalidateQueries({ queryKey: ["datasets"] });
    qc.invalidateQueries({ queryKey: ["mem-count"] }); // invalidates all mem-count/* entries
    setLastRefreshed(new Date());
  }

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: healthApi.check,
    refetchInterval: 30_000,
  });

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
    staleTime: 30_000,
  });

  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: knowledgeApi.listDatasets,
    staleTime: 30_000,
  });

  const userIds = usersQuery.data?.data ?? [];
  const datasetList = datasetsQuery.data?.data ?? [];

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Overview of all memory engines and stored data.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {lastRefreshed && !isRefreshing && (
            <span className="text-xs text-muted-foreground hidden sm:block">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      {/* ── Stat tiles ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatTile
          icon={Users}
          label="Total Users"
          value={usersQuery.data?.total}
          loading={usersQuery.isLoading}
          color="text-blue-500"
        />
        <StatTile
          icon={Database}
          label="Datasets"
          value={datasetsQuery.data?.data?.length ?? 0}
          loading={datasetsQuery.isLoading}
          color="text-purple-500"
        />
        <div className="col-span-2 sm:col-span-1">
          <StatTile
            icon={MemoryStick}
            label="API Status"
            value={healthQuery.data?.status}
            loading={healthQuery.isLoading}
            color={
              healthQuery.data?.status === "healthy"
                ? "text-green-500"
                : healthQuery.data?.status === "degraded"
                  ? "text-amber-500"
                  : "text-muted-foreground"
            }
          />
        </div>
      </div>

      {/* ── Engine health ── */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Engine Health</h3>

        {healthQuery.isLoading && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking engines…
          </div>
        )}
        {healthQuery.error && (
          <Card className="border-destructive">
            <CardContent className="pt-4 text-sm text-destructive">
              Cannot reach CozyMemory API: {String(healthQuery.error)}
            </CardContent>
          </Card>
        )}
        {healthQuery.data && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.values(healthQuery.data.engines ?? {}).map((engine) => (
              <EngineCard key={engine.name} engine={engine} />
            ))}
          </div>
        )}
      </div>

      <Separator />

      {/* ── Observability trends ── */}
      <ObservabilityPanel />

      <Separator />

      {/* ── Users + memory counts ── */}
      {usersQuery.isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading users…
        </div>
      ) : (
        <UsersTable userIds={userIds} />
      )}

      <Separator />

      {/* ── Datasets ── */}
      {datasetsQuery.isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading datasets…
        </div>
      ) : (
        <DatasetsTable datasets={datasetList} />
      )}
    </div>
  );
}
