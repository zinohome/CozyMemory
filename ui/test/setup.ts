/**
 * Vitest global setup — 每个测试文件执行前跑一次。
 *
 * 1. 提供干净的内存版 localStorage（jsdom 的 Storage 在 vitest 4.x 下
 *    有边缘情况，直接给一个 Map-backed 的 polyfill 更可靠且独立）
 * 2. 挂载 @testing-library/jest-dom 的断言（toBeInTheDocument 等）
 * 3. 每个 test 之后自动 cleanup DOM + 清 localStorage，防跨测试泄漏
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// 必须在任何 import 应用代码（Zustand persist 在模块加载时抓 storage）
// 之前就把 polyfill 装好 — 所以这段在 setup.ts 的顶层执行。
const map = new Map<string, string>();
const storage: Storage = {
  get length() {
    return map.size;
  },
  clear: () => map.clear(),
  getItem: (k) => (map.has(k) ? map.get(k)! : null),
  key: (i) => Array.from(map.keys())[i] ?? null,
  removeItem: (k) => void map.delete(k),
  setItem: (k, v) => void map.set(k, String(v)),
};
Object.defineProperty(globalThis, "localStorage", { value: storage, configurable: true });
Object.defineProperty(globalThis, "sessionStorage", { value: storage, configurable: true });

afterEach(() => {
  cleanup();
  localStorage.clear();
});
