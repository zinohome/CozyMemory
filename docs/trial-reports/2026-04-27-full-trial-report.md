# CozyMemory 全功能试用报告

**日期**: 2026-04-27  
**环境**: 192.168.66.41 (i9-12900HK, Ubuntu 24.04)  
**版本**: CozyMemory v0.2.0 + FalkorDB adapter  
**图数据库**: FalkorDB (多租户隔离)  
**向量数据库**: LanceDB (多租户隔离)

---

## 试用场景

| 公司 | 场景 | 用户 |
|------|------|------|
| 星辰科技（公司A） | 电商AI客服 — 退货/售后/批量采购 | C001(退货客户), C002(运动耳机), C003(VIP批量) |
| 云图教育（公司B） | 在线教育AI助教 — 物理/数学辅导 | S001(高一物理), S002(数学) |

---

## 功能测试结果

### 1. 用户管理 (Auth)

| 功能 | 公司A | 公司B | 备注 |
|------|-------|-------|------|
| 注册 | ⚠️ | ✅ | A 已注册过，重复注册返回 500 而非友好提示 |
| 登录 | ✅ | ✅ | |
| 创建 App | ✅ | ✅ | A slug 重复时返回错误而非已有 App |
| 生成 API Key | ✅ | ✅ | |

### 2. 对话记忆 (Mem0)

| 功能 | 公司A | 公司B | 备注 |
|------|-------|-------|------|
| 添加对话 | ✅ | ✅ | 多轮对话，自动提取记忆 |
| 记忆提取 | ✅ 8条 | ✅ 10条 | 第一轮有时为0（异步提取） |
| 搜索记忆 | ✅ 6条 | ✅ 7条 | 语义搜索有效 |
| 获取单条 | ❌ | ❌ | 返回空（API 响应格式问题） |
| 删除记忆 | ✅ | ✅ | |
| 删除全部 | 未测 | 未测 | |

### 3. 用户画像 (Memobase)

| 功能 | 公司A | 公司B | 备注 |
|------|-------|-------|------|
| 插入对话 | ✅ | ✅ | |
| 手动添加标签 | ✅ | ✅ | |
| 获取画像 | ⚠️ 0项 | ⚠️ 0项 | 画像提取可能需要更长时间 |
| LLM 上下文 | ⚠️ 空 | ⚠️ 空 | 与画像提取延迟相关 |
| 删除画像项 | 未触发 | 未触发 | 因无画像数据 |

### 4. 知识库 (Cognee + FalkorDB)

| 功能 | 公司A | 公司B | 备注 |
|------|-------|-------|------|
| 创建 Dataset | ✅ | ✅ | |
| 添加知识 | ❌ | ❌ | **FalkorDB adapter patch 在容器重启后丢失** |
| Cognify | ✅ | ✅ | 启动成功（但因 add 失败无数据可处理） |
| 搜索知识 | 未测 | 未测 | 因 add 失败 |
| 删除知识 | 未测 | 未测 | |

### 5. 统一上下文 (Context)

| 功能 | 公司A | 公司B | 备注 |
|------|-------|-------|------|
| 三引擎并行 | ✅ 响应 | ✅ 响应 | API 正常工作 |
| Mem0 数据 | 无 | 无 | 可能是 user_id scope 问题 |
| Memobase 数据 | 无 | 无 | 画像提取延迟 |
| Cognee 数据 | 无 | 无 | add 失败 |

### 6. 多租户隔离

| 测试 | 结果 | 备注 |
|------|------|------|
| B 访问 A 的 Dataset | ✅ 被拒绝 | API 层 AppDataset 归属校验生效 |
| B 搜索 A 的用户记忆 | ✅ 无结果 | UUID v5 namespace 隔离生效 |
| A 搜索 B 的用户记忆 | ✅ 无结果 | 双向隔离确认 |
| FalkorDB Graph 隔离 | 未验证 | add 失败导致无图数据 |

### 7. Operator 管理

| 功能 | 结果 | 备注 |
|------|------|------|
| 健康检查 | ✅ healthy | 三引擎均正常 |
| 全局 Dataset 列表 | ✅ | 可见所有公司的 dataset |
| Bootstrap key 搜索 | ✅ | 无数据（正常） |

---

## 发现的问题

### P1 [严重] FalkorDB adapter patch 在容器重启后丢失

**现象**: knowledge/add 返回 "Unsupported graph database provider: falkor"  
**根因**: `patch_falkor.py` 的 `patch_get_graph_engine()` 中检测条件 `if "falkor" in content` 过宽，因 docstring 中已有 "falkor" 字样而跳过了实际代码插入。之前手动在容器内修复的代码在容器重启后丢失。  
**修复**: 已修复 `patch_falkor.py` 检测条件为 `if 'graph_database_provider == "falkor"' in content`（已推送 CozyCognee），但需要**重建 Cognee 镜像**使修复生效。  
**影响**: 知识库全部功能不可用（add/cognify/search/delete）

### P2 [中等] 重复注册返回 500 InternalServerError

**现象**: 已注册的邮箱再次注册，返回 `{"error": "InternalServerError"}` 而非友好提示  
**期望**: 应返回 `{"error": "EmailAlreadyRegistered", "detail": "该邮箱已注册，请直接登录"}`  
**修复建议**: 在 `auth.py` 的 `register()` 中 catch `IntegrityError` 并返回 409

### P3 [中等] App slug 重复时报错不友好

**现象**: 已存在的 slug 创建 App 返回 `{"detail": "app slug already exists in this org"}`  
**期望**: 至少应返回已有 App 的 ID，或者建议使用不同 slug  
**修复建议**: 提供更友好的提示和建议

### P4 [低] 获取单条记忆返回空

**现象**: `GET /conversations/{id}` 返回 `data` 为空  
**可能原因**: Mem0 的 `get()` 返回 null（已知行为，CLAUDE.md 有记录）  
**修复建议**: 在 API 层处理 null 返回，给出明确的 404 响应

### P5 [低] 画像提取延迟

**现象**: 插入对话后立即获取画像为空  
**原因**: Memobase 的画像提取是异步的，`sync: true` 只等待 buffer 写入不等待 flush 完成  
**建议**: 在 UI 中增加"画像正在提取中"的提示

### P6 [低] 对话记忆搜索结果无 memory 内容显示

**现象**: 搜索返回结果但 memory 字段为空字符串  
**可能原因**: 搜索返回的数据结构中 `memory` 字段在不同响应格式中名称不一致  
**修复建议**: 统一 API 响应格式

---

## 部署问题（本次修复）

| 问题 | 修复 | 状态 |
|------|------|------|
| PG 密码 init.sh scram-sha-256 | SET password_encryption 移到 CREATE USER 之前 | ✅ 已修复 |
| 依赖服务在 PG 就绪前启动 | PG healthcheck + depends_on condition: service_healthy | ✅ 已修复 |
| base_runtime 目录命名 | 重命名为 CozyMemory + name: cozymemory | ✅ 已修复 |
| Cognee 首次启动 migration 失败 | restart: unless-stopped 自动恢复（~2分钟） | ⚠️ 可接受 |

---

## 改进建议

### 紧急（影响功能可用性）

1. **重建 Cognee 镜像** — 使 FalkorDB patch 修复生效，解决 P1
2. **统一 API 响应格式** — conversations 端点返回 `data: []` 而非 `data: {results: []}`，与 CLAUDE.md 文档不一致

### 重要（影响用户体验）

3. **注册幂等化** — 重复注册返回已有 token 或友好错误（P2）
4. **App 创建幂等化** — slug 重复时返回已有 App（P3）
5. **Memobase flush 等待** — `sync: true` 应等待画像提取完成，而非仅等待 buffer 写入

### 建议（产品优化）

6. **Cognee 启动容错** — 增加 Cognee 自身的 PG 连接重试（而非依赖 Docker restart）
7. **API 文档自动生成** — 当前 CLAUDE.md 中的 API 字段名与实际不符（`results` vs `data`）
8. **试用引导流程** — UI 中增加 Guided Tour，引导新用户完成"注册→创建App→添加记忆→搜索"
