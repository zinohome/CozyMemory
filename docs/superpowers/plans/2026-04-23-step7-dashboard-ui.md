# Step 7 — Developer Dashboard UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 Developer Dashboard UI（方案 C 全局 App 切换 + JWT/AppId 后端鉴权通路 + External Users 视图 + 中英 i18n），让 SaaS 客户自助注册、管 App 和 Key，并按"当前 App"维度浏览数据。

**Architecture:** 中间件按 header 分流：外部 App 继续走 `X-Cozy-API-Key`（不变），UI 走 `Authorization: Bearer <JWT>` + `X-Cozy-App-Id`。UI 用 Next.js 16 App Router 的 `(auth)` / `(app)` 路由组 + Zustand（jwt、currentAppId）+ TanStack Query（apps / keys / users）。

**Tech Stack:** FastAPI / SQLAlchemy async / PyJWT（后端）；Next.js 16 / React 19 / @base-ui/react / shadcn / Tailwind v4 / TanStack Query / Zustand / Vitest（前端）。

**Next.js 版本警告：** `ui/AGENTS.md` 明确本仓 Next.js 版本和训练数据有差异，写 Next 特性代码前必须查 `ui/node_modules/next/dist/docs/`（routing / middleware / use server / caching 行为）。

---

## File Structure

### 后端（新增 / 修改）

- **修改** `src/cozymemory/app.py:149-210` — `require_api_key` 中间件扩展 Bearer 分支
- **修改** `src/cozymemory/auth/app_context.py` — `api_key_id` 允许 `None`，补 JWT 模式工厂
- **新增** `src/cozymemory/api/v1/dashboard/users.py` — users 列表 / 删除路由
- **修改** `src/cozymemory/api/v1/dashboard.py` — 挂 users 子路由
- **新增** `tests/unit/test_jwt_auth_middleware.py` — 6 用例
- **新增** `tests/unit/test_dashboard_users_api.py` — 4 用例

### 前端（新增 / 修改）

- **修改** `ui/src/lib/api.ts` — `apiFetch({ scoped })` 和 `dashboardFetch`
- **修改** `ui/src/lib/store.ts` — 加 `jwt` / `currentAppId` / `currentAppSlug`
- **新增** `ui/src/middleware.ts` — `(app)/*` 无 JWT → redirect `/login`
- **新增** `ui/src/app/(auth)/layout.tsx`
- **新增** `ui/src/app/(auth)/login/page.tsx`
- **新增** `ui/src/app/(auth)/register/page.tsx`
- **新增** `ui/src/components/auth/login-form.tsx`
- **新增** `ui/src/components/auth/register-form.tsx`
- **新增** `ui/src/components/auth-guard.tsx`
- **新增** `ui/src/components/app-switcher.tsx`
- **新增** `ui/src/components/user-menu.tsx`
- **新增** `ui/src/components/create-app-dialog.tsx`
- **新增** `ui/src/components/api-key-created-dialog.tsx`
- **新增** `ui/src/app/(app)/apps/page.tsx`
- **新增** `ui/src/app/(app)/apps/[id]/page.tsx`
- **新增** `ui/src/app/(app)/apps/[id]/keys/page.tsx`
- **新增** `ui/src/app/(app)/apps/[id]/users/page.tsx`
- **修改** `ui/src/app/(app)/layout.tsx` — 加 `AuthGuard` + `AppSwitcher` + `UserMenu`
- **修改** `ui/src/components/app-sidebar.tsx` — 加"Apps 管理"
- **修改** `ui/src/lib/i18n/**` — 加约 40 条 key 中英文
- **新增** `ui/src/components/__tests__/app-switcher.test.tsx`
- **修改** `ui/src/lib/__tests__/api.test.ts` — 覆盖 scoped + 401 flow

> `apps-page` 的建 App 成功 / slug 409 路径由 `CreateAppDialog` + TanStack Query 缓存行为隐式覆盖，本期不单建测试文件（如需，作为 follow-up）。
- **重生** `ui/src/lib/api-types.ts`（`npm run gen:api`）

---

## 任务列表

### Task 1: 后端中间件支持 Bearer JWT + X-Cozy-App-Id

**Files:**
- Modify: `src/cozymemory/app.py:149-210`
- Test: `tests/unit/test_jwt_auth_middleware.py`

- [ ] **Step 1.1: 写失败测试 — Bearer + AppId 合法放行**

新建 `tests/unit/test_jwt_auth_middleware.py`：

```python
"""JWT + X-Cozy-App-Id 鉴权通路（方案 C）。

外部 App 走 X-Cozy-API-Key 的老路径不动；UI Dashboard 走 Bearer JWT +
X-Cozy-App-Id，中间件按 header 分流。本套测试覆盖 6 个关键场景。
"""
import os
import uuid
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
BOOTSTRAP_KEY = "bootstrap-jwt-test"

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


async def _register_and_app(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "d@c.com", "password": "Password1",
              "org_name": "Org", "org_slug": "org"},
    )
    token = r.json()["access_token"]
    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A", "slug": "aa"},
    )
    return token, r2.json()["id"], uuid.UUID(r2.json()["namespace_id"])


@pytest.mark.asyncio
async def test_bearer_plus_app_id_passes_and_scopes(client, mock_conv):
    token, app_id, ns = await _register_and_app(client)
    ext = "ext_user_1"
    expected = uuid.uuid5(ns, ext)

    r = await client.post(
        "/api/v1/conversations",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Cozy-App-Id": app_id,
        },
        json={"user_id": ext, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    kwargs = mock_conv.add.await_args.kwargs
    assert kwargs["user_id"] == str(expected)
```

- [ ] **Step 1.2: 跑测试验证失败**

Run: `pytest tests/unit/test_jwt_auth_middleware.py::test_bearer_plus_app_id_passes_and_scopes -v`
Expected: FAIL with 401（中间件还不识别 Bearer）

- [ ] **Step 1.3: 实现中间件 Bearer 分支**

修改 `src/cozymemory/app.py:168-195`（在 `provided = request.headers.get("x-cozy-api-key", "")` 和它后面的 if/elif 块之间插入新通路）：

```python
        provided = request.headers.get("x-cozy-api-key", "")
        authorization = request.headers.get("authorization", "")

        ok = False
        # 1) X-Cozy-API-Key — 外部 App 路径（优先）
        if provided and provided in settings.api_keys_set:
            ok = True
        elif provided:
            try:
                from .db.engine import _session_factory, init_engine
                from .services.api_key_store import ApiKeyStore
                if _session_factory is None:
                    init_engine()
                assert _session_factory is not None
                async with _session_factory() as s:
                    store = ApiKeyStore(s)
                    record = await store.verify_and_touch(provided)
                    await s.commit()
                    if record is not None:
                        ok = True
                        request.state.api_key_id = str(record.id)
                        request.state.app_id = str(record.app_id)
            except Exception:
                ok = False
        # 2) Bearer JWT + 可选 X-Cozy-App-Id — Dashboard UI 路径
        elif authorization.startswith("Bearer "):
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
                            # 跨 org → 404 防枚举（这里走 401 更一致，让
                            # dashboard 路由自己决定 403/404）
                            if row is None or str(row.org_id) != str(dev.org_id):
                                ok = False
                            else:
                                ok = True
                                request.state.app_id = str(row.id)
                                request.state.api_key_id = None
                                request.state.developer_id = str(dev.id)
                        else:
                            # Bearer 无 AppId — 只能调 /auth 或 /dashboard
                            # 这里放行，让具体路由用 require_* 依赖决定
                            ok = True
                            request.state.developer_id = str(dev.id)
            except Exception:
                ok = False
```

同时更新 401 detail 的文案：`"Missing or invalid X-Cozy-API-Key / Bearer token"`。

- [ ] **Step 1.4: 跑测试验证通过**

Run: `pytest tests/unit/test_jwt_auth_middleware.py::test_bearer_plus_app_id_passes_and_scopes -v`
Expected: PASS

- [ ] **Step 1.5: 补剩余 5 个用例**

追加到同文件末尾：

```python
@pytest.mark.asyncio
async def test_bearer_plus_cross_org_app_id_rejected(client):
    """A developer 用 B org 的 app_id → 401（中间件不放行）"""
    token_a, _, _ = await _register_and_app(client)
    # 建第二个 org
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@c.com", "password": "Password1",
              "org_name": "B", "org_slug": "bb"},
    )
    tb = r.json()["access_token"]
    rb = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tb}"},
        json={"name": "B", "slug": "bbapp"},
    )
    cross_app_id = rb.json()["id"]

    r3 = await client.post(
        "/api/v1/conversations",
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Cozy-App-Id": cross_app_id,
        },
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_bearer_without_app_id_on_business_route_passes_middleware(client, mock_conv):
    """Bearer 无 AppId 走业务路由 — 中间件放行，但业务层可能因无 app_ctx
    走 bootstrap 透传逻辑。这里只验中间件层放行。"""
    token, _, _ = await _register_and_app(client)
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code != 401


@pytest.mark.asyncio
async def test_expired_jwt_rejected(client):
    """伪造一个立刻过期的 token → 401"""
    from datetime import datetime, timedelta, timezone

    import jwt as _jwt

    from cozymemory.config import settings
    token = _jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000",
         "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_forged_jwt_rejected(client):
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": "Bearer not.a.valid.jwt"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_api_key_wins_over_bearer(client, mock_conv):
    """两者同时存在 — X-Cozy-API-Key 优先（外部 App 兼容）"""
    r = await client.post(
        "/api/v1/conversations",
        headers={
            "X-Cozy-API-Key": BOOTSTRAP_KEY,
            "Authorization": "Bearer something.invalid.here",
        },
        json={"user_id": "raw", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    kwargs = mock_conv.add.await_args.kwargs
    assert kwargs["user_id"] == "raw"  # bootstrap 透传
```

- [ ] **Step 1.6: 跑全部**

Run: `pytest tests/unit/test_jwt_auth_middleware.py -v`
Expected: 6 passed

- [ ] **Step 1.7: 回归 Step 6 的业务路由测试**

Run: `pytest tests/unit/test_route_app_scoping.py tests/unit/test_app_context.py -v`
Expected: 所有原有测试依旧 PASS。若失败，检查中间件分流逻辑是否影响了 X-Cozy-API-Key 路径。

- [ ] **Step 1.8: Commit**

```bash
git add src/cozymemory/app.py tests/unit/test_jwt_auth_middleware.py
git commit -m "feat(auth): Step 7.1 — middleware 支持 Bearer JWT + X-Cozy-App-Id 路径"
```

---

### Task 2: Dashboard Users 路由（列表 / 删除 / count）

**Files:**
- Create: `src/cozymemory/api/v1/dashboard/__init__.py`（如不存在）
- Create: `src/cozymemory/api/v1/dashboard/users.py`
- Modify: `src/cozymemory/api/v1/dashboard.py`（挂子路由）
- Test: `tests/unit/test_dashboard_users_api.py`

> **先摸现状**：跑 `ls src/cozymemory/api/v1/dashboard* 2>/dev/null && cat src/cozymemory/api/v1/dashboard.py | head -50`，看 dashboard 是单文件还是已分包。若单文件，这个 Task 把它拆成包（`dashboard/apps.py` / `dashboard/keys.py` / `dashboard/users.py` 三文件）。若已是包，直接加 `users.py`。

- [ ] **Step 2.1: 写失败测试**

新建 `tests/unit/test_dashboard_users_api.py`：

