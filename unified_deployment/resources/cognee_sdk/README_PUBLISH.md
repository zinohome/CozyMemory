# PyPI 发布说明

## 📦 当前状态

✅ **包已重新构建完成并验证通过**
- 版本: **0.2.0**
- 构建时间: 2025-12-08 16:09
- 位置: `dist/` 目录
- 状态: ✅ 已通过 `twine check` 验证
- 包含修复: ✅ 缩进错误、代码重复、导入优化等所有修复

## 🚀 发布方法

### 方法 1: 使用发布脚本（推荐）

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 设置认证信息（使用 API Token）
export TWINE_USERNAME='__token__'
export TWINE_PASSWORD='pypi-xxxxxxxxxxxxx'  # 替换为你的 API token

# 运行发布脚本
./publish_to_pypi.sh
```

### 方法 2: 直接使用 twine 命令

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 发布到 TestPyPI（推荐先测试）
python3 -m twine upload --repository testpypi dist/*

# 或直接发布到 PyPI
python3 -m twine upload dist/*
```

发布时会提示输入：
- **Username**: `__token__` （如果使用 API token）
- **Password**: `pypi-xxxxxxxxxxxxx` （你的 PyPI API token）

## 🔐 获取 PyPI API Token

1. 访问 https://pypi.org/account/login/ 登录
2. 进入 **Account settings** → **API tokens**
3. 点击 **Add API token**
4. 选择作用域：
   - **Entire account** - 所有项目
   - **Project: cognee-sdk** - 仅限此项目
5. 复制生成的 token（格式：`pypi-xxxxxxxxxxxxx`）
6. **重要**: token 只显示一次，请妥善保存

## 📋 发布检查清单

- [x] 版本号已更新（0.2.0）
- [x] CHANGELOG.md 已更新
- [x] 包已构建（dist/ 目录）
- [x] 包已通过 twine check
- [ ] 已获取 PyPI API token
- [ ] 已发布到 TestPyPI（可选但推荐）
- [ ] 已发布到正式 PyPI
- [ ] 已创建 Git tag
- [ ] 已验证安装

## ✅ 发布后验证

等待几分钟后：

```bash
# 安装最新版本
pip install --upgrade cognee-sdk

# 验证版本
python3 -c "import cognee_sdk; print(cognee_sdk.__version__)"
# 应该输出: 0.2.0

# 测试导入
python3 -c "from cognee_sdk import CogneeClient; print('✅ SDK 导入成功')"
```

## 🏷️ 创建 Git Tag

发布成功后，创建版本标签：

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

## ⚠️ 重要提示

1. **版本号不能重复**: 一旦发布到 PyPI，不能使用相同的版本号重新发布
2. **API Token 安全**: 不要将 token 提交到代码仓库
3. **测试先行**: 强烈建议先在 TestPyPI 上测试
4. **发布后等待**: 发布后需要等待几分钟才能在 PyPI 上看到

## 🔗 相关链接

- PyPI 项目页面: https://pypi.org/project/cognee-sdk/
- TestPyPI: https://test.pypi.org/project/cognee-sdk/
- PyPI 账户设置: https://pypi.org/manage/account/
- API Tokens: https://pypi.org/manage/account/token/

