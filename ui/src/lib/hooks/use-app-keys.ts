"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { dashboardFetch } from "@/lib/api";

/**
 * API Key types — mirror backend `ApiKeyInfo` / `ApiKeyCreateResponse`
 * in `src/cozymemory/models/api_key.py`.
 */
export interface KeyRow {
  id: string;
  app_id: string;
  name: string;
  prefix: string;
  environment: string;
  disabled: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface KeyCreated {
  record: KeyRow;
  key: string;
}

interface KeyListResponse {
  success: boolean;
  data: KeyRow[];
  total: number;
}

export function useAppKeys(appId: string) {
  return useQuery<KeyRow[]>({
    queryKey: ["apps", appId, "keys"],
    queryFn: async () => {
      const res = await dashboardFetch<KeyListResponse>(
        `/dashboard/apps/${appId}/keys`,
      );
      return res.data ?? [];
    },
    enabled: !!appId,
  });
}

export function useCreateKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; environment?: "live" | "test" }) =>
      dashboardFetch<KeyCreated>(`/dashboard/apps/${appId}/keys`, {
        method: "POST",
        body: JSON.stringify({
          name: input.name,
          environment: input.environment ?? "live",
        }),
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}

export function useRotateKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      dashboardFetch<KeyCreated>(
        `/dashboard/apps/${appId}/keys/${keyId}/rotate`,
        { method: "POST" },
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}

export function useDeleteKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      dashboardFetch<void>(`/dashboard/apps/${appId}/keys/${keyId}`, {
        method: "DELETE",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}
