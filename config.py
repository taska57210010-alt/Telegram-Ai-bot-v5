"""
Production-grade configuration with Pydantic validation.
Supports 100K+ concurrent users.
"""

from typing import Dict, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration with validation."""

    # ============ Telegram Configuration ============
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")
    TELEGRAM_PAYMENT_PROVIDER_TOKEN: str = Field(default="", description="Payment provider token")
    
    # Webhook Configuration (REQUIRED for production)
    WEBHOOK_ENABLED: bool = Field(default=True, description="Use webhooks instead of polling")
    WEBHOOK_DOMAIN: str = Field(default="", description="Public domain for webhooks (e.g., https://bot.example.com)")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Webhook endpoint path")
    WEBHOOK_SECRET: str = Field(default="", description="Secret token for webhook security")
    WEBHOOK_PORT: int = Field(default=8080, description="Port for webhook server")
    
    # ============ Database Configuration ============
    # PostgreSQL for production (required for 100K+ users)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_bot",
        description="PostgreSQL connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, description="Pool timeout in seconds")
    DATABASE_POOL_RECYCLE: int = Field(default=3600, description="Recycle connections after seconds")
    
    # ============ Redis Configuration ============
    # Redis for caching and session storage (required for scale)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    REDIS_POOL_SIZE: int = Field(default=50, description="Redis connection pool size")
    CACHE_TTL: int = Field(default=300, description="Default cache TTL in seconds")
    
    # ============ Celery Configuration ============
    # Task queue for background processing
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend")
    
    # ============ OpenRouter API Configuration ============
    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API key")
    OPENROUTER_URL: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API URL")
    OPENROUTER_TIMEOUT: int = Field(default=60, description="API timeout in seconds")
    
    # ============ AI Models Configuration ============
    AVAILABLE_MODELS: Dict[str, str] = Field(
        default={
            "gpt4o": "openai/gpt-4o",
            "gpt41": "openai/gpt-4-turbo",
            "claude_sonnet": "anthropic/claude-3.5-sonnet",
            "free": "meta-llama/llama-3.1-8b-instruct:free",
        },
        description="Available AI models"
    )
    DEFAULT_MODEL: str = Field(default="free", description="Default AI model")
    
    # ============ Payment Configuration ============
    STARS_PER_PACKAGE: Dict[str, int] = Field(
        default={
            "small": 10,
            "medium": 50,
            "large": 100,
        },
        description="Stars per package"
    )
    QUESTIONS_PER_STAR: int = Field(default=10, description="Questions per star")
    QUESTIONS_PER_PACKAGE: Dict[str, int] = Field(
        default={
            "small": 100,
            "medium": 500,
            "large": 1000,
        },
        description="Questions per package"
    )
    
    # ============ Rate Limiting Configuration ============
    # Per-user rate limits (critical for cost control)
    RATE_LIMIT_QUESTIONS_PER_MINUTE: int = Field(default=5, description="Max questions per minute per user")
    RATE_LIMIT_QUESTIONS_PER_HOUR: int = Field(default=20, description="Max questions per hour per user")
    RATE_LIMIT_QUESTIONS_PER_DAY: int = Field(default=100, description="Max questions per day per user")
    RATE_LIMIT_CALLBACKS_PER_SECOND: int = Field(default=3, description="Max callbacks per second per user")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")
    
    # Global rate limits (protect infrastructure)
    GLOBAL_RATE_LIMIT_PER_SECOND: int = Field(default=100, description="Max requests per second globally")
    
    # ============ Telegram Limits ============
    MESSAGE_CHAR_LIMIT: int = Field(default=4096, description="Telegram message character limit")
    CAPTION_CHAR_LIMIT: int = Field(default=1024, description="Telegram caption character limit")
    
    # ============ Logging Configuration ============
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    
    # ============ Retry Configuration ============
    MAX_RETRIES: int = Field(default=3, description="Max retry attempts for API calls")
    RETRY_DELAY: float = Field(default=1.0, description="Initial retry delay in seconds")
    RETRY_MAX_DELAY: float = Field(default=10.0, description="Max retry delay in seconds")
    
    # ============ Typing Action Configuration ============
    TYPING_REFRESH_INTERVAL: int = Field(default=4, description="Typing action refresh interval")
    TYPING_MAX_DURATION: int = Field(default=120, description="Max typing duration in seconds")
    
    # ============ Request Timeout Configuration ============
    AI_REQUEST_TIMEOUT: int = Field(default=120, description="AI request timeout in seconds")
    
    # ============ Input Validation Configuration ============
    MAX_PROMPT_LENGTH: int = Field(default=4000, description="Max prompt length")
    MIN_PROMPT_LENGTH: int = Field(default=1, description="Min prompt length")
    
    # ============ Monitoring Configuration ============
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    SENTRY_ENVIRONMENT: str = Field(default="production", description="Sentry environment")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")
    
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    PROMETHEUS_PORT: int = Field(default=9090, description="Prometheus metrics port")
    
    # ============ Admin Configuration ============
    ADMIN_USER_IDS: list[int] = Field(default=[], description="Admin user IDs")
    
    # ============ Support Configuration ============
    SUPPORT_USERNAME: str = Field(default="support", description="Telegram support username")
    BOT_NAME: str = Field(default="AI Chat Bot", description="Bot display name")
    FREE_QUESTIONS_ON_REGISTRATION: int = Field(default=3, description="Free questions for new users")
    
    # ============ Feature Flags ============
    MAINTENANCE_MODE: bool = Field(default=False, description="Enable maintenance mode")
    NEW_USER_REGISTRATION_ENABLED: bool = Field(default=True, description="Allow new user registration")
    PAYMENTS_ENABLED: bool = Field(default=True, description="Enable payment processing")
    
    # ============ Performance Configuration ============
    MAX_CONCURRENT_AI_REQUESTS: int = Field(default=100, description="Max concurrent AI requests")
    WORKER_CONCURRENCY: int = Field(default=10, description="Celery worker concurrency")
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse admin IDs from comma-separated string."""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @model_validator(mode="after")
    def validate_webhook_config(self):
        """Validate webhook configuration."""
        if self.WEBHOOK_ENABLED and not self.WEBHOOK_DOMAIN:
            raise ValueError("WEBHOOK_DOMAIN is required when WEBHOOK_ENABLED=True")
        return self

    def get_model_by_key(self, model_key: str) -> str:
        """Get model name by key."""
        if model_key not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Invalid model '{model_key}'. "
                f"Available: {', '.join(self.AVAILABLE_MODELS.keys())}"
            )
        return self.AVAILABLE_MODELS[model_key]

    def get_questions_for_package(self, package: str) -> int:
        """Get questions count for a package."""
        return self.QUESTIONS_PER_PACKAGE.get(package, 0)

    def get_stars_for_package(self, package: str) -> int:
        """Get stars count for a package."""
        return self.STARS_PER_PACKAGE.get(package, 0)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.ADMIN_USER_IDS


# Global config instance
try:
    config = Config()
except Exception as e:
    raise RuntimeError(f"Failed to load configuration: {e}") from e
