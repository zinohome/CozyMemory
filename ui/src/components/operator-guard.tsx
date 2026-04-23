"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

import { useOperatorStore } from "@/lib/store";

export function OperatorGuard({ children }: { children: React.ReactNode }) {
  const operatorKey = useOperatorStore((s) => s.operatorKey);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // landing page (/operator) 本身不需要 key
    if (pathname === "/operator") return;
    if (!operatorKey) router.replace("/operator");
  }, [operatorKey, router, pathname]);

  if (pathname !== "/operator" && !operatorKey) return null;
  return <>{children}</>;
}
