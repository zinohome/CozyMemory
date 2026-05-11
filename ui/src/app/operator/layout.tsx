"use client";

import { Shield } from "lucide-react";
import { MetricsPoller } from "@/components/metrics-poller";
import { OperatorGuard } from "@/components/operator-guard";
import { OperatorSidebar } from "@/components/operator-sidebar";
import { SidebarResizeHandle } from "@/components/sidebar-resize-handle";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { I18nProvider } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const sidebarWidth = useAppStore((s) => s.sidebarWidth);

  return (
    <I18nProvider>
      <OperatorGuard>
        <MetricsPoller />
        <SidebarProvider
          style={{ "--sidebar-width": `${sidebarWidth}px` } as React.CSSProperties}
        >
          <div className="flex h-full w-full">
            <OperatorSidebar />
            <SidebarResizeHandle />
            <main className="flex-1 flex flex-col min-w-0 overflow-auto">
              <header className="flex items-center gap-3 px-5 py-2.5 border-b bg-card/60 backdrop-blur-sm shrink-0">
                <SidebarTrigger className="-ml-1" />
                <div className="h-4 w-px bg-border" />
                <div className="flex items-center gap-1.5 text-sm">
                  <Shield className="size-3.5 text-primary" />
                  <span className="font-medium">Operator</span>
                </div>
                <div className="flex-1" />
              </header>
              <div className="flex-1 p-5 sm:p-7 min-w-0 min-h-full bg-mesh">{children}</div>
            </main>
          </div>
        </SidebarProvider>
      </OperatorGuard>
    </I18nProvider>
  );
}
