"use client";

/**
 * Sidebar 右边缘的拖拽条：鼠标按下拖动时持续更新 Zustand `sidebarWidth`，
 * 父 SidebarProvider 通过 style 注入 `--sidebar-width` CSS 变量。
 * 拖动结束 Zustand persist 自动写 localStorage。
 */

import { useCallback, useEffect, useRef } from "react";

import { SIDEBAR_MAX_PX, SIDEBAR_MIN_PX, useAppStore } from "@/lib/store";

export function SidebarResizeHandle() {
  const setWidth = useAppStore((s) => s.setSidebarWidth);
  const draggingRef = useRef(false);

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!draggingRef.current) return;
      const x = e.clientX;
      // 钳制到合理范围；组件本身放在 sidebar 右边界，所以 clientX 就是目标宽度
      setWidth(Math.max(SIDEBAR_MIN_PX, Math.min(SIDEBAR_MAX_PX, x)));
    },
    [setWidth],
  );

  const onMouseUp = useCallback(() => {
    draggingRef.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  function onMouseDown() {
    draggingRef.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize sidebar"
      onMouseDown={onMouseDown}
      className="fixed left-[var(--sidebar-width)] top-0 z-50 h-full w-1 cursor-col-resize bg-transparent hover:bg-border/60 transition-colors"
      style={{ translate: "-2px 0" }}
    />
  );
}
