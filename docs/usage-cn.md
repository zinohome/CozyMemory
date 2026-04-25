# CozyMemory 使用说明

> 面向第一次上手的用户，教你在 10 分钟内完成部署验证、创建 App、用 Playground
> 聊一轮带记忆的对话。

## 双角色模型

CozyMemory v0.2.0 有两类使用者：

| 角色 | 身份 | UI 入口 | 鉴权方式 |
|------|------|---------|----------|
| **Developer** | 应用开发者 | `/login` → `/apps` | 注册账号 → JWT 登录 |
| **Operator** | 平台运维 | `/operator` | Bootstrap key（env `COZY_API_KEYS`） |

- **Developer**：自助注册，管理自己 org 下的 App / Key / External Users；所有业务数据按 App 隔离
- **Operator**：平台管理员，跨 org 只读、全局维护、备份恢复

---

## 快速开始

**前置**：base_runtime 已启动（15 个容器），管理 UI 地址 `http://你的服务器IP:8088`。

### Developer 快速上手（5 步）

#### 第 1 步 — 注册开发者账号

1. 访问 `http://你的IP:8088/login`
2. 点 "注册"，填写邮箱和密码
3. 注册成功后自动登录，进入 Apps 页面

#### 第 2 步 — 创建 App

1. 在 **Apps** 页面点 "Create App"
2. 填写 App 名称（如 `my-chatbot`）
3. 创建成功后点击 App 卡片进入工作台

#### 第 3 步 — 创建 App Key

1. 在 App 工作台进入 **Keys** 子页
2. 点 "Create Key"，填写描述
3. **重要**：Key 只展示一次，立即复制保存！
4. 这个 Key 用于 SDK / API 调用时的 `X-Cozy-API-Key` header

#### 第 4 步 — 去 Playground 聊一句

1. 在 App 工作台进入 **Playground** 子页
2. 输入一个 User ID（如 `alice`），点 "Use"
3. 输入 "我喜欢读科幻小说"，回车
4. 等待 LLM 回复（流式输出）
5. 回到 **Memory** 子页，选 `alice`，点 "Load" → 能看到 Mem0 抽取出来的记忆

#### 第 5 步 — 查看画像和知识图谱

1. **Profiles** 子页：选 `alice` → Load → 查看 Memobase 生成的结构化画像
2. **Knowledge** 子页：创建数据集 → 添加文档 → Cognify → 搜索
3. **Context** 子页：一次性看三引擎返回的统一上下文

做完这五步，三引擎就都跑通了。

### Operator 快速上手

1. 访问 `http://你的IP:8088/operator`
2. 输入 Bootstrap key（`base_runtime/.env` 里的 `COZY_API_KEYS`，默认 `cozy-dev-key-001`）
3. 进入 Operator Dashboard，可以看到三引擎健康状态

> Bootstrap key 存在 sessionStorage，关闭浏览器自动清除。

---

## 架构速览

```
浏览器
  ├── /login → JWT 登录 → Developer 工作台
  │     └── /apps/[id]/* → Memory / Profiles / Knowledge / Context / Playground
  └── /operator → Bootstrap key → Operator 管理台
         └── Dashboard / Orgs / Memory-raw / Profiles-raw / Knowledge-raw / ...

         ↓ /api/v1/*

CozyMemory FastAPI 统一入口（:8000）+ gRPC（:50051）
  ├── /conversations   → Mem0（对话记忆）
  ├── /profiles        → Memobase（结构化画像）
  ├── /knowledge       → Cognee（知识图谱）
  ├── /context         → 三引擎并发编排
  ├── /auth/*          → Developer 注册/登录
  ├── /dashboard/*     → App/Key/User 管理
  └── /operator/*      → 跨 org 维护
```

三引擎的关系：
- **Mem0（对话记忆）**：记住用户"说过什么"，基于最近对话抽取事实
- **Memobase（结构化画像）**：提炼用户"是什么样的人"，按 topic/sub_topic 分类
- **Cognee（知识图谱）**：用户投喂的**文档**变成实体 + 关系的图
- **Context（统一上下文）**：一次性从上面三个并发取数据，给 LLM 做 system prompt 增强

---

## Developer 页面详解

### Apps — 应用列表

**作用**：管理你名下的所有 App。每个 App 有独立的 Key 和数据隔离。

