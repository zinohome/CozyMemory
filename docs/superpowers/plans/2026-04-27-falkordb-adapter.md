# FalkorDB Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 CozyCognee 中实现 FalkorDB 图数据库 adapter，替换已归档的 Kuzu 成为 Cognee 的多租户图数据库。

**Architecture:** 实现 Cognee 的 `GraphDBInterface`（26 个抽象方法）和 `FalkorDatasetDatabaseHandler`（多租户隔离）。使用 `falkordb` Python 异步客户端（基于 redis.asyncio），通过 OpenCypher 查询与 FalkorDB 服务交互。代码放在 CozyCognee 仓库中，通过 patch/构建脚本注入 Cognee 镜像。

**Tech Stack:** FalkorDB (Redis-based graph DB), `falkordb>=1.6.0` Python client, OpenCypher, `redis.asyncio`

**Spec:** `docs/superpowers/specs/2026-04-27-falkordb-adapter-design.md`

**重要约束：** CozyCognee 的 `projects/` 目录是上游 Cognee 的 clone，不允许提交。所有新代码放在 `CozyCognee/cognee-extensions/` 目录下，通过 Dockerfile `COPY` 注入到镜像的 `/app/cognee/` 对应路径。

---

## File Structure

| Action | Path (in CozyCognee repo) | Injected To (in Docker image) | Responsibility |
|--------|--------------------------|-------------------------------|---------------|
| Create | `cognee-extensions/graph/falkor/__init__.py` | `/app/cognee/infrastructure/databases/graph/falkor/__init__.py` | 模块导出 |
| Create | `cognee-extensions/graph/falkor/adapter.py` | `/app/cognee/infrastructure/databases/graph/falkor/adapter.py` | FalkorAdapter 核心 |
| Create | `cognee-extensions/graph/falkor/FalkorDatasetDatabaseHandler.py` | `/app/cognee/infrastructure/databases/graph/falkor/FalkorDatasetDatabaseHandler.py` | 多租户隔离 |
| Create | `patches/002-register-falkor-adapter.patch` | Applied at build time | 注册 falkor provider |
| Modify | `deployment/docker/cognee/Dockerfile` | N/A | 安装 falkordb 包 + COPY 扩展代码 |

---

### Task 1: FalkorAdapter 骨架 — 连接管理 + query()

**Files:**
- Create: `cognee-extensions/graph/falkor/__init__.py`
- Create: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 创建模块目录和 `__init__.py`**

```python
# cognee-extensions/graph/falkor/__init__.py
from .adapter import FalkorAdapter
from .FalkorDatasetDatabaseHandler import FalkorDatasetDatabaseHandler

__all__ = ["FalkorAdapter", "FalkorDatasetDatabaseHandler"]
```

- [ ] **Step 2: 创建 adapter 骨架 — 连接管理**

