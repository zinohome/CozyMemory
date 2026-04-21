"use client";

/**
 * ContextInspector — Playground 右侧面板，展示上一次 /api/v1/context
 * 返回结果：conv/profile/knowledge 计数 + 详情 + latency + engine errors。
 *
 * 从 playground/page.tsx 抽出纯展示组件。
 */

import type { ContextResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Brain } from "lucide-react";

interface Props {
  data: ContextResponse | null;
}

export function ContextInspector({ data }: Props) {
  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4" />
          <p className="font-medium text-sm">Last context injected</p>
        </div>
        {!data ? (
          <p className="text-xs text-muted-foreground">
            Send a message to see what memories/profile/knowledge were injected into the system prompt.
          </p>
        ) : (
          <div className="space-y-2 text-xs">
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="secondary">
                conv {data.conversations?.length ?? 0}
              </Badge>
              <Badge variant="secondary">
                profile {data.profile_context ? "✓" : "—"}
              </Badge>
              <Badge variant="secondary">
                knowledge {data.knowledge?.length ?? 0}
              </Badge>
              {data.latency_ms != null && (
                <Badge variant="outline">{Math.round(data.latency_ms)}ms</Badge>
              )}
            </div>
            {data.conversations && data.conversations.length > 0 && (
              <div>
                <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                  Conversations
                </p>
                <ul className="space-y-1 mt-1">
                  {data.conversations.map((m) => (
                    <li key={m.id} className="rounded-md border p-2">
                      {m.content}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data.profile_context && (
              <div>
                <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                  Profile
                </p>
                <pre className="whitespace-pre-wrap font-mono bg-muted rounded p-2 text-[10px] mt-1">
                  {data.profile_context}
                </pre>
              </div>
            )}
            {data.knowledge && data.knowledge.length > 0 && (
              <div>
                <p className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide mt-2">
                  Knowledge
                </p>
                <ul className="space-y-1 mt-1">
                  {data.knowledge.map((k, i) => (
                    <li key={i} className="rounded-md border p-2">
                      {(k.text as string) ?? JSON.stringify(k).slice(0, 200)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data.errors && Object.keys(data.errors).length > 0 && (
              <div>
                <p className="font-medium text-[11px] text-destructive uppercase tracking-wide mt-2">
                  Engine errors
                </p>
                <ul className="space-y-0.5 mt-1">
                  {Object.entries(data.errors).map(([engine, err]) => (
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
  );
}
