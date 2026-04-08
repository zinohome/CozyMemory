# Phase 3 Day 2: 向量数据库引擎

**日期**: 2026-04-08  
**阶段**: Phase 3 Day 2  
**主题**: 向量数据库引擎 (ChromaDB)  
**状态**: 🚀 进行中  

---

## 🎯 目标

实现基于 ChromaDB 的向量数据库引擎，支持语义搜索。

---

## 📋 任务清单

### 1. 环境准备 (30 分钟)
- [ ] 安装 ChromaDB
- [ ] 安装 sentence-transformers
- [ ] 配置依赖

### 2. 嵌入模型 (1 小时)
- [ ] 实现 EmbeddingService
- [ ] 选择预训练模型
- [ ] 文本向量化

### 3. VectorAdapter (3 小时)
- [ ] 实现 ChromaAdapter
- [ ] 集合管理
- [ ] 向量插入
- [ ] 相似度搜索
- [ ] 元数据过滤

### 4. 集成测试 (1 小时)
- [ ] 单元测试
- [ ] 性能测试
- [ ] 集成测试

### 5. 文档 (30 分钟)
- [ ] 使用文档
- [ ] API 文档
- [ ] Day 2 报告

---

## 📊 技术选型

### 向量数据库：ChromaDB

**优势**:
- 轻量级，易集成
- 支持持久化
- 内置相似度搜索
- 元数据过滤
- Python 原生

**对比**:
| 特性 | ChromaDB | FAISS | Pinecone |
|------|----------|-------|----------|
| **部署** | 本地 | 本地 | 云端 |
| **易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **性能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **成本** | 免费 | 免费 | 付费 |

### 嵌入模型：sentence-transformers

**模型**: `all-MiniLM-L6-v2`

**特性**:
- 384 维向量
- 快速推理
- 多语言支持
- 语义质量高

---

## 🏗️ 架构设计

```
┌─────────────────┐
│  VectorAdapter  │
│  (ChromaDB)     │
└────────┬────────┘
         │
┌────────▼────────┐
│ EmbeddingService│
│ (sentence-trans)│
└────────┬────────┘
         │
┌────────▼────────┐
│   ChromaDB      │
│   (持久化)      │
└─────────────────┘
```

---

## 📝 实现计划

### 1. 数据模型扩展

```python
class MemoryWithEmbedding(Memory):
    """带嵌入向量的记忆"""
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
```

### 2. ChromaAdapter

```python
class ChromaAdapter(BaseAdapter):
    """ChromaDB 适配器"""
    
    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "memories",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        ...
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        # 生成嵌入
        # 插入 ChromaDB
        ...
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        # 查询文本向量化
        # 相似度搜索
        # 返回结果
        ...
```

### 3. 相似度搜索

```python
# 余弦相似度
results = collection.query(
    query_embeddings=[query_vector],
    n_results=10,
    where={"user_id": "user1"},
    include=["documents", "metadatas", "distances"]
)
```

---

## ✅ 验收标准

- [ ] 向量插入 <100ms
- [ ] 相似度搜索 <50ms
- [ ] 语义搜索准确率 >85%
- [ ] 测试覆盖率 >90%
- [ ] 文档完整

---

**开始时间**: 2026-04-08 01:45  
**预计完成**: 2026-04-08 10:00  

🦀 **Let's build Vector Search!** 🚀
