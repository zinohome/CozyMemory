"""知识库 REST API 端点

对应引擎：Cognee
"""

from fastapi import APIRouter, Depends, HTTPException

from ...api.deps import get_knowledge_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.knowledge import (
    KnowledgeAddRequest,
    KnowledgeAddResponse,
    KnowledgeCognifyRequest,
    KnowledgeCognifyResponse,
    KnowledgeDatasetListResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ...services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def create_dataset(
    name: str, service: KnowledgeService = Depends(get_knowledge_service)
) -> KnowledgeDatasetListResponse:
    """创建数据集"""
    try:
        return await service.create_dataset(name=name)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.get(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def list_datasets(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDatasetListResponse:
    """列出所有数据集"""
    try:
        return await service.list_datasets()
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post("/add", response_model=KnowledgeAddResponse, responses={502: {"model": ErrorResponse}})
async def add_knowledge(
    request: KnowledgeAddRequest, service: KnowledgeService = Depends(get_knowledge_service)
) -> KnowledgeAddResponse:
    """添加文档到知识库"""
    try:
        return await service.add(data=request.data, dataset=request.dataset)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post(
    "/cognify", response_model=KnowledgeCognifyResponse, responses={502: {"model": ErrorResponse}}
)
async def cognify(
    request: KnowledgeCognifyRequest, service: KnowledgeService = Depends(get_knowledge_service)
) -> KnowledgeCognifyResponse:
    """触发知识图谱构建"""
    try:
        return await service.cognify(
            datasets=request.datasets, run_in_background=request.run_in_background
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post(
    "/search", response_model=KnowledgeSearchResponse, responses={502: {"model": ErrorResponse}}
)
async def search_knowledge(
    request: KnowledgeSearchRequest, service: KnowledgeService = Depends(get_knowledge_service)
) -> KnowledgeSearchResponse:
    """搜索知识库"""
    try:
        return await service.search(
            query=request.query,
            dataset=request.dataset,
            search_type=request.search_type,
            top_k=request.top_k,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )
