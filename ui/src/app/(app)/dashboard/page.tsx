"use client";

import { useQuery } from "@tanstack/react-query";
import { healthApi, type EngineStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, MessageSquare, User, BookOpen, Wifi, WifiOff, Loader2 } from "lucide-react";

const ENGINE_META: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  Mem0: { icon: MessageSquare, label: "Mem0", color: "text-blue-500" },
  Memobase: { icon: User, label: "Memobase", color: "text-green-500" },
  Cognee: { icon: BookOpen, label: "Cognee", color: "text-purple-500" },
};

function EngineCard({ engine }: { engine: EngineStatus }) {
  const meta = ENGINE_META[engine.engine] ?? { icon: Brain, label: engine.engine, color: "text-gray-500" };
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
          {healthy ? (
            <Wifi className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-red-400" />
          )}
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

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["health"],
    queryFn: healthApi.check,
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Real-time status for all three memory engines.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          Checking engine health…
        </div>
      )}

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 text-sm text-destructive">
            Cannot reach CozyMemory API: {String(error)}
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Overall status:</span>
            <Badge variant={data.status === "healthy" ? "default" : data.status === "degraded" ? "secondary" : "destructive"}>
              {data.status}
            </Badge>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {data.engines.map((engine) => (
              <EngineCard key={engine.engine} engine={engine} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
