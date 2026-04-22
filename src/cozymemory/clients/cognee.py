"""Cognee 引擎客户端

从现有 cognee_sdk 迁移简化，保留核心 API。
"""

import asyncio
from typing import Any

import structlog
from pydantic import ValidationError

from ..models.knowledge import KnowledgeDataset, KnowledgeSearchResult, SearchType
from .base import BaseClient, EngineError

logger = structlog.get_logger()


class CogneeClient(BaseClient):
    """Cognee 引擎客户端，支持 JWT 自动登录（POST /api/v1/auth/login）"""

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: str | None = None,
        user_email: str = "",
        user_password: str = "",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("timeout", 300.0)
        super().__init__(engine_name="Cognee", api_url=api_url, api_key=api_key, **kwargs)
        self._user_email = user_email
        self._user_password = user_password
        self._authenticated = False
        self._login_lock = asyncio.Lock()

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        # Cognee uses CookieTransport — cookies are handled by httpx client automatically.
        # Static api_key fallback for deployments that do use Bearer.
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _login(self) -> None:
        """POST /api/v1/auth/login → Cognee 设置 auth_token cookie，httpx 自动存储。"""
        try:
            response = await self._client.post(
                f"{self.api_url}/api/v1/auth/login",
                data={"username": self._user_email, "password": self._user_password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            if response.status_code == 200:
                self._authenticated = True
                logger.info("cognee.login.success", email=self._user_email)
            else:
                logger.warning("cognee.login.failed", status=response.status_code, body=response.text)
        except Exception as exc:
            logger.warning("cognee.login.error", error=str(exc))

    async def _request_with_auth(self, method: str, path: str, **kwargs: Any) -> Any:
        """直接发请求；遇到 401 时登录后重试一次（支持可选认证和必须认证两种部署）。"""
        try:
            return await self._request(method, path, **kwargs)
        except EngineError as e:
            if e.status_code == 401 and self._user_email and self._user_password:
                self._authenticated = False
                async with self._login_lock:
                    # double-checked: 只有第一个失败者执行登录，后续等待者复用 cookie
                    if not self._authenticated:
                        self._client.cookies.clear()
                        await self._login()
                return await self._request(method, path, **kwargs)
            raise

    async def health_check(self) -> bool:
        """健康检查：尝试自动登录后访问 /api/v1/datasets；无法登录时 401 也视为健康。"""
        try:
            await self._request_with_auth("GET", "/api/v1/datasets")
            return True
        except EngineError as e:
            return e.status_code == 401
        except Exception:
            return False

    async def add(self, data: str, dataset: str) -> dict[str, Any]:
        """添加文本到 Cognee（包装成 data.txt 上传）"""
        response = await self._request_with_auth(
            "POST",
            "/api/v1/add",
            data={"datasetName": dataset},
            files=[("data", ("data.txt", data.encode("utf-8"), "text/plain"))],
        )
        return dict(response.json())

    async def add_files(
        self,
        files: list[tuple[str, bytes, str]],
        dataset: str,
    ) -> dict[str, Any]:
        """上传一个或多个文件到 Cognee 的 dataset。

        files: 列表，每项 (filename, bytes, content_type)
        """
        multipart = [("data", (name, content, ct)) for (name, content, ct) in files]
        response = await self._request_with_auth(
            "POST",
            "/api/v1/add",
            data={"datasetName": dataset},
            files=multipart,
        )
        return dict(response.json())

    async def list_dataset_data(self, dataset_id: str) -> list[dict[str, Any]]:
        """列出某 dataset 下所有已上传的原始文档（GET /datasets/{id}/data）"""
        response = await self._request_with_auth(
            "GET", f"/api/v1/datasets/{dataset_id}/data"
        )
        data = response.json()
        return list(data) if isinstance(data, list) else []

    async def get_raw_data(
        self, dataset_id: str, data_id: str
    ) -> tuple[bytes, str, str]:
        """获取原始文件内容。返回 (bytes, content-type, filename)。"""
        response = await self._request_with_auth(
            "GET",
            f"/api/v1/datasets/{dataset_id}/data/{data_id}/raw",
            # httpx 默认已按 bytes 读取 response.content；此处不需要 stream=True
        )
        content_type = response.headers.get("content-type", "application/octet-stream")
        # Cognee FileResponse 的 content-disposition 形如: attachment; filename="xxx.txt"
        cd = response.headers.get("content-disposition", "")
        filename = ""
        if "filename=" in cd:
            filename = cd.split("filename=", 1)[1].strip().strip('"')
        return response.content, content_type, filename

    async def delete_dataset_data(self, dataset_id: str, data_id: str) -> bool:
        """删除 dataset 下某条文档（DELETE /datasets/{dataset_id}/data/{data_id}）"""
        try:
            await self._request_with_auth(
                "DELETE", f"/api/v1/datasets/{dataset_id}/data/{data_id}"
            )
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise

    async def cognify(
        self, datasets: list[str] | None = None, run_in_background: bool = True
    ) -> dict[str, Any]:
        """触发知识图谱构建"""
        payload: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets:
            payload["datasets"] = datasets
        response = await self._request_with_auth("POST", "/api/v1/cognify", json=payload)
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
        response = await self._request_with_auth("POST", "/api/v1/search", json=payload)
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
        response = await self._request_with_auth("GET", "/api/v1/datasets")
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
        response = await self._request_with_auth("POST", "/api/v1/datasets", json={"name": name})
        data = response.json()
        return KnowledgeDataset(
            id=str(data.get("id", "")),
            name=data.get("name", name),
            created_at=data.get("createdAt") or data.get("created_at"),
        )

    async def get_cognify_status(self, job_id: str) -> dict[str, Any]:
        """查询 Cognify 任务状态（代理到 Cognee /api/v1/cognify/{job_id}）"""
        response = await self._request_with_auth("GET", f"/api/v1/cognify/{job_id}")
        return dict(response.json())

    async def delete_dataset(self, dataset_id: str) -> bool:
        """删除数据集（代理到 Cognee DELETE /api/v1/datasets/{id}）"""
        try:
            await self._request_with_auth("DELETE", f"/api/v1/datasets/{dataset_id}")
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise

    async def get_dataset_graph(self, dataset_id: str) -> Any:
        """获取数据集知识图谱（代理到 Cognee /api/v1/datasets/{id}/graph）"""
        response = await self._request_with_auth("GET", f"/api/v1/datasets/{dataset_id}/graph")
        return response.json()

    async def delete(self, data_id: str, dataset_id: str) -> bool:
        """删除数据"""
        try:
            await self._request_with_auth(
                "DELETE", "/api/v1/delete", params={"data_id": data_id, "dataset_id": dataset_id}
            )
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise
