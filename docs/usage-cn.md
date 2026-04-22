# CozyMemory UI 使用说明

> 面向第一次上手的用户，教你在 10 分钟内看到 Dashboard 有数据、用 Playground
> 聊一轮带记忆的对话。

## 快速开始（3 步）

**前置**：base_runtime 已启动（14 个容器），UI 访问地址形如
`http://你的服务器IP:8088`。

### 第 1 步 — 填 Client API Key（解决 401）

后端默认开启了 API Key 鉴权（由 `base_runtime/.env` 里的 `COZY_API_KEYS`
控制，默认两把开发 key：`cozy-dev-key-001`、`cozy-dev-key-002`）。
UI 所有请求都要带 `X-Cozy-API-Key` header。首次访问 UI 控制台会看到一堆
401 错误——这是正常的，填了 key 就消失。

1. 打开 **Settings** 页（左侧导航最下方）
2. 最上面 "Client API Key" 卡片，粘贴 `cozy-dev-key-001`
3. 点 "Save"
4. 刷新页面 → 401 全部消失，Dashboard 开始有数据

> 提示：key 存在浏览器 localStorage，只在当前浏览器生效，换浏览器/清 cache
> 要重新填。

### 第 2 步 — 创建第一个用户

1. 打开 **Users** 页
2. "Create UUID Mapping" 卡片填一个 user_id（例如 `alice`）
3. 点 "Create" → 系统生成对应的 UUID v4，关系存入 Redis
4. 这个 user_id 之后在所有页面都能用

> 为什么要这步：Memobase 画像引擎强制要求 user_id 是 UUID v4 格式。
> CozyMemory 在 Redis 里维护了一层 `任意字符串 user_id ↔ UUID v4` 的
> 透明映射，你用 `alice` 就行，背后自动换成 UUID。

### 第 3 步 — 去 Playground 聊一句

1. 打开 **Playground** 页
2. 顶部 User ID 下拉选 `alice`（刚创建的），点 "Use"
3. 在下方输入框里输入 "我喜欢读科幻小说"，回车
4. 等 LLM 回复
5. 回到 **Memory Lab**，选 `alice`，点 "Load" → 能看到 Mem0 抽取出来的
   一条记忆

做完这三步，三引擎就都跑通了。下面按每页讲怎么深入使用。

---

## 架构速览

```
浏览器
  ↓ /api/v1/*  (X-Cozy-API-Key)
CozyMemory FastAPI 统一入口（:8000）
  ├── /conversations   → Mem0（对话记忆）
  ├── /profiles        → Memobase（结构化画像）
  ├── /knowledge       → Cognee（知识图谱）
  └── /context         → 三引擎并发编排
```

三引擎的关系：
- **Mem0（对话记忆）**：记住用户"说过什么"，基于最近对话抽取事实
- **Memobase（结构化画像）**：提炼用户"是什么样的人"，按 topic/sub_topic 分类
- **Cognee（知识图谱）**：用户投喂的**文档**变成实体 + 关系的图
- **Context（统一上下文）**：一次性从上面三个并发取数据，给 LLM 做 system prompt 增强

---

## 页面详解

### 🏠 Dashboard — 首页监控

**作用**：一眼看到三引擎健康 + 用户数 + 数据集数 + 延迟/增长趋势。

**关键区块**：
- **Engine Health**：三个引擎（Mem0 / Memobase / Cognee）连通性实时检查，红色表示后端不可达
- **Users / Knowledge Datasets**：系统当前规模
- **Observability sparklines**：10m / 1h / 6h 窗口切换，客户端轮询（10 秒一次）累积的时序数据；值显示为空白段表示那时服务不可达

**典型使用**：
- 部署完第一件事来这里看三引擎是不是都绿
- 日常巡检：延迟突增或稀疏空白 = 有服务抖动

**常见坑**：
- sparkline 数据存在 localStorage，换浏览器就从零开始累积
- `MetricsPoller` 在后台页面也跑，切走页面也继续累积

---

### 👤 Users — 用户 ID 映射管理

**作用**：管理 `任意字符串 user_id ↔ UUID v4` 的 Redis 映射表。

**典型使用**：
- **创建映射**：Create UUID Mapping 卡片填 user_id → 生成 UUID
- **查询**：表格列出所有 user_id + 对应 UUID，点复制按钮拷 UUID
- **过滤**：搜索框按 user_id 实时缩列
- **删除**：每行 trash 按钮；双击确认（Yes/No），删除后 Memobase 画像变成孤儿数据（UUID 还在，但 UI 访问不到）

**字段说明**：
- **User ID**：你用的字符串（`alice`、`user_01`），CozyMemory 层的身份
- **UUID v4**：自动生成的 Memobase 内部 ID，你不用关心

