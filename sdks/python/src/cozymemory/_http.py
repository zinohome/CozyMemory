"""Internal httpx wrappers shared by sync + async clients."""
from __future__ import annotations

from typing import Any

import httpx

from .exceptions import APIError, AuthError


def _raise_for(res: httpx.Response) -> None:
    if res.is_success:
        return
    try:
        body = res.json()
    except Exception:
        body = {"detail": res.text}
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("error") or "HTTP error"
    else:
        detail = "HTTP error"
        body = {"detail": body}
    if res.status_code == 401:
        raise AuthError(f"{res.status_code}: {detail}")
    raise APIError(res.status_code, detail, body)


class SyncHTTP:
    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"X-Cozy-API-Key": api_key},
        )

    def close(self) -> None:
        self._client.close()

    def get(self, path: str, **kwargs: Any) -> Any:
        r = self._client.get(path, **kwargs)
        _raise_for(r)
        return r.json()

    def post(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        r = self._client.post(path, json=json, **kwargs)
        _raise_for(r)
        return r.json()

    def delete(self, path: str, **kwargs: Any) -> Any:
        r = self._client.delete(path, **kwargs)
        _raise_for(r)
        return r.json() if r.content else {}


class AsyncHTTP:
    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"X-Cozy-API-Key": api_key},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **kwargs: Any) -> Any:
        r = await self._client.get(path, **kwargs)
        _raise_for(r)
        return r.json()

    async def post(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        r = await self._client.post(path, json=json, **kwargs)
        _raise_for(r)
        return r.json()

    async def delete(self, path: str, **kwargs: Any) -> Any:
        r = await self._client.delete(path, **kwargs)
        _raise_for(r)
        return r.json() if r.content else {}
