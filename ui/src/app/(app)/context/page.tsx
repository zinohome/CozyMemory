"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { contextApi, type ContextResponse, type ConversationMemory, type KnowledgeSearchResult } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Zap, MessageSquare, User, BookOpen, AlertTriangle } from "lucide-react";
import { UserSelector } from "@/components/user-selector";

interface ContextParams {
  user_id: string;
  query: string;
  agent_id: string;
  session_id: string;
  enable_conversations: boolean;
  enable_profile: boolean;
  enable_knowledge: boolean;
  memory_scope: string;
  top_k: number;
  max_token_size: number;
  timeout_ms: number;
}

const DEFAULT_PARAMS: ContextParams = {
  user_id: "",
  query: "",
  agent_id: "",
  session_id: "",
  enable_conversations: true,
  enable_profile: true,
  enable_knowledge: true,
  memory_scope: "long_term",
  top_k: 5,
  max_token_size: 500,
  timeout_ms: 10000,
};

function MemoryCard({ mem }: { mem: ConversationMemory }) {
  return (
    <div className="rounded-md border p-3 text-sm space-y-1">
      <p>{mem.memory}</p>
      <div className="flex gap-3 text-xs text-muted-foreground flex-wrap">
        {mem.session_id && <span>session: {mem.session_id}</span>}
        {mem.agent_id && <span>agent: {mem.agent_id}</span>}
        {mem.created_at && <span>{new Date(mem.created_at).toLocaleDateString()}</span>}
      </div>
    </div>
  );
}

function KnowledgeCard({ item }: { item: KnowledgeSearchResult }) {
  return (
    <div className="rounded-md border p-3 text-sm space-y-1">
      <p>{item.text ?? JSON.stringify(item)}</p>
      {item.score != null && (
        <span className="text-xs text-muted-foreground">score: {(item.score as number).toFixed(3)}</span>
      )}
    </div>
  );
}

