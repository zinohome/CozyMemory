"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { operatorApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function OrgsPage() {
  const t = useT();
  const { data, isLoading } = useQuery({
    queryKey: ["operator", "orgs"],
    queryFn: operatorApi.orgs,
  });
  if (isLoading) return <p>{t("common.loading")}</p>;
  const orgs = data?.data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">
        <Building2 className="size-5 inline mr-2" />
        {t("operator.orgs")}
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {orgs.map((o) => (
          <Card key={o.id}>
            <CardHeader>
              <CardTitle>{o.name}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-1">
              <p className="text-muted-foreground">/{o.slug}</p>
              <p>
                {o.dev_count} developer(s), {o.app_count} app(s)
              </p>
              <p className="text-xs text-muted-foreground">
                {new Date(o.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
        {orgs.length === 0 && (
          <p className="text-muted-foreground">No orgs yet.</p>
        )}
      </div>
    </div>
  );
}
