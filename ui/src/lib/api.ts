/**
 * CozyMemory API client — typed fetch wrapper for all CozyMemory REST endpoints.
 *
 * Base URL is injected at runtime via NEXT_PUBLIC_API_URL (defaults to /api proxy
 * for same-origin dev, overridden in Docker via entrypoint.sh env replacement).
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string | null;
}

export interface EngineStatus {
  name: string;
  status: "healthy" | "unhealthy" | "disabled";
  latency_ms?: number;
  error?: string | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  engines: Record<string, EngineStatus>;
  timestamp?: string;
}

export interface ConversationMemory {
  id: string;
  content: string;
  user_id?: string;
  agent_id?: string;
  session_id?: string;
  score?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ConversationListResponse {
  success: boolean;
  data: ConversationMemory[];
  total: number;
  short_term_memories?: ConversationMemory[];
  long_term_memories?: ConversationMemory[];
}

export interface ConversationAddRequest {
  user_id: string;
  messages: Message[];
  agent_id?: string;
  session_id?: string;
  infer?: boolean;
  memory_scope?: "short" | "long" | "both";
}

export interface ConversationSearchRequest {
  query: string;
  user_id?: string;
  agent_id?: string;
  session_id?: string;
  limit?: number;
  memory_scope?: "short" | "long" | "both";
}

export interface UserListResponse {
  success: boolean;
  data: string[];
  total: number;
}

export interface UserMappingResponse {
  success: boolean;
  user_id: string;
  uuid: string;
  created: boolean;
}

export interface ProfileItem {
  id: string;
  topic: string;
  sub_topic: string;
  content: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserProfileData {
  user_id: string;
  topics: ProfileItem[];
  updated_at?: string | null;
}

export interface ProfileResponse {
  success: boolean;
  data: UserProfileData | null;
  message?: string;
}

export interface ProfileContextData {
  user_id: string;
  context: string;
}

export interface ProfileContextResponse {
  success: boolean;
  data: ProfileContextData | null;
  message?: string;
}

export interface KnowledgeDataset {
  id: string;
  name: string;
  created_at?: string;
}

export interface KnowledgeSearchResult {
  id?: string;
  text?: string;
  score?: number;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface KnowledgeSearchResponse {
  success: boolean;
  data: KnowledgeSearchResult[];
  total: number;
}

export interface CognifyStatusResponse {
  success: boolean;
  job_id: string;
  status: string;
  data?: Record<string, unknown> | null;
}

export interface DatasetGraphResponse {
  success: boolean;
  dataset_id: string;
  data: unknown;
}

export interface ContextResponse {
  success: boolean;
  user_id: string;
  conversations?: ConversationMemory[];
  profile_context?: string;
  knowledge?: KnowledgeSearchResult[];
  errors?: Record<string, string>;
  latency_ms?: number;
}

export interface ApiError {
  success: false;
  error: string;
  detail?: string;
  engine?: string;
}

// ── Core fetch helper ──────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { params?: Record<string, string | number | boolean | undefined> }
): Promise<T> {
  // Destructure custom `params` out so it is never forwarded to fetch() — the
  // fetch spec does not recognise it and some polyfills throw on unknown keys.
  const { params, ...fetchInit } = init ?? {};

  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const res = await fetch(url.toString(), {
    headers: { "Content-Type": "application/json", ...(fetchInit?.headers ?? {}) },
    ...fetchInit,
  });

  const data = await res.json();
  if (!res.ok) {
    const err = data as ApiError;
    throw new Error(err.detail ?? err.error ?? `HTTP ${res.status}`);
  }
  return data as T;
}

// ── Health ─────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => apiFetch<HealthResponse>("/health"),
};

// ── Conversations (Mem0) ───────────────────────────────────────────────────

export const conversationsApi = {
  list: (userId: string, params?: { agent_id?: string; session_id?: string }) =>
    apiFetch<ConversationListResponse>("/conversations", {
      params: { user_id: userId, ...params },
    }),
  add: (body: ConversationAddRequest) =>
    apiFetch<{ success: boolean; data: ConversationMemory[]; message: string }>("/conversations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  search: (body: ConversationSearchRequest) =>
    apiFetch<ConversationListResponse>("/conversations/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  get: (id: string) => apiFetch<{ success: boolean; data: ConversationMemory }>(`/conversations/${id}`),
  delete: (id: string) =>
    apiFetch<{ success: boolean; message: string }>(`/conversations/${id}`, { method: "DELETE" }),
  deleteAll: (userId: string) =>
    apiFetch<{ success: boolean; message: string }>(`/conversations`, {
      method: "DELETE",
      params: { user_id: userId },
    }),
};

// ── Users (ID mapping) ────────────────────────────────────────────────────

export const usersApi = {
  list: () => apiFetch<UserListResponse>("/users"),
  getUuid: (userId: string, create = false) =>
    apiFetch<UserMappingResponse>(`/users/${userId}/uuid`, { params: { create } }),
  deleteMapping: (userId: string) =>
    apiFetch<{ success: boolean; message: string; warning: string }>(`/users/${userId}/uuid`, {
      method: "DELETE",
    }),
};

// ── Profiles (Memobase) ───────────────────────────────────────────────────

export const profilesApi = {
  get: (userId: string) => apiFetch<ProfileResponse>(`/profiles/${userId}`),
  getContext: (userId: string, maxTokenSize?: number) =>
    apiFetch<ProfileContextResponse>(`/profiles/${userId}/context`, {
      method: "POST",
      body: JSON.stringify({ max_token_size: maxTokenSize ?? 500 }),
    }),
  insert: (body: { user_id: string; messages: Message[]; sync?: boolean }) =>
    apiFetch<{ success: boolean; message: string }>("/profiles/insert", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  flush: (userId?: string) =>
    apiFetch<{ success: boolean; message: string }>("/profiles/flush", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  addItem: (userId: string, body: { topic: string; sub_topic: string; content: string }) =>
    apiFetch<{ success: boolean; message: string }>(`/profiles/${userId}/items`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteItem: (userId: string, profileId: string) =>
    apiFetch<{ success: boolean; message: string }>(`/profiles/${userId}/items/${profileId}`, {
      method: "DELETE",
    }),
};

// ── Knowledge (Cognee) ────────────────────────────────────────────────────

export const knowledgeApi = {
  listDatasets: () =>
    apiFetch<{ success: boolean; data: KnowledgeDataset[] }>("/knowledge/datasets"),
  createDataset: (name: string) =>
    apiFetch<{ success: boolean; data: KnowledgeDataset[] }>(`/knowledge/datasets?name=${encodeURIComponent(name)}`, {
      method: "POST",
    }),
  deleteDataset: (datasetId: string) =>
    apiFetch<{ success: boolean; message: string }>(`/knowledge/datasets/${datasetId}`, {
      method: "DELETE",
    }),
  add: (data: string, dataset: string) =>
    apiFetch<{ success: boolean; data_id?: string; dataset_name?: string; message: string }>("/knowledge/add", {
      method: "POST",
      body: JSON.stringify({ data, dataset }),
    }),
  cognify: (datasets?: string[], runInBackground = true) =>
    apiFetch<{ success: boolean; pipeline_run_id?: string; status: string; message: string }>("/knowledge/cognify", {
      method: "POST",
      body: JSON.stringify({ datasets, run_in_background: runInBackground }),
    }),
  getCognifyStatus: (jobId: string) =>
    apiFetch<CognifyStatusResponse>(`/knowledge/cognify/status/${jobId}`),
  search: (body: { query: string; dataset?: string; search_type?: string; top_k?: number }) =>
    apiFetch<KnowledgeSearchResponse>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getGraph: (datasetId: string) =>
    apiFetch<DatasetGraphResponse>(`/knowledge/datasets/${datasetId}/graph`),
  delete: (dataId: string, datasetId: string) =>
    apiFetch<{ success: boolean; message: string }>("/knowledge", {
      method: "DELETE",
      body: JSON.stringify({ data_id: dataId, dataset_id: datasetId }),
    }),
};

// ── Context (unified) ─────────────────────────────────────────────────────

export const contextApi = {
  fetch: (body: {
    user_id: string;
    query?: string;
    enable_conversations?: boolean;
    enable_profile?: boolean;
    enable_knowledge?: boolean;
    memory_scope?: string;
    top_k?: number;
    max_token_size?: number;
    timeout_ms?: number;
  }) =>
    apiFetch<ContextResponse>("/context", { method: "POST", body: JSON.stringify(body) }),
};
