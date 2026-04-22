"use client";

/**
 * LanguageToggle — sidebar footer 的中英切换按钮，和 ThemeToggle 并列。
 *
 * 点击在 zh ↔ en 之间切换，状态持久化到 Zustand store（localStorage）。
 */

import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

export function LanguageToggle() {
  const locale = useAppStore((s) => s.locale);
  const setLocale = useAppStore((s) => s.setLocale);
  const t = useT();

  function toggle() {
    setLocale(locale === "zh" ? "en" : "zh");
  }

  const nextLabel = locale === "zh" ? t("sidebar.language.en") : t("sidebar.language.zh");

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={toggle}
      title={nextLabel}
      aria-label={`${t("sidebar.language")}: ${nextLabel}`}
    >
      <Languages className="h-3.5 w-3.5" />
    </Button>
  );
}