```python
"""Dashboard Users API — 列出 / 删除 App 下的 external user 映射。

用于开发者 UI 的 users 视图：看到哪些 ext_id → uuid 映射存在，并可
触发 GDPR 级联删除的第一步（索引删除；引擎端数据由上层服务另做）。
"""
import os
import uuid
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
async def client():
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = "bootstrap-x"
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    mock = MagicMock()
    mock.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, mock
    app.dependency_overrides.clear()


async def _bootstrap(c):
    r = await c.post("/api/v1/auth/register", json={
        "email": "d@c.com", "password": "Password1",
        "org_name": "O", "org_slug": "oo"})
    token = r.json()["access_token"]
    r2 = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A", "slug": "aa"})
    app_id = r2.json()["id"]
    # 建个 key 然后造几个 ext user
    r3 = await c.post(f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "k"})
    key = r3.json()["key"]
    for ext in ["alice", "bob", "carol"]:
        await c.post("/api/v1/conversations",
            headers={"X-Cozy-API-Key": key},
            json={"user_id": ext, "messages": [{"role": "user", "content": "hi"}]})
    return token, app_id


@pytest.mark.asyncio
async def test_list_users_paginated(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.get(
        f"/api/v1/dashboard/apps/{app_id}/users?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_users_not_visible_across_apps(client):
    c, _ = client
    token_a, _ = await _bootstrap(c)
    # 建第二个 app（同 dev）查它的 users 应为空
    r = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "B", "slug": "bb"})
    app_b = r.json()["id"]
    r2 = await c.get(f"/api/v1/dashboard/apps/{app_b}/users",
        headers={"Authorization": f"Bearer {token_a}"})
    assert r2.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_user_then_404(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.delete(
        f"/api/v1/dashboard/apps/{app_id}/users/alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    r2 = await c.delete(
        f"/api/v1/dashboard/apps/{app_id}/users/alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_users_count_matches(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.get(f"/api/v1/dashboard/apps/{app_id}/users",
        headers={"Authorization": f"Bearer {token}"})
    assert r.json()["total"] == 3
```

- [ ] **Step 2.2: 跑 → FAIL（路由未定义 → 404）**

Run: `pytest tests/unit/test_dashboard_users_api.py -v`

- [ ] **Step 2.3: 实现路由**

新建 `src/cozymemory/api/v1/dashboard/users.py`：

```python
"""Dashboard Users 路由 — 开发者 UI 查 App 下的 external user 映射。"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....api.deps import get_redis_client
from ....auth.deps import get_current_developer
from ....db import App, get_session
from ....db.models import Developer, ExternalUser
from ....services.user_resolver import UserResolver

router = APIRouter(prefix="/apps/{app_id}/users", tags=["dashboard"])


class ExtUserItem(BaseModel):
    external_user_id: str
    internal_uuid: str
    created_at: str


class ExtUserListResponse(BaseModel):
    data: list[ExtUserItem]
    total: int


async def _assert_app_owned(session: AsyncSession, app_id: UUID, dev: Developer) -> App:
    row = (await session.execute(select(App).where(App.id == app_id))).scalar_one_or_none()
    if row is None or row.org_id != dev.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="app not found")
    return row


@router.get("", response_model=ExtUserListResponse)
async def list_users(
    app_id: UUID,
    limit: int = 50,
    offset: int = 0,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> ExtUserListResponse:
    await _assert_app_owned(session, app_id, dev)
    resolver = UserResolver(session, get_redis_client())
    items = await resolver.list_for_app(app_id, limit=limit, offset=offset)
    total = await resolver.count_for_app(app_id)
    return ExtUserListResponse(
        data=[
            ExtUserItem(
                external_user_id=u.external_user_id,
                internal_uuid=str(u.internal_uuid),
                created_at=u.created_at.isoformat(),
            )
            for u in items
        ],
        total=total,
    )


@router.delete("/{external_user_id}")
async def delete_user(
    app_id: UUID,
    external_user_id: str,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await _assert_app_owned(session, app_id, dev)
    resolver = UserResolver(session, get_redis_client())
    removed = await resolver.delete(app_id, external_user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    await session.commit()
    return {"success": True}
```

然后在 `src/cozymemory/api/v1/dashboard.py`（如果是单文件）末尾挂载：

```python
from .dashboard_users import router as users_router  # 或按 Step 2 摸到的实际结构 import
router.include_router(users_router)
```

> 若 `dashboard.py` 已是一个包目录则对应地加 `from .users import router as users_router`。

- [ ] **Step 2.4: 跑 → PASS**

Run: `pytest tests/unit/test_dashboard_users_api.py -v`

- [ ] **Step 2.5: Commit**

```bash
git add src/cozymemory/api/v1/dashboard* tests/unit/test_dashboard_users_api.py
git commit -m "feat(dashboard): Step 7.2 — External users 列表 / 删除 / count API"
```

---

### Task 3: 前端 api.ts 重构 + Zustand 扩展

**Files:**
- Modify: `ui/src/lib/store.ts`
- Modify: `ui/src/lib/api.ts`
- Modify: `ui/src/lib/__tests__/api.test.ts`

- [ ] **Step 3.1: 扩展 Zustand store**

在 `ui/src/lib/store.ts` 的 `AppState` interface 和 `persist` initial state 里加字段：

```ts
interface AppState {
  // ... 原有字段不动

  // Developer JWT（登录后持久化）
  jwt: string;
  setJwt: (t: string) => void;

  // 当前选中 App（App Switcher 维护）
  currentAppId: string;
  setCurrentAppId: (id: string) => void;
  currentAppSlug: string;
  setCurrentAppSlug: (s: string) => void;

  logout: () => void;
}
```

`create` 里对应追加：

```ts
      jwt: "",
      setJwt: (t) => set({ jwt: t }),
      currentAppId: "",
      setCurrentAppId: (id) => set({ currentAppId: id }),
      currentAppSlug: "",
      setCurrentAppSlug: (s) => set({ currentAppSlug: s }),
      logout: () => set({ jwt: "", currentAppId: "", currentAppSlug: "" }),
```

加非 hook getter：

```ts
export function getJwt(): string {
  return useAppStore.getState().jwt;
}
export function getCurrentAppId(): string {
  return useAppStore.getState().currentAppId;
}
```

- [ ] **Step 3.2: 重构 api.ts fetch helper**

修改 `ui/src/lib/api.ts:55-` 处的 `apiFetch`：

```ts
import { getApiKey, getJwt, getCurrentAppId, useAppStore } from "./store";

type FetchOpts = RequestInit & {
  params?: Record<string, string | number | boolean | undefined>;
  scoped?: boolean; // true → 业务路由（加 X-Cozy-App-Id）
};

async function buildHeaders(scoped: boolean, init?: RequestInit): Promise<Headers> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  const jwt = getJwt();
  const apiKey = getApiKey();
  if (jwt) {
    headers.set("Authorization", `Bearer ${jwt}`);
    if (scoped) {
      const appId = getCurrentAppId();
      if (appId) headers.set("X-Cozy-App-Id", appId);
    }
  } else if (apiKey) {
    headers.set("X-Cozy-API-Key", apiKey);
  }
  return headers;
}

async function apiFetch<T>(path: string, init?: FetchOpts): Promise<T> {
  const { params, scoped = true, ...rest } = init ?? {};
  const url = new URL(BASE_URL + API_PREFIX + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const headers = await buildHeaders(scoped, rest);
  const res = await fetch(url.toString(), { ...rest, headers });
  if (res.status === 401 && getJwt()) {
    useAppStore.getState().logout();
    if (typeof window !== "undefined") window.location.assign("/login");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function dashboardFetch<T>(path: string, init?: FetchOpts): Promise<T> {
  return apiFetch<T>(path, { ...init, scoped: false });
}
```

