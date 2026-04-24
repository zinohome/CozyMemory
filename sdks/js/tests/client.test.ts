import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthError, CozyMemory } from "../src/index.js";

describe("CozyMemory", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("adds a conversation and sends the API key header", async () => {
    const spy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ success: true }), { status: 200 }),
      );
    const client = new CozyMemory({ apiKey: "k", baseUrl: "http://test" });
    const r = await client.conversations.add("alice", [
      { role: "user", content: "hi" },
    ]);
    expect(r).toEqual({ success: true });
    const req = spy.mock.calls[0][1] as RequestInit;
    expect((req.headers as Record<string, string>)["X-Cozy-API-Key"]).toBe("k");
  });

  it("throws AuthError on 401", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "bad key" }), { status: 401 }),
    );
    const client = new CozyMemory({ apiKey: "k", baseUrl: "http://test" });
    await expect(client.health()).rejects.toBeInstanceOf(AuthError);
  });

  it("serializes query params for delete_all", async () => {
    const spy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(new Response("{}", { status: 200 }));
    const client = new CozyMemory({ apiKey: "k", baseUrl: "http://test" });
    await client.conversations.deleteAll("alice");
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/api/v1/conversations?user_id=alice");
  });
});
