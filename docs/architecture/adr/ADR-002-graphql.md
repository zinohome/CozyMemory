# ADR-002: GraphQL 库选型

**状态**: 已决定  
**日期**: 2026-04-05  
**决策者**: 张老师  
**记录者**: 蟹小五

---

## 背景

FastAPI 需要集成 GraphQL 端点，Python 生态有两个主流选择：
- Strawberry
- Ariadne

## 候选方案对比

| 维度 | Strawberry | Ariadne |
|------|-----------|---------|
| **类型定义方式** | Code-first (Python class) | Schema-first (SDL) |
| **类型安全** | ⭐⭐⭐⭐⭐ (Pydantic 集成) | ⭐⭐⭐ |
| **FastAPI 集成** | ⭐⭐⭐⭐⭐ (官方集成) | ⭐⭐⭐ (需要手动) |
| **学习曲线** | 低 (Python 开发者友好) | 中 (需要学 SDL) |
| **生态成熟度** | ⭐⭐⭐⭐ (2021 年发布，增长快) | ⭐⭐⭐⭐⭐ (2019 年发布，更成熟) |
| **社区活跃度** | 高 (GitHub 11k+ stars) | 中 (GitHub 4k+ stars) |
| **文档质量** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **异步支持** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **订阅支持** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 决策

✅ **选择 Strawberry**

### 理由

1. **FastAPI 原生集成**: Strawberry 提供 `strawberry.fastapi` 模块，无缝集成
2. **Code-first 类型定义**: Python 开发者更熟悉，无需学习 SDL 语法
3. **Pydantic 集成**: 可以直接使用 Pydantic 模型，与 FastAPI 一致
4. **类型安全**: 完整的类型注解支持，IDE 友好
5. **活跃生态**: 增长迅速，社区活跃，文档完善
6. **异步支持**: 完整支持 async/await

### 示例代码对比

**Strawberry (Code-first)**:
```python
import strawberry
from typing import List

@strawberry.type
class Memory:
    id: strawberry.ID
    content: str
    user_id: str

@strawberry.type
class Query:
    @strawberry.field
    def memories(self, user_id: str) -> List[Memory]:
        # 直接返回 Python 对象
        return get_memories(user_id)
```

**Ariadne (Schema-first)**:
```python
from ariadne import QueryType, make_executable_schema

type_defs = """
    type Memory {
        id: ID!
        content: String!
        user_id: String!
    }
    
    type Query {
        memories(userId: String!): [Memory!]!
    }
"""

query = QueryType()

@query.field("memories")
def resolve_memories(*_, user_id):
    # 需要手动解析
    return get_memories(user_id)

schema = make_executable_schema(type_defs, query)
```

## 影响

- ✅ 开发团队使用统一的类型系统（Pydantic + Strawberry）
- ✅ IDE 自动补全和类型检查
- ✅ 减少 schema 同步问题（Code-first 无需维护 SDL）

## 依赖

```python
# requirements.txt
strawberry-graphql[fastapi]>=0.200.0
```

## 合规性

本决策符合架构原则：
- AP-01 (松耦合): Strawberry 与 FastAPI 解耦良好
- AP-05 (文档驱动): 自动生成 GraphQL Schema 文档

---

**END OF ADR**
