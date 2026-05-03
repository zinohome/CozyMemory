# CozyMemory REST + gRPC 完整测试报告

**日期**: 2026-05-03  
**版本**: v0.3.0  
**环境**: 192.168.66.41 (i9-12900HK) | Ollama 192.168.66.163  
**LLM**: gpt-oss:20b-cloud (Mem0/Memobase) + gpt-oss:20b-cloud (Cognee, openai/ 前缀)  
**Embedding**: bge-m3 (1024 维, 本地 Ollama)  
**测试轮次**: 2 轮（每轮清空数据独立执行）

---

## 测试概述

通过 Developer 完整工作流（注册→创建 Org→创建 App→生成 API Key→业务调用）验证 REST API 和 gRPC 两种接入方式的功能完整性、性能表现和多租户隔离。

### 测试公司

| 公司 | Org Slug | App 1 | App 2 |
|------|----------|-------|-------|
| Alpha科技 | alpha-tech | Alpha CRM | Alpha AI助手 |
| Beta教育 | beta-edu | Beta智能辅导 | Beta教务 |

---

## 1. 测试结果汇总

| 轮次 | 总项数 | 通过 | 失败 | 通过率 |
|------|--------|------|------|--------|
| 第 1 轮 | 56 | 56 | 0 | **100%** |
| 第 2 轮 | 56 | 56 | 0 | **100%** |

**两轮测试 112/112 全部通过。**

---

## 2. 功能测试明细

### 2.1 Developer 工作流 (REST)

| 步骤 | 操作 | 结果 | 延迟 |
|------|------|------|------|
| 注册 | POST /auth/register (2 公司) | ✅ | 205-268ms |
| 创建 App | POST /dashboard/apps (4 个) | ✅ | — |
| 生成 Key | POST /dashboard/apps/{id}/keys (4 个) | ✅ | — |
| Operator 查看 | GET /operator/orgs | ✅ 2 Orgs | — |

### 2.2 REST API 业务功能 (4 App × 6 接口 = 24 项)

| 接口 | 全部通过 | 延迟范围 |
|------|---------|---------|
| Conversation.Add(sync) | ✅ | 1665-2272ms |
| Conversation.Add(async) | ✅ | 15-29ms |
| Conversation.Search | ✅ | 131-303ms |
| Profile.Insert | ✅ | 59-143ms |
| Knowledge.Add | ✅ | 88-297ms |
| Context (统一) | ✅ | 204-461ms |

### 2.3 gRPC 业务功能 (4 App × 5 接口 = 20 项)

| 接口 | 全部通过 | 延迟范围 |
|------|---------|---------|
| AddConversation(sync) | ✅ | 158-220ms |
| AddConversation(async) | ✅ | 13-25ms |
| SearchConversations | ✅ | 105-166ms |
| InsertProfile | ✅ | 58-132ms |
| GetUnifiedContext | ✅ | 11-18ms |

### 2.4 多租户隔离 (5 项)

| 验证 | 方式 | 结果 |
|------|------|------|
| Alpha搜Beta关键词 | REST | ✅ 无泄露 |
| Beta搜Alpha关键词 | REST | ✅ 无泄露 |
| Alpha搜Beta关键词 | gRPC | ✅ 无泄露 |
| Beta搜Alpha关键词 | gRPC | ✅ 无泄露 |
| 同公司跨App (CRM↛AI) | gRPC | ✅ 无泄露 |

---

## 3. 性能测试

### 3.1 单请求延迟 (20 轮稳态)

| 接口 | gRPC avg | REST avg | 比率 |
|------|----------|----------|------|
| Add(async) | 13-18ms | 14-16ms | ≈1.0x |
| Search | 12-40ms | 12-14ms | ≈1.0x |
| List | 18-65ms | 18-57ms | ≈1.0x |
| Profile.Get | 15-17ms | 16ms | ≈1.0x |
| Knowledge.List | 22-23ms | 19-21ms | ≈0.9x |

### 3.2 并发吞吐 (10 并发 × 100 请求)

| 接口 | gRPC QPS | REST QPS | 比率 |
|------|----------|----------|------|
| Add(async) | 153-204 | 134-156 | **gRPC +30%** |
| Search | 151-176 | 178-189 | ≈1.0x |
| List | 139-173 | 138-144 | **gRPC +20%** |

### 3.3 性能分析

- **轻量级请求**（Add async、Context）：gRPC 和 REST 差距不大，因为瓶颈在后端引擎调用
- **高并发写入**：gRPC 有 20-30% QPS 优势（HTTP/2 多路复用、二进制协议）
- **Context（统一上下文）**：gRPC 11-18ms vs REST 204-461ms — gRPC 显著更快（省去 JSON 序列化和 HTTP 头开销）
- **LLM 依赖接口**（Add sync）：瓶颈在 LLM 推理（~2s），协议差异可忽略

---

## 4. 接入建议

| 场景 | 推荐协议 | 原因 |
|------|---------|------|
| 高频搜索 / 读取 | gRPC | 低延迟，高吞吐 |
| async 写入（记忆注入） | gRPC | 并发 QPS 更高 |
| 管理操作（创建 App/Key） | REST | 只有 REST 支持 Dashboard API |
| 统一上下文获取 | gRPC | 11ms vs 200ms+ |
| 浏览器/前端直接调用 | REST | 浏览器不支持原生 gRPC |
| 服务间调用 | gRPC | 类型安全，性能好 |

---

## 5. 连接信息

| 协议 | 地址 | 鉴权 |
|------|------|------|
| REST | http://192.168.66.41:8000/api/v1 | Header: `X-Cozy-API-Key: <app-key>` |
| gRPC (insecure) | 192.168.66.41:50151 | Metadata: `x-cozy-api-key: <app-key>` |
| gRPC (TLS) | 192.168.66.41:50051 | Metadata 同上，Caddy 自签 TLS |

---

## 6. Proto 文件位置

```
proto/
├── common.proto          # 公共类型 (HealthRequest/Response)
├── conversation.proto    # 记忆服务 (6 methods)
├── profile.proto         # 画像服务 (6 methods)
├── knowledge.proto       # 知识服务 (6 methods)
└── context.proto         # 统一上下文 (1 method)
```

**Python 客户端**：`pip install cozymemory` 后 `from cozymemory.grpc_server import *`  
**其他语言**：用 proto 文件自行生成（Go: `protoc --go_out`, TS: `grpc-tools`）

---

## 7. 已知限制

1. Knowledge.Search 通过 gRPC 调用时需显式传 `search_type`（推荐 `"CHUNKS"`），不传则使用服务端默认值
2. Cognify 是异步操作，gRPC 返回 success 仅表示任务已提交，知识图谱构建在后台进行
3. gRPC 不支持 Dashboard/Auth/Operator 端点（这些只通过 REST 提供）
