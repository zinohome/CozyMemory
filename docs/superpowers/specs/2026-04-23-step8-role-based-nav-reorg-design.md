# Step 8 — 角色化导航重组（Developer / Operator 双视角）设计

**日期**：2026-04-23
**批次**：batch 17 Phase 2 Step 8
**前置**：Step 7 交付 Developer Dashboard 后发现老 admin 页污染了多租户数据（详见 root cause）

## 背景与问题

Step 7 把 AppSwitcher 加到全局顶栏，让所有页面共享"当前 App"状态。但 sidebar 里 `/dashboard`、`/memory`、`/profiles`、`/users` 等页面是多租户之前的 **全局 admin 视图**，它们基于 Mem0/Memobase 全局 user_id 池工作。

带 AppSwitcher 后，这些页面发出的 `apiFetch(scoped: true)` 会带 `X-Cozy-App-Id`，后端 Step 6 的 `scope_user_id()` 对每个全局 user_id 做 `uuid5(app.ns, uid) + upsert external_users`，**把全局 id "认领"到任意 App 名下，污染租户隔离**。

实例：创建 SelfCEO App 38 秒后有 34 条历史全局 user_id 被错误 upsert 到 SelfCEO 下。

根源：**页面定位没有角色区分**。

## 两类用户

| 角色 | 凭证 | 视角 | 数据边界 |
|---|---|---|---|
| **Platform Operator** | bootstrap key（env `COZY_API_KEYS`）| 全平台 ops / admin | 一切：跨 org，全局 Mem0/Memobase 池 |
| **Developer** | JWT 登录 | 自己 org 下的 Apps | 必须通过某个 App 才能访问业务数据 |

## 目标路由结构

### Developer 视角（JWT 登录）

```
/apps                        应用列表（默认首页）
/apps/[id]/                  App 工作台（新 layout，下辖子路由）
  ├── page.tsx               概览：统计 + 最近活动
  ├── keys/                  API Keys 管理
  ├── users/                 External Users（uuid5 映射表）
  ├── memory/                对话记忆（搬自 /memory）
  ├── profiles/              用户画像（搬自 /profiles）
  ├── knowledge/             知识库（搬自 /knowledge）
  ├── context/               上下文调试（搬自 /context）
  └── playground/            对话沙盒（搬自 /playground）
/settings                    账号设置（只含个人资料 / 修改密码 / org 信息）
/login, /register            公开（不变）
```

顶栏：AppSwitcher + UserMenu（已有）。
Sidebar：按 App 工作台展开 —— 只有选中 App 后 sidebar 才显示 App 子项。

### Operator 视角（bootstrap key，不登录）

```
/operator/                   入口（要求 X-Cozy-API-Key = bootstrap）
  ├── orgs/                  所有 Org + Developer 总览（新实现）
  ├── users-mapping/         旧 User Mapping（搬自 /users）
  ├── memory-raw/            全局 Memory 浏览（搬自 /memory）
  ├── profiles-raw/          全局画像（搬自 /profiles）
  ├── knowledge-raw/         全局 Knowledge（搬自 /knowledge）
  ├── health/                引擎健康 + Metrics（搬自 /dashboard 的一部分）
  └── backup/                全局备份/恢复（搬自 /backup）
/settings/legacy             legacy bootstrap keys 面板（搬自现 settings 的降级区）
```

Operator 页面统一使用 `apiFetch({ scoped: false })` → 不发 `X-Cozy-App-Id`。

### 已删除的路由

| 老路径 | 去向 | 原因 |
|---|---|---|
| `/dashboard` | 删除 | 老 admin 首页，意义被 `/apps` 取代 |
| `/memory` | → `/apps/[id]/memory` + `/operator/memory-raw` | 分裂成两角色版本 |
| `/profiles` | 同上 | 同上 |
| `/knowledge` | 同上 | 同上 |
| `/context` | → `/apps/[id]/context` | 仅 App scope（上下文调试天然属于某 App）|
| `/playground` | → `/apps/[id]/playground` | 同上 |
| `/users` | → `/operator/users-mapping` | 全局映射是 ops 工具 |
| `/backup` | → `/operator/backup` | 同上 |

