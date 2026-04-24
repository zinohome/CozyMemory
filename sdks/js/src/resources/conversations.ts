import type { HTTP } from "../http.js";

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export class Conversations {
  constructor(private http: HTTP) {}

  add(userId: string, messages: Message[]) {
    return this.http.post<unknown>("/api/v1/conversations", {
      user_id: userId,
      messages,
    });
  }

  list(userId: string) {
    return this.http.get<unknown>("/api/v1/conversations", { user_id: userId });
  }

  search(userId: string, query: string, limit = 10) {
    return this.http.post<unknown>("/api/v1/conversations/search", {
      user_id: userId,
      query,
      limit,
    });
  }

  get(memoryId: string) {
    return this.http.get<unknown>(`/api/v1/conversations/${memoryId}`);
  }

  delete(memoryId: string) {
    return this.http.delete<unknown>(`/api/v1/conversations/${memoryId}`);
  }

  deleteAll(userId: string) {
    return this.http.delete<unknown>("/api/v1/conversations", { user_id: userId });
  }
}
