"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  Users,
  Brain,
  UserCircle2,
  Database,
  Activity,
  Archive,
  Settings,
  type LucideIcon,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useT } from "@/lib/i18n";
import type { TKey } from "@/lib/i18n/en";

type NavItem = { href: string; labelKey: TKey; icon: LucideIcon };

const ITEMS: NavItem[] = [
  { href: "/operator/orgs", labelKey: "operator.orgs", icon: Building2 },
  { href: "/operator/users-mapping", labelKey: "operator.users_mapping", icon: Users },
  { href: "/operator/memory-raw", labelKey: "operator.memory_raw", icon: Brain },
  { href: "/operator/profiles-raw", labelKey: "operator.profiles_raw", icon: UserCircle2 },
  { href: "/operator/knowledge-raw", labelKey: "operator.knowledge_raw", icon: Database },
  { href: "/operator/health", labelKey: "operator.health", icon: Activity },
  { href: "/operator/backup", labelKey: "operator.backup", icon: Archive },
  { href: "/operator/settings", labelKey: "operator.settings", icon: Settings },
];

export function OperatorSidebar() {
  const t = useT();
  const pathname = usePathname();

  return (
    <Sidebar role="navigation" aria-label="Operator navigation">
      <SidebarContent className="pt-1">
        <SidebarGroup>
          <SidebarGroupLabel>{t("operator.sidebar.title")}</SidebarGroupLabel>
          <SidebarMenu>
            {ITEMS.map(({ href, labelKey, icon: Icon }) => {
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
    </Sidebar>
  );
}
