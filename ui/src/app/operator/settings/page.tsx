"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerApiKeysPanel } from "@/components/server-api-keys-panel";
import { useT } from "@/lib/i18n";

export default function OperatorSettings() {
  const t = useT();
  return (
    <div className="space-y-4 max-w-4xl">
      <h1 className="text-xl font-semibold">{t("operator.settings")}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.legacy_bootstrap_title")}</CardTitle>
          <CardDescription>{t("settings.legacy_bootstrap_desc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ServerApiKeysPanel />
        </CardContent>
      </Card>
    </div>
  );
}
