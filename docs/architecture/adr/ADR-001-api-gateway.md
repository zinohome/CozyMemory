# ADR-001: API Gateway 技术选型

**状态**: 已决定  
**日期**: 2026-04-05  
**决策者**: 张老师  
**记录者**: AI 架构师

---

## 背景

统一 API 层需要一个 Python Web 框架作为 Gateway，负责：
- RESTful API 路由
- GraphQL 端点托管
- gRPC Gateway（可选）
- 认证和授权
- 限流和监控

## 候选方案

| 方案 | 优势 | 劣势 |
|------|------|------|
| **FastAPI** | 高性能、异步原生、OpenAPI 自动生成、生态成熟 | 学习曲线中等 |
| Flask | 简单、生态大 | 同步为主、性能一般 |
| Django REST | 功能全、自带 ORM | 重量级、不够灵活 |
| Express (Node.js) | 轻量、生态大 | 需要切换技术栈 |

## 决策

✅ **选择 FastAPI**

### 理由

1. **用户指定**: 张老师明确要求使用 FastAPI
2. **性能优异**: 基于 Starlette + Pydantic，性能接近 Node.js
3. **异步原生**: 完美支持 async/await，适合 I/O 密集型 API Gateway
4. **OpenAPI 自动生成**: 无需手动编写 API 文档
5. **Python 生态**: 与记忆引擎 SDK 同语言，便于集成
6. **GraphQL 支持**: 可通过 Strawberry 集成
7. **gRPC 支持**: 可通过 grpc.aio 集成

## 技术栈确认

```yaml
API Gateway: FastAPI (用户指定) ✅
GraphQL: Strawberry (推荐，见 ADR-002)
gRPC: grpcio + grpc-tools (官方库，见 ADR-003)
```

## 影响

- ✅ 开发团队需要熟悉 FastAPI 异步编程模型
- ✅ 所有 API 自动获得 OpenAPI 文档
- ✅ 可以复用现有 Python 技能和库

## 合规性

本决策符合架构原则：
- AP-01 (松耦合): FastAPI 依赖注入便于解耦
- AP-04 (可观测性): 内置中间件支持
- AP-05 (文档驱动): 自动生成 OpenAPI

---

**END OF ADR**
