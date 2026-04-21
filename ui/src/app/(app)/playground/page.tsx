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
import { conversationsApi, contextApi, type ContextResponse } from "@/lib/api";
import { useAppStore, DEFAULT_PLAYGROUND_SYSTEM_PROMPT } from "@/lib/store";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Send, RotateCcw, Square, Sliders, Plus, Trash2, MessageCircle } from "lucide-react";
import { ContextInspector } from "@/components/context-inspector";
import { UserSelector } from "@/components/user-selector";
import { EmptyState } from "@/components/empty-state";
import { usePlaygroundSessions, type ChatMsg } from "@/lib/playground-sessions-store";

function formatContextAsSystemBlock(head: string, ctx: ContextResponse): string {
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
  return lines.length ? `${head}\n\n${lines.join("\n")}` : head;
}

/**
 * 从 OpenAI-compatible SSE data chunk 里抠出 delta.content。
 * 上游格式：`data: {"choices":[{"delta":{"content":"hello"}}]}\n\n` 或 `data: [DONE]\n\n`
 */
function extractDeltas(buffer: string): { deltas: string[]; rest: string; done: boolean } {
  const deltas: string[] = [];
  let done = false;
  const lines = buffer.split("\n");
  // 最后一行可能不完整，保留为下一次循环的 rest
  const rest = lines.pop() ?? "";
  for (const raw of lines) {
    const line = raw.trim();
    if (!line.startsWith("data:")) continue;
    const payload = line.slice(5).trim();
    if (payload === "[DONE]") {
      done = true;
      continue;
    }
    try {
      const obj = JSON.parse(payload);
      const d = obj?.choices?.[0]?.delta?.content;
      if (typeof d === "string") deltas.push(d);
    } catch {
      // 忽略非 JSON chunk（例如 upstream 偶发的注释/keepalive）
    }
  }
  return { deltas, rest, done };
}

// 与后端 /api/chat 的 LLM_MODEL 默认保持一致；其他为 oneapi 常见可用模型，
// 用户可通过 "Custom" 选项填任意非列表值
const MODEL_PRESETS = [
  "gpt-4.1-nano-2025-04-14",
  "gpt-4o-mini",
  "gpt-4o",
  "gpt-4.1-mini",
  "claude-sonnet-4-6",
];
const CUSTOM_MODEL = "__custom__";

