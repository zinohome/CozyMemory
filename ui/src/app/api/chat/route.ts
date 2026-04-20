/**
 * Server-side LLM proxy for the Playground.
 *
 * 浏览器不能直接暴露 LLM_API_KEY，所以这条路由在 Next.js Node runtime 运行，
 * 转发到容器网络里的 caddy:9090（内部 LLM 代理）。
 *
 * Env：
 *   LLM_ENDPOINT  例如 http://caddy:9090/v1
 *   LLM_API_KEY   bearer token
 *   LLM_MODEL     默认模型，若请求未带 model 字段
 */

import { NextResponse } from "next/server";

export const runtime = "nodejs";

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatRequest {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export async function POST(req: Request) {
  const endpoint = process.env.LLM_ENDPOINT;
  const apiKey = process.env.LLM_API_KEY;
  const defaultModel = process.env.LLM_MODEL ?? "gpt-4.1-nano-2025-04-14";

  if (!endpoint || !apiKey) {
    return NextResponse.json(
      { error: "LLM_ENDPOINT or LLM_API_KEY not configured on server" },
      { status: 500 }
    );
  }

  const body = (await req.json()) as ChatRequest;
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return NextResponse.json({ error: "messages[] required" }, { status: 400 });
  }

  const stream = body.stream === true;

  const upstream = await fetch(`${endpoint.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: body.model ?? defaultModel,
      messages: body.messages,
      temperature: body.temperature ?? 0.7,
      max_tokens: body.max_tokens ?? 512,
      stream,
    }),
    // 关闭 Node 上游超时等异常路径，upstream 会自然结束
    signal: req.signal,
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: `LLM upstream ${upstream.status}`, detail: text.slice(0, 500) },
      { status: 502 }
    );
  }

  if (stream && upstream.body) {
    // 直通 SSE 流。浏览器 fetch 可直接 reader.read() 逐块消费。
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        // 禁用 Next/Caddy 的缓冲，流立即可见
        "X-Accel-Buffering": "no",
      },
    });
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
