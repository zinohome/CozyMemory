# 发布 v0.3.0 到 PyPI

## ✅ 准备状态

**版本**: 0.3.0  
**构建状态**: ✅ 成功  
**验证状态**: ✅ 通过  
**测试状态**: ✅ 338/339 通过（91.70%覆盖率）

## 📦 包信息

- **包名**: cognee-sdk
- **版本**: 0.3.0
- **文件位置**: `dist/`
- **包含文件**:
  - `cognee_sdk-0.3.0.tar.gz` (source distribution)
  - `cognee_sdk-0.3.0-py3-none-any.whl` (wheel distribution)

## 🚀 发布步骤

### 方法 1: 使用发布脚本（推荐）

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 设置认证信息（使用 PyPI API Token）
export TWINE_USERNAME='__token__'
export TWINE_PASSWORD='pypi-xxxxxxxxxxxxx'  # 替换为你的 API token

# 运行发布脚本
./publish_to_pypi.sh
```

### 方法 2: 直接使用 twine

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

# 发布到 TestPyPI（推荐先测试）
python3 -m twine upload --repository testpypi dist/*

# 或直接发布到 PyPI
python3 -m twine upload dist/*
```

**输入信息**:
- Username: `__token__` （如果使用 API token）
- Password: `pypi-xxxxxxxxxxxxx` （你的 PyPI API token）

## 🔐 获取 PyPI API Token

1. 访问 https://pypi.org/account/login/ 登录
2. 进入 **Account settings** → **API tokens**
3. 点击 **Add API token**
4. 选择作用域：
   - **Entire account** - 所有项目
   - **Project: cognee-sdk** - 仅限此项目
5. 复制生成的 token（格式：`pypi-xxxxxxxxxxxxx`）
6. **重要**: token 只显示一次，请妥善保存

## 📋 发布前检查清单

- [x] 版本号已更新（0.3.0）
- [x] CHANGELOG 已更新
- [x] 包已重新构建
- [x] 包验证通过（twine check）
- [x] 测试通过（338/339）
- [x] 代码质量检查通过
- [ ] PyPI API token 已准备
- [ ] 已测试发布到 TestPyPI（可选但推荐）

## 🎯 版本 0.3.0 主要更新

### 性能优化（核心更新）

1. **连接池优化**
   - 默认连接数：50 keepalive, 100 total
   - HTTP/2 支持（自动降级）

2. **数据压缩**
   - 自动压缩 JSON 数据（>1KB）
   - 减少 30-70% 传输时间

3. **流式传输优化**
   - 阈值从 10MB 降低到 1MB
   - 更好的内存使用

4. **本地缓存**
   - GET 请求自动缓存
   - POST 请求（带 json）缓存
   - 90%+ 性能提升（缓存命中）

5. **自适应批量操作**
   - 根据数据大小自动调整并发数
   - 20-40% 性能提升

### 预期性能提升

- **总体**: 30-60% 性能提升
- **小数据**: 30-50% 提升
- **中等数据**: 40-50% 提升
- **大数据**: 30-50% 提升
- **批量操作**: 40-60% 提升
- **缓存命中**: 90%+ 提升

## 📝 发布后步骤

### 1. 验证发布

等待几分钟后：

```bash
pip install --upgrade cognee-sdk
python3 -c "import cognee_sdk; print(cognee_sdk.__version__)"
# 应该输出: 0.3.0
```

### 2. 创建 Git Tag

```bash
cd /Users/zhangjun/CursorProjects/CozyCognee/cognee_sdk

git add .
git commit -m "Release version 0.3.0 - Performance optimizations"
git tag -a v0.3.0 -m "Release version 0.3.0

Major performance improvements:
- Connection pool optimization (50/100 connections)
- HTTP/2 support
- Data compression (30-70% reduction)
- Streaming upload optimization (1MB threshold)
- Local caching (90%+ faster for cached queries)
- Adaptive batch operations (20-40% improvement)

Overall performance improvement: 30-60%"
git push origin main
git push origin v0.3.0
```

### 3. 更新文档

- [x] CHANGELOG 已更新
- [ ] 更新 README（如果需要）
- [ ] 更新 API 文档（如果需要）

## ⚠️ 重要提示

1. **版本号**: 0.3.0 一旦发布就不能重复使用
2. **API Token**: 确保 token 安全，不要提交到代码仓库
3. **测试**: 建议先发布到 TestPyPI 进行测试
4. **等待时间**: 发布后需要等待几分钟才能在 PyPI 上看到

## 🔗 相关文档

- [性能优化分析](../../docs/development/SDK_PERFORMANCE_ANALYSIS.md)
- [性能优化实施](../../docs/development/SDK_PERFORMANCE_OPTIMIZATIONS.md)
- [性能测试报告](PERFORMANCE_OPTIMIZATIONS_TEST_REPORT.md)

---

**准备完成时间**: 2025-12-08  
**版本**: 0.3.0  
**状态**: ✅ 准备就绪，可以发布
