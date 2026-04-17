# 立即发布到 PyPI

## ✅ 准备就绪

包已重新构建，包含所有最新修复：
- ✅ 缩进错误已修复
- ✅ 代码重复已消除
- ✅ 导入已优化
- ✅ License 格式已修复
- ✅ 包已通过验证

## 🚀 快速发布

### 步骤 1: 获取 PyPI API Token

1. 访问 https://pypi.org/account/login/
2. 登录（如果没有账户，先注册）
3. 进入 **Account settings** → **API tokens**
4. 点击 **Add API token**
5. 选择作用域（建议选择 "Entire account" 或 "Project: cognee-sdk"）
6. 复制生成的 token（格式：`pypi-xxxxxxxxxxxxx`）

### 步骤 2: 发布到 PyPI

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 发布到 PyPI
python3 -m twine upload dist/*
```

**输入信息**:
- Username: `__token__`
- Password: `pypi-xxxxxxxxxxxxx` （你的 API token）

### 步骤 3: 创建 Git Tag

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### 步骤 4: 验证发布

等待几分钟后：

```bash
pip install --upgrade cognee-sdk
python3 -c "import cognee_sdk; print(cognee_sdk.__version__)"
# 应该输出: 0.2.0
```

## 📦 构建信息

- **版本**: 0.2.0
- **文件大小**: 
  - wheel: 20KB
  - source: 47KB
- **构建时间**: 2025-12-08 16:09
- **包含文件**: 
  - 所有源代码文件
  - LICENSE 文件
  - py.typed 文件（类型提示支持）

## ⚠️ 重要提示

- 版本号 0.2.0 一旦发布就不能重复使用
- 确保 API token 安全，不要提交到代码仓库
- 发布后需要等待几分钟才能在 PyPI 上看到
