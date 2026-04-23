"use client";

/**
 * Integration Quick Start —— 在 App 概览页展示客户集成代码。
 *
 * 标签：curl / Python / JavaScript。示例覆盖最典型的两个调用：
 *   - 写入一条对话记忆（POST /conversations）
 *   - 并发拉取 三引擎 统一上下文（POST /context）
 *
 * 鉴权用 X-Cozy-API-Key（客户 app 的正式凭证）。API Key 明文不会存
 * 在我们这边；示例里用占位 cozy_live_xxx，提示用户去 Keys 页复制。
 */

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Check, Copy, KeyRound, Terminal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useT } from "@/lib/i18n";

interface Props {
  appId: string;
  appSlug: string;
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success("已复制");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }
  return (
    <div className="relative">
      <pre className="rounded-md border bg-muted/50 p-3 pr-12 text-xs overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={copy}
        className="absolute top-2 right-2"
        aria-label="copy"
      >
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      </Button>
    </div>
  );
}

function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    return envUrl && envUrl.length > 0 ? envUrl : window.location.origin;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export function IntegrationQuickstart({ appId }: Props) {
  const t = useT();
  const base = getBaseUrl();
  const apiKeyPlaceholder = "cozy_live_<your-key>";

  const curlAdd = `curl -X POST ${base}/api/v1/conversations \\
  -H "Content-Type: application/json" \\
  -H "X-Cozy-API-Key: ${apiKeyPlaceholder}" \\
  -d '{
    "user_id": "alice",
    "messages": [
      {"role": "user", "content": "I love hiking"},
      {"role": "assistant", "content": "Got it, I will remember."}
    ]
  }'`;

  const curlContext = `curl -X POST ${base}/api/v1/context \\
  -H "Content-Type: application/json" \\
  -H "X-Cozy-API-Key: ${apiKeyPlaceholder}" \\
  -d '{"user_id": "alice", "query": "outdoor activity"}'`;

  const pythonSnippet = `import httpx

BASE = "${base}/api/v1"
HEADERS = {"X-Cozy-API-Key": "${apiKeyPlaceholder}"}

async with httpx.AsyncClient() as c:
    # 1) 写入一条对话记忆
    await c.post(
        f"{BASE}/conversations",
        headers=HEADERS,
        json={
            "user_id": "alice",
            "messages": [
                {"role": "user", "content": "I love hiking"},
                {"role": "assistant", "content": "Got it."},
            ],
        },
    )

    # 2) LLM 调用前拉统一上下文（Mem0 + Memobase + Cognee 并发）
    ctx = (await c.post(
        f"{BASE}/context",
        headers=HEADERS,
        json={"user_id": "alice", "query": "outdoor activity"},
    )).json()
    # ctx["conversations"], ctx["profile_context"], ctx["knowledge"] → 拼进 prompt`;

  const jsSnippet = `const BASE = "${base}/api/v1";
const HEADERS = {
  "Content-Type": "application/json",
  "X-Cozy-API-Key": "${apiKeyPlaceholder}",
};

// 1) 写入一条对话记忆
await fetch(\`\${BASE}/conversations\`, {
  method: "POST",
  headers: HEADERS,
  body: JSON.stringify({
    user_id: "alice",
    messages: [
      { role: "user", content: "I love hiking" },
      { role: "assistant", content: "Got it." },
    ],
  }),
});

// 2) LLM 调用前拉统一上下文
const ctx = await fetch(\`\${BASE}/context\`, {
  method: "POST",
  headers: HEADERS,
  body: JSON.stringify({ user_id: "alice", query: "outdoor activity" }),
}).then((r) => r.json());
// ctx.conversations, ctx.profile_context, ctx.knowledge → 拼进 prompt`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Terminal className="h-4 w-4" />
          {t("quickstart.title")}
        </CardTitle>
        <CardDescription>{t("quickstart.subtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded-md p-2.5 border">
          <div className="flex-1 min-w-0">
            <span className="font-medium text-foreground">Base URL: </span>
            <code className="break-all">{base}/api/v1</code>
          </div>
          <Button variant="outline" size="sm" render={<Link href={`/apps/${appId}/keys`} />}>
            <KeyRound className="h-3 w-3 mr-1" />
            {t("quickstart.manage_keys")}
          </Button>
        </div>

        <Tabs defaultValue="curl">
          <TabsList>
            <TabsTrigger value="curl">cURL</TabsTrigger>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="js">JavaScript</TabsTrigger>
          </TabsList>

          <TabsContent value="curl" className="space-y-3 mt-3">
            <div>
              <p className="text-xs font-medium mb-1.5">{t("quickstart.example.add_conv")}</p>
              <CodeBlock code={curlAdd} />
            </div>
            <div>
              <p className="text-xs font-medium mb-1.5">{t("quickstart.example.get_context")}</p>
              <CodeBlock code={curlContext} />
            </div>
          </TabsContent>

          <TabsContent value="python" className="mt-3">
            <CodeBlock code={pythonSnippet} />
          </TabsContent>

          <TabsContent value="js" className="mt-3">
            <CodeBlock code={jsSnippet} />
          </TabsContent>
        </Tabs>

        <p className="text-xs text-muted-foreground">
          {t("quickstart.footer_hint")}
        </p>
      </CardContent>
    </Card>
  );
}
