/**
 * apiFetch 测试 — 验证 scoped header 行为、JWT / legacy API key 回退、
 * 以及 401 触发 logout + /login 跳转的多租户 session 过期路径。
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { healthApi, dashboardFetch } from "@/lib/api";
import { useAppStore } from "@/lib/store";

describe("apiFetch scoped", () => {
  beforeEach(() => {
    useAppStore.setState({
      jwt: "",
      apiKey: "",
      currentAppId: "",
      currentAppSlug: "",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("scoped call with JWT and currentAppId sends both headers", async () => {
    useAppStore.setState({ jwt: "jj", currentAppId: "aid-1" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ engines: {} }), { status: 200 })
    );
    await healthApi.check();
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("Authorization")).toBe("Bearer jj");
    expect(h.get("X-Cozy-App-Id")).toBe("aid-1");
    expect(h.get("X-Cozy-API-Key")).toBeNull();
  });

  it("scoped=false (dashboardFetch) sends JWT but no X-Cozy-App-Id", async () => {
    useAppStore.setState({ jwt: "jj", currentAppId: "aid-1" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );
    await dashboardFetch("/dashboard/apps");
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("Authorization")).toBe("Bearer jj");
    expect(h.get("X-Cozy-App-Id")).toBeNull();
  });

  it("falls back to X-Cozy-API-Key when no JWT is set", async () => {
    useAppStore.setState({ apiKey: "legacy-key" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ engines: {} }), { status: 200 })
    );
    await healthApi.check();
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("X-Cozy-API-Key")).toBe("legacy-key");
    expect(h.get("Authorization")).toBeNull();
  });

  it("401 response with JWT present clears JWT and redirects to /login", async () => {
    useAppStore.setState({ jwt: "jj" });
    const assign = vi.fn();
    const orig = window.location;
    Object.defineProperty(window, "location", {
      value: { ...orig, assign, href: orig.href },
      writable: true,
      configurable: true,
    });
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("", { status: 401 })
    );
    await expect(healthApi.check()).rejects.toThrow();
    expect(useAppStore.getState().jwt).toBe("");
    expect(assign).toHaveBeenCalledWith("/login");
  });
});
