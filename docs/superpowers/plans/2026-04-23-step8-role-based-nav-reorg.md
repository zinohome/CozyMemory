# Step 8 — 角色化导航重组 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把老 admin 页按 Operator vs Developer 两个角色拆开，消除 Step 7 AppSwitcher 污染多租户数据的根因。

**Architecture:** 后端把 `/api/v1/users` + `/api/v1/backup` 搬到 `/api/v1/operator/*` 命名空间，中间件对 operator 路径强制 bootstrap key、对业务路径（Bearer 分支）强制 X-Cozy-App-Id。前端新增 `(operator)` 路由组（独立 layout + 手动 key 输入），把老页面（memory / profiles / knowledge / context / playground）搬到 `(app)/apps/[id]/*` 工作台下或 `(operator)/*`；删掉全局级别的老页面。

**Tech Stack:** FastAPI / SQLAlchemy async（后端）；Next.js 16 / React 19 / shadcn / Zustand / TanStack Query / Vitest（前端）。复用 Step 7 所有基础设施。

**前置：** Step 7 已交付，commit `f0b9cf2`。

---

## 文件结构

### 后端

**删除**（搬迁）：
- `src/cozymemory/api/v1/users.py`
- `src/cozymemory/api/v1/backup.py`

**新建**：
- `src/cozymemory/api/v1/operator/__init__.py`
- `src/cozymemory/api/v1/operator/users_mapping.py`（搬自原 users.py，路径前缀改 `/users-mapping`）
- `src/cozymemory/api/v1/operator/backup.py`（搬自原 backup.py）
- `src/cozymemory/api/v1/operator/orgs.py`（新功能：列所有 org + dev 计数）
- `tests/unit/test_operator_auth_isolation.py`（新）
- `tests/unit/test_operator_orgs_api.py`（新）

**修改**：
- `src/cozymemory/app.py:168-230` —— middleware 强化：
  - `/api/v1/operator/*` 仅接 bootstrap key，拒 JWT
  - Bearer 调业务路由（非 operator/auth/dashboard）必须带 X-Cozy-App-Id，否则 401
- `src/cozymemory/api/v1/router.py` —— 挂载 operator 子路由，去掉 `users` / `backup`
- `tests/unit/test_user_mapping_api.py`（原 /users 的测试） —— 路径更新到 `/operator/users-mapping`
- `tests/unit/test_backup_*.py` —— 路径更新到 `/operator/backup`

### 前端

**删除**（搬迁后的老顶层页）：
- `ui/src/app/(app)/memory/` → 搬到 `(app)/apps/[id]/memory/` + `(operator)/memory-raw/`
- `ui/src/app/(app)/profiles/` → 同上
- `ui/src/app/(app)/knowledge/` → 同上
- `ui/src/app/(app)/context/` → 搬到 `(app)/apps/[id]/context/`（仅 App 版）
- `ui/src/app/(app)/playground/` → 搬到 `(app)/apps/[id]/playground/`
- `ui/src/app/(app)/users/` → 搬到 `(operator)/users-mapping/`
- `ui/src/app/(app)/backup/` → 搬到 `(operator)/backup/`
- `ui/src/app/(app)/dashboard/` → 搬到 `(operator)/health/`（老 admin 首页的有用部分）

**新建**：
- `ui/src/app/(operator)/layout.tsx` —— operator 独立 layout（无 AuthGuard，自己的 sidebar）
- `ui/src/app/(operator)/page.tsx` —— 手动输 bootstrap key 的 landing
- `ui/src/app/(operator)/orgs/page.tsx` —— 所有 Org + Developer 总览
- `ui/src/components/operator-guard.tsx`
- `ui/src/components/operator-sidebar.tsx`
- `ui/src/app/(app)/apps/[id]/layout.tsx` —— App 工作台 layout（带 AppWorkspaceSidebar）
- `ui/src/components/app-workspace-sidebar.tsx`
- `ui/src/lib/hooks/use-orgs.ts`
- `ui/src/lib/__tests__/operator-fetch.test.ts`（新）

**修改**：
- `ui/src/lib/store.ts` —— 加 `operatorKey: string`（session storage 而非 localStorage）+ `setOperatorKey`、`clearOperatorKey`；加 `getOperatorKey` 非 hook getter
- `ui/src/lib/api.ts` —— 新增 `operatorFetch<T>`（强制走 X-Cozy-API-Key = operatorKey，永远不带 JWT / AppId）；`buildAuthHeaders` 不变
- `ui/src/components/app-sidebar.tsx` —— 简化为只剩 `Apps` + `Settings`（其他搬到 workspace sidebar 里）
- `ui/src/app/(app)/settings/page.tsx` —— 去掉 legacy bootstrap keys 面板
- `ui/src/app/(app)/layout.tsx` —— 保持不变
- 所有搬迁后的页面 —— 内部 `apiFetch` 调用显式 `scoped` 参数（operator 版 `scoped: false`，App 工作台版 `scoped: true`）
- `ui/src/lib/i18n/{en,zh}.ts` —— 补 operator 模式相关 key

---

## 任务列表

### Task 1: 后端中间件 — 角色边界强化

**Files:**
- Modify: `src/cozymemory/app.py:168-230`
- Create: `tests/unit/test_operator_auth_isolation.py`

> **背景**：当前中间件里 Bearer 无 AppId 时 `ok = True`（放行）。这是 Step 7.1 的妥协。现在强化为：Bearer 调业务路由（`/conversations` 等）**必须**带 AppId，否则 401。`/operator/*` 拒收 Bearer，仅接 bootstrap key。

- [ ] **Step 1.1: 写失败测试**

新建 `tests/unit/test_operator_auth_isolation.py`：

```python
"""Step 8 — operator / developer 角色鉴权边界。

- /api/v1/operator/* 只接 bootstrap key，拒 JWT
- 业务路由（/conversations 等）的 Bearer 分支必须带 X-Cozy-App-Id
"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.api.deps import get_conversation_service
from cozymemory.app import create_app
from cozymemory.db.models import Base
from cozymemory.models.conversation import ConversationMemoryListResponse

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)
BOOTSTRAP_KEY = "bootstrap-role-test"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres + redis",
)


@pytest.fixture(autouse=True)
async def clean_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for t in reversed(Base.metadata.sorted_tables):
            await conn.execute(t.delete())
    await engine.dispose()
    yield


@pytest.fixture
def mock_conv():
    svc = MagicMock()
    svc.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    return svc


@pytest.fixture
async def client(mock_conv):
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_conv
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _register(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "d@c.com", "password": "Password1",
              "org_name": "Org", "org_slug": "org"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_bearer_without_appid_on_business_route_rejected(client):
    """Bearer 无 AppId 调 /conversations → 401（Step 7 之前 ok=True，这里收紧）"""
    token = await _register(client)
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_bearer_without_appid_on_dashboard_allowed(client):
    """Bearer 无 AppId 调 /dashboard/apps（管理接口）→ 200（合理）"""
    token = await _register(client)
    r = await client.get(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_jwt_cannot_access_operator_routes(client):
    """Developer JWT 调 /operator/* → 401（operator 只认 bootstrap）"""
    token = await _register(client)
    # 先随便建一条 operator 用的路由（Task 2 会搬 users-mapping 过去）；
    # 这个测试在 Task 2 完成后才能真正走通。此处用一个将会存在的路径
    # 占位；在 Task 2 实现后断言应返回 401 而非 404。
    r = await client.get(
        "/api/v1/operator/users-mapping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (401, 404)  # 现状 404，Task 2 后 401
    # Step 8 完成后期望严格 401


@pytest.mark.asyncio
async def test_bootstrap_key_can_access_operator_routes(client):
    """bootstrap key 调 /operator/* → 放行（路由可能还不存在 → 404，但至少不是 401）"""
    r = await client.get(
        "/api/v1/operator/users-mapping",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code != 401
```

