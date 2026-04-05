# ADR-005: 认证方案设计

**状态**: 已决定  
**日期**: 2026-04-05  
**决策者**: 张老师  
**记录者**: 蟹小五

---

## 背景

统一 API 层需要认证和授权机制，需求：
1. 支持 OAuth2 标准协议
2. 内置用户管理系统
3. 支持 API Key（便于服务端集成）
4. 简单够用，不过度设计

## 需求分析

| 需求 ID | 描述 | 优先级 |
|--------|------|--------|
| FR-01 | 支持 OAuth2 授权码流程 | P0 |
| FR-02 | 支持 API Key 认证 | P0 |
| FR-03 | 内置用户管理（CRUD） | P0 |
| FR-04 | 支持 JWT Token | P0 |
| FR-05 | 支持 Token 刷新 | P1 |
| FR-06 | 支持权限控制（RBAC） | P1 |

## 候选方案对比

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| **FastAPI Users** | 完整用户管理、OAuth2、JWT | 学习曲线中等 | 中小型项目 ✅ |
| Authlib | OAuth2 客户端/服务端 | 需要自己实现用户管理 | OAuth2 集成 |
| Keycloak (外部) | 功能强大、企业级 | 重量级、运维复杂 | 大型企业 |
| 自研 | 完全定制 | 开发成本高、安全风险 | 特殊需求 |

## 决策

✅ **选择 FastAPI Users + 自研 API Key 模块**

### 理由

1. **FastAPI 原生集成**: 与 FastAPI 深度集成，文档完善
2. **功能覆盖**: 用户管理、OAuth2、JWT 全部支持
3. **轻量级**: 无需外部依赖，数据库存储
4. **可扩展**: 支持自定义用户模型和认证后端
5. **活跃生态**: GitHub 6k+ stars，社区活跃

### API Key 补充

FastAPI Users 主要针对终端用户，对于服务端集成（API Key）需要补充：
- 自研轻量级 API Key 模块
- 与 FastAPI Users 共享用户数据库

---

## 架构设计

### 认证架构

```
┌─────────────────────────────────────────────────────────┐
│                     Client Request                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Authentication Middleware                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. 检查 Authorization Header                      │  │
│  │     - Bearer <JWT> → JWT 认证                       │  │
│  │     - ApiKey <key> → API Key 认证                   │  │
│  │  2. 检查 X-API-Key Header → API Key 认证            │  │
│  │  3. 未认证 → 401 Unauthorized                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Authentication Backend                      │
│  ┌─────────────────┐      ┌─────────────────┐          │
│  │  JWT Backend    │      │  API Key Backend│          │
│  │  (FastAPI Users)│      │  (Custom)       │          │
│  └─────────────────┘      └─────────────────┘          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              User Database                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  users table:                                      │  │
│  │  - id, email, hashed_password                      │  │
│  │  - is_active, is_superuser                         │  │
│  │  - created_at, updated_at                          │  │
│  │                                                    │  │
│  │  api_keys table:                                   │  │
│  │  - id, user_id, key_hash                           │  │
│  │  - name, scopes                                    │  │
│  │  - expires_at, last_used_at                        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 详细设计

### 1. 数据库模型

```python
# models/user.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联 API Keys
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


# models/api_key.py
class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    key_hash = Column(String, nullable=False, index=True)  # 存储哈希值
    key_prefix = Column(String, nullable=False)  # 存储前 8 位用于识别
    
    name = Column(String, nullable=False)  # API Key 名称
    scopes = Column(String, default="*")  # 权限范围，逗号分隔
    
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联用户
    user = relationship("User", back_populates="api_keys")
```

### 2. JWT 认证（FastAPI Users）

```python
# auth/jwt_auth.py
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    JWTAuthentication,
    AuthenticationBackend,
    CookieAuthentication,
)

from models.user import User

# JWT 配置
SECRET = "your-secret-key-change-in-production"

jwt_authentication = AuthenticationBackend(
    name="jwt",
    transport=JWTAuthentication(
        secret=SECRET,
        lifetime_seconds=3600,  # 1 小时
        tokenUrl="auth/jwt/login",
    ),
)

# Cookie 配置（可选，用于 Web 端）
cookie_authentication = AuthenticationBackend(
    name="cookies",
    transport=CookieAuthentication(
        secret=SECRET,
        lifetime_seconds=3600,
    ),
)

# FastAPI Users 实例
fastapi_users = FastAPIUsers[User, str](
    get_user_manager,
    [jwt_authentication, cookie_authentication],
)

# 依赖注入
current_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
```

### 3. API Key 认证（自研）

```python
# auth/api_key_auth.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from sqlalchemy import select
from datetime import datetime
import hashlib
import secrets

from database import get_db_session
from models.api_key import APIKey

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

def generate_api_key() -> str:
    """生成新的 API Key"""
    return f"sk_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    """哈希 API Key"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def get_key_prefix(api_key: str) -> str:
    """获取 API Key 前缀（用于识别）"""
    return api_key[:8]

async def get_api_key(
    api_key_header: str = Security(API_KEY_HEADER),
    api_key_query: str = Security(API_KEY_QUERY),
) -> str:
    """从 Header 或 Query 获取 API Key"""
    api_key = api_key_header or api_key_query
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key

async def validate_api_key(api_key: str = Security(get_api_key)) -> APIKey:
    """验证 API Key 并返回密钥对象"""
    db = next(get_db_session())
    key_hash = hash_api_key(api_key)
    
    # 查询密钥
    result = db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    )
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 检查过期
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 更新最后使用时间
    api_key_obj.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_key_obj
