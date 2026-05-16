# CozyMemory 种子目录引导手册

## 种子目录信息

| 项目 | 值 |
|------|-----|
| **种子路径** | `/home/ubuntu/CozySeeds/CozyMemory/` |
| **建立时间** | 2026-05-16 |
| **建立方式** | 从 `/home/ubuntu/CozyProjects/CozyMemory` 全量 rsync |
| **所有者** | 开发协调员（D-开发协调员），仅 leader 维护 |
| **权限** | 只读（`chmod -R a-w`） |
| **运行主机** | `192.168.66.41` |

## 标准接入流程

### 1. 克隆代码仓库

```bash
git clone git@github.com:zinohome/CozyMemory.git
cd CozyMemory
```

或在 Multica 环境中：

```bash
multica repo checkout git@github.com:zinohome/CozyMemory.git
```

### 2. 同步小件（.env 及配置）

种子目录中的 `.env` 等被 `.gitignore` 排除的运行必需小文件，通过 rsync 从种子同步：

```bash
# 同步 .env（如果种子中存在）
cp /home/ubuntu/CozySeeds/CozyMemory/.env.example .env
# 注意：.env 含密钥，需从种子或 docs/credentials-dev.md 获取实际值

# 同步 .coveragerc
cp /home/ubuntu/CozySeeds/CozyMemory/.coveragerc .coveragerc
```

> **重要**：不要直接修改种子目录中的文件。种子是只读的共享基线。

### 3. 大件策略（模型/向量库/数据目录）

GB 级文件（`.venv`、`projects/` 子项目、数据卷等）**不复制**。通过以下方式使用：

| 大件 | 种子中大小 | 策略 |
|------|-----------|------|
| `.venv/` | ~256 MB | 各开发者自行 `python -m venv .venv && pip install -r requirements.txt` |
| `projects/CozyCognee/` | ~205 MB | 子项目源码，仅在需要修改上游时 checkout |
| `projects/CozyMem0/` | ~103 MB | 子项目源码，仅在需要修改上游时 checkout |
| `projects/CozyMemobase/` | ~100 MB | 子项目源码，仅在需要修改上游时 checkout |
| `/data/CozyMemory/*` | 运行时数据 | Docker 卷挂载，由 `docker-compose` 管理，不纳入种子 |

**Docker 数据卷映射**（定义在 `CozyMemory/docker-compose.1panel.yml`）：

```
/data/CozyMemory/postgres      → PostgreSQL (pgvector)
/data/CozyMemory/redis         → Redis
/data/CozyMemory/qdrant        → Qdrant 向量存储
/data/CozyMemory/minio         → MinIO 对象存储
/data/CozyMemory/falkordb      → FalkorDB 图数据库
/data/CozyMemory/cognee/       → Cognee 数据与日志
/data/CozyMemory/mem0/         → Mem0 历史与日志
/data/CozyMemory/memobase/     → Memobase 数据
/data/CozyMemory/tiktoken/     → tiktoken 缓存（共享）
/data/CozyMemory/prometheus/   → Prometheus 时序数据
/data/CozyMemory/grafana/      → Grafana 仪表板
/data/CozyMemory/caddy/        → Caddy 反代数据
```

### 4. 环境变量指向种子的场景

如需直接读取种子中的只读资源（如参考配置），在 `.env` 或 `docker-compose` 中使用绝对路径：

```bash
# 示例：引用种子中的参考配置
SEED_DIR=/home/ubuntu/CozySeeds/CozyMemory
```

## 含密钥的文件路径清单

> ⚠️ 仅列路径，**禁止贴内容**

| 文件路径 | 说明 |
|----------|------|
| `.env` | 运行环境配置（数据库密码、API Key、JWT Secret 等） |
| `.env.example` | 模板，不含实际密钥但含键名 |
| `docs/credentials-dev.md` | 开发环境凭据文档（Operator Key、测试账号、基础设施密码） |
| `CozyMemory/docker-compose.1panel.yml` | 含环境变量引用（`${POSTGRES_PASSWORD}` 等占位符） |

## 重建/刷新种子命令

当 `.gitignore` 必需文件有变更时，由 leader 执行以下命令刷新种子：

```bash
# Step 1: 从权威副本全量同步（幂等，可重复执行）
mkdir -p /home/ubuntu/CozySeeds
rsync -a --delete /home/ubuntu/CozyProjects/CozyMemory/ /home/ubuntu/CozySeeds/CozyMemory/

# Step 2: 冻结为只读
chmod -R a-w /home/ubuntu/CozySeeds/CozyMemory

# Step 3: 核验一致性（可选）
diff -rq /home/ubuntu/CozyProjects/CozyMemory /home/ubuntu/CozySeeds/CozyMemory
```

刷新后需：
1. 更新本文档中的"建立时间"
2. 在相关 Issue 中通知小队成员

## 关键端口映射

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Caddy | 导航页 |
| 8000 | CozyMemory API | 统一记忆服务 REST API |
| 8080 | Cognee API | 知识图谱引擎 |
| 8081 | Mem0 API | 向量记忆引擎 |
| 8019 | Memobase API | 用户画像引擎 |
| 8085 | Cognee Frontend | Cognee 管理界面 |
| 8088 | FalkorDB Browser | 图数据库可视化 |
| 3001 | CozyMemory UI | 统一管理仪表板 |
| 5433 | PostgreSQL | 主机直连（容器内 5432） |
| 50051 | gRPC (Caddy TLS) | CozyMemory gRPC 接口 |
| 50151 | gRPC (直连) | CozyMemory gRPC 调试 |