- [ ] **Step 3.3: 扩展 api.test.ts 单测**

追加到 `ui/src/lib/__tests__/api.test.ts`：

```ts
describe("apiFetch scoped", () => {
  it("scoped: true 时同时发 Authorization 和 X-Cozy-App-Id", async () => {
    useAppStore.setState({ jwt: "jj", currentAppId: "aid-1" });
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await api.getHealth(); // 任意 scoped 调用
    const req = spy.mock.calls[0][1] as RequestInit;
    const h = req.headers as Headers;
    expect(h.get("Authorization")).toBe("Bearer jj");
    expect(h.get("X-Cozy-App-Id")).toBe("aid-1");
  });

  it("401 时清 JWT 并跳 /login", async () => {
    useAppStore.setState({ jwt: "jj" });
    const loc = { assign: vi.fn() };
    Object.defineProperty(window, "location", { value: loc, writable: true });
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("", { status: 401 }),
    );
    await expect(api.getHealth()).rejects.toThrow();
    expect(useAppStore.getState().jwt).toBe("");
    expect(loc.assign).toHaveBeenCalledWith("/login");
  });
});
```

- [ ] **Step 3.4: 跑 + lint**

Run (in `ui/`): `npm run test -- api.test.ts` 和 `npm run lint`
Expected: 通过

- [ ] **Step 3.5: Commit**

```bash
git add ui/src/lib/store.ts ui/src/lib/api.ts ui/src/lib/__tests__/api.test.ts
git commit -m "feat(ui): Step 7.3 — Zustand 加 JWT/currentApp，apiFetch 支持 scoped + 401 redirect"
```

---

### Task 4: 中间件 + AuthGuard + (auth) 路由

**Files:**
- Create: `ui/src/middleware.ts`
- Create: `ui/src/components/auth-guard.tsx`
- Create: `ui/src/app/(auth)/layout.tsx`
- Create: `ui/src/app/(auth)/login/page.tsx`
- Create: `ui/src/app/(auth)/register/page.tsx`
- Create: `ui/src/components/auth/login-form.tsx`
- Create: `ui/src/components/auth/register-form.tsx`

> **Next.js 注意**：先 `cat ui/node_modules/next/dist/docs/**/middleware* 2>/dev/null | head -100` 确认 middleware.ts 签名；不同版本 config matcher 语法可能有差异。Zustand persist 数据在 middleware 里读不到（middleware 只能读 cookies），所以 middleware 不能代替 AuthGuard。本任务的 middleware 只是 hard-redirect 兜底（如从未登录过则根据 cookie 预判），主守卫仍在 AuthGuard 客户端组件里。

- [ ] **Step 4.1: 写 middleware.ts**

```ts
// ui/src/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const isAppRoute = !req.nextUrl.pathname.startsWith("/login")
    && !req.nextUrl.pathname.startsWith("/register")
    && !req.nextUrl.pathname.startsWith("/_next")
    && !req.nextUrl.pathname.startsWith("/api");

  // Zustand 存 localStorage，middleware 读不到；只做 cookie hint
  const hasJwt = req.cookies.get("cm_auth")?.value === "1";
  if (isAppRoute && !hasJwt) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

> AuthGuard 登录成功后 `document.cookie = "cm_auth=1; Path=/; SameSite=Lax"`；logout 时清掉。middleware 只用这个 hint 粗判，真实 JWT 存储仍在 Zustand persist 的 localStorage。

- [ ] **Step 4.2: 写 AuthGuard**

```tsx
// ui/src/components/auth-guard.tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const jwt = useAppStore((s) => s.jwt);
  const router = useRouter();
  useEffect(() => {
    if (!jwt) router.replace("/login");
  }, [jwt, router]);
  if (!jwt) return null;
  return <>{children}</>;
}
```

- [ ] **Step 4.3: 写 (auth)/layout.tsx**

```tsx
import { I18nProvider } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <div className="min-h-screen flex items-center justify-center bg-muted p-4">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </I18nProvider>
  );
}
```

- [ ] **Step 4.4: 写 LoginForm + RegisterForm**

`ui/src/components/auth/login-form.tsx`（同 register，字段不同）：

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/lib/store";
import { dashboardFetch } from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

export function LoginForm() {
  const t = useT();
  const router = useRouter();
  const setJwt = useAppStore((s) => s.setJwt);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await dashboardFetch<{ access_token: string }>("/auth/login", {
        method: "POST", body: JSON.stringify({ email, password }),
      });
      setJwt(r.access_token);
      document.cookie = "cm_auth=1; Path=/; SameSite=Lax";
      router.replace("/apps");
    } catch (err) {
      toast.error(t("auth.login_failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>{t("auth.login")}</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4">
          <div><Label>{t("auth.email")}</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
          <div><Label>{t("auth.password")}</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
          <Button type="submit" className="w-full" disabled={loading}>{t("auth.login_submit")}</Button>
          <p className="text-sm text-muted-foreground text-center">
            <a href="/register" className="underline">{t("auth.go_register")}</a>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

`register-form.tsx` 同结构，多 `org_name` + `org_slug` 两个字段，POST `/auth/register`，收到 `access_token` 同样 setJwt + cookie + replace。

- [ ] **Step 4.5: 写页面壳**

```tsx
// ui/src/app/(auth)/login/page.tsx
import { LoginForm } from "@/components/auth/login-form";
export default function LoginPage() { return <LoginForm />; }

// ui/src/app/(auth)/register/page.tsx
import { RegisterForm } from "@/components/auth/register-form";
export default function RegisterPage() { return <RegisterForm />; }
```

- [ ] **Step 4.6: 把 AuthGuard 挂到 (app)/layout.tsx**

修改 `ui/src/app/(app)/layout.tsx`，在最内层 `<div className="flex h-full w-full">` 外包 `<AuthGuard>`：

```tsx
import { AuthGuard } from "@/components/auth-guard";

