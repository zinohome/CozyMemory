"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain,
  LayoutGrid,
  Settings,
  type LucideIcon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import { useT, type Locale } from "@/lib/i18n";
import type { TKey } from "@/lib/i18n/en";

type NavItem = { href: string; labelKey: TKey; icon: LucideIcon };

const NAV_ITEMS: NavItem[] = [
  { href: "/apps", labelKey: "apps.title", icon: LayoutGrid },
  { href: "/settings", labelKey: "sidebar.item.settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  const t = useT();

  return (
    <Sidebar role="navigation" aria-label={t("sidebar.aria.main")}>
      <SidebarHeader className="px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">{t("sidebar.brand")}</span>
        </div>
      </SidebarHeader>

      <SidebarContent className="pt-1">
        <SidebarGroup>
          <SidebarMenu>
            {NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton render={<Link href={href} />} isActive={active}>
                    <Icon className="h-4 w-4" />
                    <span>{t(labelKey)}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t px-3 py-2 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t("sidebar.theme")}</span>
          <ThemeToggle />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t("sidebar.language")}</span>
          <LanguageToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}

// locale 类型被下游 LanguageToggle 用，export 避免 tree-shake 问题
export type { Locale };
