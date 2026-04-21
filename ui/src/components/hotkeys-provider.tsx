"use client";

import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import { useHotkeys, type HotkeyBinding } from "@/lib/use-hotkeys";
import { ShortcutHelpDialog } from "@/components/shortcut-help-dialog";

/**
 * 挂在 AppLayout 里的 side-effect 组件：注册全局快捷键。
 * Gmail 式 `g x` 序列做路由跳转，`?` 打开帮助弹窗。
 */
export function HotkeysProvider() {
  const router = useRouter();
  const [helpOpen, setHelpOpen] = useState(false);

  const bindings: HotkeyBinding[] = useMemo(
    () => [
      { keys: "g d", description: "Go to Dashboard", handler: () => router.push("/dashboard") },
      { keys: "g m", description: "Go to Memory Lab", handler: () => router.push("/memory") },
      { keys: "g p", description: "Go to User Profiles", handler: () => router.push("/profiles") },
      { keys: "g k", description: "Go to Knowledge Base", handler: () => router.push("/knowledge") },
      { keys: "g c", description: "Go to Context Studio", handler: () => router.push("/context") },
      { keys: "g y", description: "Go to Playground", handler: () => router.push("/playground") },
      { keys: "g u", description: "Go to Users", handler: () => router.push("/users") },
      { keys: "g b", description: "Go to Backup", handler: () => router.push("/backup") },
      { keys: "g s", description: "Go to Settings", handler: () => router.push("/settings") },
      { keys: "?", description: "Show keyboard shortcuts", handler: () => setHelpOpen(true) },
    ],
    [router]
  );

  useHotkeys(bindings);

  return <ShortcutHelpDialog open={helpOpen} onOpenChange={setHelpOpen} bindings={bindings} />;
}
