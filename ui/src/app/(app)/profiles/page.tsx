"use client";

import { useState, memo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profilesApi, type ProfileItem, type ProfileResponse } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Trash2, User } from "lucide-react";
import { UserSelector } from "@/components/user-selector";
import { EmptyState } from "@/components/empty-state";
import { useT } from "@/lib/i18n";

const ProfileItemRow = memo(function ProfileItemRow({
  item,
  onDelete,
}: {
  item: ProfileItem;
  onDelete: (id: string) => void;
}) {
  const t = useT();
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border p-3 text-sm">
      <div className="flex-1 space-y-1">
        <div className="flex gap-2 flex-wrap">
          {item.topic && <Badge variant="secondary">{item.topic}</Badge>}
          {item.sub_topic && <Badge variant="outline">{item.sub_topic}</Badge>}
        </div>
        <p>{item.content}</p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 h-7 w-7"
        aria-label={t("profiles.delete.aria")}
        title={t("common.delete")}
        onClick={() => onDelete(item.id)}
      >
        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>
    </div>
  );
});

export default function ProfilesPage() {
  const t = useT();
  const [userId, setUserId] = useState("");
  const [newItem, setNewItem] = useState({ topic: "", sub_topic: "", content: "" });
  const qc = useQueryClient();

  const profileQuery = useQuery({
    queryKey: ["profile", userId],
    queryFn: () => profilesApi.get(userId),
    enabled: !!userId,
  });

  // CozyMemory transparently maps any string userId → UUID v4 for all
  // /profiles/* routes (including /context), so passing the raw userId is safe.
  const contextQuery = useQuery({
    queryKey: ["profile-context", userId],
    queryFn: () => profilesApi.getContext(userId),
    enabled: !!userId,
  });

  const deleteMutation = useMutation({
    mutationFn: (profileId: string) => profilesApi.deleteItem(userId, profileId),
    onMutate: async (profileId) => {
      await qc.cancelQueries({ queryKey: ["profile", userId] });
      const previous = qc.getQueryData<ProfileResponse>(["profile", userId]);
      qc.setQueryData<ProfileResponse>(["profile", userId], (old) => {
        if (!old?.data) return old;
        return {
          ...old,
          data: {
            ...old.data,
            topics: (old.data.topics ?? []).filter((t) => t.id !== profileId),
          },
        };
      });
      return { previous };
    },
    onError: (e, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(["profile", userId], ctx.previous);
      toast.error((e as Error).message);
    },
    onSuccess: () => toast.success(t("profiles.delete.success")),
    onSettled: () => qc.invalidateQueries({ queryKey: ["profile", userId] }),
  });

  const addMutation = useMutation({
    mutationFn: () => profilesApi.addItem(userId, newItem),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile", userId] });
      setNewItem({ topic: "", sub_topic: "", content: "" });
      toast.success(t("profiles.add.success"));
    },
    onError: (e) => toast.error((e as Error).message),
  });

  function handleLoad(id: string) {
    setUserId(id);
  }

  const handleDelete = useCallback(
    (id: string) => deleteMutation.mutate(id),
    [deleteMutation],
  );

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">{t("profiles.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">{t("profiles.subtitle")}</p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <UserSelector
            onConfirm={handleLoad}
            loading={profileQuery.isFetching}
            buttonLabel={t("common.load")}
          />
        </CardContent>
      </Card>

      {contextQuery.data?.data?.context && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="h-4 w-4" /> {t("profiles.contextPrompt")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs whitespace-pre-wrap font-mono bg-muted rounded p-3">
              {contextQuery.data.data.context}
            </pre>
          </CardContent>
        </Card>
      )}

      {profileQuery.data?.data && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              {t("profiles.items.count", { n: (profileQuery.data.data.topics ?? []).length })}
            </span>
            <span className="text-xs text-muted-foreground">{t("profiles.items.for")} {userId}</span>
          </div>
          <ScrollArea className="h-64">
            <div className="space-y-2 pr-2">
              {(profileQuery.data.data.topics ?? []).map((item) => (
                <ProfileItemRow
                  key={item.id}
                  item={item}
                  onDelete={handleDelete}
                />
              ))}
              {(profileQuery.data.data.topics ?? []).length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">{t("profiles.empty")}</p>
              )}
            </div>
          </ScrollArea>

          <Separator />

          <div className="space-y-2">
            <p className="text-sm font-medium">{t("profiles.add.title")}</p>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder={t("profiles.add.topic")}
                value={newItem.topic}
                onChange={(e) => setNewItem((p) => ({ ...p, topic: e.target.value }))}
              />
              <Input
                placeholder={t("profiles.add.subTopic")}
                value={newItem.sub_topic}
                onChange={(e) => setNewItem((p) => ({ ...p, sub_topic: e.target.value }))}
              />
            </div>
            <div className="flex gap-2">
              <Input
                placeholder={t("profiles.add.content")}
                value={newItem.content}
                onChange={(e) => setNewItem((p) => ({ ...p, content: e.target.value }))}
              />
              <Button
                onClick={() => addMutation.mutate()}
                disabled={!newItem.topic || !newItem.content || addMutation.isPending || !userId}
              >
                {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t("profiles.add.btn")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {!userId && (
        <EmptyState
          icon={User}
          title={t("empty.noUser.title")}
          description={t("empty.profiles.desc")}
          action={{ label: t("empty.openPlayground"), href: "/playground" }}
        />
      )}
    </div>
  );
}
