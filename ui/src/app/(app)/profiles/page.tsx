"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profilesApi, type ProfileItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Trash2, User } from "lucide-react";
import { UserSelector } from "@/components/user-selector";

function ProfileItemRow({
  item,
  onDelete,
}: {
  item: ProfileItem;
  onDelete: (id: string) => void;
}) {
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
        onClick={() => onDelete(item.id)}
      >
        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>
    </div>
  );
}

export default function ProfilesPage() {
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile", userId] }),
  });

  const addMutation = useMutation({
    mutationFn: () => profilesApi.addItem(userId, newItem),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile", userId] });
      setNewItem({ topic: "", sub_topic: "", content: "" });
    },
  });

  function handleLoad(id: string) {
    setUserId(id);
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">User Profiles</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage Memobase structured user profiles.</p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <UserSelector
            onConfirm={handleLoad}
            loading={profileQuery.isFetching}
            buttonLabel="Load"
          />
        </CardContent>
      </Card>

      {contextQuery.data?.data?.context && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="h-4 w-4" /> Context Prompt
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
            <span className="text-sm font-medium">{profileQuery.data.data.topics.length} profile items</span>
            <span className="text-xs text-muted-foreground">for {userId}</span>
          </div>
          <ScrollArea className="h-64">
            <div className="space-y-2 pr-2">
              {profileQuery.data.data.topics.map((item) => (
                <ProfileItemRow
                  key={item.id}
                  item={item}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
              {profileQuery.data.data.topics.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No profile items.</p>
              )}
            </div>
          </ScrollArea>

          <Separator />

          <div className="space-y-2">
            <p className="text-sm font-medium">Add item</p>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="topic (e.g. interest)"
                value={newItem.topic}
                onChange={(e) => setNewItem((p) => ({ ...p, topic: e.target.value }))}
              />
              <Input
                placeholder="sub_topic (e.g. sport)"
                value={newItem.sub_topic}
                onChange={(e) => setNewItem((p) => ({ ...p, sub_topic: e.target.value }))}
              />
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="content"
                value={newItem.content}
                onChange={(e) => setNewItem((p) => ({ ...p, content: e.target.value }))}
              />
              <Button
                onClick={() => addMutation.mutate()}
                disabled={!newItem.topic || !newItem.content || addMutation.isPending || !userId}
              >
                {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {!userId && (
        <p className="text-sm text-muted-foreground text-center py-8 border-2 border-dashed rounded-lg">
          Select a user to view their profile.
        </p>
      )}
    </div>
  );
}
