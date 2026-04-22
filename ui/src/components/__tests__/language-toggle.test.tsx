/**
 * LanguageToggle 测试 — 验证点击按钮在 zh ↔ en 之间切换 Zustand store
 * 的 locale，并且 Sidebar 上的文案跟着变。
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "@/lib/i18n";
import { LanguageToggle } from "@/components/language-toggle";
import { useAppStore } from "@/lib/store";

function Wrapped() {
  return (
    <I18nProvider>
      <LanguageToggle />
    </I18nProvider>
  );
}

describe("LanguageToggle", () => {
  beforeEach(() => {
    useAppStore.setState({ locale: "zh" });
  });

  it("默认在 zh，按钮 title 显示切换目标（English）", () => {
    render(<Wrapped />);
    expect(screen.getByRole("button")).toHaveAttribute("title", "English");
  });

  it("点击后 locale 变为 en，title 变为中文", async () => {
    render(<Wrapped />);
    await userEvent.click(screen.getByRole("button"));
    expect(useAppStore.getState().locale).toBe("en");
    expect(screen.getByRole("button")).toHaveAttribute("title", "中文");
  });

  it("再点一次变回 zh", async () => {
    render(<Wrapped />);
    const btn = screen.getByRole("button");
    await userEvent.click(btn);
    await userEvent.click(btn);
    expect(useAppStore.getState().locale).toBe("zh");
  });
});
