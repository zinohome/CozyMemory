"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { conversationsApi, type ConversationListResponse, type ConversationMemory } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Search, Trash2, MessageSquare } from "lucide-react";
import { UserSelector } from "@/components/user-selector";
import { EmptyState } from "@/components/empty-state";

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
        <p>{mem.content}</p>
        <div className="flex gap-2 text-xs text-muted-foreground flex-wrap">
          <span className="font-mono">{mem.id}</span>
          {mem.created_at && <span>{new Date(mem.created_at).toLocaleString()}</span>}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 h-7 w-7"
        aria-label="Delete memory"
        title="Delete"
        onClick={() => onDelete(mem.id)}
      >
        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>
    </div>
  );
}

export default function MemoryLabPage() {
  const [userId, setUserId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["memories", userId],
    queryFn: () => conversationsApi.list(userId),
    enabled: !!userId,
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      conversationsApi.search({
        query: searchQuery,
        user_id: userId,
        limit: 10,
        memory_scope: "long",
      }),
    onError: (e) => toast.error((e as Error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    // Optimistic delete: 立即从 cache 移除，失败则回滚
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["memories", userId] });
      const previous = qc.getQueryData<ConversationListResponse>(["memories", userId]);
      qc.setQueryData<ConversationListResponse>(["memories", userId], (old) => {
        if (!old) return old;
        return { ...old, data: (old.data ?? []).filter((m) => m.id !== id) };
      });
      return { previous };
    },
    onError: (e, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(["memories", userId], ctx.previous);
      toast.error((e as Error).message);
    },
    onSuccess: () => toast.success("Memory deleted"),
    onSettled: () => qc.invalidateQueries({ queryKey: ["memories", userId] }),
  });

  function handleLoad(id: string) {
    setUserId(id);
    searchMutation.reset();
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
          <UserSelector
            onConfirm={handleLoad}
            loading={listQuery.isFetching}
            buttonLabel="Load"
          />

          <div className="flex gap-2">
            <Input
              placeholder="Semantic search…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && userId && searchQuery && searchMutation.mutate()}
              disabled={!userId}
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
              <>Showing {displayList.length} search results for &ldquo;{searchQuery}&rdquo;</>
            ) : (
              <>{listQuery.data.total} memories for <strong>{userId}</strong></>
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
          {!userId && (
            <EmptyState
              icon={MessageSquare}
              title="No user selected"
              description="Pick a user above to browse their Mem0 conversation memories, or head to Playground to start a new chat."
              action={{ label: "Open Playground", href: "/playground" }}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
