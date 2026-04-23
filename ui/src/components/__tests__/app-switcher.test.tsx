import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppSwitcher } from "@/components/app-switcher";
import { I18nProvider } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
  dashboardFetch: vi.fn(),
}));
import { dashboardFetch } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <I18nProvider>{ui}</I18nProvider>
    </QueryClientProvider>
  );
}

describe("AppSwitcher", () => {
  beforeEach(() => {
    useAppStore.setState({ jwt: "j", currentAppId: "", currentAppSlug: "" });
    vi.mocked(dashboardFetch).mockReset();
  });

  it("空 apps 显示 create CTA", async () => {
    vi.mocked(dashboardFetch).mockResolvedValueOnce([]);
    render(wrap(<AppSwitcher />));
    await waitFor(() => {
      expect(screen.getByText(/create|创建/i)).toBeInTheDocument();
    });
  });

  it("有 apps 且无持久化 currentAppId → 选第一个", async () => {
    vi.mocked(dashboardFetch).mockResolvedValueOnce([
      { id: "a1", name: "App A", slug: "aa", namespace_id: "n", created_at: "2026-01-01" },
      { id: "a2", name: "App B", slug: "bb", namespace_id: "m", created_at: "2026-01-02" },
    ]);
    render(wrap(<AppSwitcher />));
    await waitFor(() => {
      expect(useAppStore.getState().currentAppId).toBe("a1");
    });
  });

  it("持久化 currentAppId 仍在列表 → 保留", async () => {
    useAppStore.setState({ jwt: "j", currentAppId: "a2", currentAppSlug: "bb" });
    vi.mocked(dashboardFetch).mockResolvedValueOnce([
      { id: "a1", name: "App A", slug: "aa", namespace_id: "n", created_at: "x" },
      { id: "a2", name: "App B", slug: "bb", namespace_id: "m", created_at: "y" },
    ]);
    render(wrap(<AppSwitcher />));
    await waitFor(() => {
      expect(useAppStore.getState().currentAppId).toBe("a2");
    });
  });
});
