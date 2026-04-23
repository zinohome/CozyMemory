"use client";

import { use } from "react";
import Link from "next/link";
import { KeyRound, Users } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useApps } from "@/lib/hooks/use-apps";
import { useT } from "@/lib/i18n";

export default function AppDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useT();
  const { data: apps } = useApps();
  const app = apps?.find((a) => a.id === id);

  if (!app) return <p>{t("common.loading")}</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{app.name}</h1>
        <p className="text-sm text-muted-foreground">/{app.slug}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link href={`/apps/${id}/keys`}>
          <Card className="hover:bg-accent transition-colors">
            <CardHeader>
              <CardTitle>
                <KeyRound className="size-4 inline mr-2" />
                {t("keys.title")}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {t("keys.manage_hint")}
            </CardContent>
          </Card>
        </Link>
        <Link href={`/apps/${id}/users`}>
          <Card className="hover:bg-accent transition-colors">
            <CardHeader>
              <CardTitle>
                <Users className="size-4 inline mr-2" />
                {t("apps.users_title")}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {t("apps.users_manage_hint")}
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
