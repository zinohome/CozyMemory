# 服务器集成测试说明

本文档说明如何运行与真实 Cognee 服务器交互的集成测试。

## 📋 前提条件

1. **Cognee 服务器已部署并运行**
   - API 地址：`http://192.168.66.11/api`
   - Swagger 文档：`http://192.168.66.11/api/docs`

2. **测试环境已配置**
   ```bash
   cd cognee_sdk
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

## 🚀 运行集成测试

### ⚠️ 重要：API URL 格式

**注意**：`API_URL` 应该是基础 URL，**不包含** `/api` 路径。

- ✅ 正确：`API_URL=http://192.168.66.11`（如果服务器在 `http://192.168.66.11/api`）
- ❌ 错误：`API_URL=http://192.168.66.11/api`

SDK 内部会自动添加 `/api/v1` 路径。

### 基本用法

```bash
# 运行所有集成测试（使用默认 API 地址）
pytest -m integration tests/test_server_integration.py -v

# 使用自定义 API 地址（注意：不包含 /api）
API_URL=http://192.168.66.11 pytest -m integration tests/test_server_integration.py -v

# 如果服务器需要认证，设置 API token
API_URL=http://192.168.66.11 API_TOKEN=your-token pytest -m integration tests/test_server_integration.py -v
```

### 运行特定测试

```bash
# 只运行健康检查测试
pytest -m integration tests/test_server_integration.py::test_server_health_check -v

# 运行完整工作流测试
pytest -m integration tests/test_server_integration.py::test_complete_workflow -v

# 运行搜索测试
pytest -m integration tests/test_server_integration.py::test_search -v
```

### 跳过集成测试

```bash
# 运行所有非集成测试（默认行为）
pytest -m "not integration"

# 或者直接运行单元测试
pytest tests/ -m "not integration"
```

## 📝 测试列表

### 基础功能测试

- `test_server_health_check` - 服务器健康检查
- `test_list_datasets` - 列出所有数据集
- `test_create_dataset` - 创建数据集
- `test_add_data` - 添加数据
- `test_add_multiple_data` - 批量添加数据

### 处理功能测试

- `test_cognify` - Cognify 处理
- `test_search` - 搜索功能
- `test_get_dataset_data` - 获取数据集数据
- `test_get_dataset_status` - 获取数据集状态

### 更新和删除测试

- `test_update_data` - 更新数据
- `test_delete_data` - 删除数据
- `test_delete_dataset` - 删除数据集

### 高级测试

- `test_complete_workflow` - 完整工作流测试
- `test_search_types` - 不同搜索类型测试
- `test_error_handling` - 错误处理测试

## ⚙️ 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `API_URL` | Cognee API 服务器基础地址（不包含 `/api`） | `http://192.168.66.11` |
| `API_TOKEN` | API 认证 token（可选） | `None` |

**注意**：如果服务器在 `http://192.168.66.11/api`，`API_URL` 应该设置为 `http://192.168.66.11`。

## 🔍 测试输出

集成测试会输出详细的执行信息：

```
tests/test_server_integration.py::test_complete_workflow PASSED
✓ Created dataset: 123e4567-e89b-12d3-a456-426614174000
✓ Added data: 123e4567-e89b-12d3-a456-426614174001
✓ Started cognify
✓ Search completed, found 3 results
✓ Deleted data
✓ Deleted dataset
✓ Complete workflow test finished
```

## ⚠️ 注意事项

1. **测试会创建真实数据**
   - 测试会在服务器上创建数据集和数据
   - 测试完成后会尝试清理，但可能不完整
   - 建议在测试环境中运行

2. **测试可能需要等待**
   - Cognify 处理需要时间
   - 某些测试包含 `asyncio.sleep()` 等待处理完成
   - 如果服务器处理较慢，可能需要增加等待时间

3. **网络连接**
   - 确保可以访问服务器地址
   - 如果服务器不可用，测试会被跳过或失败

4. **认证**
   - 如果服务器需要认证，设置 `API_TOKEN` 环境变量
   - 某些测试可能需要有效的认证 token

## 🐛 故障排查

### 测试失败：连接超时

```bash
# 检查服务器是否可访问
curl http://192.168.66.11/api/health

# 检查网络连接
ping 192.168.66.11
```

### 测试失败：认证错误

```bash
# 设置正确的 API token
export API_TOKEN=your-actual-token
pytest -m integration tests/test_server_integration.py -v
```

### 测试失败：数据未找到

- 某些测试依赖于之前的数据
- 尝试单独运行测试，而不是整个套件
- 检查服务器日志了解详细信息

## 📊 测试覆盖率

集成测试不会影响代码覆盖率统计（默认排除 tests 目录）。

要查看覆盖率，运行：

```bash
# 只运行单元测试并查看覆盖率
pytest -m "not integration" --cov=cognee_sdk --cov-report=html
```

## 🔄 CI/CD 集成

在 CI/CD 中运行集成测试：

```yaml
# GitHub Actions 示例
- name: Run integration tests
  env:
    API_URL: ${{ secrets.API_URL }}
    API_TOKEN: ${{ secrets.API_TOKEN }}
  run: |
    pytest -m integration tests/test_server_integration.py -v
```

## 📚 相关文档

- [测试指南](../docs/development/SDK_TESTING.md)
- [快速使用指南](../docs/development/SDK_QUICK_START.md)
- [API 文档](../README.md)

