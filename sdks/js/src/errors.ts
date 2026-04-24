export class CozyMemoryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CozyMemoryError";
  }
}

export class AuthError extends CozyMemoryError {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export class APIError extends CozyMemoryError {
  public statusCode: number;
  public detail: string;
  public body: unknown;
  constructor(statusCode: number, detail: string, body: unknown) {
    super(`${statusCode}: ${detail}`);
    this.name = "APIError";
    this.statusCode = statusCode;
    this.detail = detail;
    this.body = body;
  }
}
