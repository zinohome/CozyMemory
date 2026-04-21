import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { MetricsPoller } from "@/components/metrics-poller";
import { HotkeysProvider } from "@/components/hotkeys-provider";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <MetricsPoller />
      <HotkeysProvider />
      <div className="flex h-full w-full">
        <AppSidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-auto">
          <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
            <SidebarTrigger className="-ml-1" />
          </div>
          <div className="flex-1 p-6">{children}</div>
        </main>
      </div>
    </SidebarProvider>
  );
}
