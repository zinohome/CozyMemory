/**
 * Zustand global store — lightweight cross-component state.
 * Server state (lists, fetched data) lives in TanStack Query, NOT here.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  // Currently selected user across all views
  currentUserId: string;
  setCurrentUserId: (id: string) => void;

  // API base URL (can be overridden in settings)
  apiUrl: string;
  setApiUrl: (url: string) => void;

  // Optional API key; when set, sent as X-Cozy-API-Key on every request
  apiKey: string;
  setApiKey: (key: string) => void;

  // Multi-tenant dashboard auth state
  jwt: string;
  setJwt: (t: string) => void;
  currentAppId: string;
  setCurrentAppId: (id: string) => void;
  currentAppSlug: string;
  setCurrentAppSlug: (s: string) => void;
  logout: () => void;

  // Playground system prompt — 空字符串 = 用默认
  playgroundSystemPrompt: string;
  setPlaygroundSystemPrompt: (p: string) => void;

  // UI 语言，默认中文
  locale: "zh" | "en";
  setLocale: (l: "zh" | "en") => void;
}

export const DEFAULT_PLAYGROUND_SYSTEM_PROMPT =
  "You are a helpful assistant with long-term memory of the user. " +
  "Use the retrieved context below to personalize your answer. " +
  "If context is empty, answer normally. Keep replies concise.";

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentUserId: "",
      setCurrentUserId: (id) => set({ currentUserId: id }),

      apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
      setApiUrl: (url) => set({ apiUrl: url }),

      apiKey: "",
      setApiKey: (key) => set({ apiKey: key }),

      jwt: "",
      setJwt: (t) => set({ jwt: t }),
      currentAppId: "",
      setCurrentAppId: (id) => set({ currentAppId: id }),
      currentAppSlug: "",
      setCurrentAppSlug: (s) => set({ currentAppSlug: s }),
      logout: () => set({ jwt: "", currentAppId: "", currentAppSlug: "" }),

      playgroundSystemPrompt: "",
      setPlaygroundSystemPrompt: (p) => set({ playgroundSystemPrompt: p }),

      locale: "zh",
      setLocale: (l) => set({ locale: l }),
    }),
    { name: "cozymemory-app" }
  )
);

// 非 Hook 访问（api.ts 里的 apiFetch 不能调 Hook）
export function getApiKey(): string {
  return useAppStore.getState().apiKey;
}

export function getJwt(): string {
  return useAppStore.getState().jwt;
}

export function getCurrentAppId(): string {
  return useAppStore.getState().currentAppId;
}
