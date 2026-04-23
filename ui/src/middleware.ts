// NOTE: Next.js 16 deprecates the `middleware` file convention in favor of
// `proxy`. We intentionally keep `middleware.ts` here to match the task spec;
// if/when migrating to `proxy.ts`, rename the file and the exported function
// (`middleware` -> `proxy`). See
// `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md`.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const p = req.nextUrl.pathname;
  const isPublic =
    p.startsWith("/login") ||
    p.startsWith("/register") ||
    p.startsWith("/_next") ||
    p.startsWith("/api") ||
    p === "/favicon.ico";
  if (isPublic) return NextResponse.next();

  const hasJwt = req.cookies.get("cm_auth")?.value === "1";
  if (!hasJwt) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
