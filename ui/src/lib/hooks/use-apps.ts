"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { dashboardFetch } from "@/lib/api";

export interface AppRow {
  id: string;
  name: string;
  slug: string;
  namespace_id: string;
  created_at: string;
}

interface AppListEnvelope {
  success: boolean;
  data: AppRow[];
  total: number;
}

export function useApps() {
  return useQuery<AppRow[]>({
    queryKey: ["apps"],
    queryFn: async () => {
      const r = await dashboardFetch<AppListEnvelope>("/dashboard/apps");
      return r.data;
    },
  });
}

export function useCreateApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; slug: string }) =>
      dashboardFetch<AppRow>("/dashboard/apps", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps"] }),
  });
}
