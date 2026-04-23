"use client";

import { useQuery } from "@tanstack/react-query";

import { dashboardFetch } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export interface DeveloperInfo {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
  org_name: string;
  org_slug: string;
  is_active: boolean;
  last_login_at: string | null;
}

/**
 * 当前登录 Developer 信息 —— 拉 /auth/me 并缓存。
 * 依赖 JWT，未登录时 enabled=false。
 */
export function useMe() {
  const jwt = useAppStore((s) => s.jwt);
  return useQuery<DeveloperInfo>({
    queryKey: ["me"],
    queryFn: () => dashboardFetch<DeveloperInfo>("/auth/me"),
    enabled: !!jwt,
    staleTime: 60_000,
  });
}
