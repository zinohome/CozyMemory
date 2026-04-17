#!/bin/bash
# CozyMemory Base Runtime 镜像构建脚本
# 构建所有自定义 Docker 镜像（公共镜像无需构建）
#
# 用法：
#   ./build.sh          # 构建全部镜像
#   ./build.sh cognee   # 仅构建指定镜像（可选值：cognee, cognee-frontend, mem0-api, mem0-webui, memobase）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$(cd "$SCRIPT_DIR/../projects" && pwd)"
TARGET="${1:-all}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---- mem0-api ----
build_mem0_api() {
    log "Building mem0-api:latest ..."
    [ -d "$PROJECTS_DIR/CozyMem0" ] || err "CozyMem0 directory not found: $PROJECTS_DIR/CozyMem0"
    docker build \
        -f "$PROJECTS_DIR/CozyMem0/deployment/mem0/Dockerfile" \
        -t mem0-api:latest \
        "$PROJECTS_DIR/CozyMem0"
    log "mem0-api:latest built."
}

# ---- mem0-webui ----
build_mem0_webui() {
    log "Building mem0-webui:latest ..."
    UI_DIR="$PROJECTS_DIR/CozyMem0/projects/mem0/openmemory/ui"
    [ -d "$UI_DIR" ] || err "mem0 UI directory not found: $UI_DIR"
    docker build -t mem0-webui:latest "$UI_DIR"
    log "mem0-webui:latest built."
}

# ---- memobase-server ----
build_memobase() {
    log "Syncing memobase source files ..."
    DEPLOY_DIR="$PROJECTS_DIR/CozyMemobase/deployment/memobase"
    SRC_DIR="$PROJECTS_DIR/CozyMemobase/projects/memobase/src/server/api"
    [ -d "$SRC_DIR" ]    || err "Memobase source not found: $SRC_DIR"
    [ -d "$DEPLOY_DIR" ] || err "Memobase deploy dir not found: $DEPLOY_DIR"

    cp "$SRC_DIR/pyproject.toml" "$DEPLOY_DIR/"
    cp "$SRC_DIR/uv.lock"        "$DEPLOY_DIR/"
    cp "$SRC_DIR/api.py"         "$DEPLOY_DIR/"
    # 先删除旧副本，保证重复构建时目录不嵌套
    rm -rf "$DEPLOY_DIR/memobase_server"
    cp -r "$SRC_DIR/memobase_server" "$DEPLOY_DIR/"
    log "Memobase source synced. Building memobase-server:latest ..."

    docker build -f "$DEPLOY_DIR/Dockerfile" -t memobase-server:latest "$DEPLOY_DIR"
    log "memobase-server:latest built."
}

# ---- cognee ----
build_cognee() {
    log "Building cognee:0.4.1 ..."
    [ -d "$PROJECTS_DIR/CozyCognee" ] || err "CozyCognee directory not found: $PROJECTS_DIR/CozyCognee"
    docker build \
        -f "$PROJECTS_DIR/CozyCognee/deployment/docker/cognee/Dockerfile" \
        -t cognee:0.4.1 \
        "$PROJECTS_DIR/CozyCognee"
    log "cognee:0.4.1 built."
}

# ---- cognee-frontend ----
build_cognee_frontend() {
    log "Building cognee-frontend:local-0.4.1 ..."
    [ -d "$PROJECTS_DIR/CozyCognee" ] || err "CozyCognee directory not found: $PROJECTS_DIR/CozyCognee"
    docker build \
        -f "$PROJECTS_DIR/CozyCognee/deployment/docker/cognee-frontend/Dockerfile" \
        -t cognee-frontend:local-0.4.1 \
        "$PROJECTS_DIR/CozyCognee"
    log "cognee-frontend:local-0.4.1 built."
}

# ---- 入口 ----
case "$TARGET" in
    all)
        build_mem0_api
        build_mem0_webui
        build_memobase
        build_cognee
        build_cognee_frontend
        ;;
    mem0-api)       build_mem0_api ;;
    mem0-webui)     build_mem0_webui ;;
    memobase)       build_memobase ;;
    cognee)         build_cognee ;;
    cognee-frontend) build_cognee_frontend ;;
    *)
        echo "Usage: $0 [all|mem0-api|mem0-webui|memobase|cognee|cognee-frontend]"
        exit 1
        ;;
esac

echo ""
log "Done! Custom images:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
    | grep -E "mem0-api|mem0-webui|memobase-server|cognee"
