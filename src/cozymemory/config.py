"""CozyMemory 配置管理

使用 pydantic-settings 从环境变量和 .env 文件加载配置。
"""

from importlib.metadata import version as _pkg_version

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持环境变量和 .env 文件"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "CozyMemory"
    APP_VERSION: str = _pkg_version("cozymemory")
    APP_ENV: str = "development"
    DEBUG: bool = False

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    GRPC_PORT: int = 50051

    # Mem0 引擎
    MEM0_API_URL: str = "http://localhost:8888"
    MEM0_API_KEY: str = ""
    MEM0_TIMEOUT: float = 30.0
    MEM0_ENABLED: bool = True

    # Memobase 引擎
    MEMOBASE_API_URL: str = "http://localhost:8019"
    MEMOBASE_API_KEY: str = ""
    MEMOBASE_TIMEOUT: float = 60.0
    MEMOBASE_ENABLED: bool = True

    # Cognee 引擎
    COGNEE_API_URL: str = "http://localhost:8000"
    COGNEE_API_KEY: str = ""
    COGNEE_TIMEOUT: float = 300.0
    COGNEE_ENABLED: bool = True
    COGNEE_USER_EMAIL: str = "admin@cognee.com"
    COGNEE_USER_PASSWORD: str = ""

    # Redis（用户 ID 映射）
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_USER_MAPPING_TTL: int = 0  # 0 = 永不过期；正整数 = 秒

    # PostgreSQL 平台账号库（Organization / Developer / App / ApiKey 等）
    # 同 postgres 实例和 memobase 共用，不同 database
    # asyncpg 驱动 URL schema: postgresql+asyncpg://user:pass@host:port/db
    #
    # 端口逻辑：
    #   容器内（docker compose）→ cozy_postgres:5432（服务名解析）
    #   host 本地开发 / alembic → localhost:5433（避 5432 的老 PG 冲突）
    # 默认给 host 本地开发用；容器通过 .env 的 DATABASE_URL 环境变量覆写为 cozy_postgres:5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory"
    )

    # JWT（开发者 Dashboard 登录）
    JWT_SECRET: str = "change-me-in-production"  # 部署时必须设置
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL_SECONDS: int = 86400  # 24h

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # 速率限制（per-App，sliding window）
    RATE_LIMIT_PER_MINUTE: int = 600  # 0 = 不限制
    RATE_LIMIT_BURST: int = 100  # 允许的突发量

    # API Key 鉴权
    # 逗号分隔的多个 key，留空 = 鉴权关闭（开发模式）
    # 客户端通过 X-Cozy-API-Key header 传递；health/docs/openapi 不鉴权。
    COZY_API_KEYS: str = ""

    @property
    def api_keys_set(self) -> set[str]:
        return {k.strip() for k in self.COZY_API_KEYS.split(",") if k.strip()}

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys_set)


settings = Settings()
