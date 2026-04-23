"use client";

/**
 * Operator 视角的轮询器：每 10s 并发拉 health / users / datasets，push 到
 * metrics-store 给 /operator/health 页面画图。
 *
 * Step 8 后只挂在 operator layout 里 —— 用 operatorFetch（bootstrap key）
 * 避开 Bearer+AppId 鉴权，不会因无 AppId 触发 401 → logout 回踢。
 */

import { useEffect } from "react";
import { operatorApi } from "@/lib/api";
import { useMetricsStore, POLL_INTERVAL_MS } from "@/lib/metrics-store";

export function MetricsPoller() {
  const pushLatency = useMetricsStore((s) => s.pushLatency);
  const pushCounts = useMetricsStore((s) => s.pushCounts);

  useEffect(() => {
    let aborted = false;

    async function tick() {
      const ts = Date.now();
      const [healthRes, usersRes, datasetsRes] = await Promise.allSettled([
        operatorApi.health(),
        operatorApi.listUsers(),
        operatorApi.listDatasets(),
      ]);
      if (aborted) return;

      if (healthRes.status === "fulfilled") {
        const h = healthRes.value;
        const engines = h.engines ?? {};
        const find = (target: string) => {
          const direct = engines[target.toLowerCase()]?.latency_ms;
          if (direct != null) return direct;
          for (const e of Object.values(engines)) {
            if (e.name?.toLowerCase() === target.toLowerCase()) return e.latency_ms ?? null;
          }
          return null;
        };
        pushLatency({
          ts,
          mem0: find("mem0"),
          memobase: find("memobase"),
          cognee: find("cognee"),
          status: (h.status as "healthy" | "degraded" | "unhealthy") ?? "unknown",
        });
      } else {
        pushLatency({ ts, mem0: null, memobase: null, cognee: null, status: "unknown" });
      }

      const users =
        usersRes.status === "fulfilled" ? (usersRes.value.total ?? usersRes.value.data?.length ?? 0) : 0;
      const datasets =
        datasetsRes.status === "fulfilled" ? (datasetsRes.value.data?.length ?? 0) : 0;
      pushCounts({ ts, users, datasets });
    }

    tick();
    const handle = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      aborted = true;
      clearInterval(handle);
    };
  }, [pushLatency, pushCounts]);

  return null;
}