**常见坑**：
- Profile 相关 API 首次调用会**自动创建**映射，不一定非要先来这里手动建
- 删映射不会删 Mem0 / Cognee 里该用户的数据，那些按 user_id 索引

---

### 💬 Memory Lab — 对话记忆浏览

**作用**：浏览、搜索、删除 Mem0 抽取的对话记忆（"用户说过什么"）。

**典型使用**：
1. 顶部选一个 user_id，点 "Load" → 列出该用户的所有记忆
2. 语义搜索框输入关键词 → 在该用户的记忆里做向量搜索
3. 每条记忆右侧的 trash 按钮立即删除（乐观更新 + toast）

**字段说明**：
- **content**：Mem0 从原始对话里提取出来的事实陈述，例如 "用户喜欢科幻小说"
- **id**：记忆的主键（Mem0 内部）
- **created_at**：记忆写入时间

**常见坑**：
- 记忆不是"原始对话"，是**抽取出来的事实**，一轮 5 句对话可能只产生 1-2 条
- Mem0 的抽取有随机性，同样的话多跑几次结果不完全一样

---

### 🎭 User Profiles — 结构化画像

**作用**：看 / 改 Memobase 为每个用户构建的结构化画像（"这个人是什么样的"）。

**典型使用**：
1. 选 user_id，点 "Load"
2. **Context Prompt 卡片**：Memobase 自动生成的 LLM-ready prompt 文本，
   直接能塞进 system prompt
3. **Profile Items 列表**：按 topic/sub_topic 分类的细粒度画像条目
4. **Add item**：手动补画像条目（topic/sub_topic/content 三字段）

**字段说明**：
- **topic**：大类，如 `interest`、`demographic`、`skill`
- **sub_topic**：小类，如 `hobby`、`age`、`programming_language`
- **content**：具体内容，如 `reads sci-fi novels`

**常见坑**：
- 画像不是立刻生成的：Mem0 写入 → Memobase 后台 buffer 处理 → 才出现
  在 Profile。可通过 `POST /profiles/flush` 触发立即处理
- 删除 topic 只删这一条，不影响其他

---

### 📚 Knowledge Base — 知识图谱

**作用**：把文档投喂给 Cognee，生成实体 + 关系的知识图谱，做图检索。

**典型使用**：
1. **Datasets 标签**：创建数据集（点 "+ New dataset"）、重命名、删除
2. **Add 标签**：选数据集 → 粘贴文本 → "Add" 把文档塞进 staging
3. **Cognify**：点数据集旁的 "Cognify" 按钮触发**知识图谱构建**（实体抽取 + 关系 + 嵌入），耗时可能几秒到几分钟
4. **Search 标签**：选数据集 + 选 search type + 输入查询
   - **CHUNKS**：返回原始文本块
   - **SUMMARIES**：返回段落摘要
   - **RAG_COMPLETION**：LLM 基于检索到的上下文生成回答
   - **GRAPH_COMPLETION**：沿图谱关系走，给出带推理的回答（最强）
5. **Graph 标签**：力导向图可视化，点节点看详情，按类型过滤

**字段说明（Graph）**：
- **Entity** / **EntityType**：实体（文档里提到的人/物/概念）和它的类别
- **TextDocument** / **DocumentChunk** / **TextSummary**：原文档、切片、摘要层
- **EdgeType**：关系类型

**常见坑**：
- **Add 完不 Cognify，Search 会报 NoDataError**：两步流程，别漏
- **Cognify 慢**：文档多时要等。别以为卡死了
- **一个 Cognee 实例跑多 user 要注意**：数据集是全局的，不按 user 隔离

---

### ✨ Context Studio — 统一上下文

**作用**：调试 `/api/v1/context` 的并发编排，一次性看三引擎返回什么。

**典型使用**：
1. 选 user_id
2. 填 query（模拟用户这一轮的输入）
3. 勾选 Include conversations / profile / knowledge（三个勾选框）
4. 调参数：conversation_limit、knowledge_top_k、knowledge search type、max_token_size
5. 点 "Fetch context"
6. Tab 切换看每个引擎返回了什么（Errors tab 显示挂掉的引擎）

**典型场景**：
- 自己开发时调参，找合适的 conversation_limit / top_k
- 排查"为什么 Playground 回答的上下文不对"——直接看这里三引擎返回了什么

**常见坑**：
- 某个引擎挂掉不会阻塞其他引擎，失败引擎进 `errors` 字段
- 全挂的情况返回 200 + errors（不是 500），注意判断

---

### 🎨 Playground — 带记忆的 LLM 对话

**作用**：体验完整的"记忆增强对话"——每轮自动拉三引擎上下文注入 system
prompt，LLM 回复后写回 Mem0。

**典型使用**：
1. 顶部选 user_id + 点 "Use"
2. （可选）展开底下的 Model / Temp / Max tokens / System prompt 调参
3. 输入消息 → 回车（或 Shift+Enter 换行）
4. 流式输出，右上角 "Stop" 可中断
5. 完成后会话自动存 localStorage（最多 20 条），左上角 "Load session" 切换
6. 新开 "New" 按钮开新会话

**右侧面板 Last context injected**：
- 展示最近一次 `/context` 拉回来的数据（conversations / profile / knowledge）
- 对照看 LLM 回答时"看到了什么"

**字段说明**：
- **Model**：下拉是预设模型，选 "Custom..." 填任意值
- **Temperature**：0-2，越低越保守
- **Max tokens**：单次回复上限
- **System prompt**：默认模板可改，改了持久化到 localStorage

**常见坑**：
- 首次聊天前要先选 user，否则 Send 按钮是 disabled
- 如果 LLM 回复慢或挂，多半是后端 oneapi 代理或 key 问题——去 Settings 看
- 回复完"saving to memory"状态：成功存 Mem0；失败不影响聊天

---

### 💾 Backup — 用户数据备份

**作用**：单用户维度的 JSON 备份 + 恢复（Mem0 记忆 + Memobase 画像 +
可选 Cognee 数据集）。

**典型使用**：
1. **Export**：选 user_id → 勾选要导出的引擎 → 填 Cognee datasets（可选）
   → 点 "Export" → 浏览器下载 JSON 文件
2. **Import**：选一个 JSON 文件 → 选目标 user_id → 点 "Import" →
   数据恢复到目标用户

**字段说明**：
- **include_conversations / include_profile / include_knowledge**：
  控制备份范围
- **cognee_datasets**：多选，只备这些 dataset 的知识图谱（过多会很大）

**常见坑**：
- **知识图谱恢复是"重新 cognify"**：DocumentChunk 文本保真，但生成的
  实体/边可能和源略有差异
- 恢复不会清目标 user 的现有数据，而是合并（新增）

---

### ⚙️ Settings — 配置与 Key 管理

**作用**：客户端偏好（API Key）+ 服务端动态 API Key CRUD + 审计日志。

**三个主要卡片**：

**1. Client API Key**
- 你浏览器发请求带的那把 key
- 存 localStorage，换浏览器要重填
- 这是前面 "快速开始" 第 1 步设的

**2. Server-side API Keys**
- 服务端动态 key（除了 `COZY_API_KEYS` env 配的 bootstrap key）
- Create / Rotate / Delete 全部在这里
- **使用场景**：给第三方集成一把独立 key，将来能单独 revoke

**3. Audit Log**
- 每把 key 最近 200 条调用记录
- 看谁、什么时间、调了哪个接口
- 发现异常直接 Rotate 该 key

**常见坑**：
- Client API Key 不对会全局 401，先去看这个
- Bootstrap key（env 配的）不显示在 Server-side API Keys 里，那些是"动态"的

---

## FAQ

### Q: 全部 401 错误怎么办？
A: 去 Settings → Client API Key 填上 `cozy-dev-key-001`（开发默认 key）
→ Save → 刷新。

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
3. 去 Context Studio 看 `/context` 能不能拉到 conversations

### Q: 能不能把所有用户的数据一次性备份？
A: 不能直接做——Backup 是**单用户粒度**。要备全部，脚本遍历 Users 列表
挨个调 `/api/v1/backup/{user_id}/export`。

### Q: Cognee Cognify 卡住了怎么办？
A:
1. 稍等（大文档 1-5 分钟正常）
2. 看 Dashboard Engine Health，Cognee 是不是红
3. 看后端日志：`docker logs cozy_cognee`
4. 再不行，删了 dataset 重来

### Q: Dark mode 在哪里切？
A: 左下角 sidebar footer 的 Theme 开关。

### Q: 快捷键有哪些？
A: 按 `?` 弹出帮助。Gmail 风格：
- `g d` → Dashboard
- `g m` → Memory Lab
- `g p` → Profiles
- `g k` → Knowledge Base
- `g c` → Context Studio
- `g l` → Playground（l for playground）
- `g u` → Users
- `g b` → Backup
- `g s` → Settings

聚焦在输入框时快捷键自动禁用，放心打字。

---

## 开发者提示

- **API 文档**：`http://你的IP:8000/docs`（Swagger UI，需要 API key）
- **OpenAPI schema**：`http://你的IP:8000/openapi.json`
- **UI 源码**：仓库 `ui/` 目录，Next.js 16 App Router
- **后端源码**：仓库 `src/cozymemory/`，FastAPI + httpx
- **规范**：`CLAUDE.md` 里有详细的架构和引擎 API quirks
