"""知识库服务

薄层封装 Cognee 客户端，负责请求转发和错误转换。
"""

import structlog

from ..clients.cognee import CogneeClient
from ..models.knowledge import (
    CognifyStatusResponse,
    DatasetDataItem,
    DatasetDataListResponse,
    DatasetGraphResponse,
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeDatasetListResponse,
    KnowledgeDeleteResponse,
    KnowledgeSearchResponse,
    SearchType,
)

logger = structlog.get_logger()


class KnowledgeService:
    """知识库服务"""

    def __init__(self, client: CogneeClient):
        self.client = client

    async def add(self, data: str, dataset: str) -> KnowledgeAddResponse:
        """添加文本到知识库"""
        result = await self.client.add(data=data, dataset=dataset)
        return KnowledgeAddResponse(
            success=True, data_id=result.get("id"), dataset=dataset, message="数据已添加"
        )

    async def add_files(
        self, files: list[tuple[str, bytes, str]], dataset: str
    ) -> KnowledgeAddResponse:
        """上传文件到知识库"""
        result = await self.client.add_files(files=files, dataset=dataset)
        return KnowledgeAddResponse(
            success=True,
            data_id=result.get("id"),
            dataset=dataset,
            message=f"已上传 {len(files)} 个文件",
        )

    async def list_dataset_data(self, dataset_id: str) -> DatasetDataListResponse:
        """列出 dataset 下的原始文档（Cognee Data 表）"""
        raw_items = await self.client.list_dataset_data(dataset_id=dataset_id)
        items = [
            DatasetDataItem(
                id=str(it.get("id", "")),
                name=str(it.get("name") or ""),
                mime_type=it.get("mime_type") or it.get("mimeType"),
                extension=it.get("extension") or it.get("fileExtension"),
                raw_data_location=it.get("raw_data_location") or it.get("rawDataLocation"),
                created_at=it.get("createdAt") or it.get("created_at"),
                updated_at=it.get("updatedAt") or it.get("updated_at"),
            )
            for it in raw_items
        ]
        return DatasetDataListResponse(
            success=True, dataset_id=dataset_id, data=items, total=len(items)
        )

    async def get_raw_data(
        self, dataset_id: str, data_id: str
    ) -> tuple[bytes, str, str]:
        """拉取原始文件内容 (bytes, content_type, filename)"""
        return await self.client.get_raw_data(dataset_id=dataset_id, data_id=data_id)

    async def delete_dataset_data(
        self, dataset_id: str, data_id: str
    ) -> KnowledgeDeleteResponse:
        """从 dataset 删除某条文档"""
        success = await self.client.delete_dataset_data(
            dataset_id=dataset_id, data_id=data_id
        )
        msg = "文档已删除" if success else "删除失败"
        return KnowledgeDeleteResponse(success=success, message=msg)

    async def cognify(
        self, datasets: list[str] | None = None, run_in_background: bool = True
    ) -> KnowledgeCognifyResponse:
        """触发知识图谱构建"""
        result = await self.client.cognify(datasets=datasets, run_in_background=run_in_background)
        pipeline_run_id = None
        status = "pending"
        if isinstance(result, dict):
            for val in result.values():
                if isinstance(val, dict):
                    pipeline_run_id = val.get("pipeline_run_id") or val.get("run_id")
                    status = val.get("status", status)
                    break
            if pipeline_run_id is None:
                pipeline_run_id = result.get("pipeline_run_id") or result.get("run_id")
                status = result.get("status", status)
        return KnowledgeCognifyResponse(
            success=True,
            pipeline_run_id=pipeline_run_id,
            status=status,
            message="知识图谱构建已启动",
        )

    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: SearchType = "GRAPH_COMPLETION",
        top_k: int = 10,
    ) -> KnowledgeSearchResponse:
        """搜索知识库"""
        results = await self.client.search(
            query=query, dataset=dataset, search_type=search_type, top_k=top_k
        )
        return KnowledgeSearchResponse(success=True, data=results, total=len(results))

    async def create_dataset(self, name: str) -> KnowledgeDatasetListResponse:
        """创建数据集"""
        ds = await self.client.create_dataset(name=name)
        return KnowledgeDatasetListResponse(success=True, data=[ds], message="数据集已创建")

    async def list_datasets(self) -> KnowledgeDatasetListResponse:
        """列出所有数据集"""
        datasets = await self.client.list_datasets()
        return KnowledgeDatasetListResponse(success=True, data=datasets)

    async def get_cognify_status(self, job_id: str) -> CognifyStatusResponse:
        """查询 Cognify 任务状态"""
        data = await self.client.get_cognify_status(job_id=job_id)
        return CognifyStatusResponse(
            success=True,
            job_id=job_id,
            status=str(data.get("status", "unknown")),
            data=data,
        )

    async def get_dataset_graph(self, dataset_id: str) -> DatasetGraphResponse:
        """获取数据集知识图谱数据"""
        data = await self.client.get_dataset_graph(dataset_id=dataset_id)
        return DatasetGraphResponse(success=True, dataset_id=dataset_id, data=data)

    async def delete_dataset(self, dataset_id: str) -> KnowledgeDeleteResponse:
        """删除数据集（含其中所有数据）"""
        success = await self.client.delete_dataset(dataset_id=dataset_id)
        msg = "数据集已删除" if success else "删除失败"
        return KnowledgeDeleteResponse(success=success, message=msg)

    async def delete(self, data_id: str, dataset_id: str) -> KnowledgeDeleteResponse:
        """删除知识数据"""
        success = await self.client.delete(data_id=data_id, dataset_id=dataset_id)
        msg = "已删除" if success else "删除失败"
        return KnowledgeDeleteResponse(success=success, message=msg)
