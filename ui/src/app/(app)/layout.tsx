"use client";

import { AppSidebar } from "@/components/app-sidebar";
import { AppSwitcher } from "@/components/app-switcher";
import { AuthGuard } from "@/components/auth-guard";
import { HotkeysProvider } from "@/components/hotkeys-provider";
import { SidebarResizeHandle } from "@/components/sidebar-resize-handle";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { UserMenu } from "@/components/user-menu";
import { I18nProvider } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const sidebarWidth = useAppStore((s) => s.sidebarWidth);

  return (
    <I18nProvider>
      <AuthGuard>
        <SidebarProvider
          style={{ "--sidebar-width": `${sidebarWidth}px` } as React.CSSProperties}
        >
          <HotkeysProvider />
          <div className="flex h-full w-full">
            <AppSidebar />
            <SidebarResizeHandle />
            <main className="flex-1 flex flex-col min-w-0 overflow-auto">
              <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
                <SidebarTrigger className="-ml-1" />
                <div className="flex-1" />
                <AppSwitcher />
                <UserMenu />
              </div>
              <div className="flex-1 p-4 sm:p-6 min-w-0">{children}</div>
            </main>
          </div>
        </SidebarProvider>
      </AuthGuard>
    </I18nProvider>
  );
}
