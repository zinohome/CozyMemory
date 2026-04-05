# 统一 AI 记忆服务平台 - 应用架构设计

**文档编号**: ARCH-APP-003  
**版本**: 1.0  
**状态**: 草案  
**创建日期**: 2026-04-05  
**作者**: 蟹小五 (AI 架构师)

---

## 1. 应用架构概览

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   RESTful     │  │   GraphQL     │  │     gRPC      │       │
│  │   API         │  │   API         │  │   Server      │       │
│  │   /api/v1/*   │  │   /graphql    │  │   :50051      │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│                        API Gateway Layer                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                     │   │
│  │  ├── Authentication Middleware (OAuth2 + API Key)        │   │
│  │  ├── Rate Limiting Middleware                            │   │
│  │  ├── Logging Middleware                                  │   │
│  │  ├── CORS Middleware                                     │   │
│  │  └── Error Handling Middleware                           │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                      Business Logic Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Memory Service │  │  Router Service │  │  Fusion Service │ │
│  │  - Store        │  │  - Rule-based   │  │  - Merge        │ │
│  │  - Retrieve     │  │  - LLM-based    │  │  - Deduplicate  │ │
│  │  - Update       │  │  - Hybrid       │  │  - Rank         │ │
│  │  - Delete       │  │  - Cache        │  │  - Transform    │ │
│  │  - Search       │  └─────────────────┘  └─────────────────┘ │
│  └─────────────────┘                                           │
├─────────────────────────────────────────────────────────────────┤
│                      Adapter Layer (SPI)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Cognee Adapter │  │   Mem0 Adapter  │  │ Memobase Adapter│ │
│  │  - HTTP Client  │  │  - HTTP Client  │  │  - HTTP Client  │ │
│  │  - Auth         │  │  - Auth         │  │  - Auth         │ │
│  │  - Transform    │  │  - Transform    │  │  - Transform    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure Layer                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   PostgreSQL  │  │    Redis      │  │  MinIO/S3     │       │
│  │   (Users/     │  │   (Cache/     │  │   (Documents/ │       │
│  │    API Keys)  │  │    Sessions)  │  │    Files)     │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

| 组件 | 职责 | 技术选型 |
|------|------|---------|
| API Gateway | 统一入口、认证、限流 | FastAPI |
| REST API | 通用 CRUD 接口 | FastAPI Router |
| GraphQL API | 灵活查询接口 | Strawberry |
| gRPC Server | 高性能/流式接口 | grpc.aio |
| Router Service | 智能路由决策 | 规则+LLM 混合 |
| Memory Service | 记忆业务逻辑 | 自研 |
| Fusion Service | 多源结果融合 | 自研 |
| Engine Adapters | 引擎适配层 | HTTP Client |

---

## 2. 服务设计

### 2.1 Memory Service

```python
# services/memory_service.py
from typing import List, Optional
from datetime import datetime

class MemoryService:
    """记忆服务核心逻辑"""
    
    def __init__(
        self,
        cognee_adapter: CogneeAdapter,
        mem0_adapter: Mem0Adapter,
        memobase_adapter: MemobaseAdapter,
        router: HybridRouter,
        fusion_service: FusionService,
    ):
        self.cognee = cognee_adapter
        self.mem0 = mem0_adapter
        self.memobase = memobase_adapter
        self.router = router
        self.fusion = fusion_service
    
    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[dict] = None,
    ) -> Memory:
        """
        存储记忆
        
        根据记忆类型路由到对应引擎：
        - SHORT_TERM → mem0
        - LONG_TERM → memobase
        - KNOWLEDGE → cognee
        """
        adapter = self._get_adapter_by_type(memory_type)
        return await adapter.store(user_id, content, metadata)
    
    async def retrieve_memories(
        self,
        user_id: str,
        query: str,
        context: Optional[dict] = None,
        limit: int = 10,
    ) -> List[Memory]:
        """
        检索记忆
        
        1. 路由器决定使用哪些引擎
        2. 并行调用选中的引擎
        3. 融合结果并排序
        """
        # 路由决策
        routing_result = await self.router.route(query, context)
        
        # 并行调用选中的引擎
        tasks = []
        for engine_name in routing_result.engines:
            adapter = self._get_adapter(engine_name)
            tasks.append(adapter.retrieve(user_id, query, limit))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 融合结果
        all_memories = []
        for result in results:
            if isinstance(result, list):
                all_memories.extend(result)
        
        # 去重、排序、截断
        return await self.fusion.merge_and_rank(all_memories, query, limit)
    
    async def search_memories(
        self,
        user_id: str,
        filters: MemoryFilters,
        limit: int = 10,
    ) -> List[Memory]:
        """按条件搜索记忆"""
        pass
    
    async def delete_memory(
        self,
        user_id: str,
        memory_id: str,
    ) -> bool:
        """删除记忆"""
        pass
    
    async def update_memory(
        self,
        user_id: str,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Memory:
        """更新记忆"""
        pass
    
    def _get_adapter(self, engine_name: str) -> MemoryEngineAdapter:
        """根据引擎名称获取适配器"""
        adapters = {
            "cognee": self.cognee,
            "mem0": self.mem0,
            "memobase": self.memobase,
        }
        return adapters.get(engine_name)
    
    def _get_adapter_by_type(self, memory_type: MemoryType) -> MemoryEngineAdapter:
        """根据记忆类型获取适配器"""
        mapping = {
            MemoryType.SHORT_TERM: self.mem0,
            MemoryType.LONG_TERM: self.memobase,
            MemoryType.KNOWLEDGE: self.cognee,
        }
        return mapping.get(memory_type)
```

### 2.2 Router Service

```python
# services/router_service.py
# 详见 ADR-004
```

### 2.3 Fusion Service

```python
# services/fusion_service.py
from typing import List
import hashlib

class FusionService:
    """多源记忆结果融合服务"""
    
    async def merge_and_rank(
        self,
        memories: List[Memory],
        query: str,
        limit: int = 10,
    ) -> List[Memory]:
        """
        融合并排序记忆结果
        
        步骤：
        1. 去重（相同内容/ID）
        2. 计算相关性分数
        3. 按分数排序
        4. 截断到 limit
        """
        # 1. 去重
        unique_memories = self._deduplicate(memories)
        
        # 2. 计算相关性分数
        scored_memories = await self._score_memories(unique_memories, query)
        
        # 3. 排序
        sorted_memories = sorted(
            scored_memories,
            key=lambda m: m.score,
            reverse=True,
        )
        
        # 4. 截断
        return sorted_memories[:limit]
    
    def _deduplicate(self, memories: List[Memory]) -> List[Memory]:
        """
        去重记忆
        
        去重策略：
        - 相同 ID 视为重复
        - 相同内容哈希视为重复
        """
        seen_ids = set()
        seen_hashes = set()
        unique = []
        
        for memory in memories:
            # ID 去重
            if memory.id in seen_ids:
                continue
            seen_ids.add(memory.id)
            
            # 内容哈希去重
            content_hash = hashlib.md5(memory.content.encode()).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            
            unique.append(memory)
        
        return unique
    
    async def _score_memories(
        self,
        memories: List[Memory],
        query: str,
    ) -> List[ScoredMemory]:
        """
        计算记忆相关性分数
        
        评分因素：
        - 语义相似度（向量距离）
        - 时间新鲜度（越新分数越高）
        - 来源置信度（不同引擎权重不同）
        - 用户交互历史（点击/收藏加权）
        """
        scored = []
        
        for memory in memories:
            # 语义相似度（0-1）
            semantic_score = memory.similarity or 0.5
            
            # 时间新鲜度（0-1，指数衰减）
            freshness_score = self._calculate_freshness(memory.created_at)
            
            # 来源置信度
            source_weights = {
                "mem0": 0.8,
                "cognee": 0.9,
                "memobase": 0.7,
            }
            source_score = source_weights.get(memory.source, 0.5)
            
            # 加权平均
            final_score = (
                semantic_score * 0.5 +
                freshness_score * 0.3 +
                source_score * 0.2
            )
            
            scored.append(ScoredMemory(
                **memory.dict(),
                score=final_score,
            ))
        
        return scored
    
    def _calculate_freshness(self, created_at: datetime) -> float:
        """
        计算时间新鲜度分数
        
        使用指数衰减：
        - 1 天内：1.0
        - 7 天内：0.8
        - 30 天内：0.5
        - 90 天内：0.3
        - 超过 90 天：0.1
        """
        from datetime import timedelta
        
        now = datetime.utcnow()
        age = now - created_at
        
        if age < timedelta(days=1):
            return 1.0
        elif age < timedelta(days=7):
            return 0.8
        elif age < timedelta(days=30):
            return 0.5
        elif age < timedelta(days=90):
            return 0.3
        else:
            return 0.1
```

---

## 3. API 设计

### 3.1 RESTful API

```yaml
openapi: 3.0.3
info:
  title: Unified AI Memory Platform API
  version: 1.0.0
  description: 统一 AI 记忆服务平台

servers:
  - url: https://api.example.com/api/v1

paths:
  /memories:
    post:
      summary: 创建记忆
      operationId: createMemory
      tags: [Memories]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MemoryCreate'
      responses:
        '201':
          description: 创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Memory'
    
    get:
      summary: 查询记忆列表
      operationId: listMemories
      tags: [Memories]
      security:
        - BearerAuth: []
        - ApiKeyAuth: []
      parameters:
        - name: query
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
      responses:
        '200':
          description: 查询成功
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Memory'

  /memories/{memory_id}:
    get:
      summary: 获取单条记忆
      operationId: getMemory
      tags: [Memories]
      parameters:
        - name: memory_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 查询成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Memory'
        '404':
          description: 记忆不存在
    
    put:
      summary: 更新记忆
      operationId: updateMemory
      tags: [Memories]
      parameters:
        - name: memory_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MemoryUpdate'
      responses:
        '200':
          description: 更新成功
    
    delete:
      summary: 删除记忆
      operationId: deleteMemory
      tags: [Memories]
      parameters:
        - name: memory_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: 删除成功

  /conversations:
    post:
      summary: 创建会话
      operationId: createConversation
      tags: [Conversations]
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConversationCreate'
      responses:
        '201':
          description: 创建成功

  /conversations/{conversation_id}/message:
    post:
      summary: 发送消息（自动记忆）
      operationId: sendMessage
      tags: [Conversations]
      parameters:
        - name: conversation_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MessageCreate'
      responses:
        '200':
          description: 发送成功

  /users/me:
    get:
      summary: 获取当前用户信息
      operationId: getCurrentUser
      tags: [Users]
      responses:
        '200':
          description: 查询成功

  /users/me/api-keys:
    post:
      summary: 创建 API Key
      operationId: createApiKey
      tags: [API Keys]
      responses:
        '201':
          description: 创建成功
    
    get:
      summary: 列出 API Keys
      operationId: listApiKeys
      tags: [API Keys]
      responses:
        '200':
          description: 查询成功

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  
  schemas:
    MemoryCreate:
      type: object
      required:
        - content
      properties:
        content:
          type: string
        memory_type:
          type: string
          enum: [short_term, long_term, knowledge]
        metadata:
          type: object
    
    Memory:
      type: object
      properties:
        id:
          type: string
        user_id:
          type: string
        content:
          type: string
        memory_type:
          type: string
        source:
          type: string
        metadata:
          type: object
        created_at:
          type: string
          format: date-time
```

### 3.2 GraphQL Schema

```graphql
# schema.graphql
scalar DateTime
scalar JSON

type Query {
  # 记忆查询
  memory(id: ID!): Memory
  memories(
    userId: ID!
    query: String
    type: MemoryType
    limit: Int = 10
    offset: Int = 0
  ): [Memory!]!
  
  # 智能搜索
  smartSearch(
    query: String!
    context: JSON
    limit: Int = 10
  ): SearchResult!
  
  # 会话查询
  conversation(id: ID!): Conversation
  conversations(userId: ID!): [Conversation!]!
  
  # 用户查询
  me: User
}

type Mutation {
  # 记忆操作
  storeMemory(input: StoreMemoryInput!): Memory!
  updateMemory(id: ID!, input: UpdateMemoryInput!): Memory!
  deleteMemory(id: ID!): Boolean!
  
  # 会话操作
  createConversation(input: CreateConversationInput!): Conversation!
  sendMessage(conversationId: ID!, content: String!): Message!
  
  # API Key 管理
  createApiKey(input: CreateApiKeyInput!): ApiKeyPayload!
  deleteApiKey(id: ID!): Boolean!
}

type Subscription {
  # 实时记忆更新
  memoryStream(userId: ID!): Memory!
  
  # 实时会话消息
  conversationStream(conversationId: ID!): Message!
}

type Memory {
  id: ID!
  userId: ID!
  content: String!
  memoryType: MemoryType!
  source: MemorySource!
  metadata: JSON
  similarity: Float
  score: Float
  createdAt: DateTime!
  updatedAt: DateTime!
}

enum MemoryType {
  SHORT_TERM
  LONG_TERM
  KNOWLEDGE
}

enum MemorySource {
  MEM0
  COGNEE
  MEMOBASE
}

type SearchResult {
  memories: [Memory!]!
  query: String!
  routingDecision: RoutingDecision!
  executionTime: Float!
}

type RoutingDecision {
  engines: [MemorySource!]!
  confidence: Float!
  source: String!
  reasoning: String
}

type Conversation {
  id: ID!
  userId: ID!
  title: String
  messages: [Message!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Message {
  id: ID!
  conversationId: ID!
  role: MessageRole!
  content: String!
  createdAt: DateTime!
}

enum MessageRole {
  USER
  ASSISTANT
  SYSTEM
}

type User {
  id: ID!
  email: String!
  isActive: Boolean!
  createdAt: DateTime!
  apiKeys: [ApiKey!]!
}

type ApiKey {
  id: ID!
  name: String!
  keyPrefix: String!
  scopes: String!
  expiresAt: DateTime
  lastUsedAt: DateTime
  createdAt: DateTime!
}

type ApiKeyPayload {
  apiKey: ApiKey!
  rawKey: String!  # 仅创建时返回一次
}

input StoreMemoryInput {
  content: String!
  memoryType: MemoryType!
  metadata: JSON
}

input UpdateMemoryInput {
  content: String
  metadata: JSON
}

input CreateConversationInput {
  title: String
  metadata: JSON
}

input CreateApiKeyInput {
  name: String!
  scopes: String = "*"
  expiresAt: DateTime
}
```

### 3.3 gRPC Service

```protobuf
// proto/memory_service.proto
syntax = "proto3";

package memory.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/struct.proto";

service UnifiedMemoryService {
  // 基础 CRUD
  rpc StoreMemory(StoreMemoryRequest) returns (StoreMemoryResponse);
  rpc GetMemory(GetMemoryRequest) returns (GetMemoryResponse);
  rpc ListMemories(ListMemoriesRequest) returns (ListMemoriesResponse);
  rpc UpdateMemory(UpdateMemoryRequest) returns (UpdateMemoryResponse);
  rpc DeleteMemory(DeleteMemoryRequest) returns (DeleteMemoryResponse);
  
  // 搜索
  rpc SearchMemories(SearchMemoriesRequest) returns (SearchMemoriesResponse);
  rpc SmartSearch(SmartSearchRequest) returns (SmartSearchResponse);
  
  // 会话（流式）
  rpc ConversationStream(stream ConversationRequest) returns (stream ConversationResponse);
  
  // 批量操作
  rpc BatchStoreMemories(BatchStoreRequest) returns (BatchStoreResponse);
}

message StoreMemoryRequest {
  string user_id = 1;
  string content = 2;
  MemoryType type = 3;
  map<string, string> metadata = 4;
}

message StoreMemoryResponse {
  string memory_id = 1;
  google.protobuf.Timestamp created_at = 2;
}

message GetMemoryRequest {
  string memory_id = 1;
}

message GetMemoryResponse {
  Memory memory = 1;
}

message ListMemoriesRequest {
  string user_id = 1;
  MemoryType type = 2;
  int32 limit = 3;
  int32 offset = 4;
}

message ListMemoriesResponse {
  repeated Memory memories = 1;
  int32 total = 2;
}

message SearchMemoriesRequest {
  string user_id = 1;
  string query = 2;
  int32 limit = 3;
}

message SearchMemoriesResponse {
  repeated Memory memories = 1;
  float execution_time_ms = 2;
}

message SmartSearchRequest {
  string user_id = 1;
  string query = 2;
  google.protobuf.Struct context = 3;
  int32 limit = 4;
}

message SmartSearchResponse {
  repeated Memory memories = 1;
  RoutingDecision routing = 2;
  float execution_time_ms = 3;
}

message RoutingDecision {
  repeated MemorySource engines = 1;
  float confidence = 2;
  string source = 3;  // "rules" or "llm"
  string reasoning = 4;
}

message ConversationRequest {
  string conversation_id = 1;
  string user_id = 2;
  string content = 3;
  MessageRole role = 4;
}

message ConversationResponse {
  Message message = 1;
  repeated Memory related_memories = 2;
}

enum MemoryType {
  MEMORY_TYPE_UNSPECIFIED = 0;
  MEMORY_TYPE_SHORT_TERM = 1;
  MEMORY_TYPE_LONG_TERM = 2;
  MEMORY_TYPE_KNOWLEDGE = 3;
}

enum MemorySource {
  MEMORY_SOURCE_UNSPECIFIED = 0;
  MEMORY_SOURCE_MEM0 = 1;
  MEMORY_SOURCE_COGNEE = 2;
  MEMORY_SOURCE_MEMOBASE = 3;
}

enum MessageRole {
  MESSAGE_ROLE_UNSPECIFIED = 0;
  MESSAGE_ROLE_USER = 1;
  MESSAGE_ROLE_ASSISTANT = 2;
  MESSAGE_ROLE_SYSTEM = 3;
}

message Memory {
  string id = 1;
  string user_id = 2;
  string content = 3;
  MemoryType type = 4;
  MemorySource source = 5;
  map<string, string> metadata = 6;
  float similarity = 7;
  float score = 8;
  google.protobuf.Timestamp created_at = 9;
  google.protobuf.Timestamp updated_at = 10;
}

message Message {
  string id = 1;
  string conversation_id = 2;
  MessageRole role = 3;
  string content = 4;
  google.protobuf.Timestamp created_at = 5;
}
```

---

## 4. 数据模型

### 4.1 统一记忆模型

```python
# schemas/memory.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, Literal

class MemoryBase(BaseModel):
    content: str
    memory_type: Literal["short_term", "long_term", "knowledge"]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MemoryCreate(MemoryBase):
    pass

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Memory(MemoryBase):
    id: str
    user_id: str
    source: Literal["mem0", "cognee", "memobase"]
    similarity: Optional[float] = None
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ScoredMemory(Memory):
    score: float
```

---

## 5. 错误处理

### 5.1 错误码定义

```python
# exceptions.py
from fastapi import HTTPException, status

class MemoryError(HTTPException):
    """记忆服务基础异常"""
    pass

class MemoryNotFoundError(MemoryError):
    """记忆不存在"""
    def __init__(self, memory_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory not found: {memory_id}",
        )

class EngineUnavailableError(MemoryError):
    """记忆引擎不可用"""
    def __init__(self, engine_name: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Memory engine unavailable: {engine_name}",
        )

class RoutingError(MemoryError):
    """路由错误"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Routing error: {message}",
        )

class AuthenticationError(HTTPException):
    """认证错误"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer, ApiKey"},
        )
```

### 5.2 全局异常处理

```python
# middleware/exception_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
        },
    )

async def memory_error_handler(request: Request, exc: MemoryError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "memory_error",
            "detail": exc.detail,
        },
    )
```

---

## 6. 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ REST API  │  │GraphQL API│  │ gRPC API  │               │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘               │
│        │              │              │                       │
│        └──────────────┼──────────────┘                       │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                             │
│              │ Auth Middleware│                             │
│              └───────┬────────┘                             │
│                      │                                       │
│                      ▼                                       │
│              ┌────────────────┐                             │
│              │ Memory Service │                             │
│              └───────┬────────┘                             │
│                      │                                       │
│         ┌────────────┼────────────┐                         │
│         │            │            │                         │
│         ▼            ▼            ▼                         │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                 │
│  │   Router  │ │  Fusion   │ │  Cache    │                 │
│  │  Service  │ │  Service  │ │  Service  │                 │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘                 │
│        │             │             │                        │
│        └─────────────┼─────────────┘                        │
│                      │                                      │
│                      ▼                                      │
│         ┌────────────────────────┐                         │
│         │     Adapter Layer      │                         │
│         │  ┌────┐ ┌────┐ ┌────┐  │                         │
│         │  │Cog │ │Mem0│ │Memo│  │                         │
│         │  │nee │ │    │ │base│  │                         │
│         │  └────┘ └────┘ └────┘  │                         │
│         └────────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

**END OF DOCUMENT**
