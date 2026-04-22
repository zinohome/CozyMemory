"use client";

/**
 * 轻量 i18n —— React Context + Zustand 持久化语言偏好 + 扁平字典。
 *
 * 使用：
 *   const t = useT();
 *   t("sidebar.item.dashboard")          → "仪表盘" 或 "Dashboard"
 *   t("memory.count.total", { n: 12 })   → "共 12 条记忆，属于"
 *
 * 缺 key 时返回 key 本身并在开发模式下 console.warn，方便发现遗漏。
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useAppStore } from "@/lib/store";
import { en, type TKey } from "./en";
import { zh } from "./zh";

const DICTS = { zh, en } as const;
export type Locale = keyof typeof DICTS;

type TFn = (key: TKey, params?: Record<string, string | number>) => string;

const I18nContext = createContext<{ locale: Locale; t: TFn } | null>(null);

function format(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (m, k) =>
    k in params ? String(params[k]) : m,
  );
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const locale = useAppStore((s) => s.locale);

  const value = useMemo(() => {
    const dict = DICTS[locale];
    const t: TFn = (key, params) => {
      const tpl = dict[key] ?? en[key];
      if (tpl === undefined) {
        if (process.env.NODE_ENV !== "production") {
          console.warn(`[i18n] missing key: ${key}`);
        }
        return key;
      }
      return format(tpl, params);
    };
    return { locale, t };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT(): TFn {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useT must be used inside <I18nProvider>");
  return ctx.t;
}

export function useLocale(): Locale {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useLocale must be used inside <I18nProvider>");
  return ctx.locale;
}
