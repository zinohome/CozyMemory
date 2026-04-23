"use client";

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
              <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
                <SidebarTrigger className="-ml-1" />
                <span className="text-sm text-muted-foreground">Operator Mode</span>
              </div>
              <div className="flex-1 p-4 sm:p-6 min-w-0">{children}</div>
            </main>
          </div>
        </SidebarProvider>
      </OperatorGuard>
    </I18nProvider>
  );
}
