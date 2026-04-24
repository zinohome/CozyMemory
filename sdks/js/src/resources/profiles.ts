import type { HTTP } from "../http.js";
import type { Message } from "./conversations.js";

export class Profiles {
  constructor(private http: HTTP) {}

  insert(userId: string, messages: Message[], sync = false) {
    return this.http.post<unknown>("/api/v1/profiles/insert", {
      user_id: userId,
      messages,
      sync,
    });
  }

  flush(userId: string) {
    return this.http.post<unknown>("/api/v1/profiles/flush", {
      user_id: userId,
    });
  }

  get(userId: string) {
    return this.http.get<unknown>(`/api/v1/profiles/${userId}`);
  }

  getContext(userId: string, maxTokenSize?: number) {
    const body: Record<string, unknown> = {};
    if (maxTokenSize !== undefined) body.max_token_size = maxTokenSize;
    return this.http.post<unknown>(`/api/v1/profiles/${userId}/context`, body);
  }

  addItem(userId: string, topic: string, subTopic: string, content: string) {
    return this.http.post<unknown>(`/api/v1/profiles/${userId}/items`, {
      topic,
      sub_topic: subTopic,
      content,
    });
  }

  deleteItem(userId: string, profileId: string) {
    return this.http.delete<unknown>(
      `/api/v1/profiles/${userId}/items/${profileId}`,
    );
  }
}
