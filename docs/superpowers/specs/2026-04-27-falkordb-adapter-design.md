# Cognee FalkorDB Adapter 设计

## 背景

CozyMemory 的知识图谱引擎 Cognee 需要多租户隔离。当前方案分两阶段：

- **Phase 1（已完成）：** Kuzu + LanceDB 过渡方案，`ENABLE_BACKEND_ACCESS_CONTROL=true`。Kuzu 是嵌入式图数据库，Cognee 原生支持 per-dataset 隔离。但 Kuzu 的 GitHub 仓库已归档（2025-10-10 最后提交），不再有安全补丁和 bug 修复。
- **Phase 2（本 spec）：** 开发 FalkorDB adapter 替换 Kuzu。FalkorDB 活跃维护（4200+ 星，每日提交），基于 Redis 协议的服务端图数据库，支持 OpenCypher，明确面向 GraphRAG/LLM 场景。Cognee 已在 `GRAPH_DBS_WITH_MULTI_USER_SUPPORT` 中声明 `"falkor"` 但零实现。

## 目标

在 CozyCognee 仓库中开发并维护 FalkorDB adapter，实现 Cognee 的 `GraphDBInterface`（26 个抽象方法），以及 `FalkorDatasetDatabaseHandler` 实现 per-dataset 多租户隔离。完成后替换 Kuzu 成为 CozyMemory 的生产图数据库。

## 技术选型

| 维度 | Kuzu（当前过渡） | FalkorDB（目标） |
|------|-----------------|-----------------|
| 项目状态 | **已归档**，最后提交 2025-10 | 活跃，每日提交 |
| 部署模式 | 嵌入式（进程内） | 服务端（Redis 模块） |
| 查询语言 | Cypher | OpenCypher（兼容） |
| Python 客户端 | `kuzu==0.11.3`（核心依赖） | `falkordb>=1.6.0`（需安装） |
| 多租户隔离 | 文件级（每 dataset 一个 .pkl） | Graph 级（每 dataset 一个命名图） |
| CPU 要求 | 需要 AVX2 | 无特殊要求 |
| 运维 | 无（嵌入式） | 需维护 Redis/FalkorDB 服务 |

## 架构

### 多租户隔离策略

FalkorDB 支持在单个 Redis 实例中创建多个命名图。每个 dataset 对应一个独立的 FalkorDB graph，命名规则为 `cognee_{user_id}_{dataset_id}`。

```
FalkorDB (Redis)
├── cognee_user1_dataset_a    # User 1 的 dataset A
├── cognee_user1_dataset_b    # User 1 的 dataset B
├── cognee_user2_dataset_c    # User 2 的 dataset C
└── ...
```

- `GRAPH.QUERY cognee_user1_dataset_a "CREATE (n:Entity {name: 'foo'})"` — 写入
- `GRAPH.QUERY cognee_user1_dataset_a "MATCH (n) RETURN n"` — 查询（只返回该 graph 的数据）
- `GRAPH.DELETE cognee_user1_dataset_a` — 删除整个 dataset 的图

这提供了比 Kuzu 文件隔离更优雅的方案——不需要文件系统操作，graph 的创建和删除都是原子操作。

### 文件结构

所有代码在 CozyCognee 仓库中维护，通过 patch 或构建脚本注入到 Cognee 镜像。

**新建文件（在 `cognee/infrastructure/databases/graph/falkor/` 下）：**

| 文件 | 作用 | 预估行数 |
|------|------|---------|
| `__init__.py` | 模块导出 | ~5 |
| `adapter.py` | `FalkorAdapter(GraphDBInterface)` — 核心实现 | ~1500-2000 |
| `FalkorDatasetDatabaseHandler.py` | 多租户隔离 handler | ~80 |

**需修改的 Cognee 文件（通过 patch）：**

| 文件 | 改动 |
|------|------|
| `infrastructure/databases/graph/get_graph_engine.py` | 添加 `falkor` provider case |
| `infrastructure/databases/dataset_database_handler/supported_dataset_database_handlers.py` | 注册 `FalkorDatasetDatabaseHandler` |

### FalkorAdapter 核心方法

实现 `GraphDBInterface` 的 26 个抽象方法：

**连接管理：**
```python
class FalkorAdapter(GraphDBInterface):
    def __init__(self, graph_database_url: str, graph_database_port: str = "",
                 graph_database_username: str = "", graph_database_password: str = "",
                 graph_database_key: str = "", database_name: str = "cognee"):
        # 解析 Redis URL，建立 FalkorDB 连接
        # database_name 作为默认 graph 名称
```

**核心 CRUD（优先级 1）：**
- `add_node()` / `add_nodes()` — `MERGE` 语句创建或更新节点
- `add_edge()` / `add_edges()` — `MERGE` 语句创建或更新边
- `get_node()` / `get_nodes()` — `MATCH (n) WHERE n.id = $id RETURN n`
- `delete_node()` / `delete_nodes()` — `MATCH (n) WHERE n.id = $id DETACH DELETE n`
- `get_edges()` — `MATCH (n)-[r]->(m) WHERE n.id = $id RETURN r`
- `has_edge()` / `has_edges()` — 存在性检查
- `query()` — 直接执行 OpenCypher
- `is_empty()` — `MATCH (n) RETURN count(n) = 0`