export default function AppLayout(...) {
  return (
    <I18nProvider>
      <AuthGuard>
        <SidebarProvider>
          {/* 原有内容不动 */}
```

- [ ] **Step 4.7: 手动冒烟**

启动 UI `cd ui && npm run dev`，访问 `http://localhost:3000/memory`，应被 middleware redirect 到 `/login`。填 email/密码注册（先去 `/register`），回到 `/apps`。

- [ ] **Step 4.8: Commit**

```bash
git add ui/src/middleware.ts ui/src/components/auth-guard.tsx ui/src/app/\(auth\) ui/src/components/auth ui/src/app/\(app\)/layout.tsx
git commit -m "feat(ui): Step 7.4 — (auth) 路由 + AuthGuard + middleware + 登录注册"
```

---

### Task 5: Apps 列表 + AppSwitcher + CreateAppDialog

**Files:**
- Create: `ui/src/components/app-switcher.tsx`
- Create: `ui/src/components/user-menu.tsx`
- Create: `ui/src/components/create-app-dialog.tsx`
- Create: `ui/src/app/(app)/apps/page.tsx`
- Modify: `ui/src/app/(app)/layout.tsx`（顶栏加两组件）
- Modify: `ui/src/components/app-sidebar.tsx`（加 Apps 入口）
- Test: `ui/src/components/__tests__/app-switcher.test.tsx`
- Test: `ui/src/app/__tests__/apps-page.test.tsx`

- [ ] **Step 5.1: useApps hook（TanStack Query）**

在 `ui/src/lib/hooks/use-apps.ts`（新建）：

```ts
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardFetch } from "@/lib/api";

export interface AppRow {
  id: string;
  name: string;
  slug: string;
  namespace_id: string;
  created_at: string;
}

export function useApps() {
  return useQuery<AppRow[]>({
    queryKey: ["apps"],
    queryFn: () => dashboardFetch("/dashboard/apps"),
  });
}

export function useCreateApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; slug: string }) =>
      dashboardFetch<AppRow>("/dashboard/apps", {
        method: "POST", body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps"] }),
  });
}
```

- [ ] **Step 5.2: AppSwitcher**

```tsx
// ui/src/components/app-switcher.tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useApps } from "@/lib/hooks/use-apps";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue }
  from "@/components/ui/select";
import { useT } from "@/lib/i18n";

export function AppSwitcher() {
  const t = useT();
  const router = useRouter();
  const { data: apps } = useApps();
  const current = useAppStore((s) => s.currentAppId);
  const setCurrent = useAppStore((s) => s.setCurrentAppId);
  const setSlug = useAppStore((s) => s.setCurrentAppSlug);

  useEffect(() => {
    if (!apps || apps.length === 0) return;
    const stillValid = apps.some((a) => a.id === current);
    if (!stillValid) {
      setCurrent(apps[0].id);
      setSlug(apps[0].slug);
    }
  }, [apps, current, setCurrent, setSlug]);

  if (!apps || apps.length === 0) {
    return (
      <button onClick={() => router.push("/apps")} className="text-sm underline">
        {t("apps.none_create_cta")}
      </button>
    );
  }

  return (
    <Select value={current} onValueChange={(v) => {
      const a = apps.find((x) => x.id === v);
      if (a) { setCurrent(a.id); setSlug(a.slug); }
    }}>
      <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
      <SelectContent>
        {apps.map((a) => (
          <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 5.3: UserMenu**

```tsx
// ui/src/components/user-menu.tsx
"use client";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger }
  from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { LogOut, User } from "lucide-react";
import { useT } from "@/lib/i18n";

export function UserMenu() {
  const t = useT();
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon"><User className="size-4" /></Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => { logout(); document.cookie = "cm_auth=; Path=/; Max-Age=0"; router.replace("/login"); }}>
          <LogOut className="size-4 mr-2" /> {t("auth.logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 5.4: CreateAppDialog**

```tsx
// ui/src/components/create-app-dialog.tsx
"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger }
  from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useCreateApp } from "@/lib/hooks/use-apps";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

export function CreateAppDialog({ trigger }: { trigger: React.ReactNode }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const m = useCreateApp();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await m.mutateAsync({ name, slug });
      toast.success(t("apps.created"));
      setOpen(false); setName(""); setSlug("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("409")) toast.error(t("apps.slug_conflict"));
      else toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("apps.create")}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div><Label>{t("apps.name")}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required /></div>
          <div><Label>{t("apps.slug")}</Label>
            <Input value={slug} onChange={(e) => setSlug(e.target.value)}
              pattern="^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$" required /></div>
          <Button type="submit" disabled={m.isPending}>{t("apps.create_submit")}</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 5.5: Apps 列表页**

```tsx
// ui/src/app/(app)/apps/page.tsx
"use client";
import Link from "next/link";
import { useApps } from "@/lib/hooks/use-apps";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CreateAppDialog } from "@/components/create-app-dialog";
import { Plus } from "lucide-react";
import { useT } from "@/lib/i18n";

export default function AppsPage() {
  const t = useT();
  const { data: apps, isLoading } = useApps();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("apps.title")}</h1>
        <CreateAppDialog trigger={
          <Button><Plus className="size-4 mr-2" />{t("apps.create")}</Button>
        } />
      </div>
      {isLoading ? <p>{t("common.loading")}</p> :
        !apps || apps.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground mb-4">{t("apps.none")}</p>
            <CreateAppDialog trigger={<Button>{t("apps.create_first")}</Button>} />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {apps.map((a) => (
              <Link key={a.id} href={`/apps/${a.id}`}>
                <Card className="hover:bg-accent transition-colors">
                  <CardHeader><CardTitle>{a.name}</CardTitle></CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">/{a.slug}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      {new Date(a.created_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
    </div>
  );
}
```

- [ ] **Step 5.6: 顶栏加 AppSwitcher + UserMenu**

修改 `ui/src/app/(app)/layout.tsx` 的顶栏 div：

```tsx
<div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
  <SidebarTrigger className="-ml-1" />
  <div className="flex-1" />
  <AppSwitcher />
  <UserMenu />
</div>
```

并 import 两个组件。

- [ ] **Step 5.7: Sidebar 加"Apps 管理"**

改 `ui/src/components/app-sidebar.tsx`，菜单项数组顶部加 `{ label: t("apps.title"), href: "/apps", icon: LayoutGrid }`。

- [ ] **Step 5.8: 单测**

`ui/src/components/__tests__/app-switcher.test.tsx`：

```tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppSwitcher } from "../app-switcher";
import { useAppStore } from "@/lib/store";
import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("@/lib/api", () => ({
  dashboardFetch: vi.fn(),
}));
import { dashboardFetch } from "@/lib/api";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe("AppSwitcher", () => {
  beforeEach(() => { useAppStore.setState({ jwt: "j", currentAppId: "", currentAppSlug: "" }); });

  it("空 apps 显示 CTA", async () => {
    vi.mocked(dashboardFetch).mockResolvedValue([]);
    render(wrap(<AppSwitcher />));
    expect(await screen.findByText(/create/i)).toBeInTheDocument();
  });

  it("有 apps 且无持久化 currentAppId → 选第一个", async () => {
    vi.mocked(dashboardFetch).mockResolvedValue([
      { id: "a1", name: "App A", slug: "a", namespace_id: "n", created_at: "2026-01-01" },
      { id: "a2", name: "App B", slug: "b", namespace_id: "m", created_at: "2026-01-02" },
    ]);
    render(wrap(<AppSwitcher />));
    await screen.findByText("App A");
    expect(useAppStore.getState().currentAppId).toBe("a1");
  });

  it("持久化 currentAppId 仍在列表 → 保留", async () => {
    useAppStore.setState({ jwt: "j", currentAppId: "a2", currentAppSlug: "b" });
    vi.mocked(dashboardFetch).mockResolvedValue([
      { id: "a1", name: "App A", slug: "a", namespace_id: "n", created_at: "x" },
      { id: "a2", name: "App B", slug: "b", namespace_id: "m", created_at: "y" },
    ]);
    render(wrap(<AppSwitcher />));
    await screen.findByText("App B");
    expect(useAppStore.getState().currentAppId).toBe("a2");
  });
});
```

- [ ] **Step 5.9: 跑测试**

Run (in `ui/`): `npm run test`
Expected: 新测试 PASS，存量测试不回归

- [ ] **Step 5.10: Commit**

```bash
git add ui/src/lib/hooks ui/src/components/app-switcher.tsx ui/src/components/user-menu.tsx \
  ui/src/components/create-app-dialog.tsx ui/src/app/\(app\)/apps/page.tsx \
  ui/src/app/\(app\)/layout.tsx ui/src/components/app-sidebar.tsx \
  ui/src/components/__tests__/app-switcher.test.tsx
git commit -m "feat(ui): Step 7.5 — Apps 列表 + AppSwitcher + UserMenu + CreateApp"
```

---

### Task 6: App 详情 + Keys 页 + ApiKeyCreatedDialog

**Files:**
- Create: `ui/src/lib/hooks/use-app-keys.ts`
- Create: `ui/src/components/api-key-created-dialog.tsx`
- Create: `ui/src/app/(app)/apps/[id]/page.tsx`
- Create: `ui/src/app/(app)/apps/[id]/keys/page.tsx`

- [ ] **Step 6.1: useAppKeys hooks**

`ui/src/lib/hooks/use-app-keys.ts`：

```ts
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardFetch } from "@/lib/api";

export interface KeyRow {
  id: string;
  name: string;
  prefix: string;
  status: "active" | "disabled";
  created_at: string;
  last_used_at: string | null;
}

export interface KeyCreated extends KeyRow { key: string; }

export function useAppKeys(appId: string) {
  return useQuery<KeyRow[]>({
    queryKey: ["apps", appId, "keys"],
    queryFn: () => dashboardFetch(`/dashboard/apps/${appId}/keys`),
    enabled: !!appId,
  });
}

export function useCreateKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string }) =>
      dashboardFetch<KeyCreated>(`/dashboard/apps/${appId}/keys`, {
        method: "POST", body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}

export function useRotateKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      dashboardFetch<KeyCreated>(`/dashboard/apps/${appId}/keys/${keyId}/rotate`, {
        method: "POST",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}

export function useDeleteKey(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      dashboardFetch(`/dashboard/apps/${appId}/keys/${keyId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps", appId, "keys"] }),
  });
}
```

- [ ] **Step 6.2: ApiKeyCreatedDialog**

```tsx
// ui/src/components/api-key-created-dialog.tsx
"use client";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle }
  from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Copy, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

export function ApiKeyCreatedDialog({
  keyValue, open, onClose,
}: { keyValue: string | null; open: boolean; onClose: () => void }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  async function copy() {
    if (!keyValue) return;
    await navigator.clipboard.writeText(keyValue);
    setCopied(true);
    toast.success(t("keys.copied"));
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("keys.created_once")}</DialogTitle>
          <DialogDescription>{t("keys.created_warning")}</DialogDescription>
        </DialogHeader>
        <div className="rounded border bg-muted p-3 font-mono text-sm break-all">{keyValue}</div>
        <DialogFooter>
          <Button variant="outline" onClick={copy}>
            {copied ? <CheckCircle2 className="size-4 mr-2" /> : <Copy className="size-4 mr-2" />}
            {t("keys.copy")}
          </Button>
          <Button onClick={onClose}>{t("keys.saved_ack")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 6.3: Keys 页**

```tsx
// ui/src/app/(app)/apps/[id]/keys/page.tsx
"use client";
import { use, useState } from "react";
import { useAppKeys, useCreateKey, useRotateKey, useDeleteKey, type KeyCreated }
  from "@/lib/hooks/use-app-keys";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow }
  from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ApiKeyCreatedDialog } from "@/components/api-key-created-dialog";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Plus, RotateCw, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";

export default function KeysPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useT();
  const { data: keys } = useAppKeys(id);
  const createM = useCreateKey(id);
  const rotateM = useRotateKey(id);
  const deleteM = useDeleteKey(id);
  const [name, setName] = useState("");
  const [revealed, setRevealed] = useState<KeyCreated | null>(null);

  async function create() {
    const r = await createM.mutateAsync({ name: name || "key" });
    setRevealed(r); setName("");
  }
  async function rotate(keyId: string) {
    const r = await rotateM.mutateAsync(keyId);
    setRevealed(r);
  }
  async function remove(keyId: string) {
    await deleteM.mutateAsync(keyId);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{t("keys.title")}</h1>
      <div className="flex gap-2">
        <Input placeholder={t("keys.name_placeholder")} value={name} onChange={(e) => setName(e.target.value)} />
        <Button onClick={create} disabled={createM.isPending}>
          <Plus className="size-4 mr-2" />{t("keys.create")}
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("keys.name")}</TableHead>
            <TableHead>{t("keys.prefix")}</TableHead>
            <TableHead>{t("keys.status")}</TableHead>
            <TableHead>{t("keys.last_used")}</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {keys?.map((k) => (
            <TableRow key={k.id}>
              <TableCell>{k.name}</TableCell>
              <TableCell className="font-mono text-xs">{k.prefix}…</TableCell>
              <TableCell>{k.status}</TableCell>
              <TableCell>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "—"}</TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="icon" onClick={() => rotate(k.id)}>
                  <RotateCw className="size-4" />
                </Button>
                <ConfirmDialog
                  title={t("keys.delete_confirm_title")}
                  description={t("keys.delete_confirm_desc")}
                  onConfirm={() => remove(k.id)}
                  trigger={<Button variant="ghost" size="icon"><Trash2 className="size-4" /></Button>}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <ApiKeyCreatedDialog
        keyValue={revealed?.key ?? null}
        open={!!revealed}
        onClose={() => setRevealed(null)}
      />
    </div>
  );
}
```

- [ ] **Step 6.4: App 详情页（基本信息 + 链接到 keys / users）**

```tsx
// ui/src/app/(app)/apps/[id]/page.tsx
"use client";
import { use } from "react";
import Link from "next/link";
import { useApps } from "@/lib/hooks/use-apps";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { KeyRound, Users } from "lucide-react";
import { useT } from "@/lib/i18n";

export default function AppDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useT();
  const { data: apps } = useApps();
  const app = apps?.find((a) => a.id === id);
  if (!app) return <p>{t("common.loading")}</p>;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{app.name}</h1>
        <p className="text-sm text-muted-foreground">/{app.slug}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link href={`/apps/${id}/keys`}>
          <Card className="hover:bg-accent transition-colors">
            <CardHeader><CardTitle><KeyRound className="size-4 inline mr-2" />{t("keys.title")}</CardTitle></CardHeader>
            <CardContent className="text-sm text-muted-foreground">{t("keys.manage_hint")}</CardContent>
          </Card>
        </Link>
        <Link href={`/apps/${id}/users`}>
          <Card className="hover:bg-accent transition-colors">
            <CardHeader><CardTitle><Users className="size-4 inline mr-2" />{t("users.title")}</CardTitle></CardHeader>
            <CardContent className="text-sm text-muted-foreground">{t("users.manage_hint")}</CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 6.5: 手工冒烟 + Commit**

`npm run dev`，登录 → `/apps` → 建 App → 进详情 → 建 key 看 ApiKeyCreatedDialog → rotate → delete。

```bash
git add ui/src/lib/hooks/use-app-keys.ts ui/src/components/api-key-created-dialog.tsx \
  ui/src/app/\(app\)/apps/\[id\]
git commit -m "feat(ui): Step 7.6 — App 详情 + Keys 页 + ApiKeyCreatedDialog"
```

---

### Task 7: External Users 页

**Files:**
- Create: `ui/src/lib/hooks/use-app-users.ts`
- Create: `ui/src/app/(app)/apps/[id]/users/page.tsx`

- [ ] **Step 7.1: hooks**

```ts
// ui/src/lib/hooks/use-app-users.ts
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardFetch } from "@/lib/api";

export interface ExtUser {
  external_user_id: string;
  internal_uuid: string;
  created_at: string;
}
export interface ExtUserList { data: ExtUser[]; total: number; }

export function useAppUsers(appId: string, limit: number, offset: number) {
  return useQuery<ExtUserList>({
    queryKey: ["apps", appId, "users", limit, offset],
    queryFn: () => dashboardFetch(`/dashboard/apps/${appId}/users?limit=${limit}&offset=${offset}`),
    enabled: !!appId,
  });
}

export function useDeleteAppUser(appId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (extId: string) =>
      dashboardFetch(`/dashboard/apps/${appId}/users/${encodeURIComponent(extId)}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps", appId, "users"] }),
  });
}
```

- [ ] **Step 7.2: Users 页带分页**

```tsx
// ui/src/app/(app)/apps/[id]/users/page.tsx
"use client";
import { use, useState } from "react";
import { useAppUsers, useDeleteAppUser } from "@/lib/hooks/use-app-users";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow }
  from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { useT } from "@/lib/i18n";

