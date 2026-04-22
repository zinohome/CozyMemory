/**
 * EmptyState 测试 — 纯展示组件，不依赖任何 provider。
 *
 * 验证：
 *   1. title / description 渲染
 *   2. action.href 模式渲染为 <a>（Link）
 *   3. action.onClick 模式渲染为 <button> 且点击触发回调
 *   4. 不传 icon 时不崩溃
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageCircle } from "lucide-react";
import { EmptyState } from "@/components/empty-state";

describe("EmptyState", () => {
  it("渲染 title + description", () => {
    render(<EmptyState title="无数据" description="请先选择用户" />);
    expect(screen.getByText("无数据")).toBeInTheDocument();
    expect(screen.getByText("请先选择用户")).toBeInTheDocument();
  });

  it("传 href 时渲染为 Link（<a>）", () => {
    render(
      <EmptyState
        icon={MessageCircle}
        title="标题"
        action={{ label: "去对话沙盒", href: "/playground" }}
      />
    );
    const link = screen.getByRole("link", { name: "去对话沙盒" });
    expect(link).toHaveAttribute("href", "/playground");
  });

  it("传 onClick 时渲染为 button 并触发回调", async () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="标题"
        action={{ label: "点我", onClick }}
      />
    );
    const btn = screen.getByRole("button", { name: "点我" });
    await userEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("不传 icon / action 也能正常渲染（不崩溃）", () => {
    render(<EmptyState title="裸标题" />);
    expect(screen.getByText("裸标题")).toBeInTheDocument();
  });
});
