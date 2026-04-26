# CozyMemory v0.2.0 试用报告

**试用日期**: 2026-04-26
**平台版本**: v0.2.0
**三引擎状态**: Mem0 ✅ | Memobase ✅ | Cognee ✅ (全部健康)

---

## 一、星辰科技（StarAI）试用报告

**公司背景**: AI 客服平台，面向电商场景
**管理员**: 张明 (admin@starai.com)
**组织**: 星辰科技 (starai)

### 创建的应用

| 应用 | Slug | 用途 |
|------|------|------|
| AI智能客服 | ai-support | 电商平台AI客服记忆系统 |
| 营销内容助手 | marketing-ai | 基于用户画像的个性化营销 |

### 功能测试结果

#### 1. 注册与认证 ✅
- 自助注册成功，自动创建组织
- JWT Token 正常签发（24h有效期）
- 登录、获取用户信息均正常
- 错误密码正确返回 401

#### 2. 应用管理（Dashboard） ✅
- 创建应用：成功，自动分配 namespace_id
- 列出应用：返回 2 个应用，total 正确
- 组织信息：developer_count=1, app_count=2 正确
- API Key 创建：plaintext key 仅返回一次，前缀 `cozy_live_` 格式清晰

#### 3. 对话记忆（Mem0） ✅
- **添加对话**: 发送 5 条消息，自动提取 3 条记忆事实
  - "User bought a MacBook Pro 16-inch with an M3 chip last week"
  - "User's MacBook Pro has a bright spot...wants to request a replacement"
  - "User's order number is ORD-2026-88521"
- **查询记忆**: 返回 3 条，total=3
- **语义搜索**: 查询 "MacBook换货"，3 条结果按相关性排序（0.52 → 0.50 → 0.49）
- **获取单条**: 按 ID 获取成功
- **删除单条**: 删除后验证剩余 2 条

#### 4. 用户画像（Memobase） ✅
- **插入对话到缓冲**: sync=true 同步处理成功
- **手动添加画像项**: topic=preference, sub_topic=brand 添加成功
- **获取画像**: 返回结构化 topics 列表
- **LLM 上下文**: 生成格式化提示词，包含用户偏好
- **删除画像项**: 按 ID 删除成功，验证 topics 为空

#### 5. 统一上下文（/context） ✅
- 单次调用并行查询三引擎
- 返回：conversations(3条) + profile_context(含画像) + knowledge(空) + errors({})
- 延迟: 5540ms（首次调用，含引擎预热）

#### 6. API Key 管理 ✅
- **创建 Key**: 返回完整 plaintext
- **轮换 Key**: 旧 key 立即失效，新 key 立即可用
- **旧 Key 验证**: 轮换后旧 key 返回 401

#### 7. 用量统计 ✅
- 7天内 total=11, success=10, errors=1
- per_route 统计分路由：profiles.item(5), conversations(2), profiles.insert(2), context(1), conversations.search(1)
- daily 按日聚合

#### 8. 外部用户映射 ✅
- customer_001 → UUID v5 映射自动创建
- Dashboard 可查看映射列表

### 发现的问题

| # | 严重度 | 描述 |
|---|--------|------|
| A1 | 中 | `/profiles/insert` 要求 user_id 为 UUID v4 格式，但 `/conversations` 接受任意字符串。用户体验不一致，需要查文档才能发现差异 |
| A2 | 低 | profile insert 和 GET profile 使用不同的 UUID 映射路径（insert 直接传 UUID 会被再次映射），导致 user_id 对应关系不直观 |

---

## 二、云图教育（EduCloud）试用报告

**公司背景**: 智能教育平台，K12 + 教师备课
**管理员**: 李雪 (admin@educloud.cn)
**组织**: 云图教育 (educloud)

### 创建的应用

| 应用 | Slug | 用途 |
|------|------|------|
| 智能学习助手 | smart-tutor | K12学生个性化学习记忆与知识追踪 |
| 教师备课平台 | lesson-prep | 基于知识图谱的教案生成与资源管理 |

### 功能测试结果

