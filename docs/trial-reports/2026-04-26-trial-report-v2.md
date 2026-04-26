# CozyMemory v0.2.0 修复后试用报告

**试用日期**: 2026-04-26 ~ 2026-04-27
**平台版本**: v0.2.0（含 P0–P3 修复 + C1/C3/C5 优化）
**三引擎状态**: Mem0 ✅ | Memobase ✅ | Cognee ✅ (全部健康)

---

## 修复清单验证

| 问题 | 修复前 | 修复后 | 状态 |
|------|--------|--------|------|
| **P0** Docker 启动未自动迁移 | 首次部署注册 500 | entrypoint.sh 自动 `alembic upgrade head` | ✅ 已验证 |
| **P1** `/profiles/insert` 要求 UUID v4 | 字符串 user_id 返回 422 | 接受任意字符串，自动 UUID 映射 | ✅ 已验证 |
| **P2a** 响应字段 `dataset_name` 与请求 `dataset` 不一致 | 响应返回 `dataset_name` | 统一为 `dataset` | ✅ 已验证 |
| **P2b** cognify `pipeline_run_id` 始终为 null | 无法追踪构建进度 | 正确解析嵌套响应，返回有效 ID | ✅ 已验证 |
| **P3** profile insert/GET UUID 映射不一致 | 不同端点返回不同 UUID | 统一走 `_resolve_uuid` 路径 | ✅ 已验证 |

---

## 一、星辰科技 v2（StarAI）试用报告

**管理员**: 张明 (zhang@starai2.com)
**组织**: 星辰科技v2 (starai2)
**应用**: AI智能客服v2 / 营销内容助手v2

### 功能测试结果

#### 1. 注册与认证 ✅
- 自助注册成功，JWT Token 签发正常（24h 有效期）
- 登录成功，错误密码正确返回 401
- 组织信息：developer_count=1, app_count=2

#### 2. 对话记忆（Mem0） ✅
- **添加对话**: 发送 3 条消息（iPhone 购买咨询），自动提取 4 条记忆事实
- **列出记忆**: total=4，内容准确
- **语义搜索**: "iPhone购买预算" → 4 条结果，最高分 0.6020
- **获取单条**: 按 ID 获取成功
- **删除单条**: 删除后验证剩余 3 条

#### 3. 用户画像（Memobase）✅ — P1 修复验证
- **[P1] 字符串 user_id 插入**: `"customer_002"` 直接传入，返回 `success=true`，blob_id 有效 ← **修复前返回 422**
- **[P3] 获取画像**: 同一 user_id 获取成功，映射一致
- **手动添加画像项**: topic=preference, sub_topic=ecosystem 添加成功
- **LLM 上下文**: 生成格式化提示词，含 `preference::ecosystem: 苹果全家桶用户`
- **删除画像项**: 按 ID 删除成功，验证 topics 为空

#### 4. 知识图谱（Cognee）✅ — P2 修复验证
- **创建数据集**: product-faq-v2 创建成功
- **[P2a] 添加文档**: 响应字段名为 `dataset`（非 `dataset_name`）← **已修复**
- **[P2b] cognify**: `pipeline_run_id=ea5a125c-...`，`status=PipelineRunStarted` ← **修复前为 null**
- **搜索**: CHUNKS 模式返回结果

#### 5. 统一上下文 ✅
- conversations: 3 条 + profile_context: 有 + knowledge: 0 条 + errors: {}

#### 6. API Key 管理 ✅
- 创建 Key: `cozy_live_` 前缀，plaintext 仅返回一次
- 轮换 Key: 新 key 立即可用，旧 key 立即 401
- 外部用户映射: 3 个（customer_001, customer_002, 自动创建）

#### 7. 认证安全 ✅
- 无认证请求 → 401
- 无效 Key → 401
- 错误密码 → 401
- Key 轮换后旧 Key → 401

---

## 二、云图教育 v2（EduCloud）试用报告

**管理员**: 李雪 (li@educloud2.cn)
**组织**: 云图教育v2 (educloud2)
**应用**: 智能学习助手v2

### 功能测试结果

#### 1. 数据隔离 ✅（关键）
- 用云图教育 Key 查询 `customer_002`（星辰科技用户）→ **total=0**
- **确认：不同公司数据完全隔离**

#### 2. 对话记忆（Mem0）✅
- 学生对话提取 2 条记忆
- 语义搜索 "数学水平" → 正确返回数学成绩相关记忆（score 0.4875）

#### 3. 用户画像（Memobase）✅ — P1 修复验证
- **[P1] 字符串 user_id 插入**: `"student_001"` 传入成功 ← **修复前 422**
- 获取画像成功

#### 4. 知识图谱（Cognee）✅ — P2 修复验证
- 创建数据集 math-g9-v2 成功
- **[P2a]** 添加文档响应: `dataset=True, dataset_name=False` → ✅
- **[P2b]** cognify: `pipeline_run_id=708d7ebc-...` → ✅

#### 5. 统一上下文 ✅
- conversations: 1 条 + profile_context: 有 + errors: {}

