/**
 * useT 测试 — 验证 i18n 基建的三个行为：
 *   1. 默认 locale（zh）返回中文字典
 *   2. 切到 en 返回英文字典
 *   3. `{name}` 插值替换
 *   4. 缺失 key 的 fallback（回退英文，最后 key 本身）
 */

import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { I18nProvider, useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

function wrapper({ children }: { children: React.ReactNode }) {
  return <I18nProvider>{children}</I18nProvider>;
}

describe("useT", () => {
  beforeEach(() => {
    useAppStore.setState({ locale: "zh" });
  });

  it("默认返回中文", () => {
    const { result } = renderHook(() => useT(), { wrapper });
    expect(result.current("sidebar.item.dashboard")).toBe("仪表盘");
  });

  it("切换到 en 返回英文", () => {
    const { result } = renderHook(() => useT(), { wrapper });
    act(() => useAppStore.setState({ locale: "en" }));
    expect(result.current("sidebar.item.dashboard")).toBe("Dashboard");
  });

  it("插值 {name} 能正确替换", () => {
    const { result } = renderHook(() => useT(), { wrapper });
    const out = result.current("memory.count.total", { n: 42 });
    expect(out).toContain("42");
  });

  it("缺失 key 返回 key 本身（而不是崩溃）", () => {
    const { result } = renderHook(() => useT(), { wrapper });
    // @ts-expect-error — 故意传一个不存在的 key
    expect(result.current("this.key.does.not.exist")).toBe("this.key.does.not.exist");
  });
});
