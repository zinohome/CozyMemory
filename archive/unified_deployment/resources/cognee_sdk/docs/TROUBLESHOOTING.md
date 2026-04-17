# 故障排查指南

## 常见问题

### 1. 连接错误

**问题**：无法连接到 Cognee API 服务器

**解决方案**：
- 检查 API URL 是否正确
- 确认 Cognee 服务器正在运行
- 检查网络连接和防火墙设置
- 验证端口是否正确（默认 8000）

```python
# 测试连接
try:
    health = await client.health_check()
    print(f"Server status: {health.status}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### 2. 认证错误

**问题**：`AuthenticationError: [401] Unauthorized`

**解决方案**：
- 检查 API token 是否正确
- 确认 token 是否过期
- 如果使用登录，确保调用 `login()` 方法

```python
# 使用登录获取 token
token = await client.login("user@example.com", "password")
client.api_token = token
```

### 3. 文件上传失败

**问题**：文件上传时出错

**解决方案**：
- 检查文件路径是否正确
- 确认文件存在且可读
- 检查文件大小是否超过限制
- 验证文件格式是否支持

```python
# 检查文件
from pathlib import Path

file_path = Path("document.pdf")
if not file_path.exists():
    print("File not found")
elif not file_path.is_file():
    print("Path is not a file")
else:
    result = await client.add(data=file_path, dataset_name="test")
```

### 4. 超时错误

**问题**：`TimeoutError: Request timeout`

**解决方案**：
- 增加超时时间
- 检查网络连接
- 对于长时间操作，使用后台模式

```python
# 增加超时时间
client = CogneeClient(
    api_url="http://localhost:8000",
    timeout=600.0  # 10 分钟
)

# 使用后台模式
result = await client.cognify(
    datasets=["large-dataset"],
    run_in_background=True
)
```

### 5. 类型错误

**问题**：类型检查失败

**解决方案**：
- 确保使用正确的类型
- 检查 UUID 格式
- 验证枚举值

```python
from uuid import UUID
from cognee_sdk import SearchType

# 正确的 UUID 使用
dataset_id = UUID("123e4567-e89b-12d3-a456-426614174000")

# 正确的枚举使用
results = await client.search(
    query="test",
    search_type=SearchType.GRAPH_COMPLETION  # 使用枚举，不是字符串
)
```

### 6. WebSocket 连接失败

**问题**：WebSocket 连接错误

**解决方案**：
- 确保安装了 `websockets` 包
- 检查 WebSocket URL 转换
- 验证认证 token

```python
# 安装 WebSocket 支持
pip install cognee-sdk[websocket]

# 检查 WebSocket 连接
try:
    async for update in client.subscribe_cognify_progress(pipeline_run_id):
        print(update)
except ImportError:
    print("websockets package not installed")
```

## 调试技巧

### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### 检查响应内容

```python
# 在 _request 方法中添加日志
response = await client._request("GET", "/api/v1/datasets")
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Content: {response.text}")
```

### 使用健康检查

```python
# 定期检查服务器状态
health = await client.health_check()
print(f"Server: {health.status}, Version: {health.version}")
```

## 性能优化

### 使用连接池

客户端自动使用连接池，无需额外配置。

### 批量操作

使用 `add_batch()` 进行批量操作：

```python
results = await client.add_batch(
    data_list=["data1", "data2", "data3"],
    dataset_name="test"
)
```

### 并发请求

使用 `asyncio.gather()` 进行并发请求：

```python
tasks = [
    client.search("query1"),
    client.search("query2"),
    client.search("query3"),
]
results = await asyncio.gather(*tasks)
```

## 获取帮助

如果问题仍然存在：

1. 检查 [GitHub Issues](https://github.com/your-org/cognee-sdk/issues)
2. 查看 [API 文档](API.md)
3. 查看 [示例代码](../examples/)
4. 提交新的 Issue 并包含：
   - 错误消息
   - 代码示例
   - Python 版本
   - SDK 版本

