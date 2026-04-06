"""
API 路由模块

定义 RESTful API 端点。
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from ..models.memory import (
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
    MemoryResponse,
    MemoryListResponse,
    HealthResponse,
    ErrorResponse,
    EngineInfo,
)
from ..services.memory_service import MemoryService
from ..utils.logger import get_logger
from ..utils.config import settings

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/v1", tags=["memories"])


def get_memory_service() -> MemoryService:
    """获取记忆服务依赖"""
    # 这里会从依赖注入容器获取服务
    # 暂时直接返回，后续会改进
    from ..adapters.memobase_mock_adapter import MemobaseMockAdapter
    
    adapter = MemobaseMockAdapter(
        api_url=settings.MEMOBASE_API_URL,
        api_key=settings.MEMOBASE_API_KEY,
        timeout=settings.ROUTER_TIMEOUT,
    )
    
    return MemoryService(adapter)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务及各记忆引擎的健康状态"
)
async def health_check(service: MemoryService = Depends(get_memory_service)) -> HealthResponse:
    """健康检查"""
    from datetime import datetime
    
    engine_status = await service.get_engine_status()
    
    # 判断整体状态
    all_healthy = engine_status.get("healthy", False)
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(),
        engines={
            settings.MEMOBASE_API_URL: EngineInfo(
                name=engine_status.get("name", "Unknown"),
                enabled=settings.MEMOBASE_ENABLED,
                status=engine_status.get("status", "unknown"),
                latency_ms=engine_status.get("latency_ms"),
            )
        }
    )


@router.post(
    "/memories",
    response_model=MemoryResponse,
    summary="创建记忆",
    description="在记忆引擎中创建新的记忆"
)
async def create_memory(
    memory: MemoryCreate,
    service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """创建记忆"""
    try:
        created = await service.create_memory(memory)
        
        return MemoryResponse(
            success=True,
            data=created,
            message="记忆创建成功"
        )
    except Exception as e:
        logger.error("创建记忆失败", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"创建记忆失败：{str(e)}"
        )


@router.get(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="获取记忆",
    description="根据 ID 获取单个记忆"
)
async def get_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """获取记忆"""
    memory = await service.get_memory(memory_id)
    
    if not memory:
        raise HTTPException(
            status_code=404,
            detail=f"记忆不存在：{memory_id}"
        )
    
    return MemoryResponse(
        success=True,
        data=memory,
        message="获取成功"
    )


@router.get(
    "/memories",
    response_model=MemoryListResponse,
    summary="查询记忆",
    description="根据条件查询记忆列表"
)
async def query_memories(
    user_id: str = Query(..., description="用户 ID"),
    query_text: Optional[str] = Query(None, description="查询文本", alias="q"),
    memory_type: Optional[str] = Query(None, description="记忆类型"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    engine: Optional[str] = Query(None, description="指定引擎"),
    service: MemoryService = Depends(get_memory_service)
) -> MemoryListResponse:
    """查询记忆"""
    from ..models.memory import MemoryType
    
    # 构建查询对象
    memory_type_enum = None
    if memory_type:
        try:
            memory_type_enum = MemoryType(memory_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的记忆类型：{memory_type}"
            )
    
    query = MemoryQuery(
        user_id=user_id,
        query=query_text,
        memory_type=memory_type_enum,
        limit=limit,
        engine=engine,
    )
    
    memories = await service.query_memories(query)
    
    return MemoryListResponse(
        success=True,
        data=memories,
        total=len(memories),
        limit=limit,
        message="查询成功"
    )


@router.put(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="更新记忆",
    description="更新已有记忆的内容或元数据"
)
async def update_memory(
    memory_id: str,
    update: MemoryUpdate,
    service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """更新记忆"""
    memory = await service.update_memory(memory_id, update)
    
    if not memory:
        raise HTTPException(
            status_code=404,
            detail=f"记忆不存在：{memory_id}"
        )
    
    return MemoryResponse(
        success=True,
        data=memory,
        message="更新成功"
    )


@router.delete(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="删除记忆",
    description="删除指定记忆"
)
async def delete_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service)
) -> MemoryResponse:
    """删除记忆"""
    success = await service.delete_memory(memory_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"记忆不存在：{memory_id}"
        )
    
    return MemoryResponse(
        success=True,
        data=None,
        message="删除成功"
    )


@router.post(
    "/memories/batch",
    response_model=MemoryListResponse,
    summary="批量创建记忆",
    description="批量创建多条记忆"
)
async def batch_create_memories(
    memories: List[MemoryCreate],
    service: MemoryService = Depends(get_memory_service)
) -> MemoryListResponse:
    """批量创建记忆"""
    if len(memories) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"批量创建数量不能超过 {settings.MAX_BATCH_SIZE}"
        )
    
    created = await service.batch_create(memories)
    
    return MemoryListResponse(
        success=True,
        data=created,
        total=len(created),
        limit=len(memories),
        message=f"成功创建 {len(created)} 条记忆"
    )
