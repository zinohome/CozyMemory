"use client";

/**
 * Conversation Playground
 *
 * 演示 CozyMemory 三引擎协同：
 *   1. 每轮用户发言前，并发调 /api/v1/context 拉历史记忆/画像/知识
 *   2. 用拉到的 context 组装 system prompt，走 /api/chat 调 LLM
 *   3. 回复完成后写回 Mem0（/api/v1/conversations）让后续轮次记住
 *
 * 右侧抽屉展示最近一次 context 拉取结果，便于观察"记忆注入"实际发生了什么。
 */

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { conversationsApi, contextApi, type ContextResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Send, Brain, RotateCcw } from "lucide-react";
import { UserSelector } from "@/components/user-selector";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

const SYSTEM_PROMPT_HEAD =
  "You are a helpful assistant with long-term memory of the user. " +
  "Use the retrieved context below to personalize your answer. " +
  "If context is empty, answer normally. Keep replies concise.";

function formatContextAsSystemBlock(ctx: ContextResponse): string {
  const lines: string[] = [];
  if (ctx.conversations && ctx.conversations.length > 0) {
    lines.push("## Past conversation memories");
    for (const m of ctx.conversations) lines.push(`- ${m.content}`);
  }
  if (ctx.profile_context) {
    lines.push("## User profile");
    lines.push(ctx.profile_context);
  }
  if (ctx.knowledge && ctx.knowledge.length > 0) {
    lines.push("## Knowledge graph results");
    for (const k of ctx.knowledge) {
      const text = (k.text as string) ?? JSON.stringify(k);
      lines.push(`- ${text}`);
    }
  }
  return lines.length ? `${SYSTEM_PROMPT_HEAD}\n\n${lines.join("\n")}` : SYSTEM_PROMPT_HEAD;
}

