from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    STREAMLIT_PORT: int = 8501

    # Cryptographic Keys & Secrets
    ARGUS_VAULT_ENCRYPTION_KEY: str = (
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    ARGUS_TOKENIZER_SALT: str = "argus-secure-session-salt-default"
    JWT_SECRET_KEY: str = "argus-super-secret-jwt-key-default"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AGENT_MESH_SIGNING_SEED: str = "argus-agent-mesh-seed-default"

    # PostgreSQL & pgvector
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "argus"
    POSTGRES_USER: str = "argus_user"
    POSTGRES_PASSWORD: str = "argus_password_local"
    POSTGRES_VAULT_USER: str = "argus_vault_user"
    POSTGRES_VAULT_PASSWORD: str = "argus_vault_password_local"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    # Open Policy Agent
    OPA_URL: str = "http://localhost:8181"
    OPA_POLICY_BUNDLE_DIR: str = "./policies"

    # LLM Runtime & Embeddings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    # Storage
    STORAGE_BACKEND: str = "local"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "argus-regulations"

    # Observability
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str = "http://localhost:3000"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    @property
    def postgres_core_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def postgres_vault_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_VAULT_USER}:{self.POSTGRES_VAULT_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