```python
# cognee-extensions/graph/falkor/adapter.py
"""Adapter for FalkorDB graph database."""

import json
import logging
from uuid import UUID
from typing import Dict, Any, List, Union, Optional, Tuple, Type

from falkordb.asyncio import FalkorDB
from redis.asyncio import BlockingConnectionPool

from cognee.infrastructure.databases.graph.graph_db_interface import GraphDBInterface
from cognee.infrastructure.engine import DataPoint

logger = logging.getLogger(__name__)


class FalkorAdapter(GraphDBInterface):
    """
    Adapter for FalkorDB graph database operations.

    FalkorDB is a Redis-based graph database supporting OpenCypher queries.
    Each graph is identified by name, enabling per-dataset isolation for multi-tenancy.
    """

    def __init__(
        self,
        graph_database_url: str = "redis://localhost:6379",
        graph_database_port: str = "",
        graph_database_username: str = "",
        graph_database_password: str = "",
        graph_database_key: str = "",
        database_name: str = "cognee",
    ):
        """Initialize FalkorDB connection.

        Args:
            graph_database_url: Redis URL (e.g., redis://host:port)
            graph_database_port: Optional port override (extracted from URL if not provided)
            graph_database_username: Redis username (default: empty)
            graph_database_password: Redis password (default: empty)
            graph_database_key: Unused, kept for interface compatibility
            database_name: FalkorDB graph name (each dataset gets a unique name)
        """
        self.url = graph_database_url
        self.port = graph_database_port
        self.username = graph_database_username
        self.password = graph_database_password
        self.graph_name = database_name
        self._db: Optional[FalkorDB] = None
        self._pool: Optional[BlockingConnectionPool] = None

    async def _ensure_connection(self):
        """Lazily initialize the FalkorDB async connection."""
        if self._db is not None:
            return
        self._pool = BlockingConnectionPool.from_url(
            self.url,
            max_connections=16,
            timeout=30,
            decode_responses=True,
            username=self.username or None,
            password=self.password or None,
        )
        self._db = FalkorDB(connection_pool=self._pool)

    async def _get_graph(self):
        """Get the FalkorDB Graph object for the current graph_name."""
        await self._ensure_connection()
        return self._db.select_graph(self.graph_name)

    # ── Helpers ──

    @staticmethod
    def _serialize_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize complex property values to JSON strings for FalkorDB storage."""
        serialized = {}
        for key, value in properties.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            elif isinstance(value, UUID):
                serialized[key] = str(value)
            elif isinstance(value, list) and all(isinstance(v, (str, int, float, bool)) for v in value):
                serialized[key] = value
            else:
                serialized[key] = json.dumps(value, default=str)
        return serialized

    @staticmethod
    def _deserialize_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to deserialize JSON-encoded property values."""
        result = {}
        for key, value in properties.items():
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, (dict, list)):
                        result[key] = parsed
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
            result[key] = value
        return result

    @staticmethod
    def _node_to_properties(node) -> Dict[str, Any]:
        """Extract properties from a FalkorDB Node result object."""
        props = dict(node.properties) if hasattr(node, "properties") else {}
        if hasattr(node, "labels") and node.labels:
            props["_labels"] = node.labels
        return FalkorAdapter._deserialize_properties(props)

    @staticmethod
    def _datapoint_to_properties(dp: DataPoint) -> Dict[str, Any]:
        """Convert a Cognee DataPoint to a flat property dict for FalkorDB."""
        props = {}
        if hasattr(dp, "id"):
            props["id"] = str(dp.id)
        # Extract all model fields
        for field_name in dp.model_fields:
            value = getattr(dp, field_name, None)
            if value is not None:
                props[field_name] = value
        props["_node_type"] = type(dp).__name__
        return FalkorAdapter._serialize_properties(props)

    @staticmethod
    def _get_node_label(node: Union[DataPoint, str]) -> str:
        """Get the Cypher label for a node."""
        if isinstance(node, str):
            return "Node"
        return type(node).__name__

    # ── Core Interface Methods ──

    async def query(self, query: str, params: dict = None) -> List[Any]:
        """Execute a raw OpenCypher query."""
        graph = await self._get_graph()
        result = await graph.query(query, params=params or {})
        return result.result_set

    async def is_empty(self) -> bool:
        """Check if the graph has no nodes."""
        graph = await self._get_graph()
        try:
            result = await graph.query("MATCH (n) RETURN count(n) AS cnt")
            count = result.result_set[0][0] if result.result_set else 0
            return count == 0
        except Exception:
            # Graph doesn't exist yet → empty
            return True
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/projects/CozyCognee
git add cognee-extensions/graph/falkor/__init__.py cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): add FalkorAdapter skeleton with connection management and query()"
```

---

### Task 2: 节点 CRUD — add_node, add_nodes, get_node, get_nodes, delete_node, delete_nodes

**Files:**
- Modify: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 实现 add_node()**

在 `FalkorAdapter` 类中添加：

```python
    async def add_node(
        self, node: Union[DataPoint, str], properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a single node. Uses MERGE to upsert by id."""
        graph = await self._get_graph()
        if isinstance(node, str):
            props = self._serialize_properties(properties or {})
            props["id"] = node
            label = props.pop("_node_type", "Node")
        else:
            props = self._datapoint_to_properties(node)
            label = self._get_node_label(node)

        node_id = props.get("id", "")
        set_clause = ", ".join(f"n.{k} = ${k}" for k in props if k != "id")
        cypher = f"MERGE (n:{label} {{id: $id}}) SET {set_clause}" if set_clause else f"MERGE (n:{label} {{id: $id}})"
        await graph.query(cypher, params=props)
```

- [ ] **Step 2: 实现 add_nodes()**

```python
    async def add_nodes(self, nodes: Union[List[Tuple[str, Dict]], List[DataPoint]]) -> None:
        """Add multiple nodes. Each node is upserted individually."""
        for node in nodes:
            if isinstance(node, DataPoint):
                await self.add_node(node)
            elif isinstance(node, tuple) and len(node) == 2:
                node_id, props = node
                await self.add_node(node_id, props)
            else:
                await self.add_node(node)
```

- [ ] **Step 3: 实现 get_node() 和 get_nodes()**

```python
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single node by ID."""
        graph = await self._get_graph()
        result = await graph.query(
            "MATCH (n {id: $id}) RETURN n",
            params={"id": str(node_id)},
        )
        if not result.result_set:
            return None
        return self._node_to_properties(result.result_set[0][0])

    async def get_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve multiple nodes by their IDs."""
        if not node_ids:
            return []
        graph = await self._get_graph()
        ids = [str(nid) for nid in node_ids]
        result = await graph.query(
            "MATCH (n) WHERE n.id IN $ids RETURN n",
            params={"ids": ids},
        )
        return [self._node_to_properties(row[0]) for row in result.result_set]
```

- [ ] **Step 4: 实现 delete_node() 和 delete_nodes()**

```python
    async def delete_node(self, node_id: str) -> None:
        """Delete a node and all its edges."""
        graph = await self._get_graph()
        await graph.query(
            "MATCH (n {id: $id}) DETACH DELETE n",
            params={"id": str(node_id)},
        )

    async def delete_nodes(self, node_ids: List[str]) -> None:
        """Delete multiple nodes and their edges."""
        if not node_ids:
            return
        graph = await self._get_graph()
        ids = [str(nid) for nid in node_ids]
        await graph.query(
            "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
            params={"ids": ids},
        )
```

- [ ] **Step 5: Commit**

```bash
git add cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): implement node CRUD — add/get/delete node(s)"
```

---

### Task 3: 边 CRUD — add_edge, add_edges, has_edge, has_edges, get_edges

**Files:**
- Modify: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 实现 add_edge()**

```python
    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create or update an edge between two nodes."""
        graph = await self._get_graph()
        props = self._serialize_properties(properties or {})
        set_clause = ", ".join(f"r.{k} = ${k}" for k in props)
        cypher = (
            f"MATCH (a {{id: $src}}), (b {{id: $dst}}) "
            f"MERGE (a)-[r:{relationship_name}]->(b)"
        )
        if set_clause:
            cypher += f" SET {set_clause}"
        params = {"src": str(source_id), "dst": str(target_id), **props}
        await graph.query(cypher, params=params)
```

- [ ] **Step 2: 实现 add_edges()**

```python
    async def add_edges(
        self, edges: Union[List[Tuple[str, str, str, Optional[Dict[str, Any]]]], List]
    ) -> None:
        """Add multiple edges."""
        for edge in edges:
            if isinstance(edge, tuple) and len(edge) >= 3:
                src, dst, rel = edge[0], edge[1], edge[2]
                props = edge[3] if len(edge) > 3 else None
                await self.add_edge(str(src), str(dst), rel, props)
```

- [ ] **Step 3: 实现 has_edge() 和 has_edges()**

```python
    async def has_edge(self, source_id: str, target_id: str, relationship_name: str) -> bool:
        """Check if an edge exists between two nodes."""
        graph = await self._get_graph()
        result = await graph.query(
            f"MATCH (a {{id: $src}})-[r:{relationship_name}]->(b {{id: $dst}}) RETURN count(r) AS cnt",
            params={"src": str(source_id), "dst": str(target_id)},
        )
        return result.result_set[0][0] > 0 if result.result_set else False

    async def has_edges(self, edges: List[Tuple[str, str, str, Dict[str, Any]]]) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """Return the subset of edges that exist in the graph."""
        existing = []
        for edge in edges:
            src, dst, rel = str(edge[0]), str(edge[1]), edge[2]
            if await self.has_edge(src, dst, rel):
                existing.append(edge)
        return existing
```

- [ ] **Step 4: 实现 get_edges()**

```python
    async def get_edges(self, node_id: str) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """Get all edges connected to a node (outgoing and incoming)."""
        graph = await self._get_graph()
        result = await graph.query(
            "MATCH (a {id: $id})-[r]->(b) RETURN a.id, b.id, type(r), r",
            params={"id": str(node_id)},
        )
        edges = []
        for row in result.result_set:
            src_id = row[0]
            dst_id = row[1]
            rel_name = row[2]
            edge_props = self._deserialize_properties(dict(row[3].properties)) if hasattr(row[3], "properties") else {}
            edges.append((str(src_id), str(dst_id), rel_name, edge_props))

        # Also get incoming edges
        result_in = await graph.query(
            "MATCH (a)-[r]->(b {id: $id}) RETURN a.id, b.id, type(r), r",
            params={"id": str(node_id)},
        )
        for row in result_in.result_set:
            src_id = row[0]
            dst_id = row[1]
            rel_name = row[2]
            edge_props = self._deserialize_properties(dict(row[3].properties)) if hasattr(row[3], "properties") else {}
            edges.append((str(src_id), str(dst_id), rel_name, edge_props))
        return edges
```

- [ ] **Step 5: Commit**

```bash
git add cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): implement edge CRUD — add/has/get edge(s)"
```

---

### Task 4: 图遍历 — get_neighbors, get_connections, get_neighborhood, get_nodeset_subgraph

**Files:**
- Modify: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 实现 get_neighbors()**

```python
    async def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all nodes connected to the specified node (both directions)."""
        graph = await self._get_graph()
        result = await graph.query(
            "MATCH (a {id: $id})--(b) RETURN DISTINCT b",
            params={"id": str(node_id)},
        )
        return [self._node_to_properties(row[0]) for row in result.result_set]
```

- [ ] **Step 2: 实现 get_connections()**

```python
    async def get_connections(
        self, node_id: Union[str, UUID]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
        """Get all (source_node, edge, target_node) triples connected to a node."""
        graph = await self._get_graph()
        nid = str(node_id)
        # Outgoing
        result = await graph.query(
            "MATCH (a {id: $id})-[r]->(b) RETURN a, r, b",
            params={"id": nid},
        )
        connections = []
        for row in result.result_set:
            a_props = self._node_to_properties(row[0])
            r_props = self._deserialize_properties(dict(row[1].properties)) if hasattr(row[1], "properties") else {}
            r_props["relationship_name"] = row[1].relation if hasattr(row[1], "relation") else ""
            b_props = self._node_to_properties(row[2])
            connections.append((a_props, r_props, b_props))
        # Incoming
        result_in = await graph.query(
            "MATCH (a)-[r]->(b {id: $id}) RETURN a, r, b",
            params={"id": nid},
        )
        for row in result_in.result_set:
            a_props = self._node_to_properties(row[0])
            r_props = self._deserialize_properties(dict(row[1].properties)) if hasattr(row[1], "properties") else {}
            r_props["relationship_name"] = row[1].relation if hasattr(row[1], "relation") else ""
            b_props = self._node_to_properties(row[2])
            connections.append((a_props, r_props, b_props))
        return connections
```

- [ ] **Step 3: 实现 get_neighborhood()**

```python
    async def get_neighborhood(
        self,
        node_ids: List[str],
        depth: int = 1,
        edge_types: Optional[List[str]] = None,
    ) -> Tuple[List[Tuple[str, Dict]], List[Tuple[str, str, str, Dict]]]:
        """Get k-hop neighborhood around seed nodes."""
        graph = await self._get_graph()
        ids = [str(nid) for nid in node_ids]

        if edge_types:
            rel_pattern = "|".join(edge_types)
            cypher = (
                f"MATCH path = (a)-[:{rel_pattern}*1..{depth}]-(b) "
                f"WHERE a.id IN $ids "
                f"UNWIND nodes(path) AS n "
                f"UNWIND relationships(path) AS r "
                f"RETURN DISTINCT n, r, startNode(r).id AS src, endNode(r).id AS dst, type(r) AS rel_type"
            )
        else:
            cypher = (
                f"MATCH path = (a)-[*1..{depth}]-(b) "
                f"WHERE a.id IN $ids "
                f"UNWIND nodes(path) AS n "
                f"UNWIND relationships(path) AS r "
                f"RETURN DISTINCT n, r, startNode(r).id AS src, endNode(r).id AS dst, type(r) AS rel_type"
            )

        result = await graph.query(cypher, params={"ids": ids})

        nodes_dict: Dict[str, Dict] = {}
        edges_set: set = set()
        edge_list: List[Tuple[str, str, str, Dict]] = []

        for row in result.result_set:
            node_obj = row[0]
            node_props = self._node_to_properties(node_obj)
            nid = node_props.get("id", "")
            if nid and nid not in nodes_dict:
                nodes_dict[nid] = node_props

            src = str(row[2])
            dst = str(row[3])
            rel = row[4]
            edge_key = (src, dst, rel)
            if edge_key not in edges_set:
                edges_set.add(edge_key)
                edge_props = self._deserialize_properties(dict(row[1].properties)) if hasattr(row[1], "properties") else {}
                edge_list.append((src, dst, rel, edge_props))

        nodes = [(nid, props) for nid, props in nodes_dict.items()]
        return nodes, edge_list
```

- [ ] **Step 4: 实现 get_nodeset_subgraph()**

```python
    async def get_nodeset_subgraph(
        self, node_type: Type[Any], node_name: List[str], node_name_filter_operator: str = "OR"
    ) -> Tuple[List[Tuple[int, dict]], List[Tuple[int, int, str, dict]]]:
        """Fetch subgraph for nodes of a specific type matching given names."""
        graph = await self._get_graph()
        label = node_type.__name__ if hasattr(node_type, "__name__") else str(node_type)

        if node_name_filter_operator == "AND":
            where_clause = " AND ".join(f"n.name = '{name}'" for name in node_name)
        else:
            where_clause = f"n.name IN $names"

        cypher = (
            f"MATCH (n:{label})-[r]-(m) "
            f"WHERE {where_clause} "
            f"RETURN n, r, m, type(r) AS rel_type, startNode(r).id AS src, endNode(r).id AS dst"
        )
        params = {"names": node_name} if node_name_filter_operator != "AND" else {}
        result = await graph.query(cypher, params=params)

        nodes_dict: Dict[str, Tuple[int, dict]] = {}
        edges: List[Tuple[int, int, str, dict]] = []
        id_counter = 0

        for row in result.result_set:
            for node_obj in [row[0], row[2]]:
                props = self._node_to_properties(node_obj)
                nid = props.get("id", "")
                if nid not in nodes_dict:
                    nodes_dict[nid] = (id_counter, props)
                    id_counter += 1

            src = str(row[4])
            dst = str(row[5])
            rel = row[3]
            edge_props = self._deserialize_properties(dict(row[1].properties)) if hasattr(row[1], "properties") else {}
            src_idx = nodes_dict.get(src, (0, {}))[0]
            dst_idx = nodes_dict.get(dst, (0, {}))[0]
            edges.append((src_idx, dst_idx, rel, edge_props))

        nodes = list(nodes_dict.values())
        return nodes, edges
```

- [ ] **Step 5: Commit**

```bash
git add cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): implement graph traversal — neighbors, connections, neighborhood, subgraph"
```

---

### Task 5: 图管理 — delete_graph, get_graph_data, get_graph_metrics, get_filtered_graph_data

**Files:**
- Modify: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 实现 delete_graph()**

```python
    async def delete_graph(self) -> None:
        """Delete the entire graph."""
        graph = await self._get_graph()
        try:
            await graph.delete()
        except Exception as e:
            logger.warning(f"Failed to delete graph '{self.graph_name}': {e}")
```

- [ ] **Step 2: 实现 get_graph_data()**

```python
    async def get_graph_data(self) -> Tuple[List[Tuple[str, Dict]], List[Tuple[str, str, str, Dict]]]:
        """Retrieve all nodes and edges."""
        graph = await self._get_graph()

        # Get all nodes
        node_result = await graph.query("MATCH (n) RETURN n")
        nodes = []
        for row in node_result.result_set:
            props = self._node_to_properties(row[0])
            nid = props.get("id", str(row[0].node_id) if hasattr(row[0], "node_id") else "")
            nodes.append((nid, props))

        # Get all edges
        edge_result = await graph.query(
            "MATCH (a)-[r]->(b) RETURN a.id, b.id, type(r), r"
        )
        edges = []
        for row in edge_result.result_set:
            edge_props = self._deserialize_properties(dict(row[3].properties)) if hasattr(row[3], "properties") else {}
            edges.append((str(row[0]), str(row[1]), row[2], edge_props))

        return nodes, edges
```

- [ ] **Step 3: 实现 get_graph_metrics()**

```python
    async def get_graph_metrics(self, include_optional: bool = False) -> Dict[str, Any]:
        """Get graph statistics."""
        graph = await self._get_graph()
        metrics = {}
        try:
            node_count = await graph.query("MATCH (n) RETURN count(n) AS cnt")
            metrics["node_count"] = node_count.result_set[0][0] if node_count.result_set else 0

            edge_count = await graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt")
            metrics["edge_count"] = edge_count.result_set[0][0] if edge_count.result_set else 0

            if include_optional:
                label_result = await graph.query("MATCH (n) RETURN DISTINCT labels(n) AS lbl, count(n) AS cnt")
                metrics["labels"] = {str(row[0]): row[1] for row in label_result.result_set}

                rel_result = await graph.query("MATCH ()-[r]->() RETURN DISTINCT type(r) AS t, count(r) AS cnt")
                metrics["relationship_types"] = {row[0]: row[1] for row in rel_result.result_set}
        except Exception as e:
            logger.warning(f"Error getting graph metrics: {e}")
            metrics.setdefault("node_count", 0)
            metrics.setdefault("edge_count", 0)

        return metrics
```

- [ ] **Step 4: 实现 get_filtered_graph_data()**

```python
    async def get_filtered_graph_data(
        self, attribute_filters: List[Dict[str, List[Union[str, int]]]]
    ) -> Tuple[List[Tuple[str, Dict]], List[Tuple[str, str, str, Dict]]]:
        """Retrieve nodes and edges matching attribute filters."""
        graph = await self._get_graph()

        where_clauses = []
        params = {}
        for i, filter_dict in enumerate(attribute_filters):
            for attr, values in filter_dict.items():
                param_name = f"fv_{i}_{attr}"
                where_clauses.append(f"n.{attr} IN ${param_name}")
                params[param_name] = values

        if not where_clauses:
            return await self.get_graph_data()

        where_str = " OR ".join(where_clauses)
        node_result = await graph.query(
            f"MATCH (n) WHERE {where_str} RETURN n", params=params
        )
        node_ids = set()
        nodes = []
        for row in node_result.result_set:
            props = self._node_to_properties(row[0])
            nid = props.get("id", "")
            nodes.append((nid, props))
            node_ids.add(nid)

        # Get edges between matched nodes
        if not node_ids:
            return nodes, []

        ids_list = list(node_ids)
        edge_result = await graph.query(
            "MATCH (a)-[r]->(b) WHERE a.id IN $ids AND b.id IN $ids RETURN a.id, b.id, type(r), r",
            params={"ids": ids_list},
        )
        edges = []
        for row in edge_result.result_set:
            edge_props = self._deserialize_properties(dict(row[3].properties)) if hasattr(row[3], "properties") else {}
            edges.append((str(row[0]), str(row[1]), row[2], edge_props))

        return nodes, edges
```

- [ ] **Step 5: Commit**

```bash
git add cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): implement graph management — delete, export, metrics, filter"
```

---

### Task 6: 可选方法 — feedback weights + triplets

**Files:**
- Modify: `cognee-extensions/graph/falkor/adapter.py`

- [ ] **Step 1: 实现 feedback weights（基础版本）**

```python
    async def get_node_feedback_weights(self, node_ids: List[str]) -> Dict[str, float]:
        """Retrieve feedback weights for nodes."""
        if not node_ids:
            return {}
        graph = await self._get_graph()
        ids = [str(nid) for nid in node_ids]
        result = await graph.query(
            "MATCH (n) WHERE n.id IN $ids AND n.feedback_weight IS NOT NULL "
            "RETURN n.id, n.feedback_weight",
            params={"ids": ids},
        )
        return {str(row[0]): float(row[1]) for row in result.result_set}

    async def set_node_feedback_weights(
        self, node_feedback_weights: Dict[str, float]
    ) -> Dict[str, bool]:
        """Set feedback weights on nodes."""
        if not node_feedback_weights:
            return {}
        graph = await self._get_graph()
        results = {}
        for node_id, weight in node_feedback_weights.items():
            try:
                await graph.query(
                    "MATCH (n {id: $id}) SET n.feedback_weight = $weight",
                    params={"id": str(node_id), "weight": weight},
                )
                results[node_id] = True
            except Exception:
                results[node_id] = False
        return results

    async def get_edge_feedback_weights(self, edge_object_ids: List[str]) -> Dict[str, float]:
        """Retrieve feedback weights for edges by object_id property."""
        if not edge_object_ids:
            return {}
        graph = await self._get_graph()
        ids = [str(eid) for eid in edge_object_ids]
        result = await graph.query(
            "MATCH ()-[r]->() WHERE r.object_id IN $ids AND r.feedback_weight IS NOT NULL "
            "RETURN r.object_id, r.feedback_weight",
            params={"ids": ids},
        )
        return {str(row[0]): float(row[1]) for row in result.result_set}

    async def set_edge_feedback_weights(
        self, edge_feedback_weights: Dict[str, float]
    ) -> Dict[str, bool]:
        """Set feedback weights on edges."""
        if not edge_feedback_weights:
            return {}
        graph = await self._get_graph()
        results = {}
        for edge_id, weight in edge_feedback_weights.items():
            try:
                await graph.query(
                    "MATCH ()-[r]->() WHERE r.object_id = $id SET r.feedback_weight = $weight",
                    params={"id": str(edge_id), "weight": weight},
                )
                results[edge_id] = True
            except Exception:
                results[edge_id] = False
        return results
```

- [ ] **Step 2: 实现 get_triplets_batch()**

```python
    async def get_triplets_batch(self, offset: int, limit: int) -> List[Dict[str, Any]]:
        """Retrieve a batch of (source, edge, target) triplets."""
        graph = await self._get_graph()
        result = await graph.query(
            "MATCH (a)-[r]->(b) RETURN a, type(r), r, b SKIP $offset LIMIT $limit",
            params={"offset": offset, "limit": limit},
        )
        triplets = []
        for row in result.result_set:
            triplets.append({
                "source": self._node_to_properties(row[0]),
                "relationship": row[1],
                "edge_properties": self._deserialize_properties(dict(row[2].properties)) if hasattr(row[2], "properties") else {},
                "target": self._node_to_properties(row[3]),
            })
        return triplets
```

- [ ] **Step 3: Commit**

```bash
git add cognee-extensions/graph/falkor/adapter.py
git commit -m "feat(falkor): implement feedback weights and triplets batch"
```

---

### Task 7: FalkorDatasetDatabaseHandler — 多租户隔离

**Files:**
- Create: `cognee-extensions/graph/falkor/FalkorDatasetDatabaseHandler.py`

- [ ] **Step 1: 实现 handler**

```python
# cognee-extensions/graph/falkor/FalkorDatasetDatabaseHandler.py
"""FalkorDB dataset database handler for multi-tenant graph isolation."""

from uuid import UUID
from typing import Optional

from cognee.modules.users.models import User, DatasetDatabase
from cognee.infrastructure.databases.dataset_database_handler import (
    DatasetDatabaseHandlerInterface,
)


class FalkorDatasetDatabaseHandler(DatasetDatabaseHandlerInterface):
    """
    Handler for FalkorDB per-dataset graph isolation.

    Each dataset gets a unique named graph in FalkorDB: cognee_{user_id}_{dataset_id}.
    All graphs share the same FalkorDB/Redis instance but are completely isolated at
    the graph level — queries only see data within their named graph.
    """

    @classmethod
    async def create_dataset(cls, dataset_id: Optional[UUID], user: Optional[User]) -> dict:
        """Return connection info mapping this dataset to a unique FalkorDB graph."""
        from cognee.infrastructure.databases.graph.config import get_graph_config

        graph_config = get_graph_config()

        if graph_config.graph_database_provider != "falkor":
            raise ValueError(
                "FalkorDatasetDatabaseHandler can only be used with FalkorDB graph provider."
            )

        # Each dataset gets a uniquely named graph
        graph_name = f"cognee_{user.id}_{dataset_id}" if user else f"cognee_{dataset_id}"

        return {
            "graph_database_name": graph_name,
            "graph_database_url": graph_config.graph_database_url,
            "graph_database_provider": "falkor",
            "graph_dataset_database_handler": "falkor",
            "graph_database_connection_info": {
                "graph_database_username": graph_config.graph_database_username,
                "graph_database_password": graph_config.graph_database_password,
            },
        }

    @classmethod
    async def delete_dataset(cls, dataset_database: DatasetDatabase):
        """Delete the FalkorDB graph for a dataset."""
        from cognee.infrastructure.databases.graph.get_graph_engine import (
            create_graph_engine,
        )

        graph_engine = create_graph_engine(
            graph_database_provider="falkor",
            graph_database_url=dataset_database.graph_database_url,
            graph_database_name=dataset_database.graph_database_name,
            graph_database_username=dataset_database.graph_database_connection_info.get(
                "graph_database_username", ""
            ),
            graph_database_password=dataset_database.graph_database_connection_info.get(
                "graph_database_password", ""
            ),
            graph_file_path="",
            graph_dataset_database_handler="",
            graph_database_port="",
            graph_database_key="",
        )
        await graph_engine.delete_graph()
```

