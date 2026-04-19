"""CozyMemory 配置管理

使用 pydantic-settings 从环境变量和 .env 文件加载配置。
"""

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
    APP_VERSION: str = "2.0.0"
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

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
