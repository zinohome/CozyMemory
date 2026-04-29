"""知识库数据模型

对应引擎：Cognee
核心流程：添加文档 (add) → 构建知识图谱 (cognify) → 语义搜索 (search)
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SearchType = Literal["CHUNKS", "SUMMARIES", "RAG_COMPLETION", "GRAPH_COMPLETION"]


class KnowledgeAddRequest(BaseModel):
    """添加文档到知识库"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": "CozyMemory 是统一 AI 记忆平台，整合了 Mem0、Memobase 和 Cognee 三大引擎",
                "dataset": "default",
            }
        }
    }

    data: str = Field(..., description="文本内容或文件路径", min_length=1)
    dataset: str = Field(..., description="数据集名称", min_length=1)
    node_set: list[str] | None = Field(None, description="节点集标识")


class KnowledgeCognifyRequest(BaseModel):
    """触发知识图谱构建"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "datasets": ["default"],
                "run_in_background": True,
            }
        }
    }

    datasets: list[str] | None = Field(None, description="要处理的数据集列表，为 null 则处理全部")
    run_in_background: bool = Field(True, description="是否后台运行（推荐 true，图谱构建耗时较长）")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "AI 记忆服务有哪些核心能力",
                "dataset": "default",
                "search_type": "CHUNKS",
                "top_k": 5,
            }
        }
    }

    query: str = Field(..., description="搜索查询", min_length=1)
    dataset: str | None = Field(None, description="限定数据集，为 null 则搜索全部")
    search_type: SearchType | None = Field(
        None,
        description=(
            "搜索类型：CHUNKS（原文片段）/ SUMMARIES（摘要）"
            "/ RAG_COMPLETION（RAG 生成）/ GRAPH_COMPLETION（图谱推理）。"
            "为 null 时使用系统默认值（环境变量 COGNEE_DEFAULT_SEARCH_TYPE，默认 CHUNKS）"
        ),
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
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")


class KnowledgeAddResponse(BaseModel):
    """添加文档响应"""

    success: bool = True
    data_id: str | None = Field(None, description="数据项 ID")
    dataset: str | None = Field(None, description="数据集名称")
    message: str = ""


class KnowledgeCognifyResponse(BaseModel):
    """知识图谱构建响应"""

    success: bool = True
    pipeline_run_id: str | None = Field(None, description="管道运行 ID（仅作为触发标识，状态查询为实验性功能）")
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


class CognifyStatusResponse(BaseModel):
    """Cognify 任务状态响应（透传 Cognee 原始响应）"""

    success: bool = True
    job_id: str
    status: str = Field("unknown", description="状态: pending/running/completed/failed/unknown")
    data: dict[str, Any] | None = Field(None, description="Cognee 原始响应数据")

    model_config = {"extra": "allow"}


class DatasetGraphResponse(BaseModel):
    """数据集知识图谱响应（透传 Cognee 原始图谱数据）"""

    success: bool = True
    dataset_id: str
    data: Any = Field(None, description="Cognee 图谱原始数据（nodes + edges）")

    model_config = {"extra": "allow"}


class DatasetDataItem(BaseModel):
    """数据集内一条原始文档条目（Cognee Data 表）"""

    id: str = Field(..., description="data_id (UUID)")
    name: str = Field("", description="文档名称/原文件名")
    mime_type: str | None = Field(None, description="MIME 类型，如 text/plain / application/pdf")
    extension: str | None = Field(None, description="文件后缀，如 txt / pdf")
    raw_data_location: str | None = Field(None, description="后端原文存储路径（调试用，前端不展示）")
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)

    model_config = {"extra": "allow"}


class DatasetDataListResponse(BaseModel):
    """数据集文档列表响应"""

    success: bool = True
    dataset_id: str
    data: list[DatasetDataItem] = Field(default_factory=list)
    total: int = 0
    message: str = ""
