"use client";

/**
 * 挂在 AppLayout 里的 side-effect 组件：每 10s 并发拉 health + users +
 * datasets，把结果 push 到 metrics-store。NOT 为用户可见 UI，只是轮询器。
 *
 * 跨页面导航保持活跃 —— Dashboard 离开也继续攒数据，回来时直接看到
 * 完整窗口。
 */

import { useEffect } from "react";
import { healthApi, usersApi, knowledgeApi } from "@/lib/api";
import { useMetricsStore } from "@/lib/metrics-store";

const POLL_INTERVAL_MS = 10_000;

export function MetricsPoller() {
  const pushLatency = useMetricsStore((s) => s.pushLatency);
  const pushCounts = useMetricsStore((s) => s.pushCounts);

  useEffect(() => {
    let aborted = false;

    async function tick() {
      const ts = Date.now();

      // 并发拉三个端点；单个失败不影响其他 series
      const [healthRes, usersRes, datasetsRes] = await Promise.allSettled([
        healthApi.check(),
        usersApi.list(),
        knowledgeApi.listDatasets(),
      ]);

      if (aborted) return;

      if (healthRes.status === "fulfilled") {
        const h = healthRes.value;
        // 后端 engines dict key 是小写 "mem0"/"memobase"/"cognee"，不是 name 字段
        // 的 PascalCase。先按字面 key 查，失败 fallback 到扫 values 按 name 匹配。
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
        datasetsRes.status === "fulfilled"
          ? (datasetsRes.value.data?.length ?? 0)
          : 0;
      pushCounts({ ts, users, datasets });
    }

    // 首次立即跑一次，随后定时
    tick();
    const handle = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      aborted = true;
      clearInterval(handle);
    };
  }, [pushLatency, pushCounts]);

  return null;
}