- [ ] **Step 1.2: 跑测试验证失败**

Run: `.venv/bin/pytest tests/unit/test_operator_auth_isolation.py -v`
Expected: `test_bearer_without_appid_on_business_route_rejected` FAIL（因为现在是 `ok = True`）；其他可能也不完全对。

- [ ] **Step 1.3: 修改 middleware 逻辑**

修改 `src/cozymemory/app.py` 的 `_AUTH_EXEMPT_PREFIXES` 和 Bearer 分支（~line 168-230）。

关键改动点：

```python
    _AUTH_EXEMPT_PREFIXES = (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/metrics",
        "/api/v1/auth",
        "/api/v1/dashboard",
        # Step 8: operator 路径走独立鉴权分支；不豁免，进中间件
    )

    # Step 8: 业务路由白名单 —— Bearer 分支无 AppId 调这些路径 → 401。
    # 管理类路径（dashboard / auth）由 _AUTH_EXEMPT_PREFIXES 或业务豁免已覆盖，
    # 不需进这里。
    _BEARER_REQUIRES_APP_ID_PREFIXES = (
        "/api/v1/conversations",
        "/api/v1/profiles",
        "/api/v1/context",
        "/api/v1/knowledge",
    )
```

在 Bearer 分支（原 Step 7.1 那段）里改：

```python
        elif authorization.startswith("Bearer "):
            path = request.url.path
            # /operator/* 拒 JWT —— 那里只认 bootstrap
            if path.startswith("/api/v1/operator"):
                ok = False
            else:
                try:
                    from sqlalchemy import select as _select

                    from .auth.jwt import decode_access_token
                    from .db.engine import _session_factory, init_engine
                    from .db.models import App, Developer
                    if _session_factory is None:
                        init_engine()
                    assert _session_factory is not None
                    payload = decode_access_token(authorization[7:])
                    dev_id = payload.get("sub")
                    async with _session_factory() as s:
                        dev = (await s.execute(
                            _select(Developer).where(Developer.id == dev_id)
                        )).scalar_one_or_none()
                        if dev is None:
                            ok = False
                        else:
                            app_id_hdr = request.headers.get("x-cozy-app-id", "")
                            if app_id_hdr:
                                row = (await s.execute(
                                    _select(App).where(App.id == app_id_hdr)
                                )).scalar_one_or_none()
                                if row is None or str(row.org_id) != str(dev.org_id):
                                    ok = False
                                else:
                                    ok = True
                                    request.state.app_id = str(row.id)
                                    request.state.api_key_id = None
                                    request.state.developer_id = str(dev.id)
                            else:
                                # Step 8: 业务路由强制 AppId；其他路径（非业务）放行
                                if any(path.startswith(p) for p in _BEARER_REQUIRES_APP_ID_PREFIXES):
                                    ok = False
                                else:
                                    ok = True
                                    request.state.developer_id = str(dev.id)
                except Exception:
                    ok = False
```

更新 401 detail：`"Missing or invalid X-Cozy-API-Key / Bearer token; business routes require X-Cozy-App-Id when using Bearer"`。

- [ ] **Step 1.4: 跑测试验证（至少两个断言过）**

Run: `.venv/bin/pytest tests/unit/test_operator_auth_isolation.py::test_bearer_without_appid_on_business_route_rejected tests/unit/test_operator_auth_isolation.py::test_bearer_without_appid_on_dashboard_allowed tests/unit/test_operator_auth_isolation.py::test_bootstrap_key_can_access_operator_routes -v`
Expected: 3 个 PASS。（test_jwt_cannot_access_operator_routes 因 operator 路由还不存在会 404 而非 401，留到 Task 2 后收紧。）

- [ ] **Step 1.5: 回归 Step 7 测试**

Run: `.venv/bin/pytest tests/unit/test_jwt_auth_middleware.py tests/unit/test_route_app_scoping.py tests/unit/test_dashboard_users_api.py tests/unit/test_app_context.py -v`

Expected: 所有 Step 7 测试 PASS。若 `test_bearer_without_app_id_on_business_route_passes_middleware` FAIL（因为 Step 7 断言 `!= 401`，现在会 == 401）—— **更新该测试** 成 `assert r.status_code == 401` 并加注释说明是 Step 8 收紧的结果。

- [ ] **Step 1.6: Commit**

```bash
git add src/cozymemory/app.py tests/unit/test_operator_auth_isolation.py tests/unit/test_jwt_auth_middleware.py
git commit -m "feat(auth): Step 8.1 — 中间件强化角色边界（Bearer 业务路由需 AppId；/operator/* 拒 JWT）"
```

---

### Task 2: 搬 `/users` 到 `/operator/users-mapping`，`/backup` 到 `/operator/backup`

**Files:**
- Create: `src/cozymemory/api/v1/operator/__init__.py`
- Create: `src/cozymemory/api/v1/operator/users_mapping.py`（从 `users.py` 复制内容）
- Create: `src/cozymemory/api/v1/operator/backup.py`（从 `backup.py` 复制内容）
- Delete: `src/cozymemory/api/v1/users.py`
- Delete: `src/cozymemory/api/v1/backup.py`
- Modify: `src/cozymemory/api/v1/router.py`（挂载新 operator 包，去掉旧 users / backup 引用）
- Modify: existing tests referencing `/api/v1/users` or `/api/v1/backup`

- [ ] **Step 2.1: 创建 operator 包**

```bash
mkdir -p src/cozymemory/api/v1/operator
touch src/cozymemory/api/v1/operator/__init__.py
```

`src/cozymemory/api/v1/operator/__init__.py`：

```python
"""Operator (bootstrap key only) 路由集合。

这些路由提供全局 ops 视角：跨 org 的 user mapping / 备份 / 组织列表 / 全局数据浏览。
中间件已保证 /api/v1/operator/* 只接 bootstrap key，拒 JWT。
"""
from fastapi import APIRouter

from .backup import router as backup_router
from .users_mapping import router as users_mapping_router

router = APIRouter(prefix="/operator")
router.include_router(users_mapping_router)
router.include_router(backup_router)
```

- [ ] **Step 2.2: 搬 users.py 到 operator/users_mapping.py**

```bash
git mv src/cozymemory/api/v1/users.py src/cozymemory/api/v1/operator/users_mapping.py
```

