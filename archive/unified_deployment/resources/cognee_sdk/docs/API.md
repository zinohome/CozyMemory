# Cognee Python SDK API 文档

## CogneeClient

主客户端类，用于与 Cognee API 服务器交互。

### 初始化

```python
client = CogneeClient(
    api_url="http://localhost:8000",
    api_token="your-token",           # 可选
    timeout=300.0,                    # 请求超时（秒）
    max_retries=3,                    # 最大重试次数
    retry_delay=1.0,                  # 初始重试延迟（秒）
    enable_logging=False,              # 启用请求/响应日志
    request_interceptor=None,          # 请求拦截器（可选）
    response_interceptor=None          # 响应拦截器（可选）
)
```

**新功能参数：**
- `enable_logging`: 启用请求/响应日志记录
- `request_interceptor`: 请求拦截器回调函数，接收 (method, url, headers)
- `response_interceptor`: 响应拦截器回调函数，接收 httpx.Response

### 核心方法

#### add()

添加数据到 Cognee。

```python
result = await client.add(
    data="文本内容",
    dataset_name="数据集名称",
    dataset_id=None,  # 可选
    node_set=None     # 可选
)
```

**支持的数据类型：**
- 字符串
- 字节数据
- 文件路径（Path 对象或字符串）
- 文件对象（BinaryIO）
- 上述类型的列表

**流式上传：**
- 文件大小 > 10MB 时自动使用流式上传，减少内存使用
- 文件大小 > 50MB 时会发出警告，但仍可正常上传
- 小文件（< 10MB）使用内存上传以获得更好性能

#### delete()

删除数据。

```python
result = await client.delete(
    data_id=UUID("..."),
    dataset_id=UUID("..."),
    mode="soft"  # 或 "hard"
)
```

#### cognify()

处理数据生成知识图谱。

```python
result = await client.cognify(
    datasets=["dataset1"],
    dataset_ids=None,  # 可选
    run_in_background=False,
    custom_prompt=None  # 可选
)
```

#### search()

搜索知识图谱。

```python
results = await client.search(
    query="搜索查询",
    search_type=SearchType.GRAPH_COMPLETION,
    datasets=None,  # 可选
    dataset_ids=None,  # 可选
    system_prompt=None,  # 可选
    node_name=None,  # 可选
    top_k=10,
    only_context=False,
    use_combined_context=False,
    return_type="parsed"  # 或 "raw"，默认为 "parsed"
)
```

**返回类型：**
- `return_type="parsed"`（默认）：返回解析后的 `SearchResult` 或 `CombinedSearchResult` 对象
- `return_type="raw"`：返回原始字典列表

#### list_datasets()

获取数据集列表。

```python
datasets = await client.list_datasets()
```

#### create_dataset()

创建数据集。

```python
dataset = await client.create_dataset("数据集名称")
```

### 数据集管理方法

#### update()

更新数据。

#### delete_dataset()

删除数据集。

#### get_dataset_data()

获取数据集中的数据项。

#### get_dataset_graph()

获取知识图谱数据。

#### get_dataset_status()

获取数据集处理状态。

#### download_raw_data()

下载原始数据文件。

### 认证方法

#### login()

用户登录。

```python
token = await client.login("user@example.com", "password")
```

#### register()

用户注册。

```python
user = await client.register("user@example.com", "password")
```

#### get_current_user()

获取当前用户信息。

### 其他方法

#### memify()

添加记忆算法。

#### get_search_history()

获取搜索历史。

#### visualize()

生成 HTML 可视化。

#### sync_to_cloud()

同步到云端。

#### get_sync_status()

获取同步状态。

#### subscribe_cognify_progress()

订阅 Cognify 处理进度（WebSocket）。

#### add_batch()

批量添加数据，支持并发控制和错误处理。

```python
# 基本用法 - 遇到错误立即停止
results = await client.add_batch(
    data_list=["text1", "text2", "text3"],
    dataset_name="my-dataset",
    max_concurrent=10  # 最大并发数（默认：10）
)

# 继续执行并收集错误
results, errors = await client.add_batch(
    data_list=["text1", "text2", "text3"],
    dataset_name="my-dataset",
    max_concurrent=10,
    continue_on_error=True,  # 遇到错误继续执行
    return_errors=True        # 返回错误列表
)
```

**参数：**
- `data_list`: 要添加的数据项列表
- `dataset_name`: 数据集名称
- `dataset_id`: 数据集 ID（可选）
- `node_set`: 节点集合（可选）
- `max_concurrent`: 最大并发操作数（默认：10）
- `continue_on_error`: 遇到错误是否继续执行（默认：False）
- `return_errors`: 是否返回错误列表（默认：False）

**返回值：**
- 如果 `return_errors=False`：返回 `list[AddResult]`
- 如果 `return_errors=True`：返回 `tuple[list[AddResult], list[Exception]]`

## 异常类型

- `CogneeSDKError` - 基础异常
- `CogneeAPIError` - API 调用错误
- `AuthenticationError` - 认证错误（401）
- `NotFoundError` - 资源未找到（404）
- `ValidationError` - 请求验证错误（400）
- `ServerError` - 服务器错误（5xx）
- `TimeoutError` - 请求超时

## 智能重试机制

SDK 实现了智能重试逻辑：

- **4xx 错误**（除 429 外）：不重试，立即抛出异常
- **429 错误**（限流）：重试，使用指数退避
- **5xx 错误**：重试，使用指数退避
- **网络错误**：重试，使用指数退避

这样可以减少无效重试，提高响应速度。

## 流式上传

对于大文件（> 10MB），SDK 自动使用流式上传：

```python
# 小文件（< 10MB）- 使用内存上传
await client.add(data=Path("small_file.txt"), dataset_name="my-dataset")

# 大文件（> 10MB）- 自动使用流式上传
await client.add(data=Path("large_file.pdf"), dataset_name="my-dataset")
```

**优势：**
- 减少内存使用（大文件场景下降低 50-90%）
- 支持更大文件（理论上可支持任意大小文件）
- 自动优化，无需手动配置

## 数据模型

所有数据模型定义在 `cognee_sdk.models` 模块中，使用 Pydantic BaseModel。

主要模型：
- `User` - 用户模型
- `Dataset` - 数据集模型
- `DataItem` - 数据项模型
- `AddResult` - 添加结果
- `CognifyResult` - Cognify 结果
- `SearchResult` - 搜索结果
- `GraphData` - 图谱数据