## 后端改动

### 中间件强化（app.py `require_api_key`）

当前：`Bearer + 无 AppId → ok = True, developer_id 注入` —— 宽松放行。

**新**：业务路由（`/conversations`, `/profiles`, `/context`, `/knowledge`）对 Bearer 分支强制要求 AppId：

```python
elif authorization.startswith("Bearer "):
    ...
    if app_id_hdr:
        # ok + 注入
    else:
        # 如果请求走的是 /auth/* 或 /dashboard/* 允许（这两个本来就
        # 被 _AUTH_EXEMPT_PREFIXES 或业务语义豁免）；其他路径 → 403
        path = request.url.path
        if path.startswith("/api/v1/operator") or path.startswith("/api/v1/auth"):
            ok = True  # operator 和 auth 不要 AppId
        else:
            ok = False  # Bearer 调业务路由却没 AppId → 403
```

### 新增 Operator 路由命名空间

新建 `src/cozymemory/api/v1/operator/`（包），所有旧 admin 路由搬过来，挂在 `/api/v1/operator/*` 前缀下：

- 中间件对 `/api/v1/operator/*` 的规则：**只接受 bootstrap key**（env 里的），拒绝 Bearer JWT（403）
- 老的 `/api/v1/users`、`/api/v1/backup` 等 legacy 路径保留向后兼容（仍只允许 bootstrap key），但文档标为 deprecated

### 已废弃的业务路由调用

Step 6 的 `scope_user_id(app_ctx, user_id)` 逻辑保持不变。但现在保证：
- Bearer 必带 AppId → `scope_user_id` 总能命中 uuid5 路径
- bootstrap key → `scope_user_id` 走 passthrough（不变）
- 没有"Bearer 无 AppId 调业务路由"的灰色地带

## 前端改动

### 1. Layout 分叉

`(app)` layout 保留，用于 Developer。

新增 `(operator)` layout（与 `(app)` 并列，不共享 AppSwitcher）：
- 自己的 sidebar（仅 operator 条目）
- 顶栏只显示 "Operator Mode" + 登出 bootstrap
- 不走 AuthGuard，走 `OperatorGuard`（检查 apiKey 非空且匹配 bootstrap 形态）

Settings 的 "legacy bootstrap keys" 块（Step 7.8 加的）**搬到 `/operator/settings/legacy`**；Developer settings 页面不再有它。

### 2. `/apps/[id]/` 子路由

新建 `ui/src/app/(app)/apps/[id]/layout.tsx`：
- 顶栏集成 AppSwitcher（已在）
- 左 sidebar 显示 App 工作台菜单（Overview / Keys / Users / Memory / Profiles / Knowledge / Context / Playground）
- 当前全局 `AppSidebar` 组件拆分：App 工作台用新的 `AppWorkspaceSidebar`

现有老页面组件（如 `user-selector.tsx`、conversation 列表组件）直接复用，**父路由切到 `/apps/[id]/memory` 后它们自动继承 currentAppId**；不用改内部逻辑。

### 3. 登录后默认路径

登录后 `router.replace("/apps")`（不变）。

未选 App 时访问 `/apps/[id]/*` 子路由 → 404（不可能，因为 id 从路由取）。

### 4. Operator 进入方式

- UI 顶部加一个"切换到 Operator 模式"入口，只在 apiKey 为 bootstrap 且当前是 Developer 视角时显示
- 点击后跳 `/operator`，读 `apiKey` Zustand 作为鉴权

或更严格：`/operator` 要求用户**手动重新输入 bootstrap key**，不从 Zustand 沿用（避免粘贴泄漏）。**采取后者**——安全更稳。

## 测试

### 后端

