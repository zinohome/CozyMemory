"""知识库 REST API 端点

对应引擎：Cognee
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...api.deps import get_knowledge_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.knowledge import (
    CognifyStatusResponse,
    DatasetGraphResponse,
    KnowledgeAddRequest,
    KnowledgeAddResponse,
    KnowledgeCognifyRequest,
    KnowledgeCognifyResponse,
    KnowledgeDatasetListResponse,
    KnowledgeDeleteRequest,
    KnowledgeDeleteResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ...services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _engine_error_response(exc: EngineError) -> JSONResponse:
    """将 EngineError 转为统一格式的 JSONResponse"""
    status_code = 502 if exc.status_code is None or exc.status_code >= 500 else 400
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            error=f"{exc.engine}Error",
            detail=exc.message,
            engine=exc.engine,
        ).model_dump(),
    )


@router.post(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="创建数据集",
)
async def create_dataset(
    name: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDatasetListResponse | JSONResponse:
    """创建数据集"""
    try:
        return await service.create_dataset(name=name)
    except EngineError as e:
        return _engine_error_response(e)


@router.delete(
    "/datasets/{dataset_id}",
    response_model=KnowledgeDeleteResponse,
    responses={502: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="删除数据集",
)
async def delete_dataset(
    dataset_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDeleteResponse | JSONResponse:
    """删除指定数据集及其中所有文档与图谱数据。此操作不可逆。

    `dataset_id` 为 `GET /knowledge/datasets` 返回的 UUID。
    """
    try:
        return await service.delete_dataset(dataset_id=dataset_id)
    except EngineError as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail=f"数据集 '{dataset_id}' 不存在"
                ).model_dump(),
            )
        return _engine_error_response(e)


@router.get(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="列出所有数据集",
)
async def list_datasets(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDatasetListResponse | JSONResponse:
    """列出所有数据集"""
    try:
        return await service.list_datasets()
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/add",
    response_model=KnowledgeAddResponse,
    responses={502: {"model": ErrorResponse}},
    summary="添加文档到知识库",
)
async def add_knowledge(
    request: KnowledgeAddRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeAddResponse | JSONResponse:
    """添加文档到知识库"""
    try:
        return await service.add(data=request.data, dataset=request.dataset)
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/cognify",
    response_model=KnowledgeCognifyResponse,
    responses={502: {"model": ErrorResponse}},
    summary="构建知识图谱",
)
async def cognify(
    request: KnowledgeCognifyRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeCognifyResponse | JSONResponse:
    """触发知识图谱构建"""
    try:
        return await service.cognify(
            datasets=request.datasets, run_in_background=request.run_in_background
        )
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    responses={502: {"model": ErrorResponse}},
    summary="搜索知识库",
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse | JSONResponse:
    """搜索知识库"""
    try:
        return await service.search(
            query=request.query,
            dataset=request.dataset,
            search_type=request.search_type,
            top_k=request.top_k,
        )
    except EngineError as e:
        return _engine_error_response(e)


@router.get(
    "/cognify/status/{job_id}",
    response_model=CognifyStatusResponse,
    responses={502: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="查询 Cognify 任务状态",
)
async def get_cognify_status(
    job_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> CognifyStatusResponse | JSONResponse:
    """查询知识图谱构建任务的当前状态。

    `job_id` 为 `POST /knowledge/cognify` 返回的 `pipeline_run_id`。
    """
    try:
        return await service.get_cognify_status(job_id=job_id)
    except EngineError as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail=f"任务 '{job_id}' 不存在"
                ).model_dump(),
            )
        return _engine_error_response(e)


@router.get(
    "/datasets/{dataset_id}/graph",
    response_model=DatasetGraphResponse,
    responses={502: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="获取数据集知识图谱",
)
async def get_dataset_graph(
    dataset_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> DatasetGraphResponse | JSONResponse:
    """获取指定数据集的知识图谱结构（节点 + 边），供前端可视化使用。"""
    try:
        return await service.get_dataset_graph(dataset_id=dataset_id)
    except EngineError as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail=f"数据集 '{dataset_id}' 不存在"
                ).model_dump(),
            )
        return _engine_error_response(e)


@router.delete(
    "",
    response_model=KnowledgeDeleteResponse,
    responses={502: {"model": ErrorResponse}},
    summary="删除知识数据",
)
async def delete_knowledge(
    request: KnowledgeDeleteRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDeleteResponse | JSONResponse:
    """删除知识数据"""
    try:
        return await service.delete(data_id=request.data_id, dataset_id=request.dataset_id)
    except EngineError as e:
        return _engine_error_response(e)
