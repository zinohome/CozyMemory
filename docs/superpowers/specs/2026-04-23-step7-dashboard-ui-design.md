# Step 7 — Developer Dashboard UI（方案 C：全局 App 切换）设计

**日期**：2026-04-23
**批次**：batch 17 Phase 2 Step 7
**前置**：Step 1-6（auth / App CRUD / API Key 迁 PG / AppContext / uuid5 映射 / 业务路由 per-App 隔离）已完成

## 目标

为 CozyMemory 构建多租户 Developer Dashboard UI，让 SaaS 客户可以自助注册、创建 App、管理 API Key，
并以"当前 App"维度浏览 memory / profile / context / knowledge 数据。登录后一路 JWT 免粘 key。

## 关键决策

| 主题 | 选择 |
|---|---|
| 凭证流转 | 方案 C：后端加 JWT + `X-Cozy-App-Id` 鉴权通路，UI 业务路由不再依赖 apiKey |
| 注册流程 | 开放注册（任何人可注册 → 自动建 org 成为 owner） |
| 老 bootstrap key | 作 legacy 兜底，settings 页保留"切回 bootstrap"入口 |
| External Users 视图 | 本期做（GDPR 删除入口） |
| i18n | 中英文同步（存量一致性） |
| RBAC 分级 | 不做（本期所有 developer 对 org 下所有 App 同等权限） |

## 架构

### 凭证与鉴权

两种 header 并存，中间件按 header 分流：

| 调用方 | Header | 路径 | 性能影响 |
|---|---|---|---|
| 外部 App（你客户的业务） | `X-Cozy-API-Key` | 走 `ApiKeyStore.verify_and_touch()` | 不变 |
| Dashboard UI | `Authorization: Bearer <JWT>` + `X-Cozy-App-Id` | 新增通路：验 JWT → 查 developer → 校验 app 归属 org | 仅影响低 QPS 的自己人调用 |
| 同时出现两种 header | `X-Cozy-API-Key` 优先 | 兼容外部系统 | — |
| 兜底 | `COZY_API_KEYS` env 配的 bootstrap | 老 admin 视角保留 | — |

中间件行为：
```python
if request has X-Cozy-API-Key:
    走 ApiKeyStore 验证  # 外部 App 既有路径，不动
elif request has Bearer token:
    decode JWT -> developer_id
    if X-Cozy-App-Id:
        verify app.org_id == developer.org_id  # 跨 org → 404 防枚举
        inject request.state.app_id = app_id
        inject request.state.api_key_id = None
elif bootstrap key in env:
    legacy admin 模式
else:
    401
```

### 路由结构

```
ui/src/app/
├── (auth)/                      ← 新增，无 sidebar
│   ├── layout.tsx               居中卡片
│   ├── login/page.tsx
│   └── register/page.tsx
├── (app)/                       ← 已有，加 AuthGuard + AppSwitcher
│   ├── layout.tsx               顶栏加 AppSwitcher + 头像菜单（email / 退出）
│   ├── apps/                    ← 新增
│   │   ├── page.tsx                    App 列表 + 新建
│   │   └── [id]/
│   │       ├── page.tsx                App 概览 + 改名/删除
│   │       ├── keys/page.tsx           Key 管理
│   │       └── users/page.tsx          External Users（分页 + GDPR 删除）
│   └── ...（现有页面不改业务逻辑）
└── middleware.ts                ← 新增，无 JWT → redirect /login
```

### 状态与数据流

Zustand store 新增：
```ts
jwt: string;          // persist
currentAppId: string; // persist
currentAppSlug: string;
// apiKey 字段保留给 bootstrap legacy 模式
```

TanStack Query 管 dashboard server state：
```
['apps']                    → 列表
['apps', id]                → 详情
['apps', id, 'keys']        → keys
['apps', id, 'users', page] → users 分页
```

### 凭证流转时序

```
用户登录 → POST /api/v1/auth/login → {jwt}
      → store.setJwt(jwt) → redirect /apps
      → useApps() 拉列表
         ├ 空 → 引导创建第一个 App
         └ 有 → 选中持久化的 currentAppId（若仍在列表）或列表第一个
      ↓
用户点业务页（memory/profile/...）
      → apiFetch(path, { scoped: true })
      → 自动带 Authorization: Bearer + X-Cozy-App-Id
      → 后端中间件验 JWT + app 归属 → inject app_id
      → 业务路由 scope_user_id() → uuid5 隔离
```

## 组件

