"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export function UserMenu() {
  const t = useT();
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);

  function doLogout() {
    logout();
    document.cookie = "cm_auth=; Path=/; Max-Age=0";
    router.replace("/login");
  }

  return (
    <Button variant="ghost" size="sm" onClick={doLogout} aria-label={t("auth.logout")}>
      <LogOut className="size-4 mr-2" />
      {t("auth.logout")}
    </Button>
  );
}
