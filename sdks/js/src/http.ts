import { APIError, AuthError } from "./errors.js";

export interface HTTPOptions {
  apiKey: string;
  baseUrl?: string;
  timeoutMs?: number;
}

export type Query = Record<string, string | number | boolean | undefined>;

export class HTTP {
  private apiKey: string;
  private baseUrl: string;
  private timeoutMs: number;

  constructor(opts: HTTPOptions) {
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl ?? "http://localhost:8000").replace(/\/$/, "");
    this.timeoutMs = opts.timeoutMs ?? 30_000;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    query?: Query,
  ): Promise<T> {
    const url = new URL(this.baseUrl + path);
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v !== undefined) url.searchParams.set(k, String(v));
      }
    }
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const res = await fetch(url.toString(), {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Cozy-API-Key": this.apiKey,
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      if (!res.ok) {
        let parsed: unknown = {};
        try {
          parsed = await res.json();
        } catch {
          /* ignore */
        }
        const detail =
          (parsed as { detail?: string })?.detail ??
          (parsed as { error?: string })?.error ??
          `HTTP ${res.status}`;
        if (res.status === 401) throw new AuthError(detail);
        throw new APIError(res.status, detail, parsed);
      }
      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    } finally {
      clearTimeout(t);
    }
  }

  get<T>(path: string, query?: Query) {
    return this.request<T>("GET", path, undefined, query);
  }
  post<T>(path: string, body?: unknown, query?: Query) {
    return this.request<T>("POST", path, body, query);
  }
  delete<T>(path: string, query?: Query) {
    return this.request<T>("DELETE", path, undefined, query);
  }
}
