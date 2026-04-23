import { OperatorGuard } from "@/components/operator-guard";
import { OperatorSidebar } from "@/components/operator-sidebar";
import { MetricsPoller } from "@/components/metrics-poller";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { I18nProvider } from "@/lib/i18n";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <OperatorGuard>
        <MetricsPoller />
        <SidebarProvider>
          <div className="flex h-full w-full">
            <OperatorSidebar />
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