const PAGE = 20;

export default function UsersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const t = useT();
  const [offset, setOffset] = useState(0);
  const { data } = useAppUsers(id, PAGE, offset);
  const del = useDeleteAppUser(id);

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">{t("users.title")}</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("users.external_id")}</TableHead>
            <TableHead>{t("users.internal_uuid")}</TableHead>
            <TableHead>{t("users.created_at")}</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.data.map((u) => (
            <TableRow key={u.external_user_id}>
              <TableCell>{u.external_user_id}</TableCell>
              <TableCell className="font-mono text-xs">{u.internal_uuid}</TableCell>
              <TableCell>{new Date(u.created_at).toLocaleString()}</TableCell>
              <TableCell className="text-right">
                <ConfirmDialog
                  title={t("users.delete_gdpr")}
                  description={t("users.delete_gdpr_desc")}
                  onConfirm={() => del.mutateAsync(u.external_user_id)}
                  trigger={<Button variant="ghost" size="icon"><Trash2 className="size-4" /></Button>}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t("users.pagination", { page, pages, total })}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE))}>
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="outline" size="icon" disabled={offset + PAGE >= total}
            onClick={() => setOffset(offset + PAGE)}>
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7.3: Commit**

```bash
git add ui/src/lib/hooks/use-app-users.ts ui/src/app/\(app\)/apps/\[id\]/users
git commit -m "feat(ui): Step 7.7 — External Users 页（分页 + GDPR 删除）"
```

