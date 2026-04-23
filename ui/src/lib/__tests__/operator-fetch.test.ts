import { beforeEach, describe, expect, it, vi } from "vitest";

import { operatorFetch } from "@/lib/api";
import { useOperatorStore } from "@/lib/store";

describe("operatorFetch", () => {
  beforeEach(() => {
    useOperatorStore.setState({ operatorKey: "" });
    vi.restoreAllMocks();
  });

  it("未设置 operatorKey 时抛错", async () => {
    await expect(operatorFetch("/health")).rejects.toThrow(/operator key missing/i);
  });

  it("发 X-Cozy-API-Key 头，不发 Authorization / X-Cozy-App-Id", async () => {
    useOperatorStore.setState({ operatorKey: "kkk" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await operatorFetch("/operator/orgs");
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("X-Cozy-API-Key")).toBe("kkk");
    expect(h.get("Authorization")).toBeNull();
    expect(h.get("X-Cozy-App-Id")).toBeNull();
  });

  it("401 清 operatorKey 并跳 /operator", async () => {
    useOperatorStore.setState({ operatorKey: "bad" });
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, assign, href: "" },
      writable: true,
      configurable: true,
    });
    vi.spyOn(global, "fetch").mockResolvedValueOnce(new Response("", { status: 401 }));
    await expect(operatorFetch("/operator/orgs")).rejects.toThrow();
    expect(useOperatorStore.getState().operatorKey).toBe("");
    expect(assign).toHaveBeenCalledWith("/operator");
  });
});
