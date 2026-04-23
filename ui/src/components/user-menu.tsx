"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Settings as SettingsIcon, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMe } from "@/lib/hooks/use-me";
import { useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export function UserMenu() {
  const t = useT();
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);
  const { data: me } = useMe();

  function doLogout() {
    logout();
    document.cookie = "cm_auth=; Path=/; Max-Age=0";
    router.replace("/login");
  }

  return (
    <div className="flex items-center gap-1">
      <div className="hidden sm:flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground border-r pr-3 mr-1">
        <User className="h-3.5 w-3.5" />
        <div className="flex flex-col leading-tight">
          <span className="text-foreground font-medium">
            {me?.name || me?.email?.split("@")[0] || "…"}
          </span>
          <span className="text-[10px] opacity-80">{me?.org_name ?? ""}</span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        render={<Link href="/settings" />}
        aria-label={t("sidebar.item.settings")}
        title={t("sidebar.item.settings")}
      >
        <SettingsIcon className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="sm" onClick={doLogout} aria-label={t("auth.logout")}>
        <LogOut className="size-4 mr-1" />
        <span className="hidden sm:inline">{t("auth.logout")}</span>
      </Button>
    </div>
  );
}