export default function PlaygroundPage() {
  const { sessions, activeId, newSession, setActive, upsertMessages, deleteSession } =
    usePlaygroundSessions();
  const activeSession = sessions.find((s) => s.id === activeId) ?? null;

  const [userId, setUserId] = useState(activeSession?.userId ?? "");
  const [messages, setMessages] = useState<ChatMsg[]>(activeSession?.messages ?? []);
  const [input, setInput] = useState("");

  // 切换会话时同步本地 state
  useEffect(() => {
    if (activeSession) {
      setMessages(activeSession.messages);
      setUserId(activeSession.userId);
    } else {
      setMessages([]);
    }
    // 只在 activeId 真正变化时跑（不要跟 activeSession 引用变化触发）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastContext, setLastContext] = useState<ContextResponse | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [model, setModel] = useState<string>(MODEL_PRESETS[0]);
  const [customModel, setCustomModel] = useState<string>("");
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxTokens, setMaxTokens] = useState<number>(512);
  const { playgroundSystemPrompt, setPlaygroundSystemPrompt } = useAppStore();
  // 空字符串表示"沿用默认"，方便新用户看到默认值但不自动写入 store
  const effectiveSystemPrompt = playgroundSystemPrompt || DEFAULT_PLAYGROUND_SYSTEM_PROMPT;
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 实际发请求用的 model：custom 模式下取 customModel，否则取下拉选项
  const effectiveModel = model === CUSTOM_MODEL ? customModel.trim() : model;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingText]);

  // 清理：离开页面时取消 in-flight 请求
  useEffect(() => () => abortRef.current?.abort(), []);

  async function handleSend() {
    const userMsg = input.trim();
    if (!userMsg || !userId || isStreaming) return;
    if (!userId) {
      toast.error("Please select or enter a user ID first");
      return;
    }

    setInput("");
    setIsStreaming(true);
    setStreamingText("");
    setSaveStatus("idle");

    const ac = new AbortController();
    abortRef.current = ac;

    const now = new Date().toISOString();
    const historySnapshot = messages;
    setMessages([...historySnapshot, { role: "user", content: userMsg, createdAt: now }]);

    try {
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

      // 2) 流式调 LLM
      const systemPrompt = formatContextAsSystemBlock(effectiveSystemPrompt, ctx);
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: ac.signal,
        body: JSON.stringify({
          stream: true,
          model: effectiveModel || undefined,
          temperature,
          max_tokens: maxTokens,
          messages: [
            { role: "system", content: systemPrompt },
            ...historySnapshot.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: userMsg },
          ],
        }),
      });

      if (!resp.ok || !resp.body) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail ?? err.error ?? `LLM HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let full = "";

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { deltas, rest, done: sseDone } = extractDeltas(buffer);
        buffer = rest;
        if (deltas.length > 0) {
          for (const d of deltas) full += d;
          setStreamingText(full);
        }
        if (sseDone) break;
      }

      // 3) 完成，把 streaming 文本合并进永久 messages + 持久化
      const finalMsg: ChatMsg = {
        role: "assistant",
        content: full || "(empty response)",
        createdAt: new Date().toISOString(),
      };
      const nextMessages = [
        ...historySnapshot,
        { role: "user" as const, content: userMsg, createdAt: now },
        finalMsg,
      ];
      setMessages(nextMessages);
      setStreamingText("");
      // 如果还没有 active session，就即时建一个；否则更新现有会话
      const sessionId = activeId ?? newSession(userId);
      upsertMessages(sessionId, nextMessages, userId);

      // 4) 异步写回 Mem0
      setSaveStatus("saving");
      conversationsApi
        .add({
          user_id: userId,
          messages: [
            { role: "user", content: userMsg },
            { role: "assistant", content: finalMsg.content },
          ],
          infer: true,
        })
        .then(() => setSaveStatus("saved"))
        .catch(() => setSaveStatus("error"));
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        // 用户主动取消，把已经流出来的文本归档
        if (streamingText) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: streamingText + " …(cancelled)", createdAt: new Date().toISOString() },
          ]);
        }
      } else {
        toast.error((e as Error).message);
      }
      setStreamingText("");
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleCancel() {
    abortRef.current?.abort();
  }

  function handleNewChat() {
    abortRef.current?.abort();
    newSession(userId);
    setMessages([]);
    setLastContext(null);
    setSaveStatus("idle");
    setStreamingText("");
  }

  function handleReset() {
    abortRef.current?.abort();
    setMessages([]);
    setLastContext(null);
    setSaveStatus("idle");
    setStreamingText("");
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
        <div className="flex items-center gap-2">
          {sessions.length > 0 && (
            <Select
              value={activeId ?? undefined}
              onValueChange={(v) => v && setActive(v)}
            >
              <SelectTrigger className="w-52 text-xs" aria-label="Load session">
                <SelectValue placeholder="Load session…" />
              </SelectTrigger>
              <SelectContent>
                {sessions.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    <span className="truncate max-w-[180px] inline-block align-middle">
                      {s.title}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" size="sm" onClick={handleNewChat} aria-label="New chat">
            <Plus className="h-3.5 w-3.5 mr-1.5" /> New
          </Button>
          {activeId && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => deleteSession(activeId)}
              title="Delete this session"
              aria-label="Delete current session"
            >
              <Trash2 className="h-3.5 w-3.5 text-destructive" />
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={messages.length === 0}
            aria-label="Reset current session"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reset
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-4">
          <UserSelector onConfirm={setUserId} buttonLabel="Use" />

          <details className="mt-3 group">
            <summary className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden">
              <Sliders className="h-3 w-3" />
              <span className="group-open:font-medium">
                Model: {effectiveModel || "<empty>"} · temp {temperature} · max {maxTokens}
                {playgroundSystemPrompt ? " · custom prompt" : ""}
              </span>
              <span className="ml-1 opacity-60 group-open:rotate-90 transition-transform">▶</span>
            </summary>

            <div className="space-y-1.5 mt-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs">System prompt</Label>
                {playgroundSystemPrompt && (
                  <button
                    type="button"
                    className="text-[11px] text-muted-foreground hover:text-foreground underline"
                    onClick={() => setPlaygroundSystemPrompt("")}
                  >
                    Reset to default
                  </button>
                )}
              </div>
              <Textarea
                value={effectiveSystemPrompt}
                onChange={(e) => setPlaygroundSystemPrompt(e.target.value)}
                className="min-h-[72px] font-mono text-xs"
                placeholder={DEFAULT_PLAYGROUND_SYSTEM_PROMPT}
              />
              <p className="text-[11px] text-muted-foreground">
                Prepended to every turn; retrieved context is appended underneath. Persists in
                this browser.
              </p>
            </div>

            <div className="grid grid-cols-[1fr_auto_auto] gap-2 mt-3 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Model</Label>
                <Select value={model} onValueChange={(v) => setModel(v ?? MODEL_PRESETS[0])}>
                  <SelectTrigger className="h-9 text-xs" aria-label="Model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MODEL_PRESETS.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                    <SelectItem value={CUSTOM_MODEL}>Custom…</SelectItem>
                  </SelectContent>
                </Select>
                {model === CUSTOM_MODEL && (
                  <Input
                    placeholder="model-name"
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    className="h-9 text-xs font-mono mt-1"
                  />
                )}
              </div>

              <div className="space-y-1 w-24">
                <Label className="text-xs">Temperature</Label>
                <Input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="h-9 text-xs"
                />
              </div>

              <div className="space-y-1 w-24">
                <Label className="text-xs">Max tokens</Label>
                <Input
                  type="number"
                  min={16}
                  max={8192}
                  step={16}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                  className="h-9 text-xs"
                />
              </div>
            </div>
          </details>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-[1fr_340px] gap-4">
        {/* ── Chat transcript ── */}
        <Card>
          <CardContent className="pt-4 flex flex-col h-[560px]">
            <ScrollArea className="flex-1 pr-2" ref={scrollRef}>
              <div className="space-y-3">
                {messages.length === 0 && (
                  userId ? (
                    <p className="text-sm text-muted-foreground text-center py-16">
                      Type a message to start
                    </p>
                  ) : (
                    <EmptyState
                      icon={MessageCircle}
                      title="No user selected"
                      description="Pick a user above to start a chat augmented with their memories, profile, and knowledge graph."
                      className="my-8"
                    />
                  )
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
                {isStreaming && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2 text-sm whitespace-pre-wrap">
                      {streamingText || (
                        <span className="flex items-center gap-2 text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
                        </span>
                      )}
                      {streamingText && (
                        <span className="inline-block h-3 w-[2px] bg-foreground/70 animate-pulse ml-0.5" />
                      )}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>


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
                disabled={!userId || isStreaming}
                className="min-h-[60px] max-h-[120px] resize-none"
              />
              {isStreaming ? (
                <Button onClick={handleCancel} variant="destructive" title="Stop generating" aria-label="Stop generating">
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleSend} disabled={!input.trim() || !userId} aria-label="Send message">
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ── Context inspector ── */}
        <ContextInspector data={lastContext} />
      </div>
    </div>
  );
}
