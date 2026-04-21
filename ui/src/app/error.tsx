"use client";

/**
 * 页级错误边界 — Next.js App Router 会在路由段抛出错误时展示此组件。
 * 不处理根布局本身的错误（那由 global-error.tsx 接管）。
 */

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RotateCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // 浏览器 console 记录，便于本地调试
    console.error("App error boundary caught:", error);
  }, [error]);

  const isDev = process.env.NODE_ENV !== "production";

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="max-w-md space-y-4 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">Something went wrong</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The page hit an unexpected error. You can try again or navigate elsewhere.
          </p>
        </div>
        {isDev && error.message && (
          <pre className="rounded-md border bg-muted p-3 text-left font-mono text-xs whitespace-pre-wrap break-words">
            {error.message}
            {error.digest && `\n(digest: ${error.digest})`}
          </pre>
        )}
        <div className="flex justify-center gap-2">
          <Button onClick={() => reset()} aria-label="Retry the failed render">
            <RotateCw className="mr-1 h-4 w-4" />
            Try again
          </Button>
        </div>
      </div>
    </div>
  );
}
