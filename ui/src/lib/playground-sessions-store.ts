/**
 * Playground chat session persistence.
 *
 * 把 Playground 的对话历史存到 localStorage，reload 保留；支持多会话切换。
 * 容量上限 MAX_SESSIONS，按 updatedAt 挤掉最旧的。
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface PlaygroundSession {
  id: string;
  title: string;
  userId: string;
  messages: ChatMsg[];
  createdAt: number;
  updatedAt: number;
}

const MAX_SESSIONS = 20;
const TITLE_MAX_LEN = 40;

function titleFrom(messages: ChatMsg[]): string {
  const first = messages.find((m) => m.role === "user");
  if (!first) return "New chat";
  const text = first.content.trim().replace(/\s+/g, " ");
  return text.length > TITLE_MAX_LEN ? text.slice(0, TITLE_MAX_LEN - 1) + "…" : text;
}

function newId(): string {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

interface State {
  sessions: PlaygroundSession[];
  activeId: string | null;

  newSession: (userId: string) => string;
  setActive: (id: string) => void;
  upsertMessages: (id: string, messages: ChatMsg[], userId: string) => void;
  deleteSession: (id: string) => void;
  getActive: () => PlaygroundSession | null;
}

export const usePlaygroundSessions = create<State>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeId: null,

      newSession: (userId) => {
        const id = newId();
        const now = Date.now();
        const fresh: PlaygroundSession = {
          id,
          title: "New chat",
          userId,
          messages: [],
          createdAt: now,
          updatedAt: now,
        };
        set((s) => ({
          sessions: trim([fresh, ...s.sessions]),
          activeId: id,
        }));
        return id;
      },

      setActive: (id) => set({ activeId: id }),

      upsertMessages: (id, messages, userId) => {
        set((s) => {
          const existing = s.sessions.find((x) => x.id === id);
          const now = Date.now();
          if (existing) {
            const updated: PlaygroundSession = {
              ...existing,
              messages,
              userId,
              title: titleFrom(messages),
              updatedAt: now,
            };
            return {
              sessions: [updated, ...s.sessions.filter((x) => x.id !== id)],
            };
          }
          // 兜底：id 未知时也建一个
          const fresh: PlaygroundSession = {
            id,
            userId,
            messages,
            title: titleFrom(messages),
            createdAt: now,
            updatedAt: now,
          };
          return {
            sessions: trim([fresh, ...s.sessions]),
            activeId: id,
          };
        });
      },

      deleteSession: (id) => {
        set((s) => {
          const sessions = s.sessions.filter((x) => x.id !== id);
          const activeId = s.activeId === id ? (sessions[0]?.id ?? null) : s.activeId;
          return { sessions, activeId };
        });
      },

      getActive: () => {
        const { sessions, activeId } = get();
        return sessions.find((x) => x.id === activeId) ?? null;
      },
    }),
    {
      name: "cozymemory-playground-sessions",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ sessions: s.sessions, activeId: s.activeId }),
    }
  )
);

function trim(sessions: PlaygroundSession[]): PlaygroundSession[] {
  if (sessions.length <= MAX_SESSIONS) return sessions;
  return [...sessions].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_SESSIONS);
}
