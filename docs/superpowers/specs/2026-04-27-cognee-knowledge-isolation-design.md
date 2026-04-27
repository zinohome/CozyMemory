# Cognee 知识图谱多租户隔离设计

## 问题

CozyMemory 是多租户 SaaS 平台，但 Cognee 知识引擎当前配置为单租户模式：
- `GRAPH_DATABASE_PROVIDER=neo4j`（Neo4j 不支持 Cognee 的 per-dataset 隔离）
- `VECTOR_DB_PROVIDER=pgvector`（PGVector 不在 Cognee 多租户支持列表）
- `ENABLE_BACKEND_ACCESS_CONTROL=false`（搜索时 `datasets` 参数被静默忽略）

结果：**所有 App 的知识数据写入同一个 Neo4j 图，搜索会返回其他 App 的数据**。

CozyMemory API 层已有 AppDataset 归属校验，但引擎层无隔离 — 搜索结果从 Cognee 返回时可能包含跨 App 数据。

Mem0（对话）和 Memobase（画像）不受影响 — 它们通过 UUID v5 namespace 实现密码学级别的数据隔离。

## 方案

分两阶段解决：

### Phase 1（本次）：切换到 Kuzu + LanceDB，开启多租户隔离

将 Cognee 的图数据库从 Neo4j 切换到 Kuzu（嵌入式，Cognee 原生支持 per-dataset 隔离），向量数据库从 PGVector 切换到 LanceDB（嵌入式，Cognee 原生支持 per-dataset 隔离）。开启 `ENABLE_BACKEND_ACCESS_CONTROL=true`。

Kuzu 的 GitHub 仓库已归档，但 PyPI 包（v0.11.3）正常可用，Cognee 0.4.1 的 Kuzu adapter 完整实现（2400+ 行），含 per-dataset `KuzuDatasetDatabaseHandler`。对于嵌入式数据库，"稳定不再更新"可接受。

### Phase 2（后续）：开发 FalkorDB adapter 替换 Kuzu

FalkorDB 活跃维护，同时支持图和向量搜索，是 Cognee 声明的多租户支持数据库之一（但 adapter 未实现）。在 CozyCognee 中开发并维护 FalkorDB adapter，完成后替换 Kuzu。预计工期 2-3 周。

**本 spec 仅覆盖 Phase 1。Phase 2 将有独立的 spec。**

## Phase 1 详细设计

### 1. docker-compose 环境变量变更

**Cognee 服务**（`base_runtime/docker-compose.1panel.yml`）：

```yaml
# 图数据库：Neo4j → Kuzu（嵌入式，数据存储在 /app/data 内）
- GRAPH_DATABASE_PROVIDER=kuzu
# 移除以下 Neo4j 相关变量：
#   GRAPH_DATABASE_NAME, GRAPH_DATABASE_URL,
#   GRAPH_DATABASE_USERNAME, GRAPH_DATABASE_PASSWORD

# 向量数据库：PGVector → LanceDB（嵌入式，数据存储在 /app/data 内）
- VECTOR_DB_PROVIDER=lancedb
# 移除 VECTOR_DB_URL

# 开启多租户隔离
- ENABLE_BACKEND_ACCESS_CONTROL=true

# pip 安装：去掉 neo4j，Kuzu 和 LanceDB 是 Cognee 核心依赖无需额外 extra
- EXTRAS=api,postgres
```

### 2. Neo4j 服务注释保留

Neo4j 服务段（及其 depends_on 引用）注释保留在 docker-compose 中，加说明：

```yaml
# [多租户模式] Neo4j 已切换为 Kuzu，以下注释保留供单用户环境使用。
# 如需切回 Neo4j（单用户/开发模式），取消注释本段并修改 cognee 环境变量：
#   GRAPH_DATABASE_PROVIDER=neo4j
#   GRAPH_DATABASE_URL=bolt://neo4j:7687
#   GRAPH_DATABASE_USERNAME=neo4j
#   GRAPH_DATABASE_PASSWORD=${NEO4J_PASSWORD}
#   ENABLE_BACKEND_ACCESS_CONTROL=false
```

### 3. Cognee depends_on 调整

移除 `neo4j` 依赖。Kuzu 和 LanceDB 都是嵌入式的，无需外部服务。保留 `postgres`（关系型元数据）、`redis`（缓存/锁）、`minio`（文件存储）。

### 4. Cognee build.sh 调整

`build_cognee()` 函数中的 `EXTRAS` 参数去掉 `neo4j`：

```bash
# 改前
EXTRAS=api,postgres,neo4j
# 改后
EXTRAS=api,postgres
```

### 5. 数据存储路径

Kuzu 和 LanceDB 的数据存储在 Cognee 容器的 `/app/data` 目录下（已挂载到 `/data/CozyMemory/cognee/data`），无需额外配置。

多租户模式下，Cognee 会按 `{owner_id}/{dataset_id}` 目录结构创建隔离的数据库文件：
```
/app/data/
  databases/
    {user_id}/
      {dataset_id}.kuzu    # 图数据库
    lancedb/
      {user_id}/
        {dataset_id}/      # 向量索引
```

### 6. 已有数据处理

切换后 Neo4j 中的知识图谱数据不会自动迁移。处理方式：

- 试用阶段的测试数据：直接丢弃，通过 API 重新 `add` + `cognify` 即可
- 如果有生产数据需要保留：先导出文档文本，切换后重新导入并 cognify

### 7. CozyMemory 代码层影响

**无代码改动**。CozyMemory 通过 REST API 与 Cognee 通信，不直接操作图/向量数据库。以下现有机制在切换后行为更加正确：

- `CogneeClient.search(dataset=...)` — 开启 access control 后，Cognee 会真正按 dataset 过滤
- `_knowledge_scope.py` 的 `ensure_owned()` — 继续作为 API 层的双重保护
- `knowledge.py` 强制 App Key 指定 dataset — 继续生效

### 8. 验证计划

切换后需验证：

1. **基本功能**：创建 dataset → add 文档 → cognify → search → 结果仅来自指定 dataset
2. **跨 App 隔离**：App A 添加数据到 dataset "faq"，App B 搜索 "faq" → 404（不同 dataset ID）
3. **同名 dataset 隔离**：两个 App 分别创建 "faq" dataset，各自添加不同数据，搜索结果互不干扰
4. **Bootstrap key**：Operator 用 bootstrap key 搜索不指定 dataset → 应按 Cognee 默认行为返回
5. **健康检查**：`/api/v1/health` 的 Cognee 引擎状态正常

## 不在范围内

- FalkorDB adapter 开发（Phase 2）
- Mem0 / Memobase 隔离改动（已可靠）
- CozyMemory 应用层代码改动（不需要）
- Neo4j 数据迁移工具（手动重新 cognify 即可）
- Cognee 前端 UI 变更