修改 `operator/users_mapping.py` 的：
- `APIRouter(prefix="/users", ...)` → `APIRouter(prefix="/users-mapping", ...)`
- 同步更新 `summary` / `description` 提到 "operator"
- 相对 import 层级多一层：`from ..deps` → `from ...deps`，等等

打开文件顶部看原有 import，把相对层级统一调整（比如 `from ...api.deps` → `from ....api.deps`，具体以报错为准）。

- [ ] **Step 2.3: 搬 backup.py 到 operator/backup.py**

```bash
git mv src/cozymemory/api/v1/backup.py src/cozymemory/api/v1/operator/backup.py
```

同样调整路径前缀（保留 `/backup` 前缀）+ 相对 import 层级。

- [ ] **Step 2.4: 更新 router.py**

Read `src/cozymemory/api/v1/router.py` 先看当前挂载了哪些子路由。把 `users` / `backup` 的 import 和 `include_router` 去掉，加上 `from .operator import router as operator_router; router.include_router(operator_router)`。

- [ ] **Step 2.5: 更新老测试路径**

```bash
grep -rlE "api/v1/users|api/v1/backup" tests/
```

对于每个命中文件：
- `/api/v1/users` 替换为 `/api/v1/operator/users-mapping`
- `/api/v1/backup` 替换为 `/api/v1/operator/backup`

用 `sed` 批量：
```bash
grep -rlE "api/v1/users[^-]|api/v1/backup" tests/ | xargs sed -i 's|/api/v1/users|/api/v1/operator/users-mapping|g; s|/api/v1/backup|/api/v1/operator/backup|g'
```
（注意 `users[^-]` 避免误匹 `users-mapping`。）

检查改对没：`grep -rE "api/v1/users|api/v1/backup" tests/`（应无残留）。

- [ ] **Step 2.6: 收紧 Task 1 里的 operator-auth 测试**

把 `test_jwt_cannot_access_operator_routes` 的 `assert r.status_code in (401, 404)` 改成 `assert r.status_code == 401`（现在路由已存在，JWT 必须被拒）。

- [ ] **Step 2.7: 全量后端测试**

Run: `.venv/bin/pytest tests/unit/ -q 2>&1 | tail -15`
Expected: 全部 PASS（含 test_operator_auth_isolation 的全部 4 个）。

- [ ] **Step 2.8: Commit**

```bash
git add -A src/cozymemory/api/v1/ tests/unit/
git commit -m "refactor(backend): Step 8.2 — 搬 /users, /backup 到 /operator/* 命名空间"
```

---

### Task 3: 新增 `/operator/orgs` 端点

**Files:**
- Create: `src/cozymemory/api/v1/operator/orgs.py`
- Modify: `src/cozymemory/api/v1/operator/__init__.py`（挂载）
- Create: `tests/unit/test_operator_orgs_api.py`

- [ ] **Step 3.1: 写失败测试**

`tests/unit/test_operator_orgs_api.py`：

```python
"""Operator orgs 路由 —— 列所有 Organization + 对应 dev/app 数。"""
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.app import create_app
from cozymemory.db.models import Base

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)
BOOTSTRAP_KEY = "boot-orgs-test"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
)


@pytest.fixture(autouse=True)
async def clean_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for t in reversed(Base.metadata.sorted_tables):
            await conn.execute(t.delete())
    await engine.dispose()
    yield


@pytest.fixture
async def client():
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed(c):
    # 建两个 org，第一个有 2 个 dev + 1 个 app
    r = await c.post("/api/v1/auth/register", json={
        "email": "a@c.com", "password": "Password1",
        "org_name": "OrgA", "org_slug": "orga"})
    tok_a = r.json()["access_token"]
    await c.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"name": "A1", "slug": "a1"},
    )
    # Dev2 via register（不同 email / 不同 org）
    await c.post("/api/v1/auth/register", json={
        "email": "b@c.com", "password": "Password1",
        "org_name": "OrgB", "org_slug": "orgb"})


@pytest.mark.asyncio
async def test_orgs_list_requires_bootstrap_key(client):
    await _seed(client)
    # 无 key → 401
    r = await client.get("/api/v1/operator/orgs")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_orgs_list_returns_all_orgs_with_counts(client):
    await _seed(client)
    r = await client.get(
        "/api/v1/operator/orgs",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    slugs = {row["slug"] for row in data["data"]}
    assert slugs == {"orga", "orgb"}
    orga = next(r for r in data["data"] if r["slug"] == "orga")
    assert orga["dev_count"] == 1
    assert orga["app_count"] == 1
```

- [ ] **Step 3.2: 跑 → FAIL（404 路由不存在）**

Run: `.venv/bin/pytest tests/unit/test_operator_orgs_api.py -v`

- [ ] **Step 3.3: 实现 orgs 路由**

`src/cozymemory/api/v1/operator/orgs.py`：

```python
"""Operator orgs —— 跨 org 管理视角。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....db import get_session
from ....db.models import App, Developer, Organization

router = APIRouter(prefix="/orgs", tags=["operator"])


class OrgRow(BaseModel):
    id: str
    name: str
    slug: str
    created_at: str
    dev_count: int
    app_count: int


class OrgListResponse(BaseModel):
    data: list[OrgRow]
    total: int


@router.get("", response_model=OrgListResponse)
async def list_orgs(session: AsyncSession = Depends(get_session)) -> OrgListResponse:
    """跨 org 列表。counts 用 scalar subquery，避免 group_by 锁定。"""
    dev_count_sq = (
        select(func.count(Developer.id))
        .where(Developer.org_id == Organization.id)
        .scalar_subquery()
    )
    app_count_sq = (
        select(func.count(App.id))
        .where(App.org_id == Organization.id)
        .scalar_subquery()
    )
    stmt = select(
        Organization.id,
        Organization.name,
        Organization.slug,
        Organization.created_at,
        dev_count_sq.label("dev_count"),
        app_count_sq.label("app_count"),
    ).order_by(Organization.created_at)
    rows = (await session.execute(stmt)).all()
    data = [
        OrgRow(
            id=str(r.id),
            name=r.name,
            slug=r.slug,
            created_at=r.created_at.isoformat(),
            dev_count=r.dev_count,
            app_count=r.app_count,
        )
        for r in rows
    ]
    return OrgListResponse(data=data, total=len(data))
```

- [ ] **Step 3.4: 挂载到 operator 包**

修改 `src/cozymemory/api/v1/operator/__init__.py`：

```python
from fastapi import APIRouter

from .backup import router as backup_router
from .orgs import router as orgs_router
from .users_mapping import router as users_mapping_router

router = APIRouter(prefix="/operator")
router.include_router(users_mapping_router)
router.include_router(backup_router)
router.include_router(orgs_router)
```

- [ ] **Step 3.5: 跑 → PASS**

Run: `.venv/bin/pytest tests/unit/test_operator_orgs_api.py -v`

- [ ] **Step 3.6: Commit**

```bash
git add src/cozymemory/api/v1/operator/ tests/unit/test_operator_orgs_api.py
git commit -m "feat(operator): Step 8.3 — /operator/orgs 跨 org 总览"
```

---

### Task 4: Zustand `operatorKey` + `operatorFetch`