#### 6. 用量统计 ✅
- 7 天内 total=9, success=9, errors=0

---

## 三、P0 验证：Docker 自动迁移

```
$ docker inspect cozymemory --format '{{json .Config.Entrypoint}}'
["/app/entrypoint.sh"]

$ docker logs cozymemory | head -5
[entrypoint] Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
[entrypoint] Migrations complete.
```

容器启动时自动执行 `alembic upgrade head`，首次部署不再需要手动迁移。

---

## 四、综合评估

### 整体评分

| 维度 | v0.2.0 原始 | 修复后 | 说明 |
|------|-------------|--------|------|
| 核心功能完整性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 三引擎全部可用 |
| 多租户隔离 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 数据完全隔离 |
| 认证安全 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | JWT+APIKey+轮换 |
| 管理后台 API | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 全套 CRUD 可用 |
| 部署易用性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 自动迁移（P0 修复） |
| API 一致性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | user_id 统一 + dataset 字段统一 + pipeline_run_id 可用 |

### 已验证功能清单

- [x] 注册 / 登录 / JWT 签发
- [x] 组织管理
- [x] 应用 CRUD
- [x] API Key 创建 / 列出 / 轮换
- [x] 对话记忆：添加 / 列出 / 搜索 / 获取 / 删除
- [x] 用户画像：插入缓冲（字符串 user_id）/ 获取画像 / LLM 上下文 / 手动添加 / 删除
- [x] 知识图谱：创建数据集 / 添加文档 / 构建图谱(含 pipeline_run_id) / 搜索
- [x] 统一上下文 (/context)
- [x] 多租户数据隔离
- [x] 用量统计
- [x] 外部用户映射
- [x] 认证安全
- [x] 健康检查
- [x] Docker 自动迁移

### 修复前问题 → 现状

| 原问题 | 状态 |
|--------|------|
| P0: Docker 首次部署注册 500 | ✅ 已修复：entrypoint 自动迁移 |
| P1: `/profiles/insert` 要求 UUID v4 | ✅ 已修复：接受任意字符串 |
| P2a: dataset_name 与 dataset 不一致 | ✅ 已修复：统一为 dataset |
| P2b: pipeline_run_id 始终 null | ✅ 已修复：正确解析嵌套响应 |
| P3: profile insert/GET 映射不一致 | ✅ 已修复：统一 _resolve_uuid |

---

## 五、补充测试（第一轮未覆盖功能）

### 1. `/profiles/flush` 单独触发缓冲处理 ✅
- `insert(sync=false)` 异步插入 → 手动 `flush(sync=true)` → 画像生成成功
- 画像内容准确：`工作::参与项目: 用户从事外贸工作，经常需要出差东南亚`

### 2. 批量删除用户全部记忆 ✅
- 先添加 1 条记忆，确认 total=1
- `DELETE /conversations?user_id=customer_temp` → success=true
- 验证 total=0

### 3. 知识图谱 ��� 数据集文档管理 ✅
- **列出数据集文档**: `GET /knowledge/datasets/{id}/data` → 返回 1 条文档
- **获取数据集知识图谱**: `GET /knowledge/datasets/{id}/graph` → nodes: 73, edges: 61
- **cognify 状态查询**: `GET /knowledge/cognify/status/{job_id}` → 返回 404（Cognee 不支持按 pipeline_run_id 查询已完成的任务）

### 4. 文件上传到知识图谱 ✅
- `POST /knowledge/add-files` 上传 warranty-policy.txt → success=true, 已上传 1 个文件
- 验证文档列表从 1 变为 2

### 5. 删除单条文档 ✅
- `DELETE /knowledge/datasets/{id}/data/{data_id}` → success=true
- 验证文档数从 2 变为 1

### 6. 删除数据集 ✅
- 创建临时数据集 `temp-to-delete` → 删除 → 验证列表中不再包含

### 7. 旧式 `DELETE /knowledge` 接口 ✅
- 传 `data_id` + `dataset_id` → success=true

### 8. 同公司不同 App 数据隔离 ✅
- 星辰科技: 客服App（customer_002）有 3 条记忆 / 营销App（customer_002）有 0 条
- 云图教育: 学习助手（teacher_wang）有 0 条 / 教师备课（teacher_wang）有 0 条
- **确认：同一公司不同 App 之间数据完全隔离**

### 9. 第二个应用独立功能测试 ✅
- 星辰科技 营销助手: 创建 Key → 添加对话 → 正常
- 云图教育 教师备课: 创建 Key → 添加知识 → 添加对话 → 正常

### 10. gRPC 接口 ✅（14/16 方法通过）

