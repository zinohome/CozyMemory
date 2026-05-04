"use client";

import { use } from "react";
import Link from "next/link";
import { KeyRound, Users } from "lucide-react";

import { IntegrationQuickstart } from "@/components/integration-quickstart";
import { UsageCard } from "@/components/usage-card";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useApps } from "@/lib/hooks/use-apps";
import { useAppKeys } from "@/lib/hooks/use-app-keys";
import { useAppUsers } from "@/lib/hooks/use-app-users";
import { useT } from "@/lib/i18n";

export default function AppDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useT();
  const { data: apps } = useApps();
  const { data: keys } = useAppKeys(id);
  const { data: users } = useAppUsers(id, 1, 0);
  const app = apps?.find((a) => a.id === id);

  if (!app) return <p>{t("common.loading")}</p>;

  const keyCount = keys?.length ?? 0;
  const userCount = users?.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{app.name}</h1>
        <p className="text-sm text-muted-foreground">/{app.slug}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link href={`/apps/${id}/keys`}>
          <Card className="hover:border-primary/40 hover:shadow-md transition-all h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>
                  <KeyRound className="size-4 inline mr-2 text-primary" />
                  {t("keys.title")}
                </span>
                <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-sm">
                  {keyCount} 个
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {t("keys.manage_hint")}
            </CardContent>
          </Card>
        </Link>
        <Link href={`/apps/${id}/users`}>
          <Card className="hover:border-primary/40 hover:shadow-md transition-all h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>
                  <Users className="size-4 inline mr-2 text-primary" />
                  {t("apps.users_title")}
                </span>
                <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-sm">
                  {userCount} 位
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {t("apps.users_manage_hint")}
            </CardContent>
          </Card>
        </Link>
      </div>

      <IntegrationQuickstart appId={id} appSlug={app.slug} />
      <UsageCard appId={id} />
    </div>
  );
}
