"use client";

/**
 * 统一 sidebar —— 根据当前路由动态显示：
 *   - 永久项：主页 / 应用 / 设置
 *   - 进入 /apps/[id]/* 时展开 "当前 App" 分组（8 个工作台子项）
 *
 * Step 8.12: 合并原 AppSidebar + AppWorkspaceSidebar，消除双层 sidebar 丑陋。
 * 用户反馈后一次性重构。
 */

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import {
  ArrowLeft,
  Beaker,
  Brain,
  Database,
  Eye,
  Home,
  KeyRound,
  LayoutGrid,
  MessageSquare,
  Settings,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { LanguageToggle } from "@/components/language-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { useT } from "@/lib/i18n";
import type { TKey } from "@/lib/i18n/en";

type NavItem = { href: string; labelKey: TKey; icon: LucideIcon };

const PRIMARY_ITEMS: NavItem[] = [
  { href: "/home", labelKey: "sidebar.item.home", icon: Home },
  { href: "/apps", labelKey: "apps.title", icon: LayoutGrid },
];

const SETTINGS_ITEM: NavItem = {
  href: "/settings",
  labelKey: "sidebar.item.settings",
  icon: Settings,
};

function workspaceItems(base: string): NavItem[] {
  return [
    { href: base,                  labelKey: "app_workspace.overview",    icon: LayoutGrid },
    { href: `${base}/keys`,        labelKey: "keys.title",                icon: KeyRound },
    { href: `${base}/users`,       labelKey: "users.ext_title",           icon: Users },
    { href: `${base}/memory`,      labelKey: "app_workspace.memory",      icon: MessageSquare },
    { href: `${base}/profiles`,    labelKey: "app_workspace.profiles",    icon: User },
    { href: `${base}/knowledge`,   labelKey: "app_workspace.knowledge",   icon: Database },
    { href: `${base}/context`,     labelKey: "app_workspace.context",     icon: Eye },
    { href: `${base}/playground`,  labelKey: "app_workspace.playground",  icon: Beaker },
  ];
}

function MenuLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const t = useT();
  const Icon = item.icon;
  const active = pathname === item.href;
  return (
    <SidebarMenuItem>
      <SidebarMenuButton render={<Link href={item.href} />} isActive={active}>
        <Icon className="h-4 w-4" />
        <span>{t(item.labelKey)}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const params = useParams();
  const t = useT();

  // 检测是否在 App 工作台内；用 useParams 的 id 字段，只有匹配
  // /apps/[id]/* 路由树才会有值，根 /apps 列表页不会有
  const appId = params && typeof params.id === "string" ? params.id : null;
  const inWorkspace = Boolean(appId && pathname.startsWith(`/apps/${appId}`));

  return (
    <Sidebar role="navigation" aria-label={t("sidebar.aria.main")}>
      <SidebarHeader className="px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">{t("sidebar.brand")}</span>
        </div>
      </SidebarHeader>

      <SidebarContent className="pt-1">
        {/* 永久项 */}
        <SidebarGroup>
          <SidebarMenu>
            {PRIMARY_ITEMS.map((item) => (
              <MenuLink key={item.href} item={item} pathname={pathname} />
            ))}
          </SidebarMenu>
        </SidebarGroup>

        {/* 当前 App 工作台 —— 仅在 /apps/[id]/* 下展开 */}
        {inWorkspace && appId && (
          <SidebarGroup>
            <SidebarGroupLabel className="flex items-center justify-between pr-2">
              <span>{t("app_workspace.title")}</span>
              <Link
                href="/apps"
                className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                aria-label={t("app_workspace.back_to_apps")}
              >
                <ArrowLeft className="h-3 w-3" />
              </Link>
            </SidebarGroupLabel>
            <SidebarMenu>
              {workspaceItems(`/apps/${appId}`).map((item) => (
                <MenuLink key={item.href} item={item} pathname={pathname} />
              ))}
            </SidebarMenu>
          </SidebarGroup>
        )}

        {/* 设置永远在底部 */}
        <SidebarGroup className="mt-auto">
          <SidebarMenu>
            <MenuLink item={SETTINGS_ITEM} pathname={pathname} />
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