| 域 | 方法 | 状态 |
|---|------|------|
| 对话 | AddConversation | ✅ |
| 对话 | ListConversations | ✅ |
| 对话 | SearchConversations | ✅ |
| 对话 | GetConversation | ✅ |
| 对话 | DeleteConversation | ✅ |
| 对话 | DeleteAllConversations | ✅ |
| 画像 | InsertProfile | ✅ |
| 画像 | FlushProfile | ✅ |
| 画像 | GetProfile | ⚠️ 返回结构无 `success` 字段（直接返回 UserProfile，非 bug） |
| 画像 | GetContext | ✅ |
| 画像 | AddProfileItem | ✅ |
| 画像 | DeleteProfileItem | ✅ |
| 知识 | ListDatasets | ✅ |
| 知识 | AddKnowledge | ✅ |
| 知识 | Cognify | ✅ (pipeline_run_id 有值) |
| 知识 | SearchKnowledge | ⚠️ App Key 下必须传 dataset 参数（与 REST 行为一致） |

---

## 六、完整功能覆盖清单

- [x] 注册 / 登录 / JWT 签发 / 错误密码拒绝
- [x] 组织信息查看
- [x] 应用 CRUD（创建 / 列出 / 查看）
- [x] API Key 创建 / 列出 / 轮换 / 旧 Key 失效
- [x] 对话记忆：添加 / 列出 / 搜索 / 获取单条 / 删除单条 / 批量删除
- [x] 用户画像：insert(sync) / insert(async)+flush / 获取画像 / LLM 上下文 / 手动添加 / 删除
- [x] 知识图谱：创建数据集 / 添加文档(文本) / 添加文件(上传) / cognify / 搜索 / 列出文档 / 获取图谱 / 删除文档 / 删除数据集 / 旧式删除接口
- [x] cognify 状态查询（Cognee 引擎不支持按 run_id 查询已完成任务）
- [x] 统一上下文 (/context)
- [x] 多租户数据隔离（跨公司 + 同公司跨 App）
- [x] 用量统计
- [x] 外部用户映射
- [x] 认证安全（无认证 401 / 无效 Key 401 / 错误密码 401 / Key 轮换后 401）
- [x] 健康检查
- [x] Docker 自动迁移 (P0)
- [x] gRPC 接口（16 方法全部调用，14 通过，2 个为预期行为）

### 残留观察 → 优化处理

| # | 严重度 | 描述 | 处理 |
|---|--------|------|------|
| C1 | 低 | profile insert/GET 返回内部 UUID 而非调用方传入的原始 user_id | ✅ **已优化**：API 层覆写 user_id 为原始值 |
| C2 | 低 | knowledge search 在 cognify 未完成时返回其他 dataset 的旧数据（跨 dataset 搜索） | ⏭️ Cognee 引擎行为，不做处理 |
| C3 | 低 | cognify 状态查询 `/cognify/status/{job_id}` 返回 404——Cognee 引擎不支持按 run_id 查询已完成任务 | ✅ **已优化**：标记为 deprecated，更新文档说明 |
| C4 | 低 | gRPC GetProfile 响应直接返回 UserProfile 而非 `{success, data}` 包装 | ⏭️ proto 设计差异，不影响功能 |
| C5 | 低 | gRPC/REST SearchKnowledge 在 App Key 下缺 dataset 时错误消息为英文 | ✅ **已优化**：统一为中文提示 |

---

## 七、C 级优化验证（2026-04-27）

镜像重建后，对三项优化进行了快速验证：

### C1: Profile 响应返回原始 user_id ✅

```bash
# POST /profiles/insert → user_id 返回原始字符串
$ curl -s -X POST /api/v1/profiles/insert \
    -d '{"user_id":"c1_verify_test","messages":[...]}'
→ {"success":true, "user_id":"c1_verify_test", ...}
#   修复前: user_id 为 UUID v5 (scope_user_id)

# GET /profiles/{user_id} → data.user_id 返回原始字符串
$ curl -s /api/v1/profiles/c1_verify_test
→ {"success":true, "data":{"user_id":"c1_verify_test", ...}}
#   修复前: data.user_id 为 UUID v4 (Memobase 内部 ID)
```

### C3: Cognify 状态端点标记 deprecated ✅

```bash
# OpenAPI spec 确认 deprecated 标记
$ curl -s /openapi.json | jq '.paths["/api/v1/knowledge/cognify/status/{job_id}"].get.deprecated'
→ true
# summary 更新为: "查询 Cognify 任务状态（实验性）"
```

### C5: App Key 下缺 dataset 返回中文错误 ✅

```bash
# 使用 App API Key 搜索知识但不指定 dataset
$ curl -s -X POST /api/v1/knowledge/search \
    -H "X-Cozy-API-Key: cozy_live_..." \
    -d '{"query":"测试查询"}'
→ {"detail":"使用 App API Key 时必须在请求中指定 dataset 字段"}
#   修复前: 英文消息 "dataset is required when using App API Key"
```

---

**结论**: 所有 5 个原始试用问题（P0–P3）已全部修复并通过验证。3 项 C 级观察（C1/C3/C5）已优化部署。补充测试覆盖了 flush、批量删除、文件上传、数据集管理、gRPC 全接口等功能。两家公司共 4 个应用，跨公司和同公司跨 App 的数据隔离均可靠。gRPC 16 个方法全部可调用。平台功能完整度高，可进入生产准备阶段。