---

### Task 8: i18n 补全 + sidebar 整理 + legacy 降级

**Files:**
- Modify: `ui/src/lib/i18n/zh.json`（或对应中文字典文件）
- Modify: `ui/src/lib/i18n/en.json`
- Modify: `ui/src/components/server-api-keys-panel.tsx`（或 settings 页挂载处）
- Modify: `ui/src/app/(app)/settings/page.tsx`

> **先摸现状**：`ls ui/src/lib/i18n/` 看是 `.json` / `.ts` / 按 namespace 切分。下面写的 key 按平面键结构，如果实际是嵌套 `auth: { login: ... }` 样式需要自适应。

- [ ] **Step 8.1: 补 i18n keys**

追加约 40 条中英对照（示意，按实际结构调整）：

```json
// zh
{
  "auth.login": "登录",
  "auth.login_submit": "登录",
  "auth.login_failed": "登录失败，请检查邮箱/密码",
  "auth.register": "注册",
  "auth.email": "邮箱",
  "auth.password": "密码",
  "auth.org_name": "组织名",
  "auth.org_slug": "组织 slug",
  "auth.go_register": "还没账号？去注册",
  "auth.go_login": "已有账号？去登录",
  "auth.logout": "退出登录",

  "apps.title": "应用",
  "apps.create": "新建 App",
  "apps.create_first": "创建第一个 App",
  "apps.create_submit": "创建",
  "apps.created": "App 已创建",
  "apps.name": "名称",
  "apps.slug": "Slug",
  "apps.slug_conflict": "Slug 已被占用",
  "apps.none": "还没有 App",
  "apps.none_create_cta": "去创建 App",

  "keys.title": "API Keys",
  "keys.create": "新建 Key",
  "keys.name": "名称",
  "keys.name_placeholder": "key 名称（如 prod / staging）",
  "keys.prefix": "前缀",
  "keys.status": "状态",
  "keys.last_used": "最近使用",
  "keys.created_once": "Key 已创建 — 仅显示一次",
  "keys.created_warning": "请复制保存此 key，关闭弹窗后将无法再查看",
  "keys.copy": "复制",
  "keys.copied": "已复制",
  "keys.saved_ack": "我已保存",
  "keys.delete_confirm_title": "确认删除 key？",
  "keys.delete_confirm_desc": "外部使用此 key 的客户端会立即失效",
  "keys.manage_hint": "查看和管理 App 下的 API keys",

  "users.title": "External Users",
  "users.external_id": "外部 user_id",
  "users.internal_uuid": "内部 UUID",
  "users.created_at": "创建时间",
  "users.delete_gdpr": "GDPR 删除",
  "users.delete_gdpr_desc": "将删除用户索引（不可逆）；各引擎端数据需另行清理",
  "users.pagination": "第 {page} / {pages} 页，共 {total} 个用户",
  "users.manage_hint": "查看本 App 下所有 external user 映射，GDPR 删除入口",

  "common.loading": "加载中…"
}
```