#### 1. 注册与认证 ✅
- 独立于星辰科技的组织空间
- 邮箱唯一性约束正常

#### 2. 对话记忆（Mem0） ✅
- **学生对话**: 发送 3 条消息（二次方程学习 + 成绩信息），提取 3 条事实
  - "User learned about quadratic equations...doesn't understand the discriminant"
  - 判别式知识点正确提取
  - "User has an average level in mathematics but scored 95 on their last English exam"
- **语义搜索**: "这个学生的数学水平怎么样" → 正确返回数学相关记忆（score 0.53）

#### 3. 知识图谱（Cognee） ✅
- **创建数据集**: physics-grade9 创建成功
- **添加文档**: 牛顿三定律文本添加成功
- **构建图谱**: cognify 触发成功（异步）
- **搜索**: CHUNKS 模式返回完整文本片段，包含牛顿三定律内容
- **列出数据集**: 返回 1 个数据集

#### 4. 数据隔离 ✅ (关键)
- 用云图教育的 Key 查询 customer_001（星辰科技用户）→ 返回空数据 (total=0)
- **确认：不同公司的数据完全隔离**，同一 user_id 在不同 App 下映射到不同 UUID

### 发现的问题

| # | 严重度 | 描述 |
|---|--------|------|
| B1 | 高 | **数据库表缺失**：首次部署后 `developers` 表不存在（500 错误）。需手动 `alembic upgrade head`，Docker 镜像启动脚本应包含自动迁移 |
| B2 | 中 | knowledge/search 的错误提示 "dataset is required when using an App API key" 但请求模型字段名为 `dataset` 非 `dataset_name`，API 文档未明确说明 |
| B3 | 低 | cognify 任务状态始终返回 `pipeline_run_id: null`，无法通过 `/cognify/status/{job_id}` 追踪构建进度 |

---

## 三、综合评估

### 整体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 核心功能完整性 | ⭐⭐⭐⭐⭐ | 三引擎全部可用，对话记忆/画像/知识图谱/统一上下文均正常 |
| 多租户隔离 | ⭐⭐⭐⭐⭐ | 数据完全隔离，不同 App Key 查不到彼此数据 |
| 认证安全 | ⭐⭐⭐⭐⭐ | JWT+APIKey 双轨认证、Key 轮换、401 拦截均正常 |
| 管理后台 API | ⭐⭐⭐⭐ | Org/App/Key/Users/Usage 全套 CRUD 可用 |
| 部署易用性 | ⭐⭐⭐ | Docker Compose 一键启动，但缺少自动数据库迁移 |
| API 文档一致性 | ⭐⭐⭐ | 字段命名不一致（dataset vs dataset_name），profile user_id 约束不统一 |

### 已验证功能清单

- [x] 注册 / 登录 / JWT 签发
- [x] 组织管理（查看、更新）
- [x] 应用 CRUD
- [x] API Key 创建 / 列出 / 轮换
- [x] 对话记忆：添加 / 列出 / 搜索 / 获取 / 删除
- [x] 用户画像：插入缓冲 / 获取画像 / LLM 上下文 / 手动添加 / 删除
- [x] 知识图谱：创建数据集 / 添加文档 / 构建图谱 / 搜索
- [x] 统一上下文 (/context)
- [x] 多租户数据隔离
- [x] 用量统计
- [x] 外部用户映射
- [x] 认证安全（无认证拒绝、错误Key拒绝、错误密码拒绝、Key轮换后旧Key失效）
- [x] 健康检查

### 待修复问题汇总

| 优先级 | 问题 | 影响 |
|--------|------|------|
| **P0** | Docker 镜像启动时未自动 `alembic upgrade head` | 首次部署注册 500 |
| **P1** | `/profiles/insert` 的 user_id 必须 UUID v4，与 conversations 端点不一致 | 开发者困惑 |
| **P2** | knowledge search/add 字段名与 cognify 端点的 dataset_name 不一致 | API 体验差 |
| **P2** | cognify pipeline_run_id 始终为 null | 无法追踪构建进度 |
| **P3** | profile insert 的 UUID 映射逻辑与 GET profile 不同 | 数据对应关系混乱 |
