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
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentUserId: "",
      setCurrentUserId: (id) => set({ currentUserId: id }),

      apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
      setApiUrl: (url) => set({ apiUrl: url }),
    }),
    { name: "cozymemory-app" }
  )
);
