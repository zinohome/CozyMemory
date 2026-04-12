#!/bin/bash

# CozyMemory 项目初始化脚本
# 用于初始化所有子项目及其依赖

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 项目根目录
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# projects 目录
PROJECTS_DIR="$PROJECT_ROOT/projects"

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 仓库配置
# 格式: "目录名|仓库URL"
COZY_REPOS=(
    "CozyMemobase|https://github.com/zinohome/CozyMemobase.git"
    "CozyMem0|https://github.com/zinohome/CozyMem0.git"
    "CozyCognee|https://github.com/zinohome/CozyCognee.git"
)

# 依赖仓库配置
# 格式: "父目录|子目录名|仓库URL"
DEPENDENCY_REPOS=(
    "CozyMemobase|memobase|https://github.com/memodb-io/memobase.git"
    "CozyMem0|mem0|https://github.com/mem0ai/mem0.git"
    "CozyCognee|cognee|https://github.com/topoteretes/cognee.git"
)

# 创建 projects 目录
create_projects_dir() {
    if [ ! -d "$PROJECTS_DIR" ]; then
        print_info "创建 projects 目录: $PROJECTS_DIR"
        mkdir -p "$PROJECTS_DIR"
        print_success "projects 目录创建成功"
    else
        print_info "projects 目录已存在: $PROJECTS_DIR"
    fi
}

# 克隆或更新仓库
clone_or_update_repo() {
    local repo_dir="$1"
    local repo_url="$2"
    local repo_name=$(basename "$repo_dir")

    if [ -d "$repo_dir/.git" ]; then
        print_info "仓库 $repo_name 已存在，执行 git pull 更新..."
        cd "$repo_dir"
        git pull origin $(git rev-parse --abbrev-ref HEAD) 2>/dev/null || {
            print_warning "无法自动确定分支，尝试 git pull"
            git pull || print_warning "git pull 失败，可能需要手动处理"
        }
        cd - > /dev/null
        print_success "仓库 $repo_name 更新完成"
    else
        if [ -d "$repo_dir" ]; then
            print_warning "目录 $repo_name 存在但不是 git 仓库，跳过"
            return 1
        fi
        print_info "克隆仓库 $repo_name..."
        git clone "$repo_url" "$repo_dir"
        print_success "仓库 $repo_name 克隆完成"
    fi
}

# 初始化 Cozy 仓库
init_cozy_repos() {
    print_info "=== 初始化 Cozy 仓库 ==="
    for repo_config in "${COZY_REPOS[@]}"; do
        IFS='|' read -r repo_name repo_url <<< "$repo_config"
        local repo_dir="$PROJECTS_DIR/$repo_name"
        clone_or_update_repo "$repo_dir" "$repo_url"
    done
    echo ""
}

# 初始化依赖仓库
init_dependency_repos() {
    print_info "=== 初始化依赖仓库 ==="
    for dep_config in "${DEPENDENCY_REPOS[@]}"; do
        IFS='|' read -r parent_dir dep_name dep_url <<< "$dep_config"
        local parent_path="$PROJECTS_DIR/$parent_dir"
        local dep_path="$parent_path/projects/$dep_name"

        # 检查父仓库是否存在
        if [ ! -d "$parent_path" ]; then
            print_error "父仓库 $parent_dir 不存在，跳过 $dep_name"
            continue
        fi

        # 创建 projects 子目录
        if [ ! -d "$parent_path/projects" ]; then
            print_info "创建 $parent_dir/projects 目录"
            mkdir -p "$parent_path/projects"
        fi

        clone_or_update_repo "$dep_path" "$dep_url"
    done
    echo ""
}

# 显示仓库状态
show_status() {
    print_info "=== 仓库状态 ==="

    echo ""
    echo "Cozy 仓库:"
    for repo_config in "${COZY_REPOS[@]}"; do
        IFS='|' read -r repo_name _ <<< "$repo_config"
        local repo_dir="$PROJECTS_DIR/$repo_name"
        if [ -d "$repo_dir/.git" ]; then
            cd "$repo_dir"
            local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
            local commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            local status=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
            cd - > /dev/null
            if [ "$status" -eq 0 ]; then
                echo -e "  ${GREEN}✓${NC} $repo_name: $branch@$commit (clean)"
            else
                echo -e "  ${YELLOW}!${NC} $repo_name: $branch@$commit ($status uncommitted)"
            fi
        else
            echo -e "  ${RED}✗${NC} $repo_name: 未初始化"
        fi
    done

    echo ""
    echo "依赖仓库:"
    for dep_config in "${DEPENDENCY_REPOS[@]}"; do
        IFS='|' read -r parent_dir dep_name _ <<< "$dep_config"
        local dep_path="$PROJECTS_DIR/$parent_dir/projects/$dep_name"
        if [ -d "$dep_path/.git" ]; then
            cd "$dep_path"
            local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
            local commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            local status=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
            cd - > /dev/null
            if [ "$status" -eq 0 ]; then
                echo -e "  ${GREEN}✓${NC} $parent_dir/$dep_name: $branch@$commit (clean)"
            else
                echo -e "  ${YELLOW}!${NC} $parent_dir/$dep_name: $branch@$commit ($status uncommitted)"
            fi
        else
            echo -e "  ${RED}✗${NC} $parent_dir/$dep_name: 未初始化"
        fi
    done
    echo ""
}

# 主函数
main() {
    echo "========================================"
    echo "  CozyMemory 项目初始化脚本"
    echo "========================================"
    echo ""

    # 检查 git 是否安装
    if ! command -v git &> /dev/null; then
        print_error "git 未安装，请先安装 git"
        exit 1
    fi

    print_info "项目根目录: $PROJECT_ROOT"
    print_info "Projects 目录: $PROJECTS_DIR"
    echo ""

    # 根据参数执行不同操作
    case "${1:-all}" in
        status)
            show_status
            ;;
        cozy)
            create_projects_dir
            init_cozy_repos
            show_status
            ;;
        deps)
            init_dependency_repos
            show_status
            ;;
        all|*)
            create_projects_dir
            init_cozy_repos
            init_dependency_repos
            show_status
            ;;
    esac

    echo "========================================"
    print_success "初始化完成!"
    echo "========================================"
}

# 显示帮助信息
show_help() {
    cat << EOF
CozyMemory 项目初始化脚本

用法: $0 [命令]

命令:
    all     执行完整的初始化（默认）
    cozy    仅初始化 Cozy 仓库
    deps    仅初始化依赖仓库
    status  显示仓库状态
    help    显示此帮助信息

示例:
    $0              # 完整初始化
    $0 status       # 查看状态
    $0 cozy         # 仅更新 Cozy 仓库
    $0 deps         # 仅更新依赖仓库

EOF
}

# 处理帮助参数
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# 执行主函数
main "$@"
