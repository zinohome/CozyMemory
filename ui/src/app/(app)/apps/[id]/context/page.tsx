"use client";

import { useState, useEffect } from "react";
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
import { useT } from "@/lib/i18n";

interface ContextParams {
  user_id: string;
  query: string;
  agent_id: string;
  session_id: string;
  include_conversations: boolean;
  include_profile: boolean;
  include_knowledge: boolean;
  memory_scope: "short" | "long" | "both";
  knowledge_top_k: number;
  max_token_size: number;
  engine_timeout: number;
}

const DEFAULT_PARAMS: ContextParams = {
  user_id: "",
  query: "",
  agent_id: "",
  session_id: "",
  include_conversations: true,
  include_profile: true,
  include_knowledge: true,
  memory_scope: "long",
  knowledge_top_k: 5,
  max_token_size: 500,
  engine_timeout: 10,
};

function MemoryCard({ mem }: { mem: ConversationMemory }) {
  return (
    <div className="rounded-md border p-3 text-sm space-y-1">
      <p>{mem.content}</p>
      <div className="flex gap-3 text-xs text-muted-foreground flex-wrap">
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
  const t = useT();
  const { currentUserId, setCurrentUserId } = useAppStore();
  const [params, setParams] = useState<ContextParams>({ ...DEFAULT_PARAMS, user_id: currentUserId });
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  // Sync params.user_id whenever the global store changes (e.g. user switches
  // on another page and then navigates back here without re-selecting).
  useEffect(() => {
    setParams((p) => ({ ...p, user_id: currentUserId }));
  }, [currentUserId]);

  const mutation = useMutation({
    mutationFn: async (p: ContextParams) => {
      const start = Date.now();
      const res = await contextApi.fetch({
        user_id: p.user_id,
        query: p.query || undefined,
        include_conversations: p.include_conversations,
        include_profile: p.include_profile,
        include_knowledge: p.include_knowledge,
        memory_scope: p.memory_scope,
        knowledge_top_k: p.knowledge_top_k,
        max_token_size: p.max_token_size,
        engine_timeout: p.engine_timeout,
        conversation_limit: 5,
        knowledge_search_type: "GRAPH_COMPLETION",
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
        <h1 className="text-2xl font-bold">{t("context.title")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("context.subtitle")}
        </p>
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-4 flex-1 min-h-0">
        {/* ── Left panel — parameters ── */}
        <Card className="h-fit">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("context.params.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <UserSelector
              label={t("common.userId")}
              onConfirm={handleUserSelect}
              withButton={false}
            />

            <div className="space-y-1.5">
              <Label htmlFor="query">{t("context.query.optional")}</Label>
              <Textarea
                id="query"
                placeholder={t("context.query.sample")}
                rows={2}
                value={params.query}
                onChange={(e) => setParams((p) => ({ ...p, query: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label htmlFor="agent_id">{t("context.agentId")}</Label>
                <Input
                  id="agent_id"
                  placeholder={t("context.optional")}
                  value={params.agent_id}
                  onChange={(e) => setParams((p) => ({ ...p, agent_id: e.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="session_id">{t("context.sessionId")}</Label>
                <Input
                  id="session_id"
                  placeholder={t("context.optional")}
                  value={params.session_id}
                  onChange={(e) => setParams((p) => ({ ...p, session_id: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>{t("context.memoryScope")}</Label>
              <Select
                value={params.memory_scope}
                onValueChange={(v) =>
                  setParams((p) => ({
                    ...p,
                    memory_scope: (v as "short" | "long" | "both") ?? "long",
                  }))
                }
              >
                <SelectTrigger aria-label={t("context.memoryScope")}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="long">{t("context.memoryScope.long")}</SelectItem>
                  <SelectItem value="short">{t("context.memoryScope.short")}</SelectItem>
                  <SelectItem value="both">{t("context.memoryScope.both")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="top_k">{t("context.topK.label")}</Label>
                <Input
                  id="top_k"
                  type="number"
                  min={1}
                  max={50}
                  value={params.knowledge_top_k}
                  onChange={(e) =>
                    setParams((p) => ({ ...p, knowledge_top_k: Number(e.target.value) }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="max_tokens">{t("context.maxTokens.label")}</Label>
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
              <p className="font-medium text-xs uppercase text-muted-foreground tracking-wide">{t("context.engines.section")}</p>
              {(
                [
                  ["include_conversations", t("context.engines.conversations")],
                  ["include_profile", t("context.engines.profile")],
                  ["include_knowledge", t("context.engines.knowledge")],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={params[key as "include_conversations" | "include_profile" | "include_knowledge"]}
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
                  {t("context.fetchingBtn")}
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2" />
                  {t("context.fetchCtxBtn")}
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
                {elapsed != null && <span>{t("context.client.latency", { n: elapsed })}</span>}
                {result.latency_ms != null && <span>{t("context.server.latency", { n: result.latency_ms })}</span>}
                {hasErrors && (
                  <span className="flex items-center gap-1 text-amber-500">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {t("context.errors.count", { n: Object.keys(result.errors!).length })}
                  </span>
                )}
              </div>

              <Tabs defaultValue="conversations" className="flex-1 flex flex-col min-h-0">
                <TabsList className="w-full justify-start">
                  <TabsTrigger value="conversations" className="gap-1.5">
                    <MessageSquare className="h-3.5 w-3.5" />
                    {t("context.tab.conversations")}
                    {result.conversations && (
                      <Badge variant="secondary" className="text-xs">{result.conversations.length}</Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="profile" className="gap-1.5">
                    <User className="h-3.5 w-3.5" />
                    {t("context.tab.profile")}
                  </TabsTrigger>
                  <TabsTrigger value="knowledge" className="gap-1.5">
                    <BookOpen className="h-3.5 w-3.5" />
                    {t("context.tab.knowledge")}
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
                        <p className="text-sm text-muted-foreground">{t("context.empty.conversations")}</p>
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
                      <p className="text-sm text-muted-foreground">{t("context.empty.profile")}</p>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="knowledge" className="flex-1 min-h-0 mt-2">
                  <ScrollArea className="h-96">
                    <div className="space-y-2 pr-3">
                      {result.knowledge?.length ? (
                        result.knowledge.map((item, i) => <KnowledgeCard key={String(item.id ?? i)} item={item} />)
                      ) : (
                        <p className="text-sm text-muted-foreground">{t("context.empty.knowledge")}</p>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>

              {hasErrors && (
                <Card className="border-amber-400 bg-amber-50 dark:bg-amber-950/20">
                  <CardContent className="pt-3 pb-3 space-y-1">
                    <p className="text-xs font-medium text-amber-700 dark:text-amber-400">{t("context.errors.title")}</p>
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
              {t("context.selectFirst")}
            </div>
          )}

          {mutation.isPending && (
            <div className="flex-1 flex items-center justify-center gap-2 text-muted-foreground text-sm border-2 border-dashed rounded-lg min-h-48">
              <Loader2 className="h-5 w-5 animate-spin" />
              {t("context.fetching")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
