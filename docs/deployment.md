# CozyMemory 部署指南

**版本**: v0.2  
**日期**: 2026-04-09  
**定位**: Python 库 (无需部署)

---

## 🎯 重要说明

### v0.2 定位变化

**v0.1 (过时)**: 独立服务，需要 Docker 部署  
**v0.2 (当前)**: Python 库，`pip install` 即可使用

---

## 📦 安装方式

### 方式 1: 从 PyPI 安装 (推荐)

```bash
pip install cozy-memory
```

**验证安装**:

```bash
python -c "from cozy_memory import MemoryService; print('✅ 安装成功')"
```

---

### 方式 2: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 安装
pip install .

# 或开发模式
pip install -e .
```

---

### 方式 3: 使用 Poetry

```bash
# 克隆仓库
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 安装
poetry install
```

---

## 🔧 配置

### 零配置使用 (Mock 模式)

```python
from cozy_memory import MemoryService

# 无需任何配置
service = MemoryService()

# 直接使用
await service.add("测试记忆")
```

### 生产环境配置 (Memobase)

```bash
# 设置环境变量
export COZY_MEMOBASE_API_KEY="your-api-key"
export COZY_MEMOBASE_PROJECT_ID="your-project-id"
```

```python
from cozy_memory import MemoryService, MemobaseAdapter

# 从环境变量读取配置
service = MemoryService(adapter=MemobaseAdapter.from_env())

# 或显式配置
service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="your-api-key",
        project_id="your-project-id"
    )
)
```

---

## 🚀 使用示例

### 基础使用

```python
from cozy_memory import MemoryService

async def main():
    service = MemoryService()
    
    # 添加记忆
    memory = await service.add(
        "用户喜欢咖啡",
        memory_type="preference"
    )
    
    # 搜索记忆
    results = await service.search("咖啡")
    for r in results:
        print(r.content)
    
    # 更新记忆
    await service.update(
        memory.id,
        content="用户非常喜欢咖啡"
    )
    
    # 删除记忆
    await service.delete(memory.id)

# 运行
import asyncio
asyncio.run(main())
```

### 集成到 FastAPI

```python
from fastapi import FastAPI
from cozy_memory import MemoryService

app = FastAPI()
service = MemoryService()

@app.post("/memories")
async def add_memory(content: str, memory_type: str = "fact"):
    memory = await service.add(content, memory_type=memory_type)
    return {"id": memory.id, "status": "created"}

@app.get("/memories")
async def search_memories(query: str):
    results = await service.search(query)
    return {"memories": [{"id": m.id, "content": m.content} for m in results]}
```

### 集成到 LangChain

```python
from langchain.memory import ConversationBufferMemory
from cozy_memory import MemoryService

class CozyMemoryLangChain:
    def __init__(self):
        self.service = MemoryService()
    
    async def add_message(self, role: str, content: str):
        await self.service.add(
            f"{role}: {content}",
            memory_type="conversation"
        )
    
    async def get_history(self, limit: int = 10):
        results = await self.service.search(
            "",
            memory_type="conversation",
            limit=limit
        )
        return [r.content for r in results]
```

---

## 🏢 企业部署

### 多环境配置

```python
# config.py
import os
from cozy_memory import MemoryService, MemobaseAdapter, Config

class Config:
    DEBUG = os.getenv("COZY_DEBUG", "false").lower() == "true"
    MEMOBASE_API_KEY = os.getenv("COZY_MEMOBASE_API_KEY")
    MEMOBASE_PROJECT_ID = os.getenv("COZY_MEMOBASE_PROJECT_ID")
    LOG_LEVEL = os.getenv("COZY_LOG_LEVEL", "INFO")

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "WARNING"

# 使用
def create_service(env="production"):
    if env == "development":
        config = DevelopmentConfig()
    else:
        config = ProductionConfig()
    
    return MemoryService(
        adapter=MemobaseAdapter(
            api_key=config.MEMOBASE_API_KEY,
            project_id=config.MEMOBASE_PROJECT_ID
        )
    )