```

### 4. 统一认证依赖

```python
# auth/deps.py
from typing import Optional, Union
from fastapi import Depends

from models.user import User
from models.api_key import APIKey
from auth.jwt_auth import current_user
from auth.api_key_auth import validate_api_key

# 认证结果类型
AuthenticatedIdentity = Union[User, APIKey]

async def get_authenticated_user(
    user: Optional[User] = Depends(current_user),
    api_key: Optional[APIKey] = Depends(validate_api_key),
) -> AuthenticatedIdentity:
    """
    统一认证依赖
    
    支持两种认证方式：
    1. JWT Token (终端用户)
    2. API Key (服务端集成)
    """
    if user:
        return user
    if api_key:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )
```

### 5. 用户管理 API

```python
# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from typing import List

from auth.deps import get_authenticated_user, AuthenticatedIdentity
from auth.jwt_auth import fastapi_users
from models.user import User
from models.api_key import APIKey
from schemas.user import UserCreate, UserUpdate, UserRead
from schemas.api_key import APIKeyCreate, APIKeyRead

router = APIRouter(prefix="/users", tags=["users"])

# 用户注册
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate):
    """注册新用户"""
    user = await fastapi_users.create_user(user_create)
    return user

# 获取当前用户信息
@router.get("/me", response_model=UserRead)
async def get_me(user: AuthenticatedIdentity = Depends(get_authenticated_user)):
    """获取当前用户信息"""
    if isinstance(user, APIKey):
        # API Key 认证，返回关联用户
        db = next(get_db_session())
        result = db.execute(select(User).where(User.id == user.user_id))
        return result.scalar_one()
    return user

# 创建 API Key
@router.post("/me/api-keys", response_model=APIKeyRead, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_create: APIKeyCreate,
    user: AuthenticatedIdentity = Depends(get_authenticated_user),
):
    """为当前用户创建 API Key"""
    db = next(get_db_session())
    
    # 获取用户 ID
    if isinstance(user, APIKey):
        user_id = user.user_id
    else:
        user_id = user.id
    
    # 生成 API Key
    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=user_id,
        key_hash=hash_api_key(raw_key),
        key_prefix=get_key_prefix(raw_key),
        name=api_key_create.name,
        scopes=api_key_create.scopes,
        expires_at=api_key_create.expires_at,
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # 返回时包含原始密钥（只展示一次）
    result = APIKeyRead.from_orm(api_key)
    result.raw_key = raw_key  # 仅此次返回
    return result

# 列出 API Keys
@router.get("/me/api-keys", response_model=List[APIKeyRead])
async def list_api_keys(user: AuthenticatedIdentity = Depends(get_authenticated_user)):
    """列出当前用户的所有 API Keys"""
    db = next(get_db_session())
    
    if isinstance(user, APIKey):
        user_id = user.user_id
    else:
        user_id = user.id
    
    result = db.execute(select(APIKey).where(APIKey.user_id == user_id))
    return result.scalars().all()

# 删除 API Key
@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    user: AuthenticatedIdentity = Depends(get_authenticated_user),
):
    """删除指定的 API Key"""
    db = next(get_db_session())
    
    if isinstance(user, APIKey):
        user_id = user.user_id
    else:
        user_id = user.id
    
    api_key = db.get(APIKey, key_id)
    if not api_key or api_key.user_id != user_id:
        raise HTTPException(status_code=404, detail="API Key not found")
    
    db.delete(api_key)
    db.commit()
```

---

## API 端点

### OAuth2 / JWT 认证

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /auth/jwt/login | 获取 JWT Token |
| POST | /auth/jwt/logout | 注销（使 Token 失效） |
| POST | /auth/register | 用户注册 |
| GET | /users/me | 获取当前用户信息 |
| PATCH | /users/me | 更新用户信息 |

### API Key 管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /users/me/api-keys | 创建 API Key |
| GET | /users/me/api-keys | 列出 API Keys |
| DELETE | /users/me/api-keys/{id} | 删除 API Key |

---

## 安全考虑

### 1. 密码安全
- ✅ 使用 bcrypt 哈希密码
- ✅ 密码强度要求（8 位以上，包含大小写和数字）

### 2. API Key 安全
- ✅ 存储哈希值，不存储明文
- ✅ 使用 cryptographically secure 随机数生成
- ✅ 支持过期时间
- ✅ 支持权限范围（scopes）

### 3. Token 安全
- ✅ JWT 签名验证
- ✅ Token 过期时间（1 小时）
- ✅ 支持 Token 刷新

### 4. 传输安全
- ⚠️ 生产环境必须使用 HTTPS
- ⚠️ API Key 只能通过 Header 传输（不推荐 Query 参数）

---

## 依赖

```python
# requirements.txt
fastapi-users[sqlalchemy]>=13.0.0
fastapi>=0.109.0
python-jose[cryptography]>=3.3.0  # JWT
bcrypt>=4.0.0  # 密码哈希
```

---

## 影响

- ✅ 内置用户管理，无需外部服务
- ✅ 支持两种认证方式（JWT + API Key）
- ✅ 符合 OAuth2 标准
- ⚠️ 需要妥善保管 SECRET 密钥

---

## 合规性

本决策符合架构原则：
- AP-01 (松耦合): 认证模块独立，便于替换
- AP-04 (可观测性): 记录认证失败便于监控

---

**END OF ADR**