**典型使用**：
- 创建新 App（一个 App 对应一个产品/项目）
- 点击 App 卡片进入工作台
- 在工作台里切换 Memory / Profiles / Knowledge / Context / Playground 子页

### Keys — App Key 管理

**作用**：为当前 App 创建 / 吊销 API Key。

**典型使用**：
- Create：生成新 Key（只展示一次！）
- Key 用于 SDK / 第三方集成的 `X-Cozy-API-Key` header
- 发现泄漏立即删除，创建新 Key

### External Users — 外部用户管理

**作用**：查看当前 App 下的所有外部用户（由 API 调用自动创建）。

**典型使用**：
- 分页浏览所有用户
- GDPR 合规删除：删除用户及其在三引擎的所有数据

### 💬 Memory — 对话记忆浏览

**作用**：浏览、搜索、删除 Mem0 抽取的对话记忆（"用户说过什么"）。

**典型使用**：
1. 选一个 user_id，点 "Load" → 列出该用户的所有记忆
2. 语义搜索框输入关键词 → 向量搜索
3. 每条记忆右侧的 trash 按钮立即删除

**字段说明**：
- **content**：Mem0 从原始对话里提取出来的事实陈述
- **id**：记忆的主键
- **created_at**：记忆写入时间

**常见坑**：
- 记忆不是"原始对话"，是**抽取出来的事实**
- Mem0 的抽取有随机性，同样的话多跑几次结果不完全一样

### 🎭 Profiles — 结构化画像

**作用**：查看 / 编辑 Memobase 为每个用户构建的结构化画像。

**典型使用**：
1. 选 user_id，点 "Load"
2. **Context Prompt**：Memobase 自动生成的 LLM-ready prompt 文本
3. **Profile Items**：按 topic/sub_topic 分类的画像条目
4. **Add item**：手动补画像条目（topic/sub_topic/content）

**常见坑**：
- 画像不是立刻生成的：对话写入 → buffer 处理 → 出现在 Profile
- 可通过 `POST /profiles/flush` 触发立即处理

### 📚 Knowledge — 知识图谱

**作用**：把文档投喂给 Cognee，生成知识图谱，做图检索。

**典型使用**：
1. 创建数据集
2. 添加文档到数据集
3. 点 "Cognify" 触发知识图谱构建（可能需要几秒到几分钟）
4. 搜索：选 search type（CHUNKS / SUMMARIES / RAG_COMPLETION / GRAPH_COMPLETION）
5. Graph 标签：力导向图可视化

**常见坑**：
- **Add 完不 Cognify，Search 会报 NoDataError**：两步流程，别漏
- **Cognify 慢**：大文档 1-5 分钟正常

### ✨ Context — 统一上下文调试

**作用**：调试 `/api/v1/context` 的并发编排。

**典型使用**：
1. 选 user_id，填 query
2. 勾选要包含的引擎
3. 调参数：conversation_limit、knowledge_top_k 等
4. Fetch context → Tab 切换看每个引擎返回了什么

### 🎨 Playground — 带记忆的 LLM 对话

**作用**：体验完整的"记忆增强对话"——每轮自动拉三引擎上下文注入 system prompt。

**典型使用**：
1. 选 user_id，点 "Use"
2. 调参（Model / Temperature / Max tokens / System prompt）
3. 输入消息 → 流式输出
4. 右侧面板查看 "Last context injected"——LLM 实际看到了什么

**常见坑**：
- 首次聊天前要先选 user，否则 Send 按钮 disabled
- 会话存 localStorage（最多 20 条），左上角 "Load session" 切换

---

## Operator 页面详解

### Dashboard — 首页监控

**作用**：三引擎健康 + 延迟/增长 sparkline。

**关键区块**：
- **Engine Health**：Mem0 / Memobase / Cognee 连通性实时检查
- **Observability sparklines**：10m / 1h / 6h 窗口切换

### Orgs — 跨组织总览

**作用**：查看平台上所有组织和开发者。

### Memory-raw / Profiles-raw / Knowledge-raw

**作用**：全局裸数据浏览，不受 App 隔离限制。用于运维排查。

### Backup — 备份恢复

**作用**：单用户维度的 JSON 备份 + 恢复。

