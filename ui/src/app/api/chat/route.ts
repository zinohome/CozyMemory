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
    }),
  });

  const text = await upstream.text();
  if (!upstream.ok) {
    return NextResponse.json(
      { error: `LLM upstream ${upstream.status}`, detail: text.slice(0, 500) },
      { status: 502 }
    );
  }

  // Passthrough the OpenAI-style response — caller picks choices[0].message.content
  return new NextResponse(text, {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
