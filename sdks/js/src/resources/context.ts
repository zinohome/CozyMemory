import type { HTTP } from "../http.js";

export class Context {
  constructor(private http: HTTP) {}

  /**
   * Concurrently fetch conversations + profile context + knowledge for LLM prompts.
   * Returns an object shaped like `{ conversations, profile_context, knowledge, errors }`.
   */
  getUnified(userId: string, query?: string) {
    const body: Record<string, unknown> = { user_id: userId };
    if (query !== undefined) body.query = query;
    return this.http.post<unknown>("/api/v1/context", body);
  }
}
