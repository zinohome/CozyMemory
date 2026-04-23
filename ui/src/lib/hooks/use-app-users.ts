"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { dashboardFetch } from "@/lib/api";

export interface ExtUser {
  external_user_id: string;
  internal_uuid: string;
  created_at: string;
}

export interface ExtUserList {
  data: ExtUser[];
  total: number;
}

export function useAppUsers(appId: string, limit: number, offset: number) {
  return useQuery<ExtUserList>({
    queryKey: ["apps", appId, "users", limit, offset],
    queryFn: () =>
      dashboardFetch<ExtUserList>(
        `/dashboard/apps/${appId}/users?limit=${limit}&offset=${offset}`,
      ),
    enabled: !!appId,
  });
}

export function useDeleteAppUser(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (extId: string) =>
      dashboardFetch(
        `/dashboard/apps/${appId}/users/${encodeURIComponent(extId)}`,
        { method: "DELETE" },
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["apps", appId, "users"] }),
  });
}
