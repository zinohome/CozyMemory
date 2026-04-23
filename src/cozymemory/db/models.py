"""SQLAlchemy 2.0 声明式模型 — 平台账号体系 6 张表。

设计：
  Organization (租户) ─┬─ Developer (工程师账号)
                       └─ App ─┬─ ApiKey
                               └─ ExternalUser (外部 app 的用户映射)

  AuditLog 独立表，关联到 app_id + 操作者

ID 全部 UUID v4，便于分布式和 URL 安全。
external_user_id 明文存（见讨论记录），需 PII 加密时再升级。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有模型的基类"""


# ─────────────────────────── Organization ───────────────────────────


class Organization(Base):
    """租户 — 一个 B 端客户公司。

    比如"字节跳动"。下属有 Developer（工程师）和 App（多个产品）。
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # URL 友好
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    developers: Mapped[list[Developer]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    apps: Mapped[list[App]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


# ─────────────────────────── Developer ───────────────────────────


class Developer(Base):
    """开发者账号 — Organization 内的工程师。

    用邮箱+密码登录 Dashboard；不是终端用户（终端用户不在 CozyMemory 里注册）。
    """

    __tablename__ = "developers"
    __table_args__ = (UniqueConstraint("email", name="uq_developer_email"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="")
    # 角色：'owner' / 'admin' / 'member'（owner 创建 org 时自动分配）
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped[Organization] = relationship(back_populates="developers")


# ─────────────────────────── App ───────────────────────────


class App(Base):
    """应用 — Organization 下的一个产品实例（比如"抖音记忆"）。

    每个 App 一个独立的 user_id 命名空间：
      internal_uuid = uuid5(App.namespace_id, external_user_id)
    """

    __tablename__ = "apps"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_app_org_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    # namespace_id：用于 uuid5 计算的稳定 namespace。App 创建时随机生成并永不变。
    # 这样即使 app name 改了，已有的 external_user_id 映射仍然对得上。
    namespace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped[Organization] = relationship(back_populates="apps")
    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="app", cascade="all, delete-orphan"
    )
    external_users: Mapped[list[ExternalUser]] = relationship(
        back_populates="app", cascade="all, delete-orphan"
    )


# ─────────────────────────── ApiKey ───────────────────────────


class ApiKey(Base):
    """一把 API Key — 属于某个 App。

    从现有 services/api_keys.py 的 Redis 实现迁移过来。保留 prefix / hash / rotate
    / audit 等语义，加入 app_id 外键实现多租户隔离。
    """

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_hash", "key_hash"),
        Index("ix_api_keys_app", "app_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # sha256 hex
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)  # 展示用：cozy_live_abc12
    # 环境：'live' = 生产，'test' = 沙箱（可做配额/QPS 区分）
    environment: Mapped[str] = mapped_column(String(20), default="live", nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    app: Mapped[App] = relationship(back_populates="api_keys")


# ─────────────────────────── ExternalUser ───────────────────────────


class ExternalUser(Base):
    """外部 App 的终端用户 — (app_id, external_user_id) → internal_uuid 索引。

    内部 uuid 由 uuid5(App.namespace_id, external_user_id) 计算得出（确定性），
    Redis 丢数据也能从 app namespace 重新算。本表的作用：
      1. 列出 App 有哪些 user（分页、监控）
      2. GDPR 级联删除时枚举 external_user_id
      3. 审计（创建时间、最近活跃）

    注意：last_active_at 不在本表，在 Redis ZSET（每次 API 调用刷新太频繁，
    避免 PG 行锁）。
    """

    __tablename__ = "external_users"
    __table_args__ = (
        UniqueConstraint("app_id", "external_user_id", name="uq_app_ext_user"),
        Index("ix_external_users_uuid", "internal_uuid"),
    )

    internal_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    app: Mapped[App] = relationship(back_populates="external_users")


# ─────────────────────────── AuditLog ───────────────────────────


class AuditLog(Base):
    """审计日志 — 关键操作记录。

    写入场景：
      - 开发者登录 / 创建 App / 轮换 Key
      - GDPR 删除 user
      - 跨越 app 边界的操作（未来有了再记）

    保留策略：90 天（由 cron job 清理，不入本批次）。
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_app_time", "app_id", "created_at"),
        Index("ix_audit_logs_actor", "actor_type", "actor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # 操作者类型 + ID
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'developer' / 'api_key' / 'system'
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)  # 对应 id
    # 操作
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # 'app.created', 'user.deleted', ...
    # 作用对象（可选）
    target_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 所属 app（用于检索 / 客户看自己 app 的审计）
    app_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apps.id", ondelete="SET NULL"),
        nullable=True,
    )
    # 扩展字段（具体视 action 而定）
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4/v6
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ─────────────────────── App ↔ Cognee Dataset 归属 ───────────────────────


class AppDataset(Base):
    """App 名下的 Cognee dataset 归属索引。

    一个 dataset 只属于一个 App（one-to-one）。首次创建时在此登记；listing
    时按 app_id 过滤；cross-App 的 dataset 访问统一 404（防枚举）。

    legacy 数据（没有 app_id 的老 dataset）只对 Operator 可见。
    """

    __tablename__ = "app_datasets"
    __table_args__ = (
        Index("ix_app_datasets_app", "app_id"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
