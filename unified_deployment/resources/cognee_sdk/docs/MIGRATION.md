# 迁移指南

从直接使用 cognee 库迁移到 Cognee Python SDK。

## 主要差异

### 1. 安装方式

**之前（直接使用库）：**
```bash
pip install cognee[api,postgres,neo4j]
# 或
uv sync --extra api --extra postgres --extra neo4j
```

**现在（使用 SDK）：**
```bash
pip install cognee-sdk
```

### 2. 导入方式

**之前：**
```python
import cognee

await cognee.add("data", dataset_name="test")
await cognee.cognify()
results = await cognee.search("query")
```

**现在：**
```python
from cognee_sdk import CogneeClient, SearchType

client = CogneeClient(api_url="http://localhost:8000")
await client.add("data", dataset_name="test")
await client.cognify(datasets=["test"])
results = await client.search("query", search_type=SearchType.GRAPH_COMPLETION)
await client.close()
```

### 3. 初始化

**之前：**
```python
import cognee
# 需要配置环境变量
# LLM_API_KEY, DATABASE_URL, etc.
```

**现在：**
```python
from cognee_sdk import CogneeClient

# 只需要 API URL，所有配置在服务端
client = CogneeClient(api_url="http://localhost:8000")
```

### 4. 搜索类型

**之前：**
```python
from cognee.modules.search.types import SearchType

results = await cognee.search(
    query_type=SearchType.GRAPH_COMPLETION,
    query_text="query"
)
```

**现在：**
```python
from cognee_sdk import SearchType

results = await client.search(
    query="query",
    search_type=SearchType.GRAPH_COMPLETION
)
```

### 5. 错误处理

**之前：**
```python
try:
    await cognee.add("data")
except Exception as e:
    print(e)
```

**现在：**
```python
from cognee_sdk.exceptions import ValidationError, ServerError

try:
    await client.add("data", dataset_name="test")
except ValidationError as e:
    print(f"Validation error: {e.message}")
except ServerError as e:
    print(f"Server error: {e.message}")
```

## 迁移步骤

### 步骤 1：安装 SDK

```bash
pip install cognee-sdk
```

### 步骤 2：更新导入

将所有 `import cognee` 替换为：

```python
from cognee_sdk import CogneeClient, SearchType
```

### 步骤 3：创建客户端

在代码开始处创建客户端：

```python
client = CogneeClient(
    api_url="http://localhost:8000",  # 或您的 Cognee 服务器地址
    api_token="your-token"  # 如果启用了认证
)
```

### 步骤 4：更新方法调用

将所有 `cognee.method()` 调用替换为 `client.method()`。

### 步骤 5：添加清理代码

在代码结束处关闭客户端：

```python
await client.close()
```

或使用上下文管理器：

```python
async with CogneeClient(api_url="http://localhost:8000") as client:
    # 使用 client
    pass
# 自动关闭
```

## 代码对比示例

### 添加数据

**之前：**
```python
await cognee.add(
    data="text",
    dataset_name="test",
    data_id="id1"
)
```

**现在：**
```python
result = await client.add(
    data="text",
    dataset_name="test"
)
# data_id 在 result.data_id 中
```

### 搜索

**之前：**
```python
results = await cognee.search(
    query_type=cognee.SearchType.GRAPH_COMPLETION,
    query_text="query",
    datasets=["test"]
)
```

**现在：**
```python
results = await client.search(
    query="query",
    search_type=SearchType.GRAPH_COMPLETION,
    datasets=["test"]
)
```

## 注意事项

1. **环境变量**：SDK 不需要配置数据库、LLM 等环境变量，这些在服务端配置
2. **异步上下文**：确保在异步函数中使用 SDK
3. **资源清理**：记得调用 `close()` 或使用上下文管理器
4. **错误类型**：使用 SDK 的异常类型进行错误处理
5. **返回值**：SDK 返回类型化的对象，而不是原始字典

## 优势

迁移到 SDK 后，您将获得：

- ✅ 更小的安装包（5-10MB vs 500MB-2GB）
- ✅ 更快的启动时间
- ✅ 类型安全
- ✅ 更好的错误处理
- ✅ 集中管理的数据和处理逻辑

## 需要帮助？

如果迁移过程中遇到问题，请查看：
- [API 文档](API.md)
- [故障排查指南](TROUBLESHOOTING.md)
- [示例代码](../examples/)