**典型使用**：
- **Export**：选 user_id → 勾选引擎 → 下载 JSON
- **Import**：选 JSON 文件 → 选目标 user_id → 恢复

**常见坑**：
- 恢复不会清现有数据，是合并（新增）
- 知识图谱恢复是"重新 cognify"，实体/边可能略有差异

### Health — 引擎详细状态

**作用**：比 Dashboard 更详细的引擎健康信息。

### Settings — 全局设置

**作用**：Bootstrap key 管理 + 审计日志。

---

## SDK 使用

### Python

```bash
pip install cozymemory
```

```python
from cozymemory import CozyMemoryClient

with CozyMemoryClient(api_key="你的App Key", base_url="http://localhost:8000") as c:
    # 添加对话记忆
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])

    # 语义搜索
    results = c.conversations.search("alice", "outdoor activity")

    # 获取统一上下文
    ctx = c.context.get_unified("alice", query="outdoor activity")
```

### JavaScript / TypeScript

```bash
npm install @cozymemory/sdk
```

```typescript
import { CozyMemory } from '@cozymemory/sdk';

const client = new CozyMemory({
  apiKey: '你的App Key',
  baseUrl: 'http://localhost:8000',
});

// 添加对话记忆
await client.conversations.add('alice', [{ role: 'user', content: 'I love hiking' }]);

// 语义搜索
const results = await client.conversations.search('alice', 'outdoor activity');
```

---

## API 鉴权说明

| 场景 | Header | 值 |
|------|--------|----|
| SDK / 第三方集成 | `X-Cozy-API-Key` | App Key |
| Developer UI 业务调用 | `Authorization` + `X-Cozy-App-Id` | JWT + App ID |
| Operator 管理 | `X-Cozy-API-Key` | Bootstrap key |

免鉴权端点：`/health`、`/docs`、`/openapi.json`

---

## FAQ

### Q: Developer 和 Operator 有什么区别？
A: Developer 是应用开发者，通过 JWT 登录管理自己的 App 和数据；Operator 是平台管理员，用 Bootstrap key 做跨组织的运维管理。

### Q: Memory / Profile / Knowledge 有什么区别？
| | 存什么 | 谁写入 | 怎么用 |
|---|---|---|---|
| **Memory (Mem0)** | 对话里抽取的事实 | 对话自动写 | 聊天时拉历史 |
| **Profile (Memobase)** | 用户画像（topic 分类） | 自动从对话提炼 | LLM system prompt |
| **Knowledge (Cognee)** | 文档的实体 + 关系图 | 手动 add + cognify | 问答时查图 |

### Q: 为什么 Playground 回答没有记住我之前说的？
A: 可能原因：
1. Mem0 还没抽取完（对话后 1-2 秒）
2. user_id 不一致（重新聊选了别的 user）
3. 去 Context 子页看能不能拉到 conversations

### Q: Cognee Cognify 卡住了怎么办？
A:
1. 稍等（大文档 1-5 分钟正常）
2. 看 Dashboard Engine Health，Cognee 是不是红
3. 看后端日志：`docker logs cozy_cognee`

### Q: 快捷键有哪些？
A: 按 `?` 弹出帮助。Gmail 风格快捷键：
- `g d` → Dashboard、`g m` → Memory、`g p` → Profiles
- `g k` → Knowledge、`g c` → Context、`g l` → Playground

聚焦在输入框时快捷键自动禁用。

---

## 可观测性

- **Prometheus**：`/metrics` 端点暴露引擎延迟/错误/用量指标
- **Grafana**：`http://你的IP:3001` 预置 dashboard
- **告警规则**：EngineDown / HighLatency / HighErrorRate / APIDown
- **OpenTelemetry**：安装 `pip install cozymemory[otel]` + 设置 `OTEL_ENABLED=true`

---

## 开发者提示

- **API 文档**：`http://你的IP:8000/docs`（Swagger UI）
- **OpenAPI schema**：`http://你的IP:8000/openapi.json`
- **UI 源码**：仓库 `ui/` 目录，Next.js 16 App Router
- **后端源码**：仓库 `src/cozymemory/`，FastAPI + httpx + gRPC
- **架构详情**：`CLAUDE.md` 里有引擎 API quirks 和约定
- **许可证**：AGPL-3.0-or-later
