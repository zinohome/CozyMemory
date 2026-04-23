"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import {
  LayoutGrid,
  KeyRound,
  Users,
  Brain,
  UserCircle2,
  Database,
  Eye,
  Beaker,
  ArrowLeft,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import type { TKey } from "@/lib/i18n/en";

interface Item {
  href: string;
  icon: typeof LayoutGrid;
  labelKey: TKey;
}

export function AppWorkspaceSidebar() {
  const t = useT();
  const params = useParams();
  const pathname = usePathname();
  const id = params?.id as string | undefined;
  if (!id) return null;

  const base = `/apps/${id}`;
  const items: Item[] = [
    { href: base, icon: LayoutGrid, labelKey: "app_workspace.overview" },
    { href: `${base}/keys`, icon: KeyRound, labelKey: "keys.title" },
    { href: `${base}/users`, icon: Users, labelKey: "users.ext_title" },
    { href: `${base}/memory`, icon: Brain, labelKey: "app_workspace.memory" },
    { href: `${base}/profiles`, icon: UserCircle2, labelKey: "app_workspace.profiles" },
    { href: `${base}/knowledge`, icon: Database, labelKey: "app_workspace.knowledge" },
    { href: `${base}/context`, icon: Eye, labelKey: "app_workspace.context" },
    { href: `${base}/playground`, icon: Beaker, labelKey: "app_workspace.playground" },
  ];

  return (
    <nav
      className="w-56 border-r shrink-0 p-2 space-y-1 text-sm"
      aria-label={t("app_workspace.title")}
    >
      <Link
        href="/apps"
        className="flex items-center gap-2 px-2 py-1.5 rounded text-muted-foreground hover:bg-muted"
      >
        <ArrowLeft className="size-4" />
        <span>{t("app_workspace.back_to_apps")}</span>
      </Link>
      <div className="h-px bg-border my-1" />
      {items.map((it) => {
        const Icon = it.icon;
        const active = pathname === it.href;
        return (
          <Link
            key={it.href}
            href={it.href}
            className={cn(
              "flex items-center gap-2 px-2 py-1.5 rounded hover:bg-muted",
              active && "bg-muted font-medium",
            )}
          >
            <Icon className="size-4" />
            <span>{t(it.labelKey)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