英文对照版相同 key + 英文翻译。

- [ ] **Step 8.2: Sidebar 加入口**

已在 Task 5 完成。

- [ ] **Step 8.3: server-api-keys-panel 降级到 settings 的 "高级" 分组**

在 settings 页改挂载位置，title 前加 `{t("settings.legacy_bootstrap")}` 区块说明：
"仅当使用 bootstrap key 自举时启用；日常请在各 App 下管理 keys"。

- [ ] **Step 8.4: Lint + test**

```bash
cd ui && npm run lint && npm run test
```

- [ ] **Step 8.5: Commit**

```bash
git add ui/src/lib/i18n ui/src/components/server-api-keys-panel.tsx ui/src/app/\(app\)/settings
git commit -m "feat(ui): Step 7.8 — i18n 补全 + sidebar 整理 + legacy 面板降级"
```

---

### Task 9: API types 重生 + 冒烟

**Files:**
- Modify: `ui/src/lib/api-types.ts`（自动生成）

- [ ] **Step 9.1: 起后端**

```bash
docker compose -f base_runtime/docker-compose.1panel.yml up -d cozymemory
curl http://localhost:8000/api/v1/health
```

- [ ] **Step 9.2: 重生 types**

```bash
cd ui && npm run gen:api
```

修改因 schema 漂移产生的 TS 报错（多半是 ExtUserListResponse 新增）。

- [ ] **Step 9.3: 端到端冒烟**

- 访问 UI → 自动 redirect 到 /login
- 走注册 → 跳 /apps
- 建 App "Demo" / slug "demo"
- 进 Demo → Keys → 建一个 key，弹框里能复制
- 进 Memory 页面，user_id 填 "alice"，新增一条对话，应成功
- 进 users 页，应能看到 alice 的 ext_id → uuid 映射
- 删除 alice → users 页消失

- [ ] **Step 9.4: Commit**

```bash
git add ui/src/lib/api-types.ts
git commit -m "chore(ui): Step 7.9 — regen api-types + 冒烟通过"
```

---

### Task 10: 最终收尾

- [ ] **Step 10.1: 全量测试**

```bash
pytest tests/unit/ -v
cd ui && npm run lint && npm run test && npm run build
```

Expected: 全部 PASS，build 产出无 warning。

- [ ] **Step 10.2: Push**

```bash
git push
```

- [ ] **Step 10.3: 更新 CLAUDE.md**（如有显著变化）

如 `(auth)` 路由组的出现需要提及，更新 `CLAUDE.md` 的 "Frontend" 段落，描述鉴权分流行为。

- [ ] **Step 10.4: 对用户 demo**

列一下接下来可以做的：Knowledge / Backup 路由接入隔离 / RBAC / 邀请 / 计费。

---

## 估时汇总

| Task | 工作量 |
|---|---|
| 1 JWT 中间件 | 2h |
| 2 Users API | 1.5h |
| 3 api.ts 重构 | 1h |
| 4 auth 页 | 2h |
| 5 apps + switcher | 2.5h |
| 6 keys + dialog | 2h |
| 7 users 页 | 1h |
| 8 i18n + legacy | 1h |
| 9 重生 + 冒烟 | 1h |
| 10 收尾 | 0.5h |
| **合计** | **~14.5h** |
