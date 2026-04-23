/**
 * CozyMemory API client — typed fetch wrapper for all CozyMemory REST endpoints.
 *
 * 类型统一从 `./api-types`（由 `npm run gen:api` 从后端 /openapi.json 生成）
 * 导入。手动重新定义 schema 会与后端漂移，所以这个文件只保留：
 *   1. 对生成 schema 的重命名别名（保持页面层的命名稳定）
 *   2. 薄 fetch 包装 + 每个端点的方法
 *
 * Base URL 通过 NEXT_PUBLIC_API_URL 在容器启动时注入到编译产物中。
 */

import type { components } from "./api-types";
import {
  getApiKey,
  getJwt,
  getCurrentAppId,
  useAppStore,
  useOperatorStore,
  getOperatorKey,
} from "./store";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";

// ── Types (aliased from generated schema) ──────────────────────────────────

type S = components["schemas"];

export type Message = S["Message"];
export type EngineStatus = S["EngineStatus"];
export type HealthResponse = S["HealthResponse"];

export type ConversationMemory = S["ConversationMemory"];
export type ConversationListResponse = S["ConversationMemoryListResponse"];
export type ConversationAddRequest = S["ConversationMemoryCreate"];
export type ConversationSearchRequest = S["ConversationMemorySearch"];

export type UserListResponse = S["UserListResponse"];
export type UserMappingResponse = S["UserMappingResponse"];

export type ProfileItem = S["ProfileTopic"];
export type UserProfileData = S["UserProfile"];
export type ProfileResponse = S["ProfileGetResponse"];
export type ProfileContextData = S["ProfileContext"];
export type ProfileContextResponse = S["ProfileContextResponse"];

export type KnowledgeDataset = S["KnowledgeDataset"];
export type KnowledgeSearchResult = S["KnowledgeSearchResult"];
export type KnowledgeSearchResponse = S["KnowledgeSearchResponse"];
export type CognifyStatusResponse = S["CognifyStatusResponse"];
export type DatasetGraphResponse = S["DatasetGraphResponse"];
export type DatasetDataItem = S["DatasetDataItem"];
export type DatasetDataListResponse = S["DatasetDataListResponse"];

export type ContextRequest = S["ContextRequest"];
export type ContextResponse = S["ContextResponse"];

export type ApiError = S["ErrorResponse"];

// ── Core fetch helper ──────────────────────────────────────────────────────

type ApiFetchInit = RequestInit & {
  params?: Record<string, string | number | boolean | undefined>;
  scoped?: boolean;
};

// 统一的鉴权 header 构造：JWT 优先（多租户 dashboard 路径），否则走 legacy
// X-Cozy-API-Key。scoped=true 的调用在 JWT 模式下还会附加 X-Cozy-App-Id。
// 任何手写的 fetch（如 multipart 上传、原文下载）必须调用它，否则在 JWT-only
// 模式下会没有鉴权 header 导致 401。
export function buildAuthHeaders(scoped: boolean = true): Record<string, string> {
  const jwt = getJwt();
  const headers: Record<string, string> = {};
  if (jwt) {
    headers["Authorization"] = `Bearer ${jwt}`;
    if (scoped) {
      const appId = getCurrentAppId();
      if (appId) headers["X-Cozy-App-Id"] = appId;
    }
  } else {
    const apiKey = getApiKey();
    if (apiKey) headers["X-Cozy-API-Key"] = apiKey;
  }
  return headers;
}

async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  // Destructure custom `params` / `scoped` out so they are never forwarded to
  // fetch() — the fetch spec does not recognise them and some polyfills throw
  // on unknown keys.
  const { params, scoped = true, ...fetchInit } = init ?? {};

  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const authHeaders = buildAuthHeaders(scoped);

  const headers = new Headers({ "Content-Type": "application/json" });
  for (const [k, v] of Object.entries(authHeaders)) headers.set(k, v);
  const extra = fetchInit?.headers;
  if (extra) {
    const extraHeaders = new Headers(extra as HeadersInit);
    extraHeaders.forEach((v, k) => headers.set(k, v));
  }

  const res = await fetch(url.toString(), {
    ...fetchInit,
    headers,
  });

  // 401 + JWT was in flight => session expired; clear auth and redirect.
  if (res.status === 401 && getJwt()) {
    useAppStore.getState().logout();
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data as ApiError;
    throw new Error(err?.detail ?? err?.error ?? `HTTP ${res.status}`);
  }
  return data as T;
}

/**
 * Thin wrapper for dashboard-scope routes (/auth/*, /dashboard/*) that do
 * NOT require an X-Cozy-App-Id header — the JWT alone identifies the user.
 */
