"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { conversationsApi, type ConversationMemory } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Search, Trash2, MessageSquare } from "lucide-react";

function MemoryRow({
  mem,
  onDelete,
}: {
  mem: ConversationMemory;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border p-3 text-sm">
      <div className="flex-1 space-y-1">
        <p>{mem.memory}</p>
        <div className="flex gap-2 text-xs text-muted-foreground flex-wrap">
          <span className="font-mono">{mem.id}</span>
          {mem.created_at && <span>{new Date(mem.created_at).toLocaleString()}</span>}
        </div>
      </div>
      <Button variant="ghost" size="icon" className="shrink-0 h-7 w-7" onClick={() => onDelete(mem.id)}>
        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>
    </div>
  );
}

export default function MemoryLabPage() {
  const { currentUserId, setCurrentUserId } = useAppStore();
  const [userId, setUserId] = useState(currentUserId);
  const [searchQuery, setSearchQuery] = useState("");
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["memories", userId],
    queryFn: () => conversationsApi.list(userId),
    enabled: !!userId,
  });

  const searchMutation = useMutation({
    mutationFn: () => conversationsApi.search({ query: searchQuery, user_id: userId }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories", userId] }),
  });

  function handleLoad() {
    setCurrentUserId(userId);
    qc.invalidateQueries({ queryKey: ["memories", userId] });
  }

  const displayList: ConversationMemory[] =
    searchMutation.data?.data ?? listQuery.data?.data ?? [];

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">Memory Lab</h1>
        <p className="text-muted-foreground text-sm mt-1">Browse and manage Mem0 conversation memories.</p>
      </div>

      <Card>
        <CardContent className="pt-4 space-y-3">
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
              <Button onClick={handleLoad} disabled={!userId || listQuery.isFetching}>
                {listQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load"}
              </Button>
            </div>
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Semantic search…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchMutation.mutate()}
            />
            <Button
              variant="outline"
              onClick={() => searchMutation.mutate()}
              disabled={!searchQuery || !userId || searchMutation.isPending}
            >
              {searchMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {listQuery.data && (
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            {searchMutation.data ? (
              <>Showing {displayList.length} search results</>
            ) : (
              <>{listQuery.data.total} memories</>
            )}
          </span>
          {searchMutation.data && (
            <Button variant="ghost" size="sm" onClick={() => searchMutation.reset()}>
              Clear search
            </Button>
          )}
        </div>
      )}

      <ScrollArea className="h-[500px]">
        <div className="space-y-2 pr-2">
          {displayList.map((mem) => (
            <MemoryRow key={mem.id} mem={mem} onDelete={(id) => deleteMutation.mutate(id)} />
          ))}
          {listQuery.data && displayList.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">No memories found.</p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