**Files:**
- Modify: `ui/src/lib/store.ts`
- Modify: `ui/src/lib/api.ts`
- Create: `ui/src/lib/__tests__/operator-fetch.test.ts`

- [ ] **Step 4.1: 扩展 Zustand store（session storage）**

在 `ui/src/lib/store.ts`，Zustand 目前整体 persist 到 `cozymemory-app`（localStorage）。但 `operatorKey` 应该**只存 sessionStorage**，关闭浏览器即丢。

方案：用单独的 Zustand store（不 persist），其值手动在 `setOperatorKey` 时写 `sessionStorage`，启动时从 `sessionStorage` 读一次。

在 `store.ts` 末尾加：

```ts
// ── Operator mode (bootstrap key 独立 store，sessionStorage 存储，
//    不走全局 persist 避免 key 永久留存 localStorage)
interface OperatorState {
  operatorKey: string;
  setOperatorKey: (k: string) => void;
  clearOperatorKey: () => void;
}

const OPERATOR_STORAGE_KEY = "cozymemory-operator-key";

function readOperatorFromSession(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(OPERATOR_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function writeOperatorToSession(v: string) {
  if (typeof window === "undefined") return;
  try {
    if (v) window.sessionStorage.setItem(OPERATOR_STORAGE_KEY, v);
    else window.sessionStorage.removeItem(OPERATOR_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export const useOperatorStore = create<OperatorState>()((set) => ({
  operatorKey: readOperatorFromSession(),
  setOperatorKey: (k) => {
    writeOperatorToSession(k);
    set({ operatorKey: k });
  },
  clearOperatorKey: () => {
    writeOperatorToSession("");
    set({ operatorKey: "" });
  },
}));

export function getOperatorKey(): string {
  return useOperatorStore.getState().operatorKey;
}
```

- [ ] **Step 4.2: 加 `operatorFetch`**

修改 `ui/src/lib/api.ts`。在 `dashboardFetch` 旁边加：

```ts
/**
 * operator 专用 fetch —— 走 X-Cozy-API-Key = operatorKey，永远不带 JWT / AppId。
 * 只在 (operator)/* 页面里使用。
 */
export async function operatorFetch<T>(path: string, init?: Omit<ApiFetchInit, "scoped">): Promise<T> {
  const operatorKey = getOperatorKey();
  if (!operatorKey) {
    throw new Error("operator key missing");
  }
  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`);
  const params = (init as ApiFetchInit | undefined)?.params;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const headers = new Headers({ "Content-Type": "application/json" });
  headers.set("X-Cozy-API-Key", operatorKey);
  const extra = init?.headers;
  if (extra) {
    const extraHeaders = new Headers(extra as HeadersInit);
    extraHeaders.forEach((v, k) => headers.set(k, v));
  }
  const { params: _p, ...rest } = (init ?? {}) as ApiFetchInit;
  const res = await fetch(url.toString(), { ...rest, headers });
  if (res.status === 401) {
    useOperatorStore.getState().clearOperatorKey();
    if (typeof window !== "undefined") window.location.assign("/operator");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data as ApiError;
    throw new Error(err?.detail ?? err?.error ?? `HTTP ${res.status}`);
  }
  return data as T;
}
```

在文件顶部加 import：`import { useOperatorStore, getOperatorKey } from "./store";`

- [ ] **Step 4.3: 写单测**

`ui/src/lib/__tests__/operator-fetch.test.ts`：

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";

import { operatorFetch } from "@/lib/api";
import { useOperatorStore } from "@/lib/store";

describe("operatorFetch", () => {
  beforeEach(() => {
    useOperatorStore.setState({ operatorKey: "" });
    vi.restoreAllMocks();
  });

  it("未设置 operatorKey 时抛错", async () => {
    await expect(operatorFetch("/health")).rejects.toThrow(/operator key missing/i);
  });

  it("发 X-Cozy-API-Key 头，不发 Authorization / X-Cozy-App-Id", async () => {
    useOperatorStore.setState({ operatorKey: "kkk" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await operatorFetch("/operator/orgs");
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("X-Cozy-API-Key")).toBe("kkk");
    expect(h.get("Authorization")).toBeNull();
    expect(h.get("X-Cozy-App-Id")).toBeNull();
  });

  it("401 清 operatorKey 并跳 /operator", async () => {
    useOperatorStore.setState({ operatorKey: "bad" });
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, assign, href: "" },
      writable: true,
      configurable: true,
    });
    vi.spyOn(global, "fetch").mockResolvedValueOnce(new Response("", { status: 401 }));
    await expect(operatorFetch("/operator/orgs")).rejects.toThrow();
    expect(useOperatorStore.getState().operatorKey).toBe("");
    expect(assign).toHaveBeenCalledWith("/operator");
  });
});
```

- [ ] **Step 4.4: 跑测试**

Run: `cd ui && npm run test -- operator-fetch`
Expected: 3/3 PASS。跑全量 `npm run test` 确认 Step 7 的 21 个旧测试不回归。

- [ ] **Step 4.5: Commit**

```bash
git add ui/src/lib/store.ts ui/src/lib/api.ts ui/src/lib/__tests__/operator-fetch.test.ts
git commit -m "feat(ui): Step 8.4 — operatorKey（sessionStorage）+ operatorFetch"
```

---

### Task 5: `(operator)` 路由组 + 登陆页 + Guard + Sidebar

