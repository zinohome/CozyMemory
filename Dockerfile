# CozyMemory 统一 AI 记忆服务平台
# 多阶段构建 Dockerfile

# ==================== 构建阶段 ====================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖（gRPC 编译需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# ==================== 运行阶段 ====================
FROM python:3.11-slim AS runtime

LABEL maintainer="CozyMemory Team" \
      version="2.0.0" \
      description="CozyMemory - 统一 AI 记忆服务平台，整合 Mem0、Memobase、Cognee 三大引擎"

# 创建非 root 用户
RUN groupadd --gid 1000 cozymemory && \
    useradd --uid 1000 --gid cozymemory --shell /bin/bash --create-home cozymemory

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --chown=cozymemory:cozymemory src/ ./src/
COPY --chown=cozymemory:cozymemory proto/ ./proto/

# 生成 gRPC 代码
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/cozymemory/grpc_server \
    --grpc_python_out=./src/cozymemory/grpc_server \
    ./proto/common.proto \
    ./proto/conversation.proto \
    ./proto/profile.proto \
    ./proto/knowledge.proto

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

# 启动命令
CMD ["uvicorn", "cozymemory.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]