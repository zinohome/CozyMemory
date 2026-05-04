"use client";

import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CreateAppDialog } from "@/components/create-app-dialog";
import { useApps } from "@/lib/hooks/use-apps";
import { useT } from "@/lib/i18n";

export default function AppsPage() {
  const t = useT();
  const { data: apps, isLoading } = useApps();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("apps.title")}</h1>
        <CreateAppDialog
          trigger={
            <Button>
              <Plus className="size-4 mr-2" />
              {t("apps.create")}
            </Button>
          }
        />
      </div>
      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : !apps || apps.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">{t("apps.none")}</p>
          <CreateAppDialog trigger={<Button>{t("apps.create_first")}</Button>} />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
          {apps.map((a) => (
            <Link key={a.id} href={`/apps/${a.id}`}>
              <Card className="hover:border-primary/40 hover:shadow-md transition-all h-full">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{a.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground font-mono">/{a.slug}</p>
                  <p className="text-xs text-muted-foreground mt-3">
                    {t("apps.created")} {new Date(a.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
