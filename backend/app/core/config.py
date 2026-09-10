"""Centralised settings via pydantic-settings. Values come from env or .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DB
    database_url: str = "postgresql+psycopg2://cx:cxpass@localhost:5432/cxassist"

    # Vector DB (ChromaDB)
    chroma_host: str = "localhost"
    chroma_port: str = "8001"
    chroma_http: bool = True
    chroma_collection: str = "brand_context"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # LLM (OmniRoute + Gemini fallback)
    # omnipath_url is OpenAI-compatible; point it at a hosted/self-hosted router
    # (e.g. OmniRoute at http://<host>:20128/v1/chat/completions). The legacy
    # default is kept for backwards compat but does not resolve as of 2026.
    omnipath_url: str = "https://omniroute.ai/v1/chat/completions"
    omnipath_api_key: str = ""  # optional; omitted for keyless routers (REQUIRE_API_KEY=false)
    gemini_api_key: str = ""
    llm_provider: str = "auto"  # auto|omniroute|gemini
    llm_model: str = ""  # provider model; empty chooses provider default (OmniRoute: "auto", Gemini: "gemini-2.5-flash")
    temperature: float = 0.0
    max_tokens: int = 800

    # Retrieval / validation
    chunk_size: int = 900
    chunk_overlap: int = 120
    top_k: int = 5
    score_threshold: float = 0.30
    confidence_threshold: float = 0.60

    # Workflow behaviour
    workflow_grader_enabled: bool = True          # grade retrieved docs before generation
    workflow_llm_reviewer_enabled: bool = False   # extra adversarial LLM pass (costs quota); guardrails always run
    workflow_scrape_enabled: bool = True          # allow SSRF-hardened help-page scrape when KB has no relevant docs

    # Auth — NO insecure defaults. If these are unset/missing at boot, startup
    # refuses to run rather than silently shipping a "change-me" secret.
    secret_key: str = "change-me-to-a-long-random-secret"
    access_token_expire_minutes: int = 480

    # Bootstrap admin (seed once at startup when set)
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "Platform Admin"

    # Redis (cache + rate limiting + retry queue)
    redis_url: str = "redis://localhost:6379/0"

    # Fallback default for SlowAPI rules applied per-route (see main.py decorators)
    rate_limit_per_minute: int = 120

    # Webhook
    webhook_url: str = ""

    # Security: never allow cross-brand access
    enforce_brand_isolation: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return ["http://localhost:3000", "http://localhost:3001",
                "https://*.vercel.app", "https://cx-frontend.onrender.com"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()