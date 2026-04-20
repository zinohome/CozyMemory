/**
 * Client-side observability store — 环形缓冲时序数据，持久化到 localStorage
 * 以便 reload 后保留观察窗口。
 *
 * 设计选择：
 *   - 每条 point 约 80 字节，60 条 × 2 series ≈ 10KB << localStorage 配额。
 *   - 容量上限 MAX_POINTS，最旧的被挤出。
 *   - 统一时间戳由轮询器写入。
 *   - reload 时（onRehydrateStorage）过滤掉超出窗口的 stale 点，避免显示
 *     几小时前的旧数据冒充当前状态。
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// 固定 10s 采样间隔，统一存 6h 数据；UI 按用户选的窗口做显示过滤。
// 2160 × 80B × 2 series ≈ 350KB，localStorage 配额（~5MB）绰绰有余。
export const POLL_INTERVAL_MS = 10_000;
export const MAX_POINTS = 2160; // 2160 × 10s = 6 小时
const WINDOW_MS = MAX_POINTS * POLL_INTERVAL_MS;

export const WINDOW_PRESETS = [
  { label: "10m", minutes: 10 },
  { label: "1h", minutes: 60 },
  { label: "6h", minutes: 360 },
] as const;
export type WindowMinutes = (typeof WINDOW_PRESETS)[number]["minutes"];

export interface LatencyPoint {
  ts: number;
  mem0: number | null; // ms，null 表示引擎不健康或未测到
  memobase: number | null;
  cognee: number | null;
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
}

export interface CountsPoint {
  ts: number;
  users: number;
  datasets: number;
}

interface MetricsState {
  latency: LatencyPoint[];
  counts: CountsPoint[];
  pushLatency: (p: LatencyPoint) => void;
  pushCounts: (p: CountsPoint) => void;
  clear: () => void;
}

function append<T>(arr: T[], item: T): T[] {
  const next = arr.length >= MAX_POINTS ? arr.slice(arr.length - MAX_POINTS + 1) : arr.slice();
  next.push(item);
  return next;
}

function dropStale<T extends { ts: number }>(arr: T[]): T[] {
  const cutoff = Date.now() - WINDOW_MS;
  return arr.filter((p) => p.ts >= cutoff);
}

export const useMetricsStore = create<MetricsState>()(
  persist(
    (set) => ({
      latency: [],
      counts: [],
      pushLatency: (p) => set((s) => ({ latency: append(s.latency, p) })),
      pushCounts: (p) => set((s) => ({ counts: append(s.counts, p) })),
      clear: () => set({ latency: [], counts: [] }),
    }),
    {
      name: "cozymemory-metrics",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      // 只持久化数据字段，不持久化 action 函数
      partialize: (s) => ({ latency: s.latency, counts: s.counts }),
      // reload 时剔除过期点：避免一觉睡醒看到 8 小时前的数据
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.latency = dropStale(state.latency);
        state.counts = dropStale(state.counts);
      },
    }
  )
);
