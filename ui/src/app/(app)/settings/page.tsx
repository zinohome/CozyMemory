"use client";

/**
 * Settings —— Developer 账号设置。
 *
 * 三张卡：
 *   1. Account：email / 显示名 / 修改密码
 *   2. Organization：name / slug / 成员数 / App 数 / 修改（owner）
 *   3. Members：org 下所有 developer 列表（只读）
 *
 * 老的 Client API Key 面板（Step 7 之前的单租户工具）已废弃。Bootstrap 管理
 * 入口搬到了 /operator/settings。
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Building2, KeyRound, User, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/hooks/use-me";
import {
  useChangePassword,
  useMembers,
  useOrganization,
  useUpdateOrganization,
} from "@/lib/hooks/use-organization";
import { useT } from "@/lib/i18n";
import { useAppStore } from "@/lib/store";

function ChangePasswordDialog() {
  const t = useT();
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);
  const m = useChangePassword();
  const [open, setOpen] = useState(false);
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirm, setConfirm] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (newPw !== confirm) {
      toast.error(t("account.password.mismatch"));
      return;
    }
    try {
      await m.mutateAsync({ old_password: oldPw, new_password: newPw });
      toast.success(t("account.password.success"));
      setOpen(false);
      // 服务端改密后旧 JWT 仍有效（未强制登出），这里主动登出要求重登更安全
      logout();
      document.cookie = "cm_auth=; Path=/; Max-Age=0";
      router.replace("/login");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("401")) toast.error(t("account.password.wrong_old"));
      else if (msg.includes("400") || msg.includes("differ")) toast.error(t("account.password.same"));
      else toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <KeyRound className="h-4 w-4 mr-1.5" />
          {t("account.password.change")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("account.password.change")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <Label htmlFor="old">{t("account.password.old")}</Label>
            <Input
              id="old"
              type="password"
              autoComplete="current-password"
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="new">{t("account.password.new")}</Label>
            <Input
              id="new"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={72}
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t("auth.password_hint")}
            </p>
          </div>
          <div>
            <Label htmlFor="confirm">{t("account.password.confirm")}</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={m.isPending}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditOrgDialog({
  currentName,
  currentSlug,
  canEdit,
}: {
  currentName: string;
  currentSlug: string;
  canEdit: boolean;
}) {
  const t = useT();
  const m = useUpdateOrganization();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(currentName);
  const [slug, setSlug] = useState(currentSlug);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body: { name?: string; slug?: string } = {};
    if (name !== currentName) body.name = name;
    if (slug !== currentSlug) body.slug = slug;
    if (Object.keys(body).length === 0) {
      setOpen(false);
      return;
    }
    try {
      await m.mutateAsync(body);
      toast.success(t("org.updated"));
      setOpen(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("409")) toast.error(t("org.slug_conflict"));
      else toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" disabled={!canEdit}>
          {t("common.edit")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("org.edit")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <Label htmlFor="org-name">{t("org.name")}</Label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={200}
            />
          </div>
          <div>
            <Label htmlFor="org-slug">{t("org.slug")}</Label>
            <Input
              id="org-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              pattern="^[a-z0-9][a-z0-9\-]*[a-z0-9]$"
              minLength={2}
              maxLength={64}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={m.isPending}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function SettingsPage() {
  const t = useT();
  const { data: me } = useMe();
  const { data: org } = useOrganization();
  const { data: members } = useMembers();

  const isOwner = me?.role === "owner";

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
      </div>

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" />
            {t("account.title")}
          </CardTitle>
          <CardDescription>{t("account.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
            <div className="text-muted-foreground">{t("auth.email")}</div>
            <div className="font-mono">{me?.email ?? "…"}</div>

            <div className="text-muted-foreground">{t("account.role")}</div>
            <div>{me?.role ?? "…"}</div>

            <div className="text-muted-foreground">{t("account.last_login")}</div>
            <div className="text-muted-foreground">
              {me?.last_login_at
                ? new Date(me.last_login_at).toLocaleString()
                : "—"}
            </div>
          </div>
          <div>
            <ChangePasswordDialog />
          </div>
        </CardContent>
      </Card>

      {/* Organization */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            {t("org.title")}
          </CardTitle>
          <CardDescription>
            {isOwner ? t("org.subtitle_owner") : t("org.subtitle_member")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
            <div className="text-muted-foreground">{t("org.name")}</div>
            <div>{org?.name ?? "…"}</div>

            <div className="text-muted-foreground">{t("org.slug")}</div>
            <div className="font-mono">{org?.slug ?? "…"}</div>

            <div className="text-muted-foreground">{t("org.stats")}</div>
            <div>
              {org ? `${org.developer_count} ${t("org.developers")} · ${org.app_count} ${t("org.apps")}` : "…"}
            </div>
          </div>
          {org && (
            <div>
              <EditOrgDialog
                currentName={org.name}
                currentSlug={org.slug}
                canEdit={isOwner}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Members */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4" />
            {t("members.title")}
          </CardTitle>
          <CardDescription>{t("members.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <div className="grid grid-cols-[2fr_2fr_1fr_1fr] gap-2 px-3 py-2 text-xs font-medium border-b bg-muted/30">
              <div>{t("members.col.email")}</div>
              <div>{t("members.col.name")}</div>
              <div>{t("members.col.role")}</div>
              <div>{t("members.col.last_login")}</div>
            </div>
            {members?.data.map((m) => (
              <div
                key={m.id}
                className="grid grid-cols-[2fr_2fr_1fr_1fr] gap-2 px-3 py-2 text-sm items-center border-b last:border-b-0"
              >
                <div className="truncate font-mono text-xs">{m.email}</div>
                <div className="truncate">{m.name || "—"}</div>
                <div>{m.role}</div>
                <div className="text-xs text-muted-foreground">
                  {m.last_login_at
                    ? new Date(m.last_login_at).toLocaleDateString()
                    : "—"}
                </div>
              </div>
            ))}
            {(!members || members.data.length === 0) && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                {t("common.loading")}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
