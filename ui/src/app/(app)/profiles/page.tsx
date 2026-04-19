"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profilesApi, type ProfileItem } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Trash2, User } from "lucide-react";

function ProfileItemRow({
  item,
  userId,
  onDelete,
}: {
  item: ProfileItem;
  userId: string;
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
  const { currentUserId, setCurrentUserId } = useAppStore();
  const [userId, setUserId] = useState(currentUserId);
  const [newItem, setNewItem] = useState({ topic: "", sub_topic: "", content: "" });
  const qc = useQueryClient();

  const profileQuery = useQuery({
    queryKey: ["profile", userId],
    queryFn: () => profilesApi.get(userId),
    enabled: !!userId,
  });

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

  function handleLoad() {
    setCurrentUserId(userId);
    qc.invalidateQueries({ queryKey: ["profile", userId] });
    qc.invalidateQueries({ queryKey: ["profile-context", userId] });
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">User Profiles</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage Memobase structured user profiles.</p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex gap-2">
            <div className="flex-1 space-y-1">
              <Label>User ID</Label>
              <Input
                placeholder="user_01"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLoad()}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleLoad} disabled={!userId || profileQuery.isFetching}>
                {profileQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {contextQuery.data?.context && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="h-4 w-4" /> Context Prompt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs whitespace-pre-wrap font-mono bg-muted rounded p-3">
              {contextQuery.data.context}
            </pre>
          </CardContent>
        </Card>
      )}

      {profileQuery.data && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{profileQuery.data.total} profile items</span>
          </div>
          <ScrollArea className="h-64">
            <div className="space-y-2 pr-2">
              {profileQuery.data.profiles.map((item) => (
                <ProfileItemRow
                  key={item.id}
                  item={item}
                  userId={userId}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
              {profileQuery.data.total === 0 && (
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
                disabled={!newItem.topic || !newItem.content || addMutation.isPending}
              >
                {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
