#!/usr/bin/env bash
# ==============================================================================
# CozyMemory 本地开发部署脚本
#
# 用法：
#   ./scripts/dev.sh                    # 完整流程：单元测试 → 构建 → 部署 → 冒烟测试
#   ./scripts/dev.sh test               # 仅运行单元测试
#   ./scripts/dev.sh build              # 仅构建所有自定义镜像
#   ./scripts/dev.sh build cozymemory  # 仅构建单个镜像
#   ./scripts/dev.sh up                 # 仅启动/重启服务栈
#   ./scripts/dev.sh down               # 停止并移除所有容器
#   ./scripts/dev.sh smoke              # 仅运行冒烟测试（需服务已运行）
#   ./scripts/dev.sh logs [service]     # 查看日志（service 可选，如 cozymemory-api）
#   ./scripts/dev.sh status             # 查看服务健康状态
#
# 前置要求：
#   - Docker & docker compose 已安装
#   - Python 3.11+ 已安装
#   - 已设置 SERVER_IP 环境变量，或在 .env.local 中配置
#   - 已设置 OPENAI_API_KEY 环境变量，或在 .env.local 中配置
# ==============================================================================

set -euo pipefail

# ── 路径 ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_RUNTIME_DIR="$ROOT_DIR/base_runtime"
COMPOSE_FILE="$BASE_RUNTIME_DIR/docker-compose.1panel.yml"

# ── 颜色 ──────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✓]${NC} $1"; }
info()    { echo -e "${BLUE}[→]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
section() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

# ── 加载本地环境变量 ──────────────────────────────────────────────────────────
load_env() {
    # 优先 .env.local（不提交 git），其次 .env
    for f in "$ROOT_DIR/.env.local" "$ROOT_DIR/.env"; do
        if [[ -f "$f" ]]; then
            # 仅导出未设置过的变量（已有环境变量优先）
            while IFS= read -r line || [[ -n "$line" ]]; do
                [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
                varname="${line%%=*}"
                if [[ -z "${!varname:-}" ]]; then
                    export "$line" 2>/dev/null || true
                fi
            done < "$f"
            break
        fi
    done
}

# ── 配置校验 ──────────────────────────────────────────────────────────────────
validate_config() {
    if [[ -z "${SERVER_IP:-}" ]]; then
        warn "SERVER_IP 未设置，尝试自动获取本机 IP..."
        SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
        warn "使用 IP: $SERVER_IP（如有误请设置 SERVER_IP 环境变量）"
    fi
    export SERVER_IP

    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        warn "OPENAI_API_KEY 未设置 — Mem0/Cognee 相关功能将不可用"
    fi
}

# ── Docker compose 封装 ───────────────────────────────────────────────────────
compose() {
    docker compose -f "$COMPOSE_FILE" "$@"
}

compose_sudo() {
    # 优先不加 sudo，失败则自动加 sudo（某些系统 docker 需要权限）
    if docker compose -f "$COMPOSE_FILE" "$@" 2>/dev/null; then
        return 0
    else
        warn "docker compose 需要 sudo 权限，重试..."
        sudo docker compose -f "$COMPOSE_FILE" "$@"
    fi
}

# ── IP 替换（幂等）────────────────────────────────────────────────────────────
apply_server_ip() {
    # 先还原占位符（防止上次遗留真实 IP）
    if grep -q "YOUR_SERVER_IP" "$COMPOSE_FILE" 2>/dev/null; then
        info "compose 文件已包含占位符，替换为 $SERVER_IP"
    else
        warn "compose 文件中未发现 YOUR_SERVER_IP，尝试还原并重新替换..."
        # 把已有的真实 IP 还原（如果存在的话先跳过，因为可能 IP 已经对了）
    fi
    # 使用临时文件确保幂等替换
    sed "s/YOUR_SERVER_IP/$SERVER_IP/g" "$COMPOSE_FILE" > /tmp/compose_applied.yml
}

restore_server_ip() {
    sed -i "s/$SERVER_IP/YOUR_SERVER_IP/g" "$COMPOSE_FILE"
    log "compose 文件已还原占位符"
}

# ── 单元测试 ──────────────────────────────────────────────────────────────────
run_unit_tests() {
    section "单元测试"
    cd "$ROOT_DIR"

    if ! python3 -c "import cozymemory" 2>/dev/null; then
        info "安装 cozymemory 包（editable 模式）..."
        pip install -e ".[dev]" -q
    fi

    info "运行单元测试..."
    if python3 -m pytest tests/unit/ -q --tb=short; then
        log "单元测试全部通过"
    else
        error "单元测试失败，终止部署"
    fi
}

# ── 构建镜像 ──────────────────────────────────────────────────────────────────
run_build() {
    section "构建 Docker 镜像"
    local target="${1:-all}"
    cd "$ROOT_DIR"

    info "构建目标: $target"
    if bash "$BASE_RUNTIME_DIR/build.sh" "$target"; then
        log "镜像构建完成"
    else
        error "镜像构建失败"
    fi
}

# ── 创建数据目录 ──────────────────────────────────────────────────────────────
ensure_data_dirs() {
    local dirs=(
        /data/CozyMemory/postgres
        /data/CozyMemory/redis
        /data/CozyMemory/qdrant
        /data/CozyMemory/minio
        /data/CozyMemory/neo4j/data
        /data/CozyMemory/neo4j/logs
        /data/CozyMemory/neo4j/plugins
        /data/CozyMemory/cognee/data
        /data/CozyMemory/cognee/logs
        /data/CozyMemory/mem0/history
        /data/CozyMemory/mem0/logs
        /data/CozyMemory/memobase
        /data/CozyMemory/tiktoken
        /data/CozyMemory/caddy/data
        /data/CozyMemory/caddy/config
    )
    local need_create=0
    for d in "${dirs[@]}"; do
        [[ -d "$d" ]] || need_create=1
    done

    if [[ $need_create -eq 1 ]]; then
        info "创建数据目录 /data/CozyMemory/..."
        sudo mkdir -p "${dirs[@]}"
        sudo chown -R "$USER:$USER" /data/CozyMemory
        log "数据目录已创建"
    fi
}

# ── 启动服务 ──────────────────────────────────────────────────────────────────
run_up() {
    section "启动服务栈"
    ensure_data_dirs
    apply_server_ip

    info "启动所有服务（使用临时替换后的配置）..."
    if docker compose -f /tmp/compose_applied.yml up -d; then
        log "服务栈已启动"
    else
        error "服务启动失败"
    fi
}

# ── 停止服务 ──────────────────────────────────────────────────────────────────
run_down() {
    section "停止服务栈"
    info "停止并移除所有容器..."
    docker compose -f /tmp/compose_applied.yml down 2>/dev/null || \
    docker compose -f "$COMPOSE_FILE" down || true
    log "服务已停止"
}

# ── 等待服务就绪 ──────────────────────────────────────────────────────────────
wait_for_service() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"
    local max_wait="${4:-120}"
    local interval=5
    local elapsed=0

    info "等待 $name 就绪..."
    while [[ $elapsed -lt $max_wait ]]; do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" \
            --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || echo "000")
        if [[ "$code" == "$expected_code" ]]; then
            log "$name 就绪 (HTTP $code)"
            return 0
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -ne "  ${YELLOW}[${elapsed}s/${max_wait}s]${NC} $name: HTTP $code\r"
    done
    echo ""
    warn "$name 在 ${max_wait}s 内未就绪（最后状态: HTTP $code）"
    return 1
}

# ── 冒烟测试 ──────────────────────────────────────────────────────────────────
run_smoke_tests() {
    section "冒烟测试"
    local base="http://${SERVER_IP}"
    local pass=0
    local fail=0

    # ── 基础设施层 ────────────────────────────────────────────────
    info "等待核心服务就绪..."
    wait_for_service "CozyMemory API"    "$base:8000/api/v1/health" 200 120 || true
    wait_for_service "Cognee Frontend"  "$base:8080"                200 90  || true
    wait_for_service "Mem0 Frontend"    "$base:8081"                200 90  || true

    echo ""
    info "执行端点冒烟测试..."

    # 测试函数：curl 请求并检查状态码
    smoke_get() {
        local label="$1"; local url="$2"; local expect="${3:-200}"
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" \
            --connect-timeout 5 --max-time 15 "$url" 2>/dev/null || echo "000")
        if [[ "$code" == "$expect" ]]; then
            printf "  ${GREEN}[PASS]${NC} %-40s HTTP %s\n" "$label" "$code"
            ((pass++)) || true
        else
            printf "  ${RED}[FAIL]${NC} %-40s HTTP %s (期望 %s)\n" "$label" "$code" "$expect"
            ((fail++)) || true
        fi
    }

    smoke_post() {
        local label="$1"; local url="$2"; local body="$3"; local expect="${4:-200}"
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" \
            --connect-timeout 5 --max-time 15 \
            -X POST -H "Content-Type: application/json" -d "$body" \
            "$url" 2>/dev/null || echo "000")
        if [[ "$code" == "$expect" ]]; then
            printf "  ${GREEN}[PASS]${NC} %-40s HTTP %s\n" "$label" "$code"
            ((pass++)) || true
        else
            printf "  ${RED}[FAIL]${NC} %-40s HTTP %s (期望 %s)\n" "$label" "$code" "$expect"
            ((fail++)) || true
        fi
    }

    # CozyMemory 统一 API
    echo -e "\n  ${BOLD}CozyMemory 统一 API${NC} (:8000)"
    smoke_get  "健康检查"                  "$base:8000/api/v1/health"
    smoke_get  "OpenAPI 文档"              "$base:8000/docs"
    smoke_post "Conversation 校验 (422)"  "$base:8000/api/v1/conversations" \
               '{"messages":[]}' 422
    smoke_post "Profile 校验 (422)"       "$base:8000/api/v1/profiles/insert" \
               '{"messages":[]}' 422
    smoke_get  "Knowledge 数据集列表"      "$base:8000/api/v1/knowledge/datasets"

    # Cognee 生态
    echo -e "\n  ${BOLD}Cognee${NC} (:8080)"
    smoke_get  "Cognee API"               "$base:8080/api/v1/datasets"
    smoke_get  "Cognee 前端"              "$base:8080"

    # Mem0 生态
    echo -e "\n  ${BOLD}Mem0${NC} (:8081)"
    smoke_get  "Mem0 API 文档"            "$base:8081"
    smoke_get  "Mem0 前端"               "$base:8081"

    # Memobase
    echo -e "\n  ${BOLD}Memobase${NC} (:8019)"
    smoke_get  "Memobase 健康检查" \
               "$base:8019/api/v1/healthcheck" 200

    # 汇总
    echo ""
    local total=$((pass + fail))
    if [[ $fail -eq 0 ]]; then
        log "冒烟测试全部通过 ($pass/$total)"
    else
        warn "冒烟测试结果: ${GREEN}$pass 通过${NC} / ${RED}$fail 失败${NC} (共 $total)"
        return 1
    fi
}

# ── 日志 ──────────────────────────────────────────────────────────────────────
run_logs() {
    local service="${1:-}"
    apply_server_ip
    if [[ -n "$service" ]]; then
        docker compose -f /tmp/compose_applied.yml logs -f --tail=100 "$service"
    else
        docker compose -f /tmp/compose_applied.yml logs -f --tail=50
    fi
}

# ── 状态 ──────────────────────────────────────────────────────────────────────
run_status() {
    section "服务健康状态"
    apply_server_ip
    docker compose -f /tmp/compose_applied.yml ps
    echo ""
    info "端口概览："
    echo "  :8000  CozyMemory 统一 API"
    echo "  :8080  Cognee (前端 + API)"
    echo "  :8081  Mem0   (前端 + API)"
    echo "  :8019  Memobase API"
}

# ── 完整流程 ──────────────────────────────────────────────────────────────────
run_all() {
    local build_target="${1:-all}"
    run_unit_tests
    run_build "$build_target"
    run_up
    run_smoke_tests
    echo ""
    log "🎉 完整部署流程完成！"
    echo ""
    echo -e "  API 文档:  ${CYAN}http://${SERVER_IP}:8000/docs${NC}"
    echo -e "  Cognee:    ${CYAN}http://${SERVER_IP}:8080${NC}"
    echo -e "  Mem0:      ${CYAN}http://${SERVER_IP}:8081${NC}"
    echo -e "  Memobase:  ${CYAN}http://${SERVER_IP}:8019${NC}"
}

# ── 入口 ──────────────────────────────────────────────────────────────────────
main() {
    load_env
    validate_config

    local cmd="${1:-all}"
    shift || true

    case "$cmd" in
        all)     run_all "$@" ;;
        test)    run_unit_tests ;;
        build)   run_build "$@" ;;
        up)      run_up ;;
        down)    run_down ;;
        smoke)   run_smoke_tests ;;
        logs)    run_logs "$@" ;;
        status)  run_status ;;
        help|-h|--help)
            sed -n '/^# 用法/,/^# 前置/p' "$0" | grep -v "^#$" | sed 's/^# /  /'
            ;;
        *)
            error "未知命令: $cmd。运行 '$0 help' 查看用法。"
            ;;
    esac
}

main "$@"
