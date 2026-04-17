#!/bin/bash
# Cognee SDK PyPI 发布脚本（使用环境变量）

set -e

echo "🚀 Cognee SDK PyPI 发布"
echo "================================"

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在 cognee_sdk 目录下运行此脚本"
    exit 1
fi

# 检查构建文件
if [ ! -d "dist" ] || [ -z "$(ls -A dist/*.whl dist/*.tar.gz 2>/dev/null)" ]; then
    echo "❌ 错误: 未找到构建文件，请先运行: python3 -m build"
    exit 1
fi

# 读取版本号
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "📦 版本号: $VERSION"
echo ""

# 检查环境变量
if [ -z "$TWINE_USERNAME" ] && [ -z "$PYPI_USERNAME" ]; then
    echo "⚠️  未设置认证信息"
    echo ""
    echo "请设置以下环境变量之一："
    echo ""
    echo "选项 1: 使用 API Token（推荐）"
    echo "  export TWINE_USERNAME='__token__'"
    echo "  export TWINE_PASSWORD='pypi-xxxxxxxxxxxxx'"
    echo ""
    echo "选项 2: 使用用户名和密码"
    echo "  export PYPI_USERNAME='your-username'"
    echo "  export PYPI_PASSWORD='your-password'"
    echo ""
    echo "然后重新运行此脚本，或直接执行："
    echo "  python3 -m twine upload dist/*"
    echo ""
    exit 1
fi

# 设置认证信息
if [ -n "$TWINE_USERNAME" ]; then
    export TWINE_USERNAME
    export TWINE_PASSWORD
elif [ -n "$PYPI_USERNAME" ]; then
    export TWINE_USERNAME="$PYPI_USERNAME"
    export TWINE_PASSWORD="$PYPI_PASSWORD"
fi

# 选择发布目标
echo "选择发布目标："
echo "1) TestPyPI (测试)"
echo "2) PyPI (正式)"
read -p "请选择 (1/2): " choice

case $choice in
    1)
        echo ""
        echo "📤 发布到 TestPyPI..."
        python3 -m twine upload --repository testpypi dist/*
        echo ""
        echo "✅ 已发布到 TestPyPI"
        echo "测试安装: pip install --index-url https://test.pypi.org/simple/ cognee-sdk"
        ;;
    2)
        echo ""
        echo "📤 发布到 PyPI..."
        python3 -m twine upload dist/*
        echo ""
        echo "✅ 已发布到 PyPI"
        echo "安装: pip install --upgrade cognee-sdk"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "================================"
echo "下一步：创建 Git tag"
echo "  git tag -a v$VERSION -m \"Release version $VERSION\""
echo "  git push origin v$VERSION"
echo "================================"