**Files:**
- Create: `ui/src/app/(operator)/layout.tsx`
- Create: `ui/src/app/(operator)/page.tsx`（landing with key input）
- Create: `ui/src/components/operator-guard.tsx`
- Create: `ui/src/components/operator-sidebar.tsx`
- Modify: `ui/src/proxy.ts`（放行 /operator/*）

- [ ] **Step 5.1: proxy.ts 放行 /operator**

Read `ui/src/proxy.ts`，确认 `/operator` 被视为 public 路径（不 redirect 到 /login）。修改 `isPublic` 判断：

```ts
  const isPublic = p.startsWith("/login")
    || p.startsWith("/register")
    || p.startsWith("/operator")   // 新增
    || p.startsWith("/_next")
    || p.startsWith("/api")
    || p === "/favicon.ico";
```

- [ ] **Step 5.2: OperatorGuard 组件**

`ui/src/components/operator-guard.tsx`：

```tsx
"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

import { useOperatorStore } from "@/lib/store";

export function OperatorGuard({ children }: { children: React.ReactNode }) {
  const operatorKey = useOperatorStore((s) => s.operatorKey);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // landing page (/operator) 本身不需要 key
    if (pathname === "/operator") return;
    if (!operatorKey) router.replace("/operator");
  }, [operatorKey, router, pathname]);

  if (pathname !== "/operator" && !operatorKey) return null;
  return <>{children}</>;
}
```

- [ ] **Step 5.3: OperatorSidebar 组件**

`ui/src/components/operator-sidebar.tsx`：

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  Users,
  Brain,
  UserCircle2,
  Database,
  Activity,
  Archive,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useT } from "@/lib/i18n";

const items = [
  { href: "/operator/orgs",           icon: Building2,    labelKey: "operator.orgs" },
  { href: "/operator/users-mapping",  icon: Users,        labelKey: "operator.users_mapping" },
  { href: "/operator/memory-raw",     icon: Brain,        labelKey: "operator.memory_raw" },
  { href: "/operator/profiles-raw",   icon: UserCircle2,  labelKey: "operator.profiles_raw" },
  { href: "/operator/knowledge-raw",  icon: Database,     labelKey: "operator.knowledge_raw" },
  { href: "/operator/health",         icon: Activity,     labelKey: "operator.health" },
  { href: "/operator/backup",         icon: Archive,      labelKey: "operator.backup" },
] as const;

export function OperatorSidebar() {
  const t = useT();
  const pathname = usePathname();
  return (
    <Sidebar collapsible="none">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t("operator.sidebar.title")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((it) => (
                <SidebarMenuItem key={it.href}>
                  <SidebarMenuButton asChild isActive={pathname === it.href}>
                    <Link href={it.href}>
                      <it.icon className="size-4" />
                      <span>{t(it.labelKey)}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
```

> 如果 `@/components/ui/sidebar` 还没这些 export，先读文件确认实际 API，再同样用（Step 7 的 AppSidebar 可以参考）。

- [ ] **Step 5.4: layout.tsx**

`ui/src/app/(operator)/layout.tsx`：

```tsx
import { OperatorGuard } from "@/components/operator-guard";
import { OperatorSidebar } from "@/components/operator-sidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Providers } from "@/components/providers";
import { I18nProvider } from "@/lib/i18n";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <Providers>
        <OperatorGuard>
          <SidebarProvider>
            <div className="flex h-full w-full">
              <OperatorSidebar />
              <main className="flex-1 flex flex-col min-w-0 overflow-auto">
                <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
                  <SidebarTrigger className="-ml-1" />
                  <span className="text-sm text-muted-foreground">Operator Mode</span>
                </div>
                <div className="flex-1 p-4 sm:p-6 min-w-0">{children}</div>
              </main>
            </div>
          </SidebarProvider>
        </OperatorGuard>
      </Providers>
    </I18nProvider>
  );
}
```

> 先读 `ui/src/app/(app)/layout.tsx` 确认 `Providers` 的实际 path。

- [ ] **Step 5.5: landing page（输 key）**

`ui/src/app/(operator)/page.tsx`：

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useT } from "@/lib/i18n";
import { useOperatorStore } from "@/lib/store";

export default function OperatorLanding() {
  const t = useT();
  const router = useRouter();
  const setStoreKey = useOperatorStore((s) => s.setOperatorKey);
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    try {
      // 用提交的 key 试探 /operator/orgs，403/401 → key 无效
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const r = await fetch(`${base}/api/v1/operator/orgs`, {
        headers: { "X-Cozy-API-Key": key },
      });
      if (!r.ok) {
        toast.error(t("operator.key_invalid"));
        return;
      }
      setStoreKey(key);
      router.replace("/operator/orgs");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Operator Mode</CardTitle>
          <CardDescription>{t("operator.landing_desc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="op-key">{t("operator.bootstrap_key")}</Label>
              <Input
                id="op-key"
                type="password"
                autoComplete="off"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t("operator.bootstrap_key_hint")}
              </p>
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("common.loading") : t("operator.enter")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

> 注意：本页**不**走 OperatorGuard（landing page 本来就是无 key 状态）。`OperatorGuard` 内判断 `pathname === "/operator"` 时不 redirect。

- [ ] **Step 5.6: i18n keys**

加到 en.ts + zh.ts：

```
operator.sidebar.title — "Operator" / "Operator"
operator.orgs — "Organizations" / "组织列表"
operator.users_mapping — "User Mapping (legacy)" / "用户映射（遗留）"
operator.memory_raw — "Memory (global)" / "对话记忆（全局）"
operator.profiles_raw — "Profiles (global)" / "用户画像（全局）"
operator.knowledge_raw — "Knowledge (global)" / "知识库（全局）"
operator.health — "Health / Metrics" / "运行状态"
operator.backup — "Backup" / "备份"
operator.landing_desc — "Enter your bootstrap API key to access global ops views." / "输入 bootstrap 密钥进入全局运维视图。"
operator.bootstrap_key — "Bootstrap Key" / "Bootstrap 密钥"
operator.bootstrap_key_hint — "From your .env COZY_API_KEYS; not stored in localStorage, session only." / "来自 .env COZY_API_KEYS；仅保存在当前会话，关闭浏览器即清除。"
operator.enter — "Enter Operator Mode" / "进入 Operator 模式"
operator.key_invalid — "Key rejected. Check your bootstrap value." / "密钥无效，请检查 bootstrap 配置。"
```

- [ ] **Step 5.7: 手工冒烟**

起 UI（容器已 live）：
- 浏览器访问 `http://<host>:8088/operator` → 看到 landing 输入框
- 输错 key → toast 错误
- 输对 bootstrap key → 跳 `/operator/orgs`（目前可能空白，页面 Task 6 做；但至少看到左 sidebar）

- [ ] **Step 5.8: Commit**

```bash
git add ui/src/proxy.ts ui/src/components/operator-guard.tsx \
  ui/src/components/operator-sidebar.tsx ui/src/app/\(operator\) \
  ui/src/lib/i18n
git commit -m "feat(ui): Step 8.5 — (operator) 路由组 + landing + guard + sidebar"
```

---

### Task 6: 搬老页面到 `(operator)/*`

**Files:**
- Create: `ui/src/app/(operator)/orgs/page.tsx`（新实现）
- Copy: `ui/src/app/(operator)/users-mapping/page.tsx`（从 `(app)/users/page.tsx`）
- Copy: `ui/src/app/(operator)/memory-raw/page.tsx`（从 `(app)/memory/page.tsx`）
- Copy: `ui/src/app/(operator)/profiles-raw/page.tsx`（从 `(app)/profiles/page.tsx`）
- Copy: `ui/src/app/(operator)/knowledge-raw/page.tsx`（从 `(app)/knowledge/page.tsx`）
- Copy: `ui/src/app/(operator)/backup/page.tsx`（从 `(app)/backup/page.tsx`）
- Copy: `ui/src/app/(operator)/health/page.tsx`（从 `(app)/dashboard/page.tsx`）

> 这些页面基本就是把现有 page.tsx 复制过去。**关键改动**：它们内部的 `apiFetch(...)` 或 `usersApi.list()` 等调用本来依赖 Zustand 的 `apiKey` + `jwt`。Operator 模式下：
> - 新建一个 `operatorApi` 命名空间（在 `api.ts` 里）用 `operatorFetch` 构建对等接口；或
> - 给现有 `usersApi.list` 等加一个 mode switch；或
> - 页面内 `useEffect` 里手动把 `jwt` 清空后再让 `apiFetch` 走 legacy apiKey 分支
>
> 最简洁：**新建 operator 的 API 方法集合**，operator 页面用这些。见 Step 6.0。

- [ ] **Step 6.0: api.ts 增加 operator 专用方法**

在 `ui/src/lib/api.ts` 末尾加：

```ts
// ── Operator API methods —— 全部走 operatorFetch（X-Cozy-API-Key = operatorKey）
export const operatorApi = {
  orgs: () => operatorFetch<{ data: Array<{id: string; name: string; slug: string; created_at: string; dev_count: number; app_count: number}>; total: number }>("/operator/orgs"),
  // user mapping
  listUsers: () => operatorFetch<UserListResponse>("/operator/users-mapping"),
  getUserUuid: (userId: string, create = false) =>
    operatorFetch<UserMappingResponse>(`/operator/users-mapping/${userId}/uuid`, { params: { create } }),
  deleteUserMapping: (userId: string) =>
    operatorFetch<{ success: boolean; message: string; warning: string }>(
      `/operator/users-mapping/${userId}/uuid`,
      { method: "DELETE" },
    ),
  // 全局 memory / profiles / knowledge —— 后端业务路由对 bootstrap key 是
  // passthrough，operator 可直接调 /conversations /profiles /knowledge
  // 传任意 user_id 都能看到
  listConversations: (userId: string) =>
    operatorFetch<ConversationListResponse>("/conversations", { params: { user_id: userId } }),
  getProfile: (userId: string) =>
    operatorFetch<ProfileResponse>(`/profiles/${userId}`),
  listKnowledgeDatasets: () =>
    operatorFetch<S["DatasetListResponse"]>("/knowledge/datasets"),
  health: () => operatorFetch<HealthResponse>("/health"),
};
```

> 如果部分路径前缀需要调（/conversations → /operator/conversations 或者直接用 /conversations 都行），原则：**老全局浏览走 `/conversations` 这些 passthrough 接口即可**（因为 operator 用 bootstrap key，后端 scope_user_id 是 passthrough，不污染 external_users）。`/users-mapping` 必须用 operator 前缀（那条路由真的搬了）。

- [ ] **Step 6.1: orgs page（新实现）**

`ui/src/app/(operator)/orgs/page.tsx`：

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { operatorApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function OrgsPage() {
  const t = useT();
  const { data, isLoading } = useQuery({
    queryKey: ["operator", "orgs"],
    queryFn: operatorApi.orgs,
  });
  if (isLoading) return <p>{t("common.loading")}</p>;
  const orgs = data?.data ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">
        <Building2 className="size-5 inline mr-2" />{t("operator.orgs")}
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {orgs.map((o) => (
          <Card key={o.id}>
            <CardHeader><CardTitle>{o.name}</CardTitle></CardHeader>
            <CardContent className="text-sm space-y-1">
              <p className="text-muted-foreground">/{o.slug}</p>
              <p>{o.dev_count} developer(s), {o.app_count} app(s)</p>
              <p className="text-xs text-muted-foreground">
                {new Date(o.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
        {orgs.length === 0 && <p className="text-muted-foreground">No orgs yet.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 6.2: Copy users page**

```bash
cp ui/src/app/\(app\)/users/page.tsx ui/src/app/\(operator\)/users-mapping/page.tsx
```

修改新文件：
- `usersApi.list` → `operatorApi.listUsers`
- `usersApi.getUuid(uid, false)` → `operatorApi.getUserUuid(uid, false)`
- `usersApi.deleteMapping(uid)` → `operatorApi.deleteUserMapping(uid)`
- import 从 `"@/lib/api"` 拉 `operatorApi`

- [ ] **Step 6.3: Copy memory / profiles / knowledge / backup / health pages**

```bash
cp ui/src/app/\(app\)/memory/page.tsx ui/src/app/\(operator\)/memory-raw/page.tsx
cp ui/src/app/\(app\)/profiles/page.tsx ui/src/app/\(operator\)/profiles-raw/page.tsx
cp ui/src/app/\(app\)/knowledge/page.tsx ui/src/app/\(operator\)/knowledge-raw/page.tsx
cp ui/src/app/\(app\)/backup/page.tsx ui/src/app/\(operator\)/backup/page.tsx
cp ui/src/app/\(app\)/dashboard/page.tsx ui/src/app/\(operator\)/health/page.tsx
```

每个复制过来的文件里：
- `conversationsApi.xxx` 替换为 `operatorApi.xxx`（或者直接留着——但在 operator layout 下 jwt 为空，apiFetch 会自动走 apiKey 分支。**陷阱**：apiFetch 读 `getApiKey()` 而 operator 是 `getOperatorKey()`——所以必须改）。**硬性规则**：operator 页面里所有 fetch 走 `operatorFetch` / `operatorApi.*`，不走 `apiFetch`。
- 碰到 `scoped: true` 的地方全部改成 `operatorFetch`
- 碰到 `usersApi` → `operatorApi`

每搬一个文件就 `grep -n "apiFetch\|dashboardFetch\|usersApi\|conversationsApi\|profilesApi" <file>`，把残留的都替换成 operatorApi 或 operatorFetch。

- [ ] **Step 6.4: 手工冒烟**

打开 `/operator`（输 bootstrap key）→ `/operator/orgs` 看到你的 org → 点 sidebar 切各页面 → 看到全局数据。

- [ ] **Step 6.5: Commit**

```bash
git add ui/src/app/\(operator\) ui/src/lib/api.ts
git commit -m "feat(ui): Step 8.6 — operator 页面（orgs/users-mapping/memory-raw/profiles-raw/knowledge-raw/backup/health）"
```

---

### Task 7: `(app)/apps/[id]/` 工作台 layout + 搬 App 子页

**Files:**
- Create: `ui/src/app/(app)/apps/[id]/layout.tsx`
- Create: `ui/src/components/app-workspace-sidebar.tsx`
- Copy: `ui/src/app/(app)/apps/[id]/memory/page.tsx`（从 `(app)/memory/page.tsx`）
- Copy: `ui/src/app/(app)/apps/[id]/profiles/page.tsx`（从 `(app)/profiles/page.tsx`）
- Copy: `ui/src/app/(app)/apps/[id]/knowledge/page.tsx`（从 `(app)/knowledge/page.tsx`）
- Copy: `ui/src/app/(app)/apps/[id]/context/page.tsx`（从 `(app)/context/page.tsx`）
- Copy: `ui/src/app/(app)/apps/[id]/playground/page.tsx`（从 `(app)/playground/page.tsx`）

- [ ] **Step 7.1: AppWorkspaceSidebar**

`ui/src/components/app-workspace-sidebar.tsx`：

```tsx
"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import {
  LayoutGrid,
  KeyRound,
  Users,
  Brain,
  UserCircle2,
  Database,
  Eye,
  Beaker,
  ArrowLeft,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useT } from "@/lib/i18n";

export function AppWorkspaceSidebar() {
  const t = useT();
  const params = useParams();
  const pathname = usePathname();
  const id = params?.id as string | undefined;
  if (!id) return null;

  const base = `/apps/${id}`;
  const items = [
    { href: base,                      icon: LayoutGrid,   labelKey: "app_workspace.overview" },
    { href: `${base}/keys`,            icon: KeyRound,     labelKey: "keys.title" },
    { href: `${base}/users`,           icon: Users,        labelKey: "users.ext_title" },
    { href: `${base}/memory`,          icon: Brain,        labelKey: "app_workspace.memory" },
    { href: `${base}/profiles`,        icon: UserCircle2,  labelKey: "app_workspace.profiles" },
    { href: `${base}/knowledge`,       icon: Database,     labelKey: "app_workspace.knowledge" },
    { href: `${base}/context`,         icon: Eye,          labelKey: "app_workspace.context" },
    { href: `${base}/playground`,      icon: Beaker,       labelKey: "app_workspace.playground" },
  ] as const;

  return (
    <Sidebar collapsible="none">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t("app_workspace.title")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <Link href="/apps">
                    <ArrowLeft className="size-4" />
                    <span>{t("app_workspace.back_to_apps")}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              {items.map((it) => (
                <SidebarMenuItem key={it.href}>
                  <SidebarMenuButton asChild isActive={pathname === it.href}>
                    <Link href={it.href}>
                      <it.icon className="size-4" />
                      <span>{t(it.labelKey)}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
```

- [ ] **Step 7.2: [id]/layout.tsx**

`ui/src/app/(app)/apps/[id]/layout.tsx`：

```tsx
"use client";

import { use, useEffect } from "react";

import { AppWorkspaceSidebar } from "@/components/app-workspace-sidebar";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useAppStore } from "@/lib/store";

export default function AppWorkspaceLayout({
  params,
  children,
}: {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
}) {
  const { id } = use(params);
  const setAppId = useAppStore((s) => s.setCurrentAppId);

  // 进工作台自动把 Zustand 的 currentAppId 绑到路由参数，
  // 确保 apiFetch(scoped:true) 始终带 X-Cozy-App-Id
  useEffect(() => {
    setAppId(id);
  }, [id, setAppId]);

  return (
    <SidebarProvider>
      <div className="flex w-full">
        <AppWorkspaceSidebar />
        <main className="flex-1 p-4 sm:p-6 min-w-0">{children}</main>
      </div>
    </SidebarProvider>
  );
}
```

> 这样每进一个 App 详情 URL，自动把 currentAppId 同步到 store —— 即使用户是从外部链接直接打开某 App 的 memory 页，apiFetch scoped 也能拿到正确 AppId。

- [ ] **Step 7.3: Copy sub-pages**

```bash
cp ui/src/app/\(app\)/memory/page.tsx ui/src/app/\(app\)/apps/\[id\]/memory/page.tsx
cp ui/src/app/\(app\)/profiles/page.tsx ui/src/app/\(app\)/apps/\[id\]/profiles/page.tsx
cp ui/src/app/\(app\)/knowledge/page.tsx ui/src/app/\(app\)/apps/\[id\]/knowledge/page.tsx
cp ui/src/app/\(app\)/context/page.tsx ui/src/app/\(app\)/apps/\[id\]/context/page.tsx
cp ui/src/app/\(app\)/playground/page.tsx ui/src/app/\(app\)/apps/\[id\]/playground/page.tsx
```

这些页面**内部逻辑不用改**：它们用的 `apiFetch` 会自动带 JWT + X-Cozy-App-Id（currentAppId 由 layout 设的），后端会走 uuid5 scope。

**但 knowledge 页面**按 spec 决策 4 "本期不做真隔离"，要让它继续用全局 API：
打开 `ui/src/app/(app)/apps/[id]/knowledge/page.tsx`，顶部加 comment：
```tsx
// FIXME(Step 9): 本文件的 knowledgeApi.* 调用仍是全局的（跨 App 共享 dataset）。
// 真 per-App 隔离要等 Step 9 的 App↔Dataset 表 + 路由改造。
```
不改内部逻辑。

- [ ] **Step 7.4: i18n keys**

加 en.ts + zh.ts：

```
app_workspace.title — "App Workspace" / "应用工作台"
app_workspace.back_to_apps — "← All apps" / "← 返回应用列表"
app_workspace.overview — "Overview" / "概览"
app_workspace.memory — "Memory" / "对话记忆"
app_workspace.profiles — "Profiles" / "用户画像"
app_workspace.knowledge — "Knowledge" / "知识库"
app_workspace.context — "Context" / "上下文调试"
app_workspace.playground — "Playground" / "沙盒"
```

- [ ] **Step 7.5: 手工冒烟**

`/apps` 点卡片进 `/apps/<id>` → 看左侧工作台 sidebar 完整 → 点 Memory 看到该 App 的记忆（老数据看不到是正常的，是隔离结果）。

- [ ] **Step 7.6: Commit**

```bash
git add ui/src/app/\(app\)/apps/\[id\] ui/src/components/app-workspace-sidebar.tsx ui/src/lib/i18n
git commit -m "feat(ui): Step 8.7 — /apps/[id]/ 工作台 layout + memory/profiles/knowledge/context/playground 子页"
```

---

### Task 8: 删除全局级别的老页面 + 精简 AppSidebar

**Files:**
- Delete: `ui/src/app/(app)/memory/`
- Delete: `ui/src/app/(app)/profiles/`
- Delete: `ui/src/app/(app)/knowledge/`
- Delete: `ui/src/app/(app)/context/`
- Delete: `ui/src/app/(app)/playground/`
- Delete: `ui/src/app/(app)/users/`
- Delete: `ui/src/app/(app)/backup/`
- Delete: `ui/src/app/(app)/dashboard/`
- Modify: `ui/src/components/app-sidebar.tsx`
- Modify: `ui/src/app/(app)/settings/page.tsx`（去 legacy bootstrap 面板）

- [ ] **Step 8.1: 删旧顶层页面目录**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git rm -r ui/src/app/\(app\)/memory ui/src/app/\(app\)/profiles \
  ui/src/app/\(app\)/knowledge ui/src/app/\(app\)/context \
  ui/src/app/\(app\)/playground ui/src/app/\(app\)/users \
  ui/src/app/\(app\)/backup ui/src/app/\(app\)/dashboard
```

- [ ] **Step 8.2: 精简 AppSidebar**

Read `ui/src/components/app-sidebar.tsx`。只保留顶层需要的条目：Apps、Settings。其他（memory / profiles / knowledge / context / playground / users / backup / dashboard）删掉。

具体：找到 sidebar items 数组，删掉除 `/apps` 和 `/settings` 之外的全部项。如果留 `/apps` 名字是"Apps 管理"，顶栏依赖 AppSwitcher 工作。

- [ ] **Step 8.3: 从 settings 页去掉 legacy bootstrap 面板**

Read `ui/src/app/(app)/settings/page.tsx`，找到 ServerApiKeysPanel 的 Card 包装（Step 7.8 加的），整段删除。同时 import 也删。

- [ ] **Step 8.4: 删除 usersApi 引用漏网**

全局搜 `usersApi` `conversationsApi\.` `profilesApi\.` `knowledgeApi\.` 在非 `(app)/apps/[id]` 和非 `(operator)` 路径下的引用：

```bash
grep -rnE "usersApi|conversationsApi|profilesApi|knowledgeApi" ui/src/app/\(app\)/ | grep -v "apps/\[id\]" | head
```

预期只剩几处合法残留（比如 hooks 文件）。有遗漏的旧页面没删就删掉。

- [ ] **Step 8.5: Lint + test**

```bash
cd ui
npm run lint 2>&1 | tail -15
npm run test 2>&1 | tail -10
```

预期 lint 只剩 Step 7 之前的 9 个 pre-existing 错误（如果有新错就对着改）；test 全 PASS。

- [ ] **Step 8.6: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add -A
git commit -m "refactor(ui): Step 8.8 — 删除全局级老页面，精简 AppSidebar，settings 移除 legacy 面板"
```

---

### Task 9: `(operator)/settings` + 完整冒烟

**Files:**
- Create: `ui/src/app/(operator)/settings/page.tsx`（legacy bootstrap keys 面板搬这里）
- Update: `ui/src/components/operator-sidebar.tsx`（加 settings 条目）

- [ ] **Step 9.1: 搬 server-api-keys-panel.tsx 到 operator settings**

`ui/src/app/(operator)/settings/page.tsx`：

```tsx
"use client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ServerApiKeysPanel } from "@/components/server-api-keys-panel";
import { useT } from "@/lib/i18n";

export default function OperatorSettings() {
  const t = useT();
  return (
    <div className="space-y-4 max-w-4xl">
      <h1 className="text-xl font-semibold">{t("operator.settings")}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.legacy_bootstrap_title")}</CardTitle>
          <CardDescription>{t("settings.legacy_bootstrap_desc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ServerApiKeysPanel />
        </CardContent>
      </Card>
    </div>
  );
}
```

> server-api-keys-panel 里的调用是老的 `/api/v1/admin/api-keys`。如该端点不存在或已迁，此面板功能已经 Stale 了 —— 就这样留着作 "legacy reference"，不在本期处理。

- [ ] **Step 9.2: operator-sidebar 加 settings 条目**

在 `ui/src/components/operator-sidebar.tsx` 的 items 数组最后加：

```ts
  { href: "/operator/settings",       icon: Settings,     labelKey: "operator.settings" },
```

并 import `Settings` 图标。

- [ ] **Step 9.3: i18n**

```
operator.settings — "Legacy Settings" / "遗留设置"
```

- [ ] **Step 9.4: 重建 UI 镜像 + 重启容器**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
sudo ./build.sh cozymemory-ui 2>&1 | tail -3
sudo docker compose -f docker-compose.1panel.yml up -d --force-recreate cozymemory-ui 2>&1 | tail -3
```

- [ ] **Step 9.5: 全链路冒烟**

浏览器走一遍：
1. `/` → proxy 跳 `/login`
2. 登录（已有 smoke@test.com 账号）→ `/apps`
3. 建个新 App `"acme"` / slug `"acme"` → 点进去
4. 左 sidebar workspace → Memory → 加一条 user_id="alice" 的对话 → 回 External Users 看到 alice 的 uuid5 映射
5. 顶栏 AppSwitcher 切到 SelfCEO（已清过空 external_users）→ Memory 应空
6. 浏览器新开一个窗口访问 `/operator` → 输 bootstrap key → 进 orgs 总览 → 看到 acme + SelfCEO + Smoke 等多 org
7. operator 下 `/operator/memory-raw` 应看到全部 Mem0 历史 user（包括 Step 7 之前的老数据）
8. operator 下 `/operator/orgs` → 验证 dev/app 计数正确

验证 DB 干净：
```bash
sudo docker exec cozy_postgres psql -U cozymemory_user -d cozymemory -c "SELECT app_id, COUNT(*) FROM external_users GROUP BY app_id;"
```
每个 app_id 的 count 等于你在该 App 下真实写入的 user 数（不含旧全局 id）。

- [ ] **Step 9.6: Commit 冒烟 artifacts**

（冒烟本身无代码变化，但可能改了 operator-sidebar / i18n）

```bash
git add -A ui/src/app/\(operator\)/settings ui/src/components/operator-sidebar.tsx ui/src/lib/i18n
git commit -m "feat(ui): Step 8.9 — operator settings + 冒烟"
```

---

### Task 10: 收尾

- [ ] **Step 10.1: 全量测试**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
.venv/bin/pytest tests/unit/ -q 2>&1 | tail -5
cd ui && npm run test 2>&1 | tail -5
cd ui && npm run lint 2>&1 | tail -5
```

后端 PASS；UI test PASS；lint 不新增错误。

- [ ] **Step 10.2: 重生 api-types（后端路由变了）**

后端也得重建（/operator/* 新路由）：
```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
sudo ./build.sh cozymemory
sudo docker compose -f docker-compose.1panel.yml up -d --force-recreate cozymemory-api
sleep 5
cd ../ui && npm run gen:api
cd .. && git add ui/src/lib/api-types.ts
git commit -m "chore(ui): Step 8.10 — regen api-types (operator routes)"
```

- [ ] **Step 10.3: 更新 CLAUDE.md**

在 `CLAUDE.md` 的 "Architecture" 段下加一小节 "Role Model"：

```markdown
### Role model（Step 8 后）

CozyMemory 有两类使用者，对应两条 UI 入口 / 两种鉴权：

- **Developer**（JWT 登录）：自助注册，管理自己 org 下的 App + Key + External Users；所有业务数据访问强制按 App scope。UI 入口 `/login` → `/apps/[id]/*`。
- **Operator**（bootstrap key，env `COZY_API_KEYS`）：平台 ops / admin，跨 org 只读或维护全局数据。UI 入口 `/operator`（手动输 key，sessionStorage 保存）。

中间件（`src/cozymemory/app.py` 的 `require_api_key`）按 header 分流：
- `X-Cozy-API-Key` = bootstrap → 全放行（包括 `/operator/*`）
- `X-Cozy-API-Key` = App key → 只能走业务路由 `/conversations` `/profiles` `/context` `/knowledge`，自动带 `request.state.app_id`
- `Authorization: Bearer <JWT>` → 调 `/dashboard/*` `/auth/*` 放行；调业务路由**必须**同时带 `X-Cozy-App-Id`（否则 401）；调 `/operator/*` → 401

`/api/v1/operator/*` 命名空间：
- `users-mapping`（老 Mem0 UUID v4 映射；Step 8 前叫 `/api/v1/users`）
- `backup`（Step 8 前叫 `/api/v1/backup`）
- `orgs`（Step 8 新增）
```

```bash
git add CLAUDE.md
git commit -m "docs(claude-md): Step 8 角色模型说明"
```

- [ ] **Step 10.4: Push**

```bash
git push
```

---

## 估时汇总

| Task | 预估 |
|---|---|
| 1 中间件强化 | 2h |
| 2 搬 users / backup | 2.5h |
| 3 orgs 端点 | 1h |
| 4 Zustand operatorKey + operatorFetch | 1h |
| 5 (operator) 路由组壳 | 2h |
| 6 搬 operator 页面 | 2.5h |
| 7 /apps/[id]/ workspace | 2h |
| 8 删老页 + 精简 sidebar | 1h |
| 9 operator settings + 冒烟 | 1h |
| 10 收尾 / regen / 文档 / push | 1h |
| **合计** | **~16h** |
