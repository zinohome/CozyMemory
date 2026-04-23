"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAppStore } from "@/lib/store";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const jwt = useAppStore((s) => s.jwt);
  const router = useRouter();
  // Zustand persist 从 localStorage 恢复是异步的；首次渲染 jwt=""
  // 会误触发 redirect。等 hydration 完成再判定。
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (useAppStore.persist.hasHydrated()) {
      setHydrated(true);
      return;
    }
    const unsub = useAppStore.persist.onFinishHydration(() => setHydrated(true));
    return () => unsub();
  }, []);

  useEffect(() => {
    if (hydrated && !jwt) router.replace("/login");
  }, [hydrated, jwt, router]);

  if (!hydrated) return null;
  if (!jwt) return null;
  return <>{children}</>;
}
