# 配置指南

**版本**: v0.2  
**日期**: 2026-04-09

---

## 🎯 配置概览

CozyMemory v0.2 采用**零配置优先**原则：

- ✅ 默认无需配置即可使用 (Mock 模式)
- ✅ 需要时通过环境变量或代码配置
- ✅ 所有配置项都有合理默认值

---

## 🔑 核心配置

### Memobase 配置

使用真实 Memobase 服务时需要：

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `api_key` | `COZY_MEMOBASE_API_KEY` | 无 | Memobase API Key |
| `project_id` | `COZY_MEMOBASE_PROJECT_ID` | 无 | Memobase 项目 ID |
| `api_base` | `COZY_MEMOBASE_API_BASE` | `https://api.memobase.io` | API 端点 |

**配置方式**:

```python
# 方式 1: 代码中直接配置
from cozy_memory import MemoryService, MemobaseAdapter

service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="your-api-key",
        project_id="your-project-id",
        api_base="https://api.memobase.io"  # 可选
    )
)

# 方式 2: 从环境变量读取
# 设置环境变量
# export COZY_MEMOBASE_API_KEY="your-api-key"
# export COZY_MEMOBASE_PROJECT_ID="your-project-id"

service = MemoryService(adapter=MemobaseAdapter.from_env())

# 方式 3: 混合配置 (代码优先，环境 fallback)
service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="explicit-key",  # 优先使用
        # project_id 从环境变量读取
    )
)
```

---

## 📝 日志配置

### 日志级别

| 级别 | 环境变量 | 说明 |
|------|---------|------|
| `DEBUG` | `COZY_LOG_LEVEL=DEBUG` | 详细调试信息 |
| `INFO` | `COZY_LOG_LEVEL=INFO` | 一般信息 (默认) |
| `WARNING` | `COZY_LOG_LEVEL=WARNING` | 警告信息 |
| `ERROR` | `COZY_LOG_LEVEL=ERROR` | 错误信息 |

**配置方式**:

```python
# 方式 1: 环境变量
# export COZY_LOG_LEVEL=DEBUG

# 方式 2: 代码配置
from cozy_memory import Config, MemoryService

config = Config(log_level="DEBUG")
service = MemoryService.from_config(config)

# 方式 3: 运行时修改
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG)
)
```

### 日志格式

默认使用结构化日志 (JSON 格式)：

```json
{"event": "Memory added", "memory_id": "xxx", "level": "info", "timestamp": "..."}
```

**自定义格式**:

```python
import logging
import structlog

# 开发环境：人类可读格式
logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO
)

# 生产环境：JSON 格式
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
```

---

## 🗄️ 存储配置

### Mock 适配器 (默认)

```python
from cozy_memory import MemoryService

# 无需配置，内存存储
service = MemoryService()
```

**特点**:
- ✅ 零配置
- ✅ 快速测试
- ❌ 重启后数据丢失
- ❌ 单进程使用

### SQLite 适配器 (计划中)

```python
from cozy_memory import MemoryService, SQLiteAdapter

service = MemoryService(
    adapter=SQLiteAdapter(
        db_path="./cozy_memory.db"  # 数据库文件路径
    )
)
```

**配置项**:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `db_path` | `./cozy_memory.db` | 数据库文件路径 |
| `pool_size` | 1 | 连接池大小 |
| `timeout` | 30 | 超时秒数 |

### Redis 适配器 (计划中)

```python
from cozy_memory import MemoryService, RedisAdapter

service = MemoryService(
    adapter=RedisAdapter(
        host="localhost",
        port=6379,
        db=0,
        password=None,  # 可选
        ttl=3600  # 可选，缓存过期时间
    )
)
```

**配置项**:

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `host` | `COZY_REDIS_HOST` | `localhost` | Redis 主机 |
| `port` | `COZY_REDIS_PORT` | `6379` | Redis 端口 |
| `db` | `COZY_REDIS_DB` | `0` | Redis 数据库 |
| `password` | `COZY_REDIS_PASSWORD` | `None` | 密码 |
| `ttl` | `COZY_REDIS_TTL` | `3600` | 缓存过期时间 (秒) |

---

## 🔄 路由配置 (可选)

### 关键词路由

```python
from cozy_memory import MemoryService, RouterAdapter, MemobaseAdapter

# 定义路由规则
rules = {
    "pricing": ["价格", "费用", "成本", "报价"],
    "technical": ["技术", "代码", "架构", "API"],
    "general": ["*"]  # 默认
}

# 创建路由器
router = RouterAdapter(
    rules=rules,
    adapters={
        "pricing": MemobaseAdapter(...),
        "technical": MemobaseAdapter(...),
        "general": MemobaseAdapter(...)
    }
)

service = MemoryService(adapter=router)
```

### LLM 路由 (高级)

