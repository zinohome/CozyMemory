# CozyMemory 部署及合并说明指南

本文档包含 `CozyMemory` 的全局整合部署指南。本方案遵循安全性隔离准则，将三款微内存系统（Cognee、Mem0、Memobase）的部署聚合于一体。

## 目录结构
在完成整合后，您会在本目录下看到以下重要结构：
```text
CozyMemory/
├── docs/                             # 总库文档中心
│   └── deployment.md                 # 当前部署白皮书
├── unified_deployment/               # 整合环境目录（入口）
│   ├── sql/
│   │   └── init.sql                  # PostgreSQL 初始数据库映射脚本
│   ├── conf/
│   │   └── config.yaml               # 主 Memobase LLM 鉴权路由
│   ├── resources/                    # 从原微项目迁移过来的组件资源（Patches, SDK等）
│   └── docker-compose.1panel.yml     # ★核心编排文件
└── projects/                         # 原始克隆项目集合（保留不修改）
```

## 核心配置指引

### 1. 架构梳理与网络
我们使用 Docker 的外部网络 `1panel-network`。所有的持久化存储都被收束并重新定位于宿主机的 `/data/cozy-memory` 下（兼容 1panel 标准规范）。

- **禁用所有的对外数据库端口绑定**：
  为提高安全性并遏制越权攻击风险，Postgres (`5432`)、Redis (`6379`)、Qdrant (`6333`)、MinIO 等基础节点均不再对宿主机暴露。
  它们只能由同一 `1panel-network` 网络下的 AI Agent API 及网关发起通讯。

### 2. 数据库逻辑分离方案
为了减少对宿主机的影响并有效降本增效，我们合并了数据库实例层：
- **Redis 合并**：由 `unified_deployment/docker-compose.1panel.yml` 统一拉起密码为 `cozy_redis_password` 的缓存服务器。
  - Cognee 连接位于 `0` 号 DB（`redis://.../0`）。
  - Memobase 连接位于 `1` 号 DB（`redis://.../1`）。
- **Postgres 合并**：配合了基于 `pgvector:0.8.1` 的增强镜像。启动时，挂载的 `./sql/init.sql` 会同步部署并建构两个子库 `cognee_db` 和 `memobase`（配置相应的只读属主凭证）。

### 3. Web 端访问端口一览
在整合架构拉起后，本地暴露供您测试及 1Panel OpenResty 反向代理使用的接口对应关系如下：
- **Cognee Core API**: -> `8000`
- **Cognee Frontend UI**: -> `3000`
- **Cognee Nginx 转发**: -> `8080` (防止与 1panel 80 端口互斥)
- **Mem0 API**: -> `8888`
- **Mem0 WebUI**: -> `3001` (由原 `3000` 偏移防止端口占用了前端服务)
- **Memobase API**: -> `8019`

### 4. 数据清理与重测
由于架构革新，若您原本于本地有旧数据，这些整合部署并不会自动衔接回原挂载点（原环境被留存在 `/data/mem0` 或 `/data/cognee`）。全新目录将在 `/data/cozy-memory/` 创建并伴随 `init.sql` 进行重新初始化。

## 使用指引
请打开 1Panel 面板 -> 【容器】 -> 【编排】并导入，或者在对应的终端路径使用 Docker CLI：
```bash
cd /Users/zhangjun/CursorProjects/CozyMemory/unified_deployment
docker network create 1panel-network || true
docker-compose -f docker-compose.1panel.yml up -d
```
请在 `.env` (如果需要管理环境凭证) 或者对应的 `conf/config.yaml` 中将 OpenAI KEY 的等价配置设为您专属的值，即可拉起服务！
