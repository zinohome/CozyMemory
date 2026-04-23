"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { dashboardFetch } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  developer_count: number;
  app_count: number;
}

export interface MemberInfo {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface MemberListResponse {
  data: MemberInfo[];
  total: number;
}

export function useOrganization() {
  const jwt = useAppStore((s) => s.jwt);
  return useQuery<OrganizationInfo>({
    queryKey: ["organization"],
    queryFn: () => dashboardFetch<OrganizationInfo>("/dashboard/organization"),
    enabled: !!jwt,
    staleTime: 60_000,
  });
}

export function useUpdateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; slug?: string }) =>
      dashboardFetch<OrganizationInfo>("/dashboard/organization", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organization"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useMembers() {
  const jwt = useAppStore((s) => s.jwt);
  return useQuery<MemberListResponse>({
    queryKey: ["organization", "members"],
    queryFn: () =>
      dashboardFetch<MemberListResponse>("/dashboard/organization/developers"),
    enabled: !!jwt,
    staleTime: 60_000,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { old_password: string; new_password: string }) =>
      dashboardFetch<void>("/auth/password", {
        method: "PATCH",
        body: JSON.stringify(body),
        // /auth/password 的 401 表示"旧密码错"，不是 session 过期；
        // 不走 apiFetch 的自动登出分支。
        skipAuthRedirect: true,
      }),
  });
}
