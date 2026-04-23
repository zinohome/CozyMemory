"""备份/恢复路由（operator 命名空间）

- GET  /api/v1/operator/backup/export/{user_id}  → MemoryBundle JSON
- POST /api/v1/operator/backup/import            → 接受 bundle，返回计数

挂载于 `/api/v1/operator/backup`，仅 bootstrap key 可访问。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from ....clients.base import EngineError
from ....models.backup import BackupImportRequest, BackupImportResponse, MemoryBundle
from ....services.backup import BackupService
from ...deps import get_backup_service

router = APIRouter(prefix="/backup", tags=["operator-backup"])


@router.get(
    "/export/{user_id}",
    response_model=MemoryBundle,
    summary="导出用户记忆为 JSON bundle",
)
async def export_user(
    user_id: str,
    datasets: str | None = None,
    service: BackupService = Depends(get_backup_service),
) -> MemoryBundle:
    """
    datasets: 可选逗号分隔的 Cognee dataset ID 列表，附加到 bundle 里。
    """
    dataset_ids = [d.strip() for d in datasets.split(",") if d.strip()] if datasets else None
    try:
        return await service.export_user(user_id, dataset_ids=dataset_ids)
    except EngineError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY if e.status_code >= 500 else status.HTTP_400_BAD_REQUEST,
            detail={"error": e.engine, "detail": str(e)},
        )


@router.post(
    "/import",
    response_model=BackupImportResponse,
    summary="从 bundle 恢复用户记忆",
)
async def import_bundle(
    body: BackupImportRequest,
    service: BackupService = Depends(get_backup_service),
) -> BackupImportResponse:
    return await service.import_bundle(body.bundle, body.target_user_id)
