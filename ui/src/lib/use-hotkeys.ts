"use client";

/**
 * 极简键盘快捷键 hook。
 *
 * 支持两种绑定：
 *   - 单键：`?` → 调 handler
 *   - 序列：`g d` → 先按 g（1 秒内）再按 d → 调 handler
 *
 * 聚焦 input/textarea/[contenteditable] 时自动失效，防止打字被截获。
 * 序列按键之间有 SEQUENCE_TIMEOUT_MS 的窗口；超时清空。
 */

import { useEffect, useRef } from "react";

export interface HotkeyBinding {
  /** 单键如 "?"，序列如 "g d"（空格分隔） */
  keys: string;
  handler: () => void;
  /** 描述，用于帮助弹窗 */
  description: string;
}

const SEQUENCE_TIMEOUT_MS = 1000;

function isTextInput(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

export function useHotkeys(bindings: HotkeyBinding[]) {
  // 把 bindings 存引用避免每帧重绑
  const ref = useRef(bindings);
  ref.current = bindings;

  useEffect(() => {
    let buffer: string[] = [];
    let timer: ReturnType<typeof setTimeout> | null = null;

    function reset() {
      buffer = [];
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    }

    function handle(e: KeyboardEvent) {
      if (isTextInput(e.target)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key;
      // 忽略纯修饰符
      if (key === "Shift" || key === "Meta" || key === "Control" || key === "Alt") return;

      buffer.push(key);
      if (timer) clearTimeout(timer);
      timer = setTimeout(reset, SEQUENCE_TIMEOUT_MS);

      const current = buffer.join(" ");
      // 先试完整匹配
      for (const b of ref.current) {
        if (b.keys === current) {
          e.preventDefault();
          b.handler();
          reset();
          return;
        }
      }
      // 看是否有 binding 以当前 buffer 为前缀（需要再等一个键）
      const hasPrefix = ref.current.some((b) => b.keys.startsWith(current + " "));
      if (!hasPrefix) reset();
    }

    window.addEventListener("keydown", handle);
    return () => {
      window.removeEventListener("keydown", handle);
      if (timer) clearTimeout(timer);
    };
  }, []);
}
