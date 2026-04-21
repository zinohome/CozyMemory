"use client";

/**
 * 根级错误边界 — 当 RootLayout 本身抛错时 Next.js 会装载此组件，
 * 所以它必须提供完整 <html>/<body> 且不能依赖 RootLayout 的 Providers。
 */

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error boundary caught:", error);
  }, [error]);

  const isDev = process.env.NODE_ENV !== "production";

  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", padding: "2rem", background: "#0f1117", color: "#e2e8f0" }}>
        <div style={{ maxWidth: "40rem", margin: "0 auto", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>Something broke badly</h1>
          <p style={{ opacity: 0.75, marginBottom: "1.5rem" }}>
            The app root crashed. Reload the page; if it keeps happening, check the server logs.
          </p>
          {isDev && error.message && (
            <pre
              style={{
                background: "#1e2230",
                padding: "1rem",
                borderRadius: "0.5rem",
                textAlign: "left",
                whiteSpace: "pre-wrap",
                fontSize: "0.8rem",
                overflow: "auto",
              }}
            >
              {error.message}
              {error.digest && `\n(digest: ${error.digest})`}
            </pre>
          )}
          <button
            onClick={() => reset()}
            style={{
              marginTop: "1.5rem",
              padding: "0.5rem 1rem",
              border: "1px solid #4a4f66",
              background: "#1e2230",
              color: "inherit",
              borderRadius: "0.375rem",
              cursor: "pointer",
            }}
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
