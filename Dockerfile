# CozyMemory 统一 AI 记忆服务平台
# 多阶段构建 Dockerfile

# ==================== 构建阶段 ====================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装到虚拟环境
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目元数据和源码，用 pip install 安装包（注册 entry_points）
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# ==================== 运行阶段 ====================
FROM python:3.11-slim AS runtime

LABEL maintainer="CozyMemory Team" \
      version="2.0.0" \
      description="CozyMemory - 统一 AI 记忆服务平台，整合 Mem0、Memobase、Cognee 三大引擎"

# 创建非 root 用户
RUN groupadd --gid 1000 cozymemory && \
    useradd --uid 1000 --gid cozymemory --shell /bin/bash --create-home cozymemory

# 安装 supervisord 用于同时运行 REST + gRPC
RUN apt-get update && \
    apt-get install -y --no-install-recommends supervisor && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码（已包含预生成的 protobuf 代码）
COPY --chown=cozymemory:cozymemory src/ ./src/
COPY --chown=cozymemory:cozymemory pyproject.toml ./

# 安装应用包（注册 CLI entry_points）
RUN pip install --no-cache-dir -e .

# 复制 alembic 迁移文件（启动时自动升级数据库）
COPY --chown=cozymemory:cozymemory alembic.ini ./
COPY --chown=cozymemory:cozymemory alembic/ ./alembic/

# 复制 supervisord 配置和 entrypoint
COPY --chown=cozymemory:cozymemory deploy/supervisord.conf /etc/supervisor/conf.d/cozymemory.conf
COPY --chown=cozymemory:cozymemory deploy/entrypoint.sh /app/entrypoint.sh

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO

# 切换到非 root 用户
USER cozymemory

# 暴露端口：8000 (REST API) / 50051 (gRPC)
EXPOSE 8000 50051

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# entrypoint 先执行数据库迁移，再启动 supervisord
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/cozymemory.conf"]