export default function ContextStudioPage() {
  const { currentUserId, setCurrentUserId } = useAppStore();
  const [params, setParams] = useState<ContextParams>({ ...DEFAULT_PARAMS, user_id: currentUserId });
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: async (p: ContextParams) => {
      const start = Date.now();
      const res = await contextApi.fetch({
        user_id: p.user_id,
        query: p.query || undefined,
        enable_conversations: p.enable_conversations,
        enable_profile: p.enable_profile,
        enable_knowledge: p.enable_knowledge,
        memory_scope: p.memory_scope,
        top_k: p.top_k,
        max_token_size: p.max_token_size,
        timeout_ms: p.timeout_ms,
      });
      setElapsed(Date.now() - start);
      return res;
    },
    onSuccess: (data) => setResult(data),
  });

  function handleUserSelect(id: string) {
    setCurrentUserId(id);
    setParams((p) => ({ ...p, user_id: id }));
  }

  function handleFetch() {
    mutation.mutate(params);
  }

  const hasErrors = result?.errors && Object.keys(result.errors).length > 0;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div>
        <h1 className="text-2xl font-bold">Context Studio</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Fetch all three memory types in one concurrent call.
        </p>
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        {/* ── Left panel — parameters ── */}
        <Card className="h-fit">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <UserSelector
              label="User ID"
              onConfirm={handleUserSelect}
              withButton={false}
            />

            <div className="space-y-1.5">
              <Label htmlFor="query">Query (optional)</Label>
              <Textarea
                id="query"
                placeholder="What does the user like?"
                rows={2}
                value={params.query}
                onChange={(e) => setParams((p) => ({ ...p, query: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label htmlFor="agent_id">Agent ID</Label>
                <Input
                  id="agent_id"
                  placeholder="optional"
                  value={params.agent_id}
                  onChange={(e) => setParams((p) => ({ ...p, agent_id: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="session_id">Session ID</Label>
                <Input
                  id="session_id"
                  placeholder="optional"
                  value={params.session_id}
                  onChange={(e) => setParams((p) => ({ ...p, session_id: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Memory scope</Label>
              <Select
                value={params.memory_scope}
                onValueChange={(v) => setParams((p) => ({ ...p, memory_scope: v ?? "long_term" }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="long_term">Long-term</SelectItem>
                  <SelectItem value="short_term">Short-term</SelectItem>
                  <SelectItem value="both">Both</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="top_k">Top K</Label>
                <Input
                  id="top_k"
                  type="number"
                  min={1}
                  max={50}
                  value={params.top_k}
                  onChange={(e) => setParams((p) => ({ ...p, top_k: Number(e.target.value) }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max_tokens">Max tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  min={100}
                  value={params.max_token_size}
                  onChange={(e) => setParams((p) => ({ ...p, max_token_size: Number(e.target.value) }))}
                />
              </div>
            </div>

            <Separator />

            <div className="space-y-2 text-sm">
              <p className="font-medium text-xs uppercase text-muted-foreground tracking-wide">Engines</p>
              {(
                [
                  ["enable_conversations", "Mem0 Conversations"],
                  ["enable_profile", "Memobase Profile"],
                  ["enable_knowledge", "Cognee Knowledge"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={params[key]}
                    onChange={(e) => setParams((p) => ({ ...p, [key]: e.target.checked }))}
                    className="rounded"
                  />
                  {label}
                </label>
              ))}
            </div>

            <Button
              onClick={handleFetch}
              disabled={!params.user_id || mutation.isPending}
              className="w-full"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Fetching…
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2" />
                  Fetch Context
                </>
              )}
            </Button>

            {mutation.isError && (
              <p className="text-xs text-destructive">{String(mutation.error)}</p>
            )}
          </CardContent>
        </Card>

        {/* ── Right panel — results ── */}
        <div className="flex flex-col gap-3 min-h-0">
          {result && (
            <>
              <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                <Badge variant="outline">{result.user_id}</Badge>
                {elapsed != null && <span>client: {elapsed}ms</span>}
                {result.latency_ms != null && <span>server: {result.latency_ms}ms</span>}
                {hasErrors && (
                  <span className="flex items-center gap-1 text-amber-500">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {Object.keys(result.errors!).length} engine error(s)
                  </span>
                )}
              </div>

              <Tabs defaultValue="conversations" className="flex-1 flex flex-col min-h-0">
                <TabsList className="w-full justify-start">
                  <TabsTrigger value="conversations" className="gap-1.5">
                    <MessageSquare className="h-3.5 w-3.5" />
                    Conversations
                    {result.conversations && (
                      <Badge variant="secondary" className="text-xs">{result.conversations.length}</Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="profile" className="gap-1.5">
                    <User className="h-3.5 w-3.5" />
                    Profile
                  </TabsTrigger>
                  <TabsTrigger value="knowledge" className="gap-1.5">
                    <BookOpen className="h-3.5 w-3.5" />
                    Knowledge
                    {result.knowledge && (
                      <Badge variant="secondary" className="text-xs">{result.knowledge.length}</Badge>
                    )}
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="conversations" className="flex-1 min-h-0 mt-2">
                  <ScrollArea className="h-96">
                    <div className="space-y-2 pr-3">
                      {result.conversations?.length ? (
                        result.conversations.map((m, i) => <MemoryCard key={m.id ?? i} mem={m} />)
                      ) : (
                        <p className="text-sm text-muted-foreground">No conversation memories.</p>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="profile" className="flex-1 min-h-0 mt-2">
                  <ScrollArea className="h-96">
                    {result.profile_context ? (
                      <pre className="text-sm whitespace-pre-wrap font-mono bg-muted rounded-md p-3">
                        {result.profile_context}
                      </pre>
                    ) : (
                      <p className="text-sm text-muted-foreground">No profile context.</p>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="knowledge" className="flex-1 min-h-0 mt-2">
                  <ScrollArea className="h-96">
                    <div className="space-y-2 pr-3">
                      {result.knowledge?.length ? (
                        result.knowledge.map((item, i) => <KnowledgeCard key={String(item.id ?? i)} item={item} />)
                      ) : (
                        <p className="text-sm text-muted-foreground">No knowledge results.</p>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>

              {hasErrors && (
                <Card className="border-amber-400 bg-amber-50 dark:bg-amber-950/20">
                  <CardContent className="pt-3 pb-3 space-y-1">
                    <p className="text-xs font-medium text-amber-700 dark:text-amber-400">Engine errors</p>
                    {Object.entries(result.errors!).map(([engine, err]) => (
                      <p key={engine} className="text-xs text-amber-600 dark:text-amber-500">
                        <strong>{engine}:</strong> {err}
                      </p>
                    ))}
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {!result && !mutation.isPending && (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm border-2 border-dashed rounded-lg min-h-48">
              Select a user and click &quot;Fetch Context&quot; to see results.
            </div>
          )}

          {mutation.isPending && (
            <div className="flex-1 flex items-center justify-center gap-2 text-muted-foreground text-sm border-2 border-dashed rounded-lg min-h-48">
              <Loader2 className="h-5 w-5 animate-spin" />
              Querying all three engines in parallel…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
