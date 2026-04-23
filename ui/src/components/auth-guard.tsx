"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAppStore } from "@/lib/store";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const jwt = useAppStore((s) => s.jwt);
  const router = useRouter();

  useEffect(() => {
    if (!jwt) router.replace("/login");
  }, [jwt, router]);

  if (!jwt) return null;
  return <>{children}</>;
}
