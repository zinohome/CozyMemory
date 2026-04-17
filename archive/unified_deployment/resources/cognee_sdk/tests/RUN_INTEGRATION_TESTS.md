# 运行服务器集成测试

## ✅ 快速开始

```bash
cd cognee_sdk
source venv/bin/activate

# 运行所有集成测试
API_URL=http://192.168.66.11 pytest -m integration tests/test_server_integration.py -v --no-cov

# 运行特定测试
API_URL=http://192.168.66.11 pytest -m integration tests/test_server_integration.py::test_list_datasets -v --no-cov
```

## ⚠️ 重要提示

1. **API_URL 格式**：应该是基础 URL，不包含 `/api`
   - ✅ 正确：`http://192.168.66.11`
   - ❌ 错误：`http://192.168.66.11/api`

2. **权限问题**：某些测试可能需要认证或特定权限
   - 如果遇到 403 错误，可能需要设置 `API_TOKEN`
   - 某些操作可能需要管理员权限

3. **测试会创建真实数据**：
   - 测试会在服务器上创建数据集和数据
   - 测试会尝试清理，但可能不完整
   - 建议在测试环境中运行

## 📝 测试状态

当前测试结果：
- ✅ `test_server_health_check` - 健康检查
- ✅ `test_list_datasets` - 列出数据集
- ✅ `test_create_dataset` - 创建数据集
- ✅ `test_delete_dataset` - 删除数据集
- ⚠️ 其他测试可能需要认证或权限

## 🔧 故障排查

### 403 权限错误

```bash
# 设置 API token（如果需要）
export API_TOKEN=your-token-here
API_URL=http://192.168.66.11 pytest -m integration tests/test_server_integration.py -v --no-cov
```

### 连接失败

```bash
# 先运行连接测试
API_URL=http://192.168.66.11 python tests/test_server_connection.py
```

### 跳过需要权限的测试

```bash
# 只运行基础测试
API_URL=http://192.168.66.11 pytest -m integration tests/test_server_integration.py -v --no-cov -k "health_check or list_datasets or create_dataset"
```

