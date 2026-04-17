# Cognee SDK PyPI 发布指南

## 📦 当前状态

✅ 包已构建完成
- `dist/cognee_sdk-0.2.0-py3-none-any.whl` (20KB)
- `dist/cognee_sdk-0.2.0.tar.gz` (47KB)
- ✅ 已通过 twine check 验证

## 🚀 发布步骤

### 方法 1: 使用发布脚本（推荐）

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk
./publish.sh
```

### 方法 2: 手动发布

#### 1. 测试发布到 TestPyPI（推荐先测试）

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 发布到 TestPyPI
python3 -m twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ cognee-sdk
```

**TestPyPI 账户：**
- 访问 https://test.pypi.org/account/register/ 注册
- 或使用现有的 PyPI 账户

#### 2. 发布到正式 PyPI

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 发布到正式 PyPI
python3 -m twine upload dist/*
```

**PyPI 账户设置：**

1. **创建 PyPI 账户**（如果还没有）：
   - 访问 https://pypi.org/account/register/
   - 注册并验证邮箱

2. **使用 API Token（推荐）**：
   - 登录 PyPI
   - 进入 Account settings → API tokens
   - 创建新的 API token（选择 "Entire account" 或项目范围）
   - 使用 token 发布：
     ```
     Username: __token__
     Password: pypi-xxxxxxxxxxxxx（你的 API token）
     ```

3. **或使用用户名和密码**：
   ```
   Username: 你的 PyPI 用户名
   Password: 你的 PyPI 密码
   ```

#### 3. 创建 Git Tag

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 创建版本标签
git tag -a v0.2.0 -m "Release version 0.2.0"

# 推送标签
git push origin v0.2.0
```

## ✅ 发布后验证

等待几分钟后，验证发布：

```bash
# 安装最新版本
pip install --upgrade cognee-sdk

# 验证版本
python3 -c "import cognee_sdk; print(cognee_sdk.__version__)"
# 应该输出: 0.2.0
```

## 📋 发布检查清单

- [x] 版本号已更新（0.2.0）
- [x] CHANGELOG.md 已更新
- [x] 包已构建（dist/ 目录）
- [x] 包已通过 twine check
- [ ] 已测试发布到 TestPyPI（可选但推荐）
- [ ] 已发布到正式 PyPI
- [ ] 已创建 Git tag
- [ ] 已验证安装

## ⚠️ 重要提示

1. **版本号不能重复**：一旦发布到 PyPI，不能使用相同的版本号重新发布
2. **测试先行**：强烈建议先在 TestPyPI 上测试
3. **API Token 安全**：不要将 API token 提交到代码仓库
4. **发布后等待**：发布后需要等待几分钟才能在 PyPI 上看到

## 🔗 相关链接

- PyPI: https://pypi.org/project/cognee-sdk/
- TestPyPI: https://test.pypi.org/project/cognee-sdk/
- PyPI 账户设置: https://pypi.org/manage/account/
- API Tokens: https://pypi.org/manage/account/token/

