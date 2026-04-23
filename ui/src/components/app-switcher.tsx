"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApps } from "@/lib/hooks/use-apps";
import { useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

export function AppSwitcher() {
  const t = useT();
  const router = useRouter();
  const { data: apps } = useApps();
  const current = useAppStore((s) => s.currentAppId);
  const setCurrent = useAppStore((s) => s.setCurrentAppId);
  const setSlug = useAppStore((s) => s.setCurrentAppSlug);

  useEffect(() => {
    if (!apps || apps.length === 0) return;
    const stillValid = apps.some((a) => a.id === current);
    if (!stillValid) {
      setCurrent(apps[0].id);
      setSlug(apps[0].slug);
    }
  }, [apps, current, setCurrent, setSlug]);

  if (!apps || apps.length === 0) {
    return (
      <button
        type="button"
        onClick={() => router.push("/apps")}
        className="text-sm underline"
      >
        {t("apps.none_create_cta")}
      </button>
    );
  }

  return (
    <Select
      value={current}
      onValueChange={(v) => {
        const a = apps.find((x) => x.id === v);
        if (a) {
          setCurrent(a.id);
          setSlug(a.slug);
        }
      }}
    >
      <SelectTrigger className="w-48">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {apps.map((a) => (
          <SelectItem key={a.id} value={a.id}>
            {a.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
