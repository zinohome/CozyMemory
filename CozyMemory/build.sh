#!/bin/bash
# CozyMemory Base Runtime 镜像构建脚本
# 构建所有自定义 Docker 镜像（公共镜像无需构建）
#
# 用法：
#   ./build.sh          # 构建全部镜像
#   ./build.sh cognee   # 仅构建指定镜像（可选值见下方）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$(cd "$SCRIPT_DIR/../projects" && pwd)"
TARGET="${1:-all}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---- mem0-api ----
# 使用 staging 目录组装构建上下文，Dockerfile 和 main.py 来自 CozyMem0/deployment/mem0/。
# main.py 替换了上游版本：使用 Qdrant（无 psycopg 依赖）、APIRouter /api/v1、CORS 中间件。
build_mem0_api() {
    log "Building mem0-api:latest ..."
    local cozy_dir="$PROJECTS_DIR/CozyMem0"
    [ -d "$cozy_dir" ] || err "CozyMem0 directory not found: $cozy_dir"

    local stage_dir
    stage_dir=$(mktemp -d)
    trap "rm -rf '$stage_dir'" RETURN

    cp -r "$cozy_dir/projects" "$stage_dir/"
    cp -r "$cozy_dir/deployment" "$stage_dir/"

    docker build \
        -f "$cozy_dir/deployment/mem0/Dockerfile" \
        -t mem0-api:latest \
        "$stage_dir"
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
    rm -rf "$DEPLOY_DIR/memobase_server"
    cp -r "$SRC_DIR/memobase_server" "$DEPLOY_DIR/"
    log "Memobase source synced. Building memobase-server:latest ..."

    docker build -f "$DEPLOY_DIR/Dockerfile" -t memobase-server:latest "$DEPLOY_DIR"
    log "memobase-server:latest built."
}

# ---- cognee ----
# Dockerfile 来自 CozyCognee/deployment/docker/cognee/Dockerfile，修复了：
#   - alembic 路径：上游将其移入 cognee/ 子包（project/cognee/cognee/alembic.ini）
build_cognee() {
    log "Building cognee:0.4.1 ..."
    local cozy_dir="$PROJECTS_DIR/CozyCognee"
    local src="$cozy_dir/projects/cognee"
    local dst="$cozy_dir/project/cognee"
    [ -d "$cozy_dir" ] || err "CozyCognee directory not found: $cozy_dir"
    [ -d "$src" ]      || err "cognee source not found: $src"

    log "Syncing cognee source to project/cognee ..."
    rm -rf "$dst"
    cp -r "$src" "$dst"

    docker build \
        -f "$cozy_dir/deployment/docker/cognee/Dockerfile" \
        -t cognee:0.4.1 \
        "$cozy_dir"

    rm -rf "$dst"
    log "cognee:0.4.1 built."
}

# ---- cognee-frontend ----
# Dockerfile 来自 CozyCognee/deployment/docker/cognee-frontend/Dockerfile，修复了：
#   - npm ci → npm install：上游 package-lock.json 与 package.json 不同步
build_cognee_frontend() {
    log "Building cognee-frontend:local-0.4.1 ..."
    local cozy_dir="$PROJECTS_DIR/CozyCognee"
    local src="$cozy_dir/projects/cognee"
    local dst="$cozy_dir/project/cognee"
    [ -d "$cozy_dir" ] || err "CozyCognee directory not found: $cozy_dir"
    [ -d "$src" ]      || err "cognee source not found: $src"

    log "Syncing cognee source to project/cognee ..."
    rm -rf "$dst"
    cp -r "$src" "$dst"

    # Apply patches (CozyCognee/patches/*.patch)
    local patch_dir="$cozy_dir/patches"
    if [ -d "$patch_dir" ]; then
        for p in "$patch_dir"/*.patch; do
            [ -f "$p" ] || continue
            log "Applying patch: $(basename "$p") ..."
            git -C "$dst" apply "$(realpath "$p")" || log "WARN: patch $(basename "$p") failed, skipping"
        done
    fi

    docker build \
        -f "$cozy_dir/deployment/docker/cognee-frontend/Dockerfile" \
        -t cognee-frontend:local-0.4.1 \
        "$cozy_dir"

    rm -rf "$dst"
    log "cognee-frontend:local-0.4.1 built."
}

# ---- cozymemory ----
build_cozymemory() {
    log "Building cozymemory:latest ..."
    local root_dir
    root_dir="$(cd "$SCRIPT_DIR/.." && pwd)"
    [ -f "$root_dir/Dockerfile" ] || err "CozyMemory Dockerfile not found: $root_dir/Dockerfile"
    docker build -t cozymemory:latest "$root_dir"
    log "cozymemory:latest built."
}

# ---- cozymemory-ui ----
build_cozymemory_ui() {
    log "Building cozymemory-ui:latest ..."
    local root_dir
    root_dir="$(cd "$SCRIPT_DIR/.." && pwd)"
    local ui_dir="$root_dir/ui"
    [ -d "$ui_dir" ] || err "CozyMemory UI directory not found: $ui_dir"
    docker build -t cozymemory-ui:latest "$ui_dir"
    log "cozymemory-ui:latest built."
}

# ---- 入口 ----
case "$TARGET" in
    all)
        build_mem0_api
        build_mem0_webui
        build_memobase
        build_cognee
        build_cognee_frontend
        build_cozymemory
        build_cozymemory_ui
        ;;
    mem0-api)        build_mem0_api ;;
    mem0-webui)      build_mem0_webui ;;
    memobase)        build_memobase ;;
    cognee)          build_cognee ;;
    cognee-frontend) build_cognee_frontend ;;
    cozymemory)      build_cozymemory ;;
    cozymemory-ui)   build_cozymemory_ui ;;
    *)
        echo "Usage: $0 [all|mem0-api|mem0-webui|memobase|cognee|cognee-frontend|cozymemory|cozymemory-ui]"
        exit 1
        ;;
esac

echo ""
log "Done! Custom images:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
    | grep -E "mem0-api|mem0-webui|memobase-server|cognee|cozymemory"