| 组件 | 路径 | 职责 |
|---|---|---|
| `AuthGuard` | `components/auth-guard.tsx` | 无 JWT → redirect `/login` |
| `AppSwitcher` | `components/app-switcher.tsx` | 顶栏下拉：App 列表 + 新建；空时跳 `/apps` 引导 |
| `UserMenu` | `components/user-menu.tsx` | 头像 + email + 退出登录 |
| `LoginForm` / `RegisterForm` | `components/auth/*.tsx` | BaseUI 表单 + Zod 校验 |
| `CreateAppDialog` | `components/create-app-dialog.tsx` | name + slug，slug 冲突显示错误 |
| `ApiKeyCreatedDialog` | `components/api-key-created-dialog.tsx` | 一次性明文 + 复制 + "我已保存" |
| `RotateKeyDialog` / `DeleteKeyConfirm` | `components/*.tsx` | 危险操作二次确认 |
| `DeleteUserConfirm` | `components/delete-user-confirm.tsx` | GDPR 删除确认 + "此操作不可逆" |

## 后端新增工作

1. **JWT + AppId 中间件分支**（`src/cozymemory/auth/middleware.py` 扩展）
2. **`AppContext` 允许 `api_key_id=None`**（JWT 模式）
3. **Dashboard users 路由**（`src/cozymemory/api/v1/dashboard/users.py` 新建）：
   - `GET /api/v1/dashboard/apps/{id}/users?limit&offset` → `UserResolver.list_for_app` + `count_for_app`
   - `DELETE /api/v1/dashboard/apps/{id}/users/{ext_id}` → `UserResolver.delete`（GDPR 仅删索引，引擎数据由上层服务另做）
4. **i18n**：后端错误消息键化（若已有则跳过）

## 前端新增工作

1. **`ui/src/lib/api.ts` 重构**：`apiFetch(path, { scoped?: boolean })` + `dashboardFetch(path)`
   - `scoped: true` → 加 `X-Cozy-App-Id`
   - 401 → 清 JWT + redirect `/login`
2. **`ui/src/middleware.ts`**：`(app)/*` 路径无 JWT cookie/持久化 → redirect
3. **Zustand 扩展** + `getJwt()` / `getCurrentAppId()` 非 hook 访问
4. **新页面 5 个**（register / login / apps / apps/[id] / apps/[id]/keys / apps/[id]/users）
5. **Layout 改造**：顶栏 AppSwitcher + UserMenu；`(app)/layout.tsx` 包 AuthGuard
6. **Sidebar 调整**：加"Apps 管理"入口；老 `server-api-keys-panel.tsx` 移入 settings "高级 / legacy" 分组
7. **i18n 新键 ~40 条**（中英文同步）
8. **API types 重生**：`npm run gen:api` 保持 `ui/src/lib/api-types.ts` 最新

## 测试

### 后端

**`tests/unit/test_jwt_auth_middleware.py`（新，6 用例）**
- `Bearer + X-Cozy-App-Id` 合法 → 业务路由 200，service 收到 uuid5
- `Bearer + X-Cozy-App-Id` 跨 org → 404（防枚举）
- `Bearer` 缺 `X-Cozy-App-Id` 调业务路由 → 400
- JWT 过期 → 401
- JWT 签名伪造 → 401
- `X-Cozy-API-Key` 和 `Bearer` 同时存在 → X-Cozy-API-Key 优先

**`tests/unit/test_dashboard_users_api.py`（新，4 用例）**
- 列表分页
- 跨 app 不可见
- 删除 → 列表消失
- count 与实际一致

### 前端

**`ui/src/lib/__tests__/api.test.ts` 扩展**
- `scoped: true` → 同时发 Authorization + X-Cozy-App-Id
- 401 → 清 JWT + redirect（mock `window.location`）

**`ui/src/components/__tests__/app-switcher.test.tsx`（新）**
- 空 apps → 显示 CTA
- 持久化 currentAppId 仍存在 → 保留选中
- 切换 App → `store.currentAppId` 更新

**`ui/src/app/__tests__/apps-page.test.tsx`（新）**
- 建 App 成功 → invalidate + toast
- slug 冲突 → 409 → 表单错误

### E2E

不做（现有 UI 本身无 e2e，本期不推）。

## 实施顺序

```
1. 后端：JWT + AppId 中间件分支（TDD）
2. 后端：AppContext 支持 api_key_id=None
3. 后端：dashboard users 路由 + 测试
4. 前端：api.ts 重构 + Zustand 扩展 + middleware.ts
5. 前端：(auth) 路由 + 登录/注册页 + AuthGuard
6. 前端：Apps 列表 + AppSwitcher + CreateAppDialog
7. 前端：App 详情 + keys 页 + ApiKeyCreatedDialog / Rotate / Delete
8. 前端：users 页（分页 + GDPR 删除确认）
9. 前端：i18n 补全 + sidebar 整理 + server-api-keys-panel 降级
10. 冒烟：起后端 + UI，跑 注册 → 建 App → 建 Key → memory 读写 / profile / context / users 删除
11. commit + push
```

## 估时

1-2 天：后端半天，前端一天，联调半天。

## 非目标

- RBAC 分级（owner/admin/member）
- 邀请流程
- Knowledge / Backup 路由接入 per-App 隔离（下期）
- Playwright e2e
- 计费 / 限流 / 用量统计
