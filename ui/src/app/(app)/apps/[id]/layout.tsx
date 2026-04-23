"use client";

import { use, useEffect } from "react";

import { AppWorkspaceSidebar } from "@/components/app-workspace-sidebar";
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

  return (
    <div className="flex -m-4 sm:-m-6 h-[calc(100vh-3rem)]">
      <AppWorkspaceSidebar />
      <div className="flex-1 min-w-0 overflow-auto p-4 sm:p-6">{children}</div>
    </div>
  );
}
