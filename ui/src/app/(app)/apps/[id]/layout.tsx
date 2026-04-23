"use client";

/**
 * App 工作台 layout —— 仅职责是把路由 id 同步到 Zustand currentAppId，
 * 确保业务调用带正确的 X-Cozy-App-Id。
 *
 * Step 8.12 前这里曾渲染独立的 workspace sidebar；合并到 AppSidebar 后
 * 此 layout 只剩 side effect，子页直接继承父 (app)/layout 的内边距。
 */

import { use, useEffect } from "react";

import { useAppStore } from "@/lib/store";

export default function AppWorkspaceLayout({
  params,
  children,
}: {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
}) {
  const { id } = use(params);
  const setAppId = useAppStore((s) => s.setCurrentAppId);

  useEffect(() => {
    setAppId(id);
  }, [id, setAppId]);

  return <>{children}</>;
}