export default function PlaygroundPage() {
  const [userId, setUserId] = useState("");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [lastContext, setLastContext] = useState<ContextResponse | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const sendMutation = useMutation({
    mutationFn: async (userMsg: string) => {
      if (!userId) throw new Error("Please select or enter a user ID first");

      // 1) 拉 context
      const ctx = await contextApi.fetch({
        user_id: userId,
        query: userMsg,
        include_conversations: true,
        include_profile: true,
        include_knowledge: true,
        memory_scope: "long",
        conversation_limit: 5,
        knowledge_top_k: 3,
        max_token_size: 500,
        knowledge_search_type: "GRAPH_COMPLETION",
      });
      setLastContext(ctx);

      // 2) 组装消息后调 LLM
      const systemPrompt = formatContextAsSystemBlock(ctx);
      const llmPayload = {
        messages: [
          { role: "system" as const, content: systemPrompt },
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: "user" as const, content: userMsg },
        ],
      };
      const llmResp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(llmPayload),
      });
      if (!llmResp.ok) {
        const err = await llmResp.json().catch(() => ({}));
        throw new Error(err.detail ?? err.error ?? `LLM HTTP ${llmResp.status}`);
      }
      const llmData = await llmResp.json();
      const assistantContent = llmData?.choices?.[0]?.message?.content ?? "(empty response)";

      return { assistantContent };
    },
    onSuccess: ({ assistantContent }, userMsg) => {
      const now = new Date().toISOString();
      const newMessages: ChatMsg[] = [
        ...messages,
        { role: "user", content: userMsg, createdAt: now },
        { role: "assistant", content: assistantContent, createdAt: now },
      ];
      setMessages(newMessages);
      setInput("");

      // 3) 异步写回 Mem0（不阻塞 UI）
      setSaveStatus("saving");
      conversationsApi
        .add({
          user_id: userId,
          messages: [
            { role: "user", content: userMsg },
            { role: "assistant", content: assistantContent },
          ],
          infer: true,
        })
        .then(() => setSaveStatus("saved"))
        .catch(() => setSaveStatus("error"));
    },
  });

  function handleSend() {
    const text = input.trim();
    if (!text || !userId || sendMutation.isPending) return;
    sendMutation.mutate(text);
  }

  function handleReset() {
    setMessages([]);
    setLastContext(null);
    setSaveStatus("idle");
    sendMutation.reset();
  }

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Playground</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Chat augmented by Mem0 memories, Memobase profile, and Cognee knowledge.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleReset} disabled={messages.length === 0}>
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reset
        </Button>
      </div>

      <Card>
        <CardContent className="pt-4">
          <UserSelector onConfirm={setUserId} buttonLabel="Use" />
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-[1fr_340px] gap-4">
        {/* ── Chat transcript ── */}
        <Card>
          <CardContent className="pt-4 flex flex-col h-[560px]">
            <ScrollArea className="flex-1 pr-2" ref={scrollRef}>
              <div className="space-y-3">
                {messages.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-16">
                    {userId ? "Type a message to start" : "Select a user to start chatting."}
                  </p>
                )}
                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                        m.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
                {sendMutation.isPending && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2 text-sm flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {sendMutation.error && (
              <p className="text-xs text-destructive mt-2">
                {(sendMutation.error as Error).message}
              </p>
            )}

            <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
              <span>
                {saveStatus === "saving" && (
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> saving to memory…
                  </span>
                )}
                {saveStatus === "saved" && "✅ last turn saved to Mem0"}
                {saveStatus === "error" && "⚠️ memory save failed"}
              </span>
            </div>

            <Separator className="my-2" />

            <div className="flex gap-2">
              <Textarea
                placeholder="Ask anything… (Enter to send, Shift+Enter for newline)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                disabled={!userId || sendMutation.isPending}
                className="min-h-[60px] max-h-[120px] resize-none"
              />
              <Button onClick={handleSend} disabled={!input.trim() || !userId || sendMutation.isPending}>
                {sendMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* ── Context inspector ── */}
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4" />
              <p className="font-medium text-sm">Last context injected</p>
            </div>
            {!lastContext ? (
              <p className="text-xs text-muted-foreground">
                Send a message to see what memories/profile/knowledge were injected into the system prompt.
              </p>
            ) : (
              <div className="space-y-2 text-xs">
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="secondary">
                    conv {lastContext.conversations?.length ?? 0}
                  </Badge>
                  <Badge variant="secondary">
                    profile {lastContext.profile_context ? "✓" : "—"}
                  </Badge>
                  <Badge variant="secondary">
                    knowledge {lastContext.knowledge?.length ?? 0}
                  </Badge>
                  {lastContext.latency_ms != null && (
                    <Badge variant="outline">{Math.round(lastContext.latency_ms)}ms</Badge>
                  )}
                </div>
                {lastContext.conversations && lastContext.conversations.length > 0 && (
                  <div>
                    <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                      Conversations
                    </p>
                    <ul className="space-y-1 mt-1">
                      {lastContext.conversations.map((m) => (
                        <li key={m.id} className="rounded-md border p-2">
                          {m.content}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {lastContext.profile_context && (
                  <div>
                    <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                      Profile
                    </p>
                    <pre className="whitespace-pre-wrap font-mono bg-muted rounded p-2 text-[10px] mt-1">
                      {lastContext.profile_context}
                    </pre>
                  </div>
                )}
                {lastContext.knowledge && lastContext.knowledge.length > 0 && (
                  <div>
                    <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                      Knowledge
                    </p>
                    <ul className="space-y-1 mt-1">
                      {lastContext.knowledge.map((k, i) => (
                        <li key={i} className="rounded-md border p-2">
                          {(k.text as string) ?? JSON.stringify(k).slice(0, 200)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {lastContext.errors && Object.keys(lastContext.errors).length > 0 && (
                  <div>
                    <p className="font-medium text-[11px] text-destructive uppercase tracking-wide mt-2">
                      Engine errors
                    </p>
                    <ul className="space-y-0.5 mt-1">
                      {Object.entries(lastContext.errors).map(([engine, err]) => (
                        <li key={engine} className="text-destructive">
                          {engine}: {err}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
