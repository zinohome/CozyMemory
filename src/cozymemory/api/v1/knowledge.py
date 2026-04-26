"""知识库 REST API 端点

对应引擎：Cognee

Step 8.15 起：按 app_ctx 分流。
- bootstrap key（app_ctx=None）→ 路由透传，Operator 全局视角
- App Key / Bearer+AppId（app_ctx 非 None）→ 创建自动登记、列表过滤、
  跨 App 访问统一 404（防枚举）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_knowledge_service
from ...auth import AppContext, get_app_context
from ...clients.base import EngineError
from ...db import get_session
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
from ...services.dataset_registry import AppDatasetRegistry
from ...services.knowledge import KnowledgeService
from ._knowledge_scope import (
    ensure_owned,
    filter_datasets_for_app,
    register_dataset_for_app,
    resolve_name_to_id,
    unregister_dataset,
)

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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDatasetListResponse | JSONResponse:
    """创建数据集"""
    try:
        resp = await service.create_dataset(name=name)
    except EngineError as e:
        return _engine_error_response(e)
    # App Key → 登记归属；bootstrap → no-op
    for ds in resp.data or []:
        await register_dataset_for_app(app_ctx, ds.id, session)
    return resp


@router.delete(
    "/datasets/{dataset_id}",
    response_model=KnowledgeDeleteResponse,
    responses={502: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="删除数据集",
)
async def delete_dataset(
    dataset_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDeleteResponse | JSONResponse:
    """删除指定数据集及其中所有文档与图谱数据。此操作不可逆。

    `dataset_id` 为 `GET /knowledge/datasets` 返回的 UUID。
    """
    await ensure_owned(app_ctx, dataset_id, session)
    try:
        resp = await service.delete_dataset(dataset_id=dataset_id)
    except EngineError as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail=f"数据集 '{dataset_id}' 不存在"
                ).model_dump(),
            )
        return _engine_error_response(e)
    await unregister_dataset(app_ctx, dataset_id, session)
    return resp


@router.get(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="列出所有数据集",
)
async def list_datasets(
    service: KnowledgeService = Depends(get_knowledge_service),
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDatasetListResponse | JSONResponse:
    """列出所有数据集"""
    try:
        resp = await service.list_datasets()
    except EngineError as e:
        return _engine_error_response(e)
    filtered = await filter_datasets_for_app(app_ctx, resp.data, session)
    return KnowledgeDatasetListResponse(
        success=resp.success,
        data=filtered,
        message=resp.message,
    )


@router.post(
    "/add",
    response_model=KnowledgeAddResponse,
    responses={502: {"model": ErrorResponse}},
    summary="添加文本到知识库",
)
async def add_knowledge(
    request: KnowledgeAddRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeAddResponse | JSONResponse:
    """添加纯文本到知识库（JSON body）"""
    # App Key: 若 dataset 已存在，校验归属；若未存在（新建），允许并之后登记
    if app_ctx is not None:
        existing_id = await resolve_name_to_id(service, request.dataset)
        if existing_id is not None:
            await ensure_owned(app_ctx, existing_id, session)
    try:
        resp = await service.add(data=request.data, dataset=request.dataset)
    except EngineError as e:
        return _engine_error_response(e)
    # 新建 dataset 情况下，add 之后重新解析并登记
    if app_ctx is not None:
        new_id = await resolve_name_to_id(service, request.dataset)
        if new_id is not None:
            await register_dataset_for_app(app_ctx, new_id, session)
    return resp


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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeAddResponse | JSONResponse:
    """通过 multipart/form-data 上传一个或多个文件到指定数据集。"""
    if not files:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                success=False, error="ValidationError", detail="至少提供一个文件"
            ).model_dump(),
        )
    if app_ctx is not None:
        existing_id = await resolve_name_to_id(service, dataset)
        if existing_id is not None:
            await ensure_owned(app_ctx, existing_id, session)
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
        resp = await service.add_files(files=payload, dataset=dataset)
    except EngineError as e:
        return _engine_error_response(e)
    if app_ctx is not None:
        new_id = await resolve_name_to_id(service, dataset)
        if new_id is not None:
            await register_dataset_for_app(app_ctx, new_id, session)
    return resp


@router.get(
    "/datasets/{dataset_id}/data",
    response_model=DatasetDataListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="列出数据集文档",
)
async def list_dataset_data(
    dataset_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> DatasetDataListResponse | JSONResponse:
    """列出指定数据集下所有已上传的原始文档（未分片，Cognee Data 表）"""
    await ensure_owned(app_ctx, dataset_id, session)
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> Response | JSONResponse:
    """代理 Cognee 的原文下载，返回原始字节 + content-type。

    浏览器可直接打开（PDF / 图片），或 fetch 拿文本。
    """
    await ensure_owned(app_ctx, dataset_id, session)
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDeleteResponse | JSONResponse:
    """从数据集删除一条原始文档（不影响已生成的图谱节点）"""
    await ensure_owned(app_ctx, dataset_id, session)
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeCognifyResponse | JSONResponse:
    """触发知识图谱构建"""
    datasets_arg = request.datasets
    if app_ctx is not None:
        if datasets_arg is None:
            # 不允许全局 cognify；转为"当前 App 下所有已登记 dataset"
            owned_ids = await AppDatasetRegistry(session).list_for_app(app_ctx.app_id)
            try:
                all_ds = await service.list_datasets()
            except EngineError as e:
                return _engine_error_response(e)
            names = [d.name for d in (all_ds.data or []) if _parse_id(d.id) in owned_ids]
            if not names:
                # 没 dataset 就什么也不做
                return KnowledgeCognifyResponse(
                    success=True,
                    pipeline_run_id=None,
                    status="completed",
                    message="no datasets to cognify",
                )
            datasets_arg = names
        else:
            for name in datasets_arg:
                existing_id = await resolve_name_to_id(service, name)
                if existing_id is None:
                    raise HTTPException(status_code=404, detail="dataset not found")
                await ensure_owned(app_ctx, existing_id, session)
    try:
        return await service.cognify(
            datasets=datasets_arg, run_in_background=request.run_in_background
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSearchResponse | JSONResponse:
    """搜索知识库"""
    if app_ctx is not None:
        if not request.dataset:
            raise HTTPException(
                status_code=400,
                detail="使用 App API Key 时必须在请求中指定 dataset 字段",
            )
        existing_id = await resolve_name_to_id(service, request.dataset)
        if existing_id is None:
            raise HTTPException(status_code=404, detail="dataset not found")
        await ensure_owned(app_ctx, existing_id, session)
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
    summary="查询 Cognify 任务状态（实验性）",
    deprecated=True,
)
async def get_cognify_status(
    job_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> CognifyStatusResponse | JSONResponse:
    """查询知识图谱构建任务的当前状态（实验性，部分 Cognee 版本不支持）。

    `job_id` 为 `POST /knowledge/cognify` 返回的 `pipeline_run_id`。
    当前 Cognee 版本对已完成的任务可能返回 404。
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> DatasetGraphResponse | JSONResponse:
    """获取指定数据集的知识图谱结构（节点 + 边），供前端可视化使用。"""
    await ensure_owned(app_ctx, dataset_id, session)
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
    app_ctx: AppContext | None = Depends(get_app_context),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDeleteResponse | JSONResponse:
    """删除知识数据"""
    await ensure_owned(app_ctx, request.dataset_id, session)
    try:
        return await service.delete(data_id=request.data_id, dataset_id=request.dataset_id)
    except EngineError as e:
        return _engine_error_response(e)


# ─────────────────────────── 私有 helper ───────────────────────────


def _parse_id(s: str):
    from uuid import UUID

    try:
        return UUID(str(s))
    except (ValueError, TypeError):
        return None
