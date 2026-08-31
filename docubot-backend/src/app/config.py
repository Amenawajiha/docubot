from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str
    debug: bool = False

    # ── URLs ──────────────────────────────────────────────────────────────────
    # Base URL of THIS backend server — used to build OAuth callback URIs.
    # Dev:  http://localhost:8000
    # Prod: https://api.yourdomain.com
    backend_url: str = "http://localhost:8001"
    # Base URL of the frontend — used in email links and OAuth redirects.
    frontend_url: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Fernet ────────────────────────────────────────────────────────────────
    fernet_key: str

    # ── Email (fastapi-mail) ──────────────────────────────────────────────────
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@docubot.app"
    mail_from_name: str = "DocuBot"
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    # True in dev → skip real SMTP, print link to console instead
    mail_suppress_send: bool = False

    # ── Celery ────────────────────────────────────────────────────────────────
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # ── S3 / MinIO ────────────────────────────────────────────────────────────
    s3_endpoint_url: str = ""
    s3_external_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_name: str = "docubot-files"
    s3_region: str = "us-east-1"

    # ── LLM ───────────────────────────────────────────────────────────────────
    default_openai_api_key: str = ""

    # ── Knowledge base ────────────────────────────────────────────────────────
    # Max file size in MB for document uploads
    max_upload_size_mb: int = 50
    # Chatbot-RAG service URL (used for health checks and direct API calls if needed)
    chatbot_rag_url: str = "http://localhost:8000"

    # ── Chatbot Retention & Cleanup ───────────────────────────────────────────
    # Number of days soft-deleted chatbots and their MinIO/Qdrant assets are
    # preserved before being permanently hard-deleted by the background worker.
    chatbot_retention_days: int = 1

    # ── Internal API ──────────────────────────────────────────────────────────
    # Shared secret this backend sends to chatbot-rag in X-Internal-API-Key
    # Must match the key configured in the chatbot-rag service
    internal_api_key: str = ""
    # End-user chat session TTL in hours (default 4)
    session_ttl_hours: int = 4

    # ── Playground Settings ───────────────────────────────────────────────────
    playground_query_limit: int = 10

    # ── Billing ───────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
 
    # ── Rate limiting ────────────────────────────────────────────────────────
    # Set to False to disable all rate limiting (useful in development/testing)
    rate_limit_enabled: bool = True
    # Override individual zone limits via env (useful for staging/prod tuning)
    rate_limit_auth_write: int = 10    # per IP per minute
    rate_limit_auth_token: int = 30    # per IP per minute
    rate_limit_chat_ws: int = 20       # per session per minute
    rate_limit_upload: int = 10        # per workspace per minute
    rate_limit_internal: int = 500     # per internal key per minute
    rate_limit_workspace: int = 120    # per user per minute
 
    # ── Testing ───────────────────────────────────────────────────────────────
    test_database_url: str = ""

    # ── OAuth — Google ────────────────────────────────────────────────────────
    google_client_id: str = ""

    # ── OAuth — GitHub ────────────────────────────────────────────────────────
    github_client_id: str = ""
    github_client_secret: str = ""

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            self.frontend_url,
            "http://localhost:3000",
            "http://localhost:8091",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8091",
        ]
        return list(dict.fromkeys(origins))



    @property
    def github_redirect_uri(self) -> str:
        """OAuth callback URI registered in GitHub OAuth App settings."""
        return f"{self.backend_url}/api/v1/auth/github/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()