export function dashboardFetch<T>(
  path: string,
  init?: Omit<ApiFetchInit, "scoped">
): Promise<T> {
  return apiFetch<T>(path, { ...(init ?? {}), scoped: false });
}

/**
 * Operator 专用 fetch —— 走 X-Cozy-API-Key = operatorKey，永远不带 JWT / AppId。
 * 只在 (operator)/* 页面里使用。401 时清 key 并跳 /operator landing。
 */
export async function operatorFetch<T>(
  path: string,
  init?: Omit<ApiFetchInit, "scoped">,
): Promise<T> {
  const operatorKey = getOperatorKey();
  if (!operatorKey) {
    throw new Error("operator key missing");
  }

  const { params, ...rest } = (init ?? {}) as ApiFetchInit;
  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const headers = new Headers({ "Content-Type": "application/json" });
  headers.set("X-Cozy-API-Key", operatorKey);
  const extra = rest.headers;
  if (extra) {
    const extraHeaders = new Headers(extra as HeadersInit);
    extraHeaders.forEach((v, k) => headers.set(k, v));
  }

  const res = await fetch(url.toString(), { ...rest, headers });
  if (res.status === 401) {
    useOperatorStore.getState().clearOperatorKey();
    if (typeof window !== "undefined") window.location.assign("/operator");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data as ApiError;
    throw new Error(err?.detail ?? err?.error ?? `HTTP ${res.status}`);
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
    apiFetch<ConversationListResponse>("/conversations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  search: (body: ConversationSearchRequest) =>
    apiFetch<ConversationListResponse>("/conversations/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  get: (id: string) =>
    apiFetch<{ success: boolean; data: ConversationMemory }>(`/conversations/${id}`),
  delete: (id: string) =>
    apiFetch<{ success: boolean; message: string }>(`/conversations/${id}`, { method: "DELETE" }),
  deleteAll: (userId: string) =>
    apiFetch<{ success: boolean; message: string }>("/conversations", {
      method: "DELETE",
      params: { user_id: userId },
    }),
};

// ── Users (ID mapping) ────────────────────────────────────────────────────
// Step 8: /api/v1/users 搬到 /api/v1/operator/users-mapping（仅 operator 用）。
// Developer 端看 App-scoped users：用 useAppUsers hook。
// 此处不再导出 usersApi —— 老 Redis 全局视图属于 operator（operatorApi.listUsers）。

// ── Profiles (Memobase) ───────────────────────────────────────────────────

export const profilesApi = {
  get: (userId: string) => apiFetch<ProfileResponse>(`/profiles/${userId}`),
  getContext: (userId: string, maxTokenSize?: number) =>
    apiFetch<ProfileContextResponse>(`/profiles/${userId}/context`, {
      method: "POST",
      body: JSON.stringify({ max_token_size: maxTokenSize ?? 500 }),
    }),
  insert: (body: S["ProfileInsertRequest"]) =>
    apiFetch<S["ProfileInsertResponse"]>("/profiles/insert", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  flush: (userId?: string) =>
    apiFetch<S["ProfileFlushResponse"]>("/profiles/flush", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  addItem: (userId: string, body: S["ProfileAddItemRequest"]) =>
    apiFetch<S["ProfileAddItemResponse"]>(`/profiles/${userId}/items`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteItem: (userId: string, profileId: string) =>
    apiFetch<S["ProfileDeleteItemResponse"]>(`/profiles/${userId}/items/${profileId}`, {
      method: "DELETE",
    }),
};

// ── Knowledge (Cognee) ────────────────────────────────────────────────────

export const knowledgeApi = {
  listDatasets: () => apiFetch<S["KnowledgeDatasetListResponse"]>("/knowledge/datasets"),
  createDataset: (name: string) =>
    apiFetch<S["KnowledgeDatasetListResponse"]>(
      `/knowledge/datasets?name=${encodeURIComponent(name)}`,
      { method: "POST" }
    ),
  deleteDataset: (datasetId: string) =>
    apiFetch<{ success: boolean; message: string }>(`/knowledge/datasets/${datasetId}`, {
      method: "DELETE",
    }),
  add: (data: string, dataset: string) =>
    apiFetch<S["KnowledgeAddResponse"]>("/knowledge/add", {
      method: "POST",
      body: JSON.stringify({ data, dataset }),
    }),
  addFiles: async (dataset: string, files: File[]) => {
    // multipart/form-data；不能走 apiFetch（它强制 JSON）
    const form = new FormData();
    form.append("dataset", dataset);
    for (const f of files) form.append("files", f, f.name);
    const res = await fetch(`${BASE_URL}${API_PREFIX}/knowledge/add-files`, {
      method: "POST",
      headers: buildAuthHeaders(true),
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      const err = data as ApiError;
      throw new Error(err.detail ?? err.error ?? `HTTP ${res.status}`);
    }
    return data as S["KnowledgeAddResponse"];
  },
  listData: (datasetId: string) =>
    apiFetch<DatasetDataListResponse>(`/knowledge/datasets/${datasetId}/data`),
  rawDataUrl: (datasetId: string, dataId: string) =>
    `${BASE_URL}${API_PREFIX}/knowledge/datasets/${datasetId}/data/${dataId}/raw`,
  fetchRawText: async (datasetId: string, dataId: string): Promise<string> => {
    const res = await fetch(
      `${BASE_URL}${API_PREFIX}/knowledge/datasets/${datasetId}/data/${dataId}/raw`,
      { headers: buildAuthHeaders(true) }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },
  deleteData: (datasetId: string, dataId: string) =>
    apiFetch<{ success: boolean; message: string }>(
      `/knowledge/datasets/${datasetId}/data/${dataId}`,
      { method: "DELETE" }
    ),
  cognify: (datasets?: string[], runInBackground = true) =>
    apiFetch<S["KnowledgeCognifyResponse"]>("/knowledge/cognify", {
      method: "POST",
      body: JSON.stringify({ datasets, run_in_background: runInBackground }),
    }),
  getCognifyStatus: (jobId: string) =>
    apiFetch<CognifyStatusResponse>(`/knowledge/cognify/status/${jobId}`),
  search: (body: S["KnowledgeSearchRequest"]) =>
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
  fetch: (body: ContextRequest) =>
    apiFetch<ContextResponse>("/context", { method: "POST", body: JSON.stringify(body) }),
};

// ── Operator API namespace ────────────────────────────────────────────────
// All operator pages go through these — they send X-Cozy-API-Key=operatorKey
// and never carry JWT or X-Cozy-App-Id. Backend treats bootstrap as admin
// passthrough (no uuid5 scoping), so callers see global Mem0/Memobase state.

export interface OperatorOrgRow {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  dev_count: number;
  app_count: number;
}
export interface OperatorOrgListResponse {
  data: OperatorOrgRow[];
  total: number;
}

export interface OperatorBackupImportResult {
  success: boolean;
  user_id: string;
  conversations_imported: number;
  conversations_skipped: number;
  profiles_imported: number;
  profiles_skipped: number;
  datasets_imported?: number;
  documents_imported?: number;
  datasets_skipped?: number;
  errors: { kind: string; id: string; reason: string }[];
}

export const operatorApi = {
  // orgs (new endpoint from Task 3)
  orgs: () => operatorFetch<OperatorOrgListResponse>("/operator/orgs"),

  // user mapping (relocated to /operator/users-mapping in Task 2)
  listUsers: () => operatorFetch<UserListResponse>("/operator/users-mapping"),
  getUserUuid: (userId: string, create = false) =>
    operatorFetch<UserMappingResponse>(
      `/operator/users-mapping/${userId}/uuid`,
      { params: { create } },
    ),
  deleteUserMapping: (userId: string) =>
    operatorFetch<{ success: boolean; message: string; warning: string }>(
      `/operator/users-mapping/${userId}/uuid`,
      { method: "DELETE" },
    ),

  // Global business data browsers — backend passthrough for bootstrap key
  // (no uuid5 scoping)
  listConversations: (
    userId: string,
    params?: { agent_id?: string; session_id?: string },
  ) =>
    operatorFetch<ConversationListResponse>("/conversations", {
      params: { user_id: userId, ...params },
    }),
  searchConversations: (body: ConversationSearchRequest) =>
    operatorFetch<ConversationListResponse>("/conversations/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteConversation: (id: string) =>
    operatorFetch<{ success: boolean; message: string }>(
      `/conversations/${id}`,
      { method: "DELETE" },
    ),
  deleteAllConversations: (userId: string) =>
    operatorFetch<{ success: boolean; message: string }>("/conversations", {
      method: "DELETE",
      params: { user_id: userId },
    }),

  getProfile: (userId: string) =>
    operatorFetch<ProfileResponse>(`/profiles/${userId}`),
  getProfileContext: (userId: string, maxTokenSize?: number) =>
    operatorFetch<ProfileContextResponse>(`/profiles/${userId}/context`, {
      method: "POST",
      body: JSON.stringify({ max_token_size: maxTokenSize ?? 500 }),
    }),
  addProfileItem: (
    userId: string,
    body: { topic: string; sub_topic: string; content: string },
  ) =>
    operatorFetch<S["ProfileAddItemResponse"]>(
      `/profiles/${userId}/items`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  deleteProfileItem: (userId: string, profileId: string) =>
    operatorFetch<S["ProfileDeleteItemResponse"]>(
      `/profiles/${userId}/items/${profileId}`,
      { method: "DELETE" },
    ),

  // Knowledge (Cognee) — global view
  listDatasets: () =>
    operatorFetch<S["KnowledgeDatasetListResponse"]>("/knowledge/datasets"),
  createDataset: (name: string) =>
    operatorFetch<S["KnowledgeDatasetListResponse"]>(
      `/knowledge/datasets?name=${encodeURIComponent(name)}`,
      { method: "POST" },
    ),
  deleteDataset: (datasetId: string) =>
    operatorFetch<{ success: boolean; message: string }>(
      `/knowledge/datasets/${datasetId}`,
      { method: "DELETE" },
    ),
  addKnowledge: (data: string, dataset: string) =>
    operatorFetch<S["KnowledgeAddResponse"]>("/knowledge/add", {
      method: "POST",
      body: JSON.stringify({ data, dataset }),
    }),
  // multipart upload — can't use operatorFetch (JSON only)
  addKnowledgeFiles: async (dataset: string, files: File[]) => {
    const operatorKey = getOperatorKey();
    if (!operatorKey) throw new Error("operator key missing");
    const form = new FormData();
    form.append("dataset", dataset);
    for (const f of files) form.append("files", f, f.name);
    const res = await fetch(`${BASE_URL}${API_PREFIX}/knowledge/add-files`, {
      method: "POST",
      headers: { "X-Cozy-API-Key": operatorKey },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      const err = data as ApiError;
      throw new Error(err.detail ?? err.error ?? `HTTP ${res.status}`);
    }
    return data as S["KnowledgeAddResponse"];
  },
  listDatasetData: (datasetId: string) =>
    operatorFetch<DatasetDataListResponse>(
      `/knowledge/datasets/${datasetId}/data`,
    ),
  rawDataUrl: (datasetId: string, dataId: string) =>
    `${BASE_URL}${API_PREFIX}/knowledge/datasets/${datasetId}/data/${dataId}/raw`,
  fetchRawText: async (datasetId: string, dataId: string): Promise<string> => {
    const operatorKey = getOperatorKey();
    if (!operatorKey) throw new Error("operator key missing");
    const res = await fetch(
      `${BASE_URL}${API_PREFIX}/knowledge/datasets/${datasetId}/data/${dataId}/raw`,
      { headers: { "X-Cozy-API-Key": operatorKey } },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },
  deleteKnowledgeData: (datasetId: string, dataId: string) =>
    operatorFetch<{ success: boolean; message: string }>(
      `/knowledge/datasets/${datasetId}/data/${dataId}`,
      { method: "DELETE" },
    ),
  cognify: (datasets?: string[], runInBackground = true) =>
    operatorFetch<S["KnowledgeCognifyResponse"]>("/knowledge/cognify", {
      method: "POST",
      body: JSON.stringify({ datasets, run_in_background: runInBackground }),
    }),
  getCognifyStatus: (jobId: string) =>
    operatorFetch<CognifyStatusResponse>(
      `/knowledge/cognify/status/${jobId}`,
    ),
  searchKnowledge: (body: S["KnowledgeSearchRequest"]) =>
    operatorFetch<KnowledgeSearchResponse>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getGraph: (datasetId: string) =>
    operatorFetch<DatasetGraphResponse>(
      `/knowledge/datasets/${datasetId}/graph`,
    ),

  // Health — same /health endpoint, different auth header
  health: () => operatorFetch<HealthResponse>("/health"),

  // Backup (mounted at /api/v1/operator/backup)
  exportUser: async (
    userId: string,
    datasetIds?: string[],
  ): Promise<unknown> => {
    const operatorKey = getOperatorKey();
    if (!operatorKey) throw new Error("operator key missing");
    const qs =
      datasetIds && datasetIds.length > 0
        ? `?datasets=${datasetIds.join(",")}`
        : "";
    const resp = await fetch(
      `${BASE_URL}${API_PREFIX}/operator/backup/export/${encodeURIComponent(userId)}${qs}`,
      { headers: { "X-Cozy-API-Key": operatorKey } },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(
        body.detail?.detail ?? body.detail ?? body.error ?? `HTTP ${resp.status}`,
      );
    }
    return resp.json();
  },
  importBackup: (body: { bundle: unknown; target_user_id: string | null }) =>
    operatorFetch<OperatorBackupImportResult>("/operator/backup/import", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
