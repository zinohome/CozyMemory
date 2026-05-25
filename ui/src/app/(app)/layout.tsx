"use client";

import { AppSidebar } from "@/components/app-sidebar";
import { AppSwitcher } from "@/components/app-switcher";
import { AuthGuard } from "@/components/auth-guard";
import { HotkeysProvider } from "@/components/hotkeys-provider";
import { SidebarResizeHandle } from "@/components/sidebar-resize-handle";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { UserMenu } from "@/components/user-menu";
import { I18nProvider, useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

function AppHeader({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <main className="flex-1 flex flex-col min-w-0 overflow-auto">
      <header className="flex items-center gap-3 px-5 py-2.5 border-b bg-card/60 backdrop-blur-sm shrink-0">
        <SidebarTrigger className="-ml-1" aria-label={t("sidebar.toggleSidebar")} title={t("sidebar.toggleSidebar")} />
        <div className="h-4 w-px bg-border" />
        <div className="flex-1" />
        <AppSwitcher />
        <UserMenu />
      </header>
      <div className="flex-1 p-5 sm:p-7 min-w-0 min-h-full bg-mesh">{children}</div>
    </main>
  );
}

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
            <AppHeader>{children}</AppHeader>
          </div>
        </SidebarProvider>
      </AuthGuard>
    </I18nProvider>
  );
}
