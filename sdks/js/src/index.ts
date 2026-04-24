import { HTTP, type HTTPOptions } from "./http.js";
import { Context } from "./resources/context.js";
import { Conversations } from "./resources/conversations.js";
import { Knowledge } from "./resources/knowledge.js";
import { Profiles } from "./resources/profiles.js";

export { APIError, AuthError, CozyMemoryError } from "./errors.js";
export type { Message } from "./resources/conversations.js";
export type { HTTPOptions } from "./http.js";

export class CozyMemory {
  public conversations: Conversations;
  public profiles: Profiles;
  public knowledge: Knowledge;
  public context: Context;
  private http: HTTP;

  constructor(opts: HTTPOptions) {
    this.http = new HTTP(opts);
    this.conversations = new Conversations(this.http);
    this.profiles = new Profiles(this.http);
    this.knowledge = new Knowledge(this.http);
    this.context = new Context(this.http);
  }

  health() {
    return this.http.get<unknown>("/api/v1/health");
  }
}
