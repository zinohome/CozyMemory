import type { HTTP } from "../http.js";
import type { UnifiedContextResponse } from "../types.js";

export class Context {
  constructor(private http: HTTP) {}

  getUnified(userId: string, query?: string) {
    const body: Record<string, unknown> = { user_id: userId };
    if (query !== undefined) body.query = query;
    return this.http.post<UnifiedContextResponse>("/api/v1/context", body);
  }
}
