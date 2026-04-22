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
import { getApiKey } from "./store";

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

  // 全局 API key 自动注入，用户可在 Settings 页配置；未配置时后端若也关闭
  // 鉴权则正常放行
  const apiKey = getApiKey();
  const authHeaders: Record<string, string> = apiKey ? { "X-Cozy-API-Key": apiKey } : {};

  const res = await fetch(url.toString(), {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(fetchInit?.headers ?? {}),
    },
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
    const apiKey = getApiKey();
    const res = await fetch(`${BASE_URL}${API_PREFIX}/knowledge/add-files`, {
      method: "POST",
      headers: apiKey ? { "X-Cozy-API-Key": apiKey } : {},
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
    const apiKey = getApiKey();
    const res = await fetch(
      `${BASE_URL}${API_PREFIX}/knowledge/datasets/${datasetId}/data/${dataId}/raw`,
      { headers: apiKey ? { "X-Cozy-API-Key": apiKey } : {} }
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