```python
from cozy_memory import LLMRouterAdapter

router = LLMRouterAdapter(
    model="gpt-3.5-turbo",  # 或本地模型
    adapters={
        "pricing": MemobaseAdapter(...),
        "technical": MemobaseAdapter(...),
    }
)

service = MemoryService(adapter=router)
```

**配置项**:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `model` | `gpt-3.5-turbo` | LLM 模型 |
| `api_key` | 从环境变量读取 | LLM API Key |
| `temperature` | `0.3` | 温度参数 |
| `max_tokens` | `100` | 最大 token 数 |

---

## 🛡️ 安全配置

### API Key 管理

**推荐方式**: 使用环境变量

```bash
# .env 文件
COZY_MEMOBASE_API_KEY=your-secret-key
COZY_MEMOBASE_PROJECT_ID=your-project-id
```

```python
# 使用 python-dotenv
from dotenv import load_dotenv
load_dotenv()

from cozy_memory import MemoryService, MemobaseAdapter

service = MemoryService(adapter=MemobaseAdapter.from_env())
```

**不推荐**: 硬编码在代码中

```python
# ❌ 避免这样做
service = MemoryService(
    adapter=MemobaseAdapter(api_key="hardcoded-key")
)
```

### 敏感信息脱敏

```python
from cozy_memory import MemoryService, sanitize_content

# 自动脱敏
service = MemoryService(sanitize=True)

# 自定义脱敏规则
service = MemoryService(
    sanitize=True,
    sanitize_rules={
        "phone": r"\d{3}-\d{4}-\d{4}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "credit_card": r"\d{4}-\d{4}-\d{4}-\d{4}"
    }
)
```

---

## ⚙️ 性能配置

### 连接池

```python
from cozy_memory import MemoryService, MemobaseAdapter

service = MemoryService(
    adapter=MemobaseAdapter(
        pool_size=10,  # 连接池大小
        max_overflow=5,  # 最大溢出连接数
        pool_timeout=30,  # 获取连接超时
        pool_recycle=3600  # 连接回收时间
    )
)
```

### 缓存配置

```python
from cozy_memory import MemoryService, CacheAdapter

service = MemoryService(
    adapter=CacheAdapter(
        backend="redis",  # 或 "memory"
        ttl=3600,  # 缓存过期时间
        max_size=1000  # 最大缓存条目
    )
)
```

### 批量操作配置

```python
from cozy_memory import MemoryService

service = MemoryService(
    batch_size=100,  # 批量操作大小
    batch_timeout=30  # 批量操作超时
)

# 使用批量操作
memories = await service.batch_add([...])
```

---

## 📊 监控配置

### 指标收集

```python
from cozy_memory import MemoryService, MetricsMiddleware

service = MemoryService(
    middleware=[
        MetricsMiddleware(
            enabled=True,
            export_to="prometheus"  # 或 "statsd"
        )
    ]
)
```

### 追踪配置

```python
from cozy_memory import MemoryService, TracingMiddleware

service = MemoryService(
    middleware=[
        TracingMiddleware(
            enabled=True,
            exporter="jaeger",  # 或 "zipkin"
            sample_rate=0.1  # 采样率
        )
    ]
)
```

---

## 🎯 配置最佳实践

### 1. 环境分离

```python
# config.py
import os

class Config:
    DEBUG = os.getenv("COZY_DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("COZY_LOG_LEVEL", "INFO")
    MEMOBASE_API_KEY = os.getenv("COZY_MEMOBASE_API_KEY")
    MEMOBASE_PROJECT_ID = os.getenv("COZY_MEMOBASE_PROJECT_ID")

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "WARNING"
```

### 2. 配置验证

```python
from pydantic import BaseSettings, validator

class CozyConfig(BaseSettings):
    memobase_api_key: str
    memobase_project_id: str
    log_level: str = "INFO"
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v

# 使用
config = CozyConfig()  # 自动验证
```

### 3. 配置热重载

```python
import asyncio
from pathlib import Path
from cozy_memory import MemoryService

class ConfigWatcher:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.service = None
    
    async def watch(self):
        while True:
            await asyncio.sleep(5)
            # 检测配置变化并重新加载
            # ...

# 使用
watcher = ConfigWatcher("config.yaml")
await watcher.watch()
```

---

## 🦀 维护者注释

**配置设计原则**:

1. **零配置优先**: 默认就能用
2. **环境变量优先**: 敏感信息不硬编码
3. **合理默认值**: 每个配置都有默认值
4. **类型安全**: Pydantic 验证
5. **文档完整**: 每个配置项都有说明

**配置演进**:

- v0.2: 基础配置 (Memobase + 日志)
- v0.3: 存储配置 (SQLite + Redis)
- v0.4: 路由配置 (关键词 + LLM)
- v1.0: 完整配置体系

---

## 📚 相关文档

- [快速开始](./getting-started.md)
- [适配器指南](./adapters.md)
- [API 参考](../api/reference.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀
