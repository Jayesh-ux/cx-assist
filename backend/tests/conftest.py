"""Test bootstrap: configure env BEFORE any app module is imported so the
lru_cached settings singleton picks up sane, non-production values."""
import os

os.environ.setdefault("SECRET_KEY", "t" * 40)
os.environ.setdefault("JWT_SECRET", "j" * 40)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:5999/0")  # unroutable -> in-memory fallback
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("OMNIPATH_API_KEY", "")
os.environ.setdefault("WORKFLOW_LLM_REVIEWER_ENABLED", "false")