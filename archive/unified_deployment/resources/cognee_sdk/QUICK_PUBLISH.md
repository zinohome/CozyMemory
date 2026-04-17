# 快速发布到 PyPI

## 📦 当前状态

✅ 包已构建并验证通过
- 版本: 0.2.0
- 文件: `dist/cognee_sdk-0.2.0-py3-none-any.whl` (20KB)
- 文件: `dist/cognee_sdk-0.2.0.tar.gz` (47KB)

## 🚀 快速发布命令

### 选项 1: 发布到 TestPyPI（推荐先测试）

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk
python3 -m twine upload --repository testpypi dist/*
```

### 选项 2: 直接发布到 PyPI

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk
python3 -m twine upload dist/*
```

## 🔐 认证信息

发布时会提示输入：
- **Username**: `__token__` （如果使用 API token）
- **Password**: `pypi-xxxxxxxxxxxxx` （你的 PyPI API token）

或使用用户名和密码：
- **Username**: 你的 PyPI 用户名
- **Password**: 你的 PyPI 密码

## 📝 发布后步骤

1. 创建 Git tag:
   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   ```

2. 验证发布（等待几分钟后）:
   ```bash
   pip install --upgrade cognee-sdk
   python3 -c "import cognee_sdk; print(cognee_sdk.__version__)"
   ```

## ⚠️ 注意事项

- 确保你有 PyPI 账户和发布权限
- 建议先在 TestPyPI 上测试
- 版本号 0.2.0 一旦发布就不能重复使用

