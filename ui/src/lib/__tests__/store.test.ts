/**
 * Zustand store 测试 — 验证核心持久化状态和非 Hook 访问路径。
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useAppStore, getApiKey } from "@/lib/store";

describe("useAppStore", () => {
  beforeEach(() => {
    // 每个测试前重置到初始值
    useAppStore.setState({
      currentUserId: "",
      apiKey: "",
      locale: "zh",
      playgroundSystemPrompt: "",
    });
  });

  it("setApiKey 同步写入 state 并可通过 getApiKey 读取（非 Hook 路径）", () => {
    expect(getApiKey()).toBe("");
    useAppStore.getState().setApiKey("cozy-dev-key-001");
    expect(getApiKey()).toBe("cozy-dev-key-001");
    expect(useAppStore.getState().apiKey).toBe("cozy-dev-key-001");
  });

  it("setLocale 切换默认中文到英文", () => {
    expect(useAppStore.getState().locale).toBe("zh");
    useAppStore.getState().setLocale("en");
    expect(useAppStore.getState().locale).toBe("en");
  });

  it("setCurrentUserId 独立于其他字段", () => {
    useAppStore.getState().setApiKey("k");
    useAppStore.getState().setCurrentUserId("alice");
    expect(useAppStore.getState().currentUserId).toBe("alice");
    expect(useAppStore.getState().apiKey).toBe("k");
  });
});
