"use client";

import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import { useHotkeys, type HotkeyBinding } from "@/lib/use-hotkeys";
import { ShortcutHelpDialog } from "@/components/shortcut-help-dialog";
import { useT } from "@/lib/i18n";

/**
 * 挂在 AppLayout 里的 side-effect 组件：注册全局快捷键。
 * Gmail 式 `g x` 序列做路由跳转，`?` 打开帮助弹窗。
 */
export function HotkeysProvider() {
  const router = useRouter();
  const t = useT();
  const [helpOpen, setHelpOpen] = useState(false);

  const bindings: HotkeyBinding[] = useMemo(
    () => [
      { keys: "g d", description: t("hotkeys.go.dashboard"), handler: () => router.push("/dashboard") },
      { keys: "g m", description: t("hotkeys.go.memory"), handler: () => router.push("/memory") },
      { keys: "g p", description: t("hotkeys.go.profiles"), handler: () => router.push("/profiles") },
      { keys: "g k", description: t("hotkeys.go.knowledge"), handler: () => router.push("/knowledge") },
      { keys: "g c", description: t("hotkeys.go.context"), handler: () => router.push("/context") },
      { keys: "g y", description: t("hotkeys.go.playground"), handler: () => router.push("/playground") },
      { keys: "g u", description: t("hotkeys.go.users"), handler: () => router.push("/users") },
      { keys: "g b", description: t("hotkeys.go.backup"), handler: () => router.push("/backup") },
      { keys: "g s", description: t("hotkeys.go.settings"), handler: () => router.push("/settings") },
      { keys: "?", description: t("hotkeys.help"), handler: () => setHelpOpen(true) },
    ],
    [router, t]
  );

  useHotkeys(bindings);

  return <ShortcutHelpDialog open={helpOpen} onOpenChange={setHelpOpen} bindings={bindings} />;
}
