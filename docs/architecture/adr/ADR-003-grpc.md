# ADR-003: gRPC 库选型

**状态**: 已决定  
**日期**: 2026-04-05  
**决策者**: 张老师  
**记录者**: AI 架构师

---

## 背景

统一 API 层需要提供 gRPC 端点，用于高性能场景和微服务间通信。Python 生态有多个 gRPC 相关库。

## 候选方案对比

| 方案 | 描述 | 优势 | 劣势 |
|------|------|------|------|
| **grpcio (官方)** | Google 官方 gRPC Python 实现 | 最成熟、功能全、性能最好 | API 较底层 |
| **grpcio-tools (官方)** | 官方 Protobuf 编译工具 | 必备工具链 | 仅用于代码生成 |
| **betterproto** | 基于 grpclib 的异步实现 | 异步友好、类型注解好 | 生态较小、社区活跃度低 |
| **grpclib** | 纯 Python 异步实现 | 轻量、异步原生 | 功能不如官方全 |

## 决策

✅ **选择 grpcio + grpcio-tools (官方库)**

### 理由

1. **成熟稳定**: Google 官方维护，生产环境广泛使用
2. **功能完整**: 支持所有 gRPC 特性（单向、流式、双向流）
3. **性能最优**: C 扩展实现，性能最佳
4. **生态支持**: 文档、示例、社区支持最丰富
5. **异步支持**: `grpc.aio` 提供完整的异步支持
6. **FastAPI 集成**: 可以通过中间件或独立进程集成

### 关于 betterproto 的说明

虽然 betterproto 类型注解更好，但：
- 社区活跃度低（GitHub 1k+ stars vs grpcio 10k+）
- 功能不如官方完整
- 生产环境案例少
- **不推荐用于企业级项目**

## 技术实现

### Protobuf 定义示例

```protobuf
// proto/memory_service.proto
syntax = "proto3";

package memory;

service UnifiedMemoryService {
  // 单向请求
  rpc StoreMemory (StoreMemoryRequest) returns (StoreMemoryResponse);
  rpc GetMemory (GetMemoryRequest) returns (GetMemoryResponse);
  rpc SearchMemories (SearchRequest) returns (SearchResponse);
  
  // 双向流式（实时会话）
  rpc ConversationStream (stream ConversationRequest) 
      returns (stream ConversationResponse);
  
  // 批量操作
  rpc BatchStoreMemories (BatchStoreRequest) returns (BatchStoreResponse);
}

message StoreMemoryRequest {
  string user_id = 1;
  string content = 2;
  MemoryType type = 3;
  map<string, string> metadata = 4;
}

message StoreMemoryResponse {
  string memory_id = 1;
  int64 created_at = 2;
}

enum MemoryType {
  MEMORY_TYPE_UNSPECIFIED = 0;
  MEMORY_TYPE_SHORT_TERM = 1;   // mem0
  MEMORY_TYPE_LONG_TERM = 2;    // memobase
  MEMORY_TYPE_KNOWLEDGE = 3;    // cognee
}

// ... 其他消息定义
```

### 代码生成

```bash
# 安装工具
pip install grpcio grpcio-tools

# 生成 Python 代码
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/grpc \
    --grpc_python_out=./src/grpc \
    ./proto/memory_service.proto
```

### FastAPI 集成方式

**方案 A: 独立 gRPC 服务进程**（推荐）
```python
# grpc_server.py
import grpc
from concurrent import futures
from src.grpc import memory_service_pb2_grpc

class MemoryServiceServicer(memory_service_pb2_grpc.UnifiedMemoryServiceServicer):
    async def StoreMemory(self, request, context):
        # 调用业务逻辑
        pass

async def serve():
    server = grpc.aio.server()
    memory_service_pb2_grpc.add_UnifiedMemoryServiceServicer_to_server(
        MemoryServiceServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    await server.start()
    await server.wait_for_termination()
```

**方案 B: FastAPI 内嵌 gRPC Gateway**
```python
# 通过 HTTP 转 gRPC，适合外部访问
@app.post("/api/v1/grpc/memory")
async def grpc_gateway(request: Request):
    # HTTP → gRPC 转换
    pass
```

## 依赖

```python
# requirements.txt
grpcio>=1.60.0
grpcio-tools>=1.60.0
protobuf>=4.25.0
```

## 影响

- ✅ 需要学习 Protobuf 语法
- ✅ 需要维护 `.proto` 文件
- ✅ 需要代码生成步骤（可集成到 CI/CD）
- ✅ 获得最佳性能和类型安全

## 合规性

本决策符合架构原则：
- AP-01 (松耦合): gRPC 天然支持服务解耦
- AP-04 (可观测性): gRPC 内置拦截器支持监控

---

**END OF ADR**
