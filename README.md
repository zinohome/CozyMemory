# CozyMemory 🦀

**个人记忆管理系统 - 整合 Memobase/Mem0/Cognee**

> 站在巨人肩膀上，不重复造轮子

---

## 🎯 定位

**不是**自己实现存储引擎，而是：
- ✅ **统一 API** - 一个接口调用所有记忆引擎
- ✅ **智能路由** - 根据意图选择最佳引擎
- ✅ **结果融合** - 去重、排序、缓存
- ✅ **零重复造轮子** - 用现有引擎的能力

---

## 🏗️ 架构

```
┌─────────────────────────────────┐
│      CozyMemory (统一 API)      │
│  ┌─────────────────────────┐    │
│  │   智能路由 + 缓存层      │    │
│  └───────────┬─────────────┘    │
└──────────────┼──────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│Memobase│ │ Mem0  │ │ Cognee│ │ 其他  │
│ (已有) │ │ (已有) │ │ (已有) │ │ 引擎  │
└───────┘ └───────┘ └───────┘ └───────┘
```

---

## 🚀 快速开始

### 安装

```bash
pip install cozy-memory
```

### 配置

```yaml
# config.yaml
engines:
  memobase:
    api_url: "http://localhost:8000"
    enabled: true
  
  mem0:
    api_key: "your-api-key"
    enabled: true
  
  cognee:
    api_url: "http://localhost:8001"
    enabled: true

router:
  default_engine: memobase
  cache_ttl: 3600
```

### 使用

```python
from cozy_memory import CozyMemory

# 初始化
cm = CozyMemory.from_config("config.yaml")

# 创建记忆
await cm.create_memory(
    user_id="user1",
    content="我喜欢 Python 编程",
    memory_type="preference",
)

# 查询记忆 (自动路由)
memories = await cm.query("我的编程偏好")

# 指定引擎
memories = await cm.query("我的编程偏好", engine="mem0")
```

---

## 📋 功能

### 核心功能

- [x] 统一 API 接口
- [x] 多引擎支持
- [x] 智能路由
- [x] 结果融合
- [x] 缓存层
- [ ] 意图识别 (LLM)
- [ ] 记忆推荐
- [ ] 可视化分析

### 支持的引擎

| 引擎 | 状态 | 特性 |
|------|------|------|
| **Memobase** | ✅ 支持 | 事实、事件、技能 |
| **Mem0** | ✅ 支持 | 用户偏好、配置 |
| **Cognee** | 📅 计划中 | 知识图谱 |
| **SQLite** | 📅 可选 | 本地存储 |

---

## 🔧 技术栈

- **Python** 3.11+
- **FastAPI** - API 框架
- **Pydantic** - 数据验证
- **AsyncIO** - 异步支持
- **Redis** (可选) - 缓存

---

## 📊 对比

| 特性 | CozyMemory | 直接使用引擎 |
|------|-----------|-------------|
| **统一接口** | ✅ | ❌ |
| **智能路由** | ✅ | ❌ |
| **结果融合** | ✅ | ❌ |
| **缓存** | ✅ | 部分 |
| **扩展性** | ✅ 插件式 | ❌ 硬编码 |

---

## 📝 许可证

MIT License

---

**🦀 Built with love by 蟹小五**