- [ ] **Step 2: Commit**

```bash
git add cognee-extensions/graph/falkor/FalkorDatasetDatabaseHandler.py
git commit -m "feat(falkor): implement FalkorDatasetDatabaseHandler for multi-tenant isolation"
```

---

### Task 8: Cognee 集成 — patch + Dockerfile

**Files:**
- Create: `patches/002-register-falkor-adapter.patch`
- Modify: `deployment/docker/cognee/Dockerfile`

- [ ] **Step 1: 创建注册 patch**

```patch
# patches/002-register-falkor-adapter.patch
--- a/cognee/infrastructure/databases/graph/get_graph_engine.py
+++ b/cognee/infrastructure/databases/graph/get_graph_engine.py
@@ -143,6 +143,15 @@
         from .kuzu.adapter import KuzuAdapter
 
         return KuzuAdapter(db_path=graph_file_path)
+
+    elif graph_database_provider == "falkor":
+        if not graph_database_url:
+            raise EnvironmentError("Missing required FalkorDB URL.")
+
+        from .falkor.adapter import FalkorAdapter
+
+        return FalkorAdapter(
+            graph_database_url=graph_database_url,
+            graph_database_port=graph_database_port,
+            graph_database_username=graph_database_username,
+            graph_database_password=graph_database_password,
+            database_name=graph_database_name or "cognee",
+        )
 
     elif graph_database_provider == "kuzu-remote":
--- a/cognee/infrastructure/databases/dataset_database_handler/supported_dataset_database_handlers.py
+++ b/cognee/infrastructure/databases/dataset_database_handler/supported_dataset_database_handlers.py
@@ -11,6 +11,9 @@
 from cognee.infrastructure.databases.vector.pgvector.PGVectorDatasetDatabaseHandler import (
     PGVectorDatasetDatabaseHandler,
 )
+from cognee.infrastructure.databases.graph.falkor.FalkorDatasetDatabaseHandler import (
+    FalkorDatasetDatabaseHandler,
+)
 
 supported_dataset_database_handlers = {
     "neo4j_aura_dev": {
@@ -22,4 +25,5 @@
         "handler_instance": PGVectorDatasetDatabaseHandler,
         "handler_provider": "pgvector",
     },
     "kuzu": {"handler_instance": KuzuDatasetDatabaseHandler, "handler_provider": "kuzu"},
+    "falkor": {"handler_instance": FalkorDatasetDatabaseHandler, "handler_provider": "falkor"},
 }
```

- [ ] **Step 2: 修改 Dockerfile — 安装 falkordb 包 + COPY 扩展代码**

在 `deployment/docker/cognee/Dockerfile` 的现有 patch 应用之后、第二个 `uv sync` 之前，添加：

```dockerfile
# Install FalkorDB Python client
RUN pip install falkordb>=1.6.0

# Copy CozyCognee FalkorDB adapter extension
COPY cognee-extensions/graph/falkor /app/cognee/infrastructure/databases/graph/falkor
```

在 patch 应用部分（已有 `patch_cors.py`），添加 FalkorDB 注册 patch：

```dockerfile
# Apply FalkorDB registration patch
COPY patches/002-register-falkor-adapter.patch /tmp/002-register-falkor-adapter.patch
RUN cd /app && git apply /tmp/002-register-falkor-adapter.patch 2>/dev/null || \
    (echo "FalkorDB patch: trying manual apply..." && \
     python3 -c "
import re, sys
# Patch get_graph_engine.py
f = '/app/cognee/infrastructure/databases/graph/get_graph_engine.py'
content = open(f).read()
if 'falkor' not in content:
    insert = '''
    elif graph_database_provider == \"falkor\":
        if not graph_database_url:
            raise EnvironmentError(\"Missing required FalkorDB URL.\")
        from .falkor.adapter import FalkorAdapter
        return FalkorAdapter(
            graph_database_url=graph_database_url,
            graph_database_port=graph_database_port,
            graph_database_username=graph_database_username,
            graph_database_password=graph_database_password,
            database_name=graph_database_name or \"cognee\",
        )
'''
    content = content.replace(
        'elif graph_database_provider == \"kuzu-remote\"',
        insert + '\n    elif graph_database_provider == \"kuzu-remote\"'
    )
    open(f, 'w').write(content)
    print('Patched get_graph_engine.py')

# Patch supported_dataset_database_handlers.py
f2 = '/app/cognee/infrastructure/databases/dataset_database_handler/supported_dataset_database_handlers.py'
content2 = open(f2).read()
if 'falkor' not in content2:
    content2 = content2.replace(
        'supported_dataset_database_handlers = {',
        'from cognee.infrastructure.databases.graph.falkor.FalkorDatasetDatabaseHandler import FalkorDatasetDatabaseHandler\n\nsupported_dataset_database_handlers = {'
    )
    content2 = content2.rstrip().rstrip('}')
    content2 += '    \"falkor\": {\"handler_instance\": FalkorDatasetDatabaseHandler, \"handler_provider\": \"falkor\"},\n}\n'
    open(f2, 'w').write(content2)
    print('Patched supported_dataset_database_handlers.py')
") && rm /tmp/002-register-falkor-adapter.patch
```