**图遍历（优先级 2）：**
- `get_neighbors()` — 返回邻接节点
- `get_connections()` — 返回 (node, edge, node) 三元组
- `get_neighborhood()` — 指定深度的子图
- `get_nodeset_subgraph()` — 按类型和名称过滤子图

**图管理（优先级 3）：**
- `delete_graph()` — `GRAPH.DELETE {graph_name}`
- `get_graph_data()` — 全图导出
- `get_graph_metrics()` — 节点/边计数等统计
- `get_filtered_graph_data()` — 按属性过滤

**可选方法（优先级 4，可暂时 NotImplementedError）：**
- `get_node_feedback_weights()` / `set_node_feedback_weights()`
- `get_edge_feedback_weights()` / `set_edge_feedback_weights()`
- `get_triplets_batch()`

### FalkorDatasetDatabaseHandler

```python
class FalkorDatasetDatabaseHandler(DatasetDatabaseHandlerInterface):
    @classmethod
    async def create_dataset(cls, dataset_id: UUID, user: User) -> dict:
        graph_name = f"cognee_{user.id}_{dataset_id}"
        return {
            "graph_database_name": graph_name,
            "graph_database_provider": "falkor",
            "graph_dataset_database_handler": "falkor",
        }

    @classmethod
    async def delete_dataset(cls, dataset_database: DatasetDatabase):
        # 连接 FalkorDB，执行 GRAPH.DELETE {graph_name}
```

### 属性序列化

FalkorDB 的节点/边属性支持基础类型（string, int, float, bool, list）。复杂嵌套对象需要 JSON 序列化（与 KuzuAdapter 的做法一致）：

- 写入时：`json.dumps(value)` 存为 string
- 读取时：尝试 `json.loads(value)`，失败则返回原值

### 异步处理

FalkorDB Python 客户端（`falkordb>=1.6.0`）基于 `redis-py`，支持同步和异步模式。优先使用异步 Redis 连接（`redis.asyncio`），避免 ThreadPoolExecutor 的开销。

## 部署变更

### docker-compose 新增 FalkorDB 服务

```yaml
falkordb:
  image: falkordb/falkordb:latest
  container_name: cozy_falkordb
  restart: unless-stopped
  volumes:
    - /data/CozyMemory/falkordb:/data
  networks:
    - 1panel-network
  logging: *default-logging
  labels:
    createdBy: "Apps"
  deploy:
    resources:
      limits:
        memory: 1g
      reservations:
        memory: 256m
```

### Cognee 环境变量切换

```yaml
# 图数据库：Kuzu → FalkorDB
- GRAPH_DATABASE_PROVIDER=falkor
- GRAPH_DATABASE_URL=redis://falkordb:6379
- GRAPH_DATABASE_NAME=cognee

# 向量数据库保持 LanceDB（已验证可用）
- VECTOR_DB_PROVIDER=lancedb

# 多租户隔离保持开启
- ENABLE_BACKEND_ACCESS_CONTROL=true
```

### Cognee Dockerfile 变更

在 `uv sync` 命令中无需额外 extra（FalkorDB 不是 Cognee 的 optional dependency）。需要在镜像构建时额外安装 `falkordb` 包：

```dockerfile
RUN pip install falkordb>=1.6.0
```

或在 Cognee 的 `pyproject.toml` 中作为 CozyCognee 的 patch 添加依赖。

### Kuzu 注释保留

切换后，Kuzu 相关配置注释保留在 docker-compose 中（与 Neo4j 类似），供回退使用。Kuzu 是嵌入式的无需额外服务。

## 开发计划

| 阶段 | 内容 | 预计工期 |
|------|------|---------|
| 1 | 核心 CRUD + 连接管理 + query() | 1 周 |
| 2 | 图遍历 + 子图操作 | 1 周 |
| 3 | DatasetDatabaseHandler + 注册 patch | 2 天 |
| 4 | 图指标 + 属性序列化 + 错误处理 | 1 周 |
| 5 | 集成测试 + docker-compose + 部署验证 | 1 周 |

**总计：** 约 4-5 周

## 验证计划

1. **基本功能：** 创建 dataset → add 文档 → cognify → search → 结果正确
2. **多租户隔离：** App A 和 App B 各自创建 dataset，数据互不可见
3. **Graph 级隔离：** `docker exec cozy_falkordb redis-cli GRAPH.LIST` 确认每个 dataset 独立 graph
4. **性能对比：** 与 Kuzu 对比 search 延迟（FalkorDB 有网络开销但有索引优势）
5. **故障恢复：** FalkorDB 容器重启后数据持久化验证

## 不在范围内

- Kuzu adapter 的修改或维护（保持现状作为过渡）
- LanceDB 向量数据库的变更（保持不变）
- CozyMemory 应用层代码变更（不需要）
- Cognee 前端 UI 变更
- FalkorDB 集群/高可用部署（后续按需）
