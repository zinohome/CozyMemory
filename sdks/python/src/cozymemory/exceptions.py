"""CozyMemory SDK exceptions."""
from __future__ import annotations


class CozyMemoryError(Exception):
    """Base error."""


class AuthError(CozyMemoryError):
    """401 — invalid or missing X-Cozy-API-Key."""


class APIError(CozyMemoryError):
    """Non-2xx response from the CozyMemory REST API."""

    def __init__(self, status_code: int, detail: str, body: dict) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
        self.body = body
