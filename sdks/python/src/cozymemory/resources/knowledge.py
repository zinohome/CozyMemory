"""Knowledge-graph resource (Cognee-backed)."""
from __future__ import annotations

from typing import Any


class _Base:
    def __init__(self, http: Any) -> None:
        self._http = http


class KnowledgeSync(_Base):
    def list_datasets(self) -> Any:
        return self._http.get("/api/v1/knowledge/datasets")

    def create_dataset(self, name: str) -> Any:
        return self._http.post("/api/v1/knowledge/datasets", params={"name": name})

    def delete_dataset(self, dataset_id: str) -> Any:
        return self._http.delete(f"/api/v1/knowledge/datasets/{dataset_id}")

    def add(self, data: str, dataset: str) -> Any:
        return self._http.post(
            "/api/v1/knowledge/add", json={"data": data, "dataset": dataset}
        )

    def cognify(
        self,
        datasets: list[str] | None = None,
        run_in_background: bool = False,
    ) -> Any:
        body: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets is not None:
            body["datasets"] = datasets
        return self._http.post("/api/v1/knowledge/cognify", json=body)

    def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: str | None = None,
        top_k: int | None = None,
    ) -> Any:
        body: dict[str, Any] = {"query": query}
        if dataset is not None:
            body["dataset"] = dataset
        if search_type is not None:
            body["search_type"] = search_type
        if top_k is not None:
            body["top_k"] = top_k
        return self._http.post("/api/v1/knowledge/search", json=body)


class KnowledgeAsync(_Base):
    async def list_datasets(self) -> Any:
        return await self._http.get("/api/v1/knowledge/datasets")

    async def create_dataset(self, name: str) -> Any:
        return await self._http.post(
            "/api/v1/knowledge/datasets", params={"name": name}
        )

    async def delete_dataset(self, dataset_id: str) -> Any:
        return await self._http.delete(f"/api/v1/knowledge/datasets/{dataset_id}")

    async def add(self, data: str, dataset: str) -> Any:
        return await self._http.post(
            "/api/v1/knowledge/add", json={"data": data, "dataset": dataset}
        )

    async def cognify(
        self,
        datasets: list[str] | None = None,
        run_in_background: bool = False,
    ) -> Any:
        body: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets is not None:
            body["datasets"] = datasets
        return await self._http.post("/api/v1/knowledge/cognify", json=body)

    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: str | None = None,
        top_k: int | None = None,
    ) -> Any:
        body: dict[str, Any] = {"query": query}
        if dataset is not None:
            body["dataset"] = dataset
        if search_type is not None:
            body["search_type"] = search_type
        if top_k is not None:
            body["top_k"] = top_k
        return await self._http.post("/api/v1/knowledge/search", json=body)
