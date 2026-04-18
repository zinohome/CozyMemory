"""知识库数据模型

对应引擎：Cognee
核心流程：添加文档 (add) → 构建知识图谱 (cognify) → 语义搜索 (search)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeAddRequest(BaseModel):
    """添加文档到知识库"""

    data: str = Field(..., description="文本内容或文件路径", min_length=1)
    dataset: str = Field(..., description="数据集名称", min_length=1)
    node_set: list[str] | None = Field(None, description="节点集标识")


class KnowledgeCognifyRequest(BaseModel):
    """触发知识图谱构建"""

    datasets: list[str] | None = Field(None, description="要处理的数据集列表")
    run_in_background: bool = Field(True, description="是否后台运行")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索"""

    query: str = Field(..., description="搜索查询", min_length=1)
    dataset: str | None = Field(None, description="限定数据集")
    search_type: str = Field(
        "GRAPH_COMPLETION",
        description="搜索类型: GRAPH_COMPLETION, SUMMARIES, CHUNKS, RAG_COMPLETION",
    )
    top_k: int = Field(10, ge=1, le=100, description="返回数量限制")


class KnowledgeSearchResult(BaseModel):
    """搜索结果"""

    id: str | None = Field(None, description="结果 ID")
    text: str | None = Field(None, description="结果文本内容")
    score: float | None = Field(None, description="相关性分数")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")

    model_config = {"extra": "allow"}  # Cognee 搜索结果字段不固定，允许透传未知字段


class KnowledgeDataset(BaseModel):
    """数据集信息"""

    id: str = Field(..., description="数据集 ID (UUID)")
    name: str = Field(..., description="数据集名称")
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)


class KnowledgeAddResponse(BaseModel):
    """添加文档响应"""

    success: bool = True
    data_id: str | None = Field(None, description="数据项 ID")
    dataset_name: str | None = Field(None)
    message: str = ""


class KnowledgeCognifyResponse(BaseModel):
    """知识图谱构建响应"""

    success: bool = True
    pipeline_run_id: str | None = Field(None, description="管道运行 ID")
    status: str = Field("pending", description="状态: pending/running/completed/failed")
    message: str = ""


class KnowledgeSearchResponse(BaseModel):
    """搜索响应"""

    success: bool = True
    data: list[KnowledgeSearchResult] = Field(default_factory=list)
    total: int = Field(0)
    message: str = ""


class KnowledgeDatasetListResponse(BaseModel):
    """数据集列表响应"""

    success: bool = True
    data: list[KnowledgeDataset] = Field(default_factory=list)
    message: str = ""


class KnowledgeDeleteRequest(BaseModel):
    """删除知识数据请求"""

    data_id: str = Field(..., description="数据项 ID", min_length=1)
    dataset_id: str = Field(..., description="数据集 ID", min_length=1)


class KnowledgeDeleteResponse(BaseModel):
    """删除知识数据响应"""

    success: bool = True
    message: str = ""
