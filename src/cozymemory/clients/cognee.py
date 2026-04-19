"""Cognee 引擎客户端

从现有 cognee_sdk 迁移简化，保留核心 API。
"""

from typing import Any

import structlog
from pydantic import ValidationError

from ..models.knowledge import KnowledgeDataset, KnowledgeSearchResult, SearchType
from .base import BaseClient, EngineError

logger = structlog.get_logger()


class CogneeClient(BaseClient):
    """Cognee 引擎客户端"""

    def __init__(
        self, api_url: str = "http://localhost:8000", api_key: str | None = None, **kwargs: Any
    ) -> None:
        kwargs.setdefault("timeout", 300.0)
        super().__init__(engine_name="Cognee", api_url=api_url, api_key=api_key, **kwargs)

    async def health_check(self) -> bool:
        """健康检查 — Cognee 无专属 /health 端点，使用 /api/v1/datasets 探活"""
        try:
            response = await self._request("GET", "/api/v1/datasets")
            return response.status_code == 200
        except Exception:
            return False

    async def add(self, data: str, dataset: str) -> dict[str, Any]:
        """添加数据到 Cognee"""
        response = await self._request(
            "POST",
            "/api/v1/add",
            data={"datasetName": dataset},
            files=[("data", ("data.txt", data.encode("utf-8"), "text/plain"))],
        )
        return dict(response.json())

    async def cognify(
        self, datasets: list[str] | None = None, run_in_background: bool = True
    ) -> dict[str, Any]:
        """触发知识图谱构建"""
        payload: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets:
            payload["datasets"] = datasets
        response = await self._request("POST", "/api/v1/cognify", json=payload)
        return dict(response.json())

    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: SearchType = "GRAPH_COMPLETION",
        top_k: int = 10,
    ) -> list[KnowledgeSearchResult]:
        """搜索知识库"""
        payload: dict[str, Any] = {"query": query, "search_type": search_type, "top_k": top_k}
        if dataset:
            payload["datasets"] = [dataset]
        response = await self._request("POST", "/api/v1/search", json=payload)
        data = response.json()

        results = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict):
                try:
                    results.append(KnowledgeSearchResult(**item))
                except ValidationError:
                    logger.warning("cognee.search.parse_error", item=item)
        return results

    async def list_datasets(self) -> list[KnowledgeDataset]:
        """列出所有数据集"""
        response = await self._request("GET", "/api/v1/datasets")
        data = response.json()
        return [
            KnowledgeDataset(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                created_at=item.get("createdAt") or item.get("created_at"),
            )
            for item in data
        ]

    async def create_dataset(self, name: str) -> KnowledgeDataset:
        """创建数据集"""
        response = await self._request("POST", "/api/v1/datasets", json={"name": name})
        data = response.json()
        return KnowledgeDataset(
            id=str(data.get("id", "")),
            name=data.get("name", name),
            created_at=data.get("createdAt") or data.get("created_at"),
        )

    async def get_cognify_status(self, job_id: str) -> dict[str, Any]:
        """查询 Cognify 任务状态（代理到 Cognee /api/v1/cognify/{job_id}）"""
        response = await self._request("GET", f"/api/v1/cognify/{job_id}")
        return dict(response.json())

    async def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集（代理到 Cognee DELETE /api/v1/datasets/{id}）"""
        try:
            await self._request("DELETE", f"/api/v1/datasets/{dataset_id}")
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise

    async def get_dataset_graph(self, dataset_id: str) -> Any:
        """获取数据集知识图谱（代理到 Cognee /api/v1/datasets/{id}/graph）"""
        response = await self._request("GET", f"/api/v1/datasets/{dataset_id}/graph")
        return response.json()

    async def delete(self, data_id: str, dataset_id: str) -> bool:
        """删除数据"""
        try:
            await self._request(
                "DELETE", "/api/v1/delete", params={"data_id": data_id, "dataset_id": dataset_id}
            )
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise
