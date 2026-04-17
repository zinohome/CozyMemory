#!/bin/bash
# Cognee SDK PyPI 发布脚本

set -e  # 遇到错误立即退出

echo "🚀 Cognee SDK PyPI 发布脚本"
echo "================================"

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在 cognee_sdk 目录下运行此脚本"
    exit 1
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "📌 Python 版本: $PYTHON_VERSION"

# 读取版本号
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "📦 版本号: $VERSION"

# 1. 安装构建工具
echo ""
echo "📥 安装构建工具..."
python3 -m pip install --upgrade --quiet build twine

# 2. 清理旧的构建文件
echo ""
echo "🧹 清理旧的构建文件..."
rm -rf dist/ build/ *.egg-info

# 3. 运行代码质量检查
echo ""
echo "🔍 运行代码质量检查..."
if command -v ruff &> /dev/null; then
    echo "  - 运行 ruff check..."
    python3 -m ruff check cognee_sdk/ || echo "⚠️  ruff 检查发现问题，但继续..."
else
    echo "  ⚠️  ruff 未安装，跳过检查"
fi

# 4. 构建分发包
echo ""
echo "🔨 构建分发包..."
python3 -m build

# 5. 检查分发包
echo ""
echo "✅ 检查分发包..."
python3 -m twine check dist/*

# 6. 显示构建结果
echo ""
echo "📦 构建完成！生成的文件："
ls -lh dist/

echo ""
echo "================================"
echo "✅ 构建成功！"
echo ""
echo "下一步："
echo "1. 测试发布到 TestPyPI:"
echo "   twine upload --repository testpypi dist/*"
echo ""
echo "2. 发布到正式 PyPI:"
echo "   twine upload dist/*"
echo ""
echo "3. 创建 Git tag:"
echo "   git tag -a v$VERSION -m \"Release version $VERSION\""
echo "   git push origin v$VERSION"
echo ""
echo "注意："
echo "- 发布到 PyPI 需要用户名和密码（或 API token）"
echo "- 使用 API token 时，用户名填写: __token__"
echo "- 密码填写: pypi-xxxxxxxxxxxxx（你的 API token）"
echo "================================"

