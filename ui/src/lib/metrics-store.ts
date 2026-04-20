/**
 * Client-side observability store — 环形缓冲时序数据，没有后端依赖。
 *
 * 设计选择：
 *   - 内存存，不持久化。reload 清空，换窗口观察 OK。
 *   - 固定容量 MAX_POINTS，最旧的被挤出。
 *   - 统一时间戳由轮询器写入，保证等距对齐便于绘图。
 */

import { create } from "zustand";

export const MAX_POINTS = 60; // 60 × 10s = 10 分钟历史窗口

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
}

function append<T>(arr: T[], item: T): T[] {
  const next = arr.length >= MAX_POINTS ? arr.slice(arr.length - MAX_POINTS + 1) : arr.slice();
  next.push(item);
  return next;
}

export const useMetricsStore = create<MetricsState>((set) => ({
  latency: [],
  counts: [],
  pushLatency: (p) => set((s) => ({ latency: append(s.latency, p) })),
  pushCounts: (p) => set((s) => ({ counts: append(s.counts, p) })),
}));