- [ ] **Step 3: Commit**

```bash
git add patches/002-register-falkor-adapter.patch deployment/docker/cognee/Dockerfile
git commit -m "feat(falkor): add registration patch and Dockerfile integration"
```

---

### Task 9: docker-compose 配置 + 部署切换

**Files:**
- Modify: `/home/ubuntu/CozyProjects/CozyMemory/base_runtime/docker-compose.1panel.yml`

- [ ] **Step 1: 在基础设施层添加 FalkorDB 服务**

在 `minio:` 服务之后、Neo4j 注释之前添加：

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

- [ ] **Step 2: 切换 Cognee 环境变量**

将 cognee 服务的环境变量：

```yaml
      - VECTOR_DB_PROVIDER=lancedb
      - GRAPH_DATABASE_PROVIDER=kuzu
```

替换为：

```yaml
      - VECTOR_DB_PROVIDER=lancedb
      - GRAPH_DATABASE_PROVIDER=falkor
      - GRAPH_DATABASE_URL=redis://falkordb:6379
      - GRAPH_DATABASE_NAME=cognee
```

在 depends_on 中添加 `falkordb`：

```yaml
    depends_on:
      - postgres
      - redis
      - minio
      - falkordb
```

- [ ] **Step 3: 重建 Cognee 镜像并部署**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
sudo base_runtime/build.sh cognee
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d --force-recreate cognee falkordb
```

- [ ] **Step 4: 验证健康检查**

```bash
# 等待 Cognee 启动
sleep 30
curl -s http://192.168.66.41:8000/api/v1/health | python3 -m json.tool
# 期望：所有引擎 healthy
```

- [ ] **Step 5: Commit**

```bash
git add base_runtime/docker-compose.1panel.yml
git commit -m "feat(cognee): switch from Kuzu to FalkorDB for multi-tenant graph isolation"
```

---

### Task 10: 端到端验证 — 多租户隔离测试

> 此任务无代码变更，仅为验证。

- [ ] **Step 1: 确认 FalkorDB 服务运行**

```bash
sudo docker exec cozy_falkordb redis-cli PING
# 期望：PONG

sudo docker exec cozy_falkordb redis-cli GRAPH.LIST
# 期望：空列表或初始 graph
```

- [ ] **Step 2: 通过 CozyMemory API 添加知识数据（App A）**

```bash
APP_A_KEY="<App A 的 API Key>"

# 创建 dataset
curl -s -X POST "http://192.168.66.41:8000/api/v1/knowledge/datasets?name=test-falkor" \
  -H "X-Cozy-API-Key: $APP_A_KEY" | python3 -m json.tool

# 添加数据
curl -s -X POST http://192.168.66.41:8000/api/v1/knowledge/add \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"dataset_id":"<dataset_id>","data":"FalkorDB is a Redis-based graph database."}' | python3 -m json.tool

# Cognify
curl -s -X POST http://192.168.66.41:8000/api/v1/knowledge/cognify \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"dataset_id":"<dataset_id>"}' | python3 -m json.tool
```

- [ ] **Step 3: 验证 Graph 级隔离**

```bash
# 查看 FalkorDB 中创建的 graph 列表
sudo docker exec cozy_falkordb redis-cli GRAPH.LIST
# 期望：看到 cognee_{user_id}_{dataset_id} 格式的 graph
```

- [ ] **Step 4: 验证跨 App 隔离**

```bash
APP_B_KEY="<App B 的 API Key>"

# App B 搜索 App A 的 dataset → 应返回 404
curl -s -X POST http://192.168.66.41:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_B_KEY" \
  -d '{"query":"graph database","dataset_id":"<App A 的 dataset_id>"}' | python3 -m json.tool
# 期望：404
```

---

## Spec Coverage Check

| Spec Section | Task |
|---|---|
| FalkorAdapter 连接管理 | Task 1 |
| 核心 CRUD（节点） | Task 2 |
| 核心 CRUD（边） | Task 3 |
| 图遍历 | Task 4 |
| 图管理 | Task 5 |
| 可选方法（feedback weights, triplets） | Task 6 |
| FalkorDatasetDatabaseHandler | Task 7 |
| Cognee 集成（patch + Dockerfile） | Task 8 |
| docker-compose + 部署 | Task 9 |
| 多租户验证 | Task 10 |
| 属性序列化 | Task 1 (helpers) |
| 异步处理 | Task 1 (async client) |