新增 `tests/unit/test_role_separation.py`：
- Bearer 无 AppId 调 `/conversations` POST → 403
- Bearer 无 AppId 调 `/dashboard/apps` → 200（exempt）
- Bearer + AppId 调 `/operator/*` → 403（dev 不能进 operator）
- Bootstrap key 调 `/operator/*` → 200
- Bootstrap key 调 `/apps/[id]/memory` 对应后端路由 → 200（仍能看任意 App 数据，admin 权限）
- Bootstrap key 调带 X-Cozy-App-Id 的业务路由 → 优先 bootstrap（忽略 AppId，保留 passthrough 语义）

### 前端

- `app-workspace-sidebar.test.tsx`：验证 selected App 下 7 个子项可点
- `operator-guard.test.tsx`：无 bootstrap → redirect 首页
- E2E 手测清单（README）：
  - Developer 登录 → 建 App → 进 Memory 加一条记忆 → External Users 增加 1 条 → 切另一 App → Memory 空
  - 切 Operator → 看到全局 old data，切回 Developer 看不到

## 数据迁移 & 清理

**老数据**（pre-multi-tenant 的 Mem0/Memobase user_id 池）：
- **保留**，只对 Operator 可见
- 不做自动归并到 Apps —— 那会错误地给老数据分配 namespace
- 文档里说明：迁移到 per-App 模式需要客户侧重新走 `POST /conversations`（这会触发 uuid5 upsert 到正确 App）

**本次脏数据**（34 条被 Step 7 错误认领的）：
- 已在 spec 决策前手动删除（SQL DELETE）
- 正式实施时加一次性 migration script：扫 external_users，删掉 external_user_id 本身是 UUID v4 格式且 app 创建时间 > 客户首次调用时间的记录（或者干脆让 Operator 在 UI 上主动 review/清理）

## 实施顺序

1. 后端：中间件分流强化 + operator 路由命名空间 + 路由搬迁 + 测试
2. 前端：operator layout + 新路由 + App workspace layout
3. 前端：`/apps/[id]/memory`、`profiles`、`knowledge`、`context`、`playground` 各自的 page.tsx（实际是把老 page.tsx 搬路径，内部组件不改）
4. 前端：老路径删除 + redirect shim（老链接跳到新路径）
5. i18n：新导航结构相关 key 补齐
6. 文档：更新 CLAUDE.md 说明角色模型
7. 冒烟 + commit + push

## 估时

1.5-2 天：
- 后端 3h（中间件 + 路由迁移测试）
- 前端 layout 分叉 4h
- 页面搬迁 3h（多是机械改路径）
- 删 legacy + redirect + i18n 2h
- 冒烟 + 文档 2h

## 非目标

- Operator 的 Org/Dev 管理 UI（dev 账号禁用、切换 owner 等）—— 后续做
- Developer 内的多 dev 权限分级（owner / member）
- 老 global 数据批量迁到某 App 的 UI 工具（Operator 想做自己写 SQL）
- 计费 / 配额 / 限流

## 待决点（请 review）

1. **登录后默认路径** —— 现在是 `/apps`；如果 Developer 只有一个 App，是否自动跳进去 `/apps/[id]/memory`？（建议：否，保持 `/apps` 作为明确落地页）
2. **Operator 进入方式** —— 是从 Developer 顶栏点切换（Zustand 沿用 apiKey），还是独立 URL + 手动输 key？（spec 里选了手动输，更安全）
3. **老 `/api/v1/users`、`/api/v1/backup` 后端路径** —— 删除还是保留 deprecated？（建议：保留 deprecated 6 个月，给客户迁移时间）
4. **`/apps/[id]/knowledge`** —— Knowledge 的 dataset 本来是跨 user 的，是否按 App 隔离？（Step 6 没接入，这步要决定：方案 A 加 app_id 列到 datasets 表；方案 B 让 App 和 dataset 多对多映射）—— **如果现在不想处理 Knowledge 隔离，就先把页面移过去但依然用全局 API（留 FIXME），Step 9 再做**