```

### Docker 容器化 (可选)

虽然 CozyMemory 是库，但如果你需要容器化应用：

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 CozyMemory
RUN pip install cozy-memory

# 复制应用代码
COPY . .

# 运行应用
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      - COZY_MEMOBASE_API_KEY=${MEMOBASE_API_KEY}
      - COZY_MEMOBASE_PROJECT_ID=${MEMOBASE_PROJECT_ID}
    volumes:
      - ./app:/app
```

---

## 📊 监控和日志

### 日志配置

```python
import logging
from cozy_memory import MemoryService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

service = MemoryService()
```

### 性能监控

```python
import time
from functools import wraps
from cozy_memory import MemoryService

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} completed in {duration:.3f}s")
        return result
    return wrapper

# 使用
service = MemoryService()
service.add = monitor_performance(service.add)
```

---

## 🔒 安全最佳实践

### 1. 环境变量管理

```bash
# .env 文件 (不要提交到 Git)
COZY_MEMOBASE_API_KEY=your-secret-key
COZY_MEMOBASE_PROJECT_ID=your-project-id
COZY_LOG_LEVEL=WARNING
```

```python
# .gitignore
.env
*.log
__pycache__/
*.pyc
```

### 2. API Key 轮换

```python
# 定期轮换 API Key
import os
from cozy_memory import MemoryService, MemobaseAdapter

def rotate_api_key():
    new_key = os.getenv("COZY_MEMOBASE_API_KEY_NEW")
    service = MemoryService(
        adapter=MemobaseAdapter(api_key=new_key)
    )
    # 测试新 key
    # ...
    # 更新环境变量
    os.environ["COZY_MEMOBASE_API_KEY"] = new_key
```

### 3. 数据脱敏

```python
from cozy_memory import MemoryService, sanitize_content

service = MemoryService(sanitize=True)

# 自动脱敏敏感信息
await service.add("用户电话：123-4567-8901")
# 存储为：用户电话：***-****-****
```

---

## 📈 性能优化

### 1. 连接池

```python
from cozy_memory import MemoryService, MemobaseAdapter

service = MemoryService(
    adapter=MemobaseAdapter(
        pool_size=10,
        max_overflow=5,
        pool_timeout=30
    )
)
```

### 2. 批量操作

```python
from cozy_memory import MemoryService

service = MemoryService()

# 批量添加
memories = ["记忆 1", "记忆 2", "记忆 3"]
results = await asyncio.gather(*[
    service.add(m) for m in memories
])
```

### 3. 缓存 (计划中)

```python
from cozy_memory import MemoryService, CacheAdapter

service = MemoryService(
    adapter=CacheAdapter(
        backend="redis",
        ttl=3600
    )
)
```

---

## ❓ 常见问题

### Q: 需要部署服务器吗？

**A**: 不需要。CozyMemory v0.2 是 Python 库，直接 `pip install` 使用。

### Q: 如何高可用部署？

**A**: CozyMemory 本身无状态，高可用由调用方保证：
- 多实例部署应用
- 使用负载均衡
- Memobase 服务保证高可用

### Q: 数据如何备份？

**A**: 使用 Memobase 时，数据由 Memobase 负责备份。本地存储时，定期导出 JSON。

### Q: 如何监控性能？

**A**: 集成 Prometheus 或自定义监控：

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('cozy_memory_requests_total', 'Total requests')
REQUEST_DURATION = Histogram('cozy_memory_request_duration_seconds', 'Request duration')

@REQUEST_DURATION.time()
async def add_with_monitor(content):
    REQUEST_COUNT.inc()
    return await service.add(content)
```

---

## 📚 相关文档

- [快速开始](./guides/getting-started.md)
- [配置指南](./guides/configuration.md)
- [本地开发](./dev/local-dev.md)
- [API 参考](./api/reference.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀
