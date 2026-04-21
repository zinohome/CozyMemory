"use client";

/**
 * EmptyState — 通用空状态组件，提示 + 可选下一步 CTA。
 *
 * 用于每页"尚未选择 user / 尚未有数据"的引导：一个柔和图标 + 标题 +
 * 说明 + 可选跳转按钮。比单行灰字更友好，帮新用户知道去哪里做第一步。
 */

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";

interface Action {
  label: string;
  href?: string;
  onClick?: () => void;
}

interface Props {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: Action;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: Props) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center rounded-lg border-2 border-dashed px-6 py-10 space-y-3 ${className ?? ""}`}
    >
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
        </div>
      )}
      <div className="space-y-1">
        <p className="font-medium text-sm">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground max-w-sm">{description}</p>
        )}
      </div>
      {action && (action.href ? (
        <Link href={action.href} className={buttonVariants({ size: "sm", variant: "outline" })}>
          {action.label}
        </Link>
      ) : (
        <Button size="sm" variant="outline" onClick={action.onClick}>
          {action.label}
        </Button>
      ))}
    </div>
  );
}
