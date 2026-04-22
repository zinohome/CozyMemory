"""知识库 REST API 端点

对应引擎：Cognee
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from ...api.deps import get_knowledge_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.knowledge import (
    CognifyStatusResponse,
    DatasetDataListResponse,
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
    summary="添加文本到知识库",
)
async def add_knowledge(
    request: KnowledgeAddRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeAddResponse | JSONResponse:
    """添加纯文本到知识库（JSON body）"""
    try:
        return await service.add(data=request.data, dataset=request.dataset)
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/add-files",
    response_model=KnowledgeAddResponse,
    responses={502: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="上传文件到知识库",
)
async def add_files(
    dataset: str = Form(..., description="数据集名称"),
    files: list[UploadFile] = File(..., description="一个或多个文件"),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeAddResponse | JSONResponse:
    """通过 multipart/form-data 上传一个或多个文件到指定数据集。"""
    if not files:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                success=False, error="ValidationError", detail="至少提供一个文件"
            ).model_dump(),
        )
    try:
        payload: list[tuple[str, bytes, str]] = []
        for f in files:
            content = await f.read()
            if not content:
                continue
            payload.append(
                (f.filename or "upload.bin", content, f.content_type or "application/octet-stream")
            )
        if not payload:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    success=False, error="ValidationError", detail="所有文件都为空"
                ).model_dump(),
            )
        return await service.add_files(files=payload, dataset=dataset)
    except EngineError as e:
        return _engine_error_response(e)


@router.get(
    "/datasets/{dataset_id}/data",
    response_model=DatasetDataListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="列出数据集文档",
)
async def list_dataset_data(
    dataset_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> DatasetDataListResponse | JSONResponse:
    """列出指定数据集下所有已上传的原始文档（未分片，Cognee Data 表）"""
    try:
        return await service.list_dataset_data(dataset_id=dataset_id)
    except EngineError as e:
        return _engine_error_response(e)


@router.get(
    "/datasets/{dataset_id}/data/{data_id}/raw",
    response_model=None,
    responses={
        200: {"content": {"application/octet-stream": {}}, "description": "原始文件字节流"},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="下载/查看原始文件",
)
async def get_raw_data(
    dataset_id: str,
    data_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Response | JSONResponse:
    """代理 Cognee 的原文下载，返回原始字节 + content-type。

    浏览器可直接打开（PDF / 图片），或 fetch 拿文本。
    """
    try:
        content, content_type, filename = await service.get_raw_data(
            dataset_id=dataset_id, data_id=data_id
        )
        headers: dict[str, str] = {}
        if filename:
            # 用 inline 让浏览器尝试内嵌显示；前端需要下载时自己改成 attachment
            headers["content-disposition"] = f'inline; filename="{filename}"'
        return Response(content=content, media_type=content_type, headers=headers)
    except EngineError as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail="文档不存在"
                ).model_dump(),
            )
        return _engine_error_response(e)


@router.delete(
    "/datasets/{dataset_id}/data/{data_id}",
    response_model=KnowledgeDeleteResponse,
    responses={502: {"model": ErrorResponse}},
    summary="从数据集删除单个文档",
)
async def delete_dataset_data(
    dataset_id: str,
    data_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeDeleteResponse | JSONResponse:
    """从数据集删除一条原始文档（不影响已生成的图谱节点）"""
    try:
        return await service.delete_dataset_data(dataset_id=dataset_id, data_id=data_id)
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
