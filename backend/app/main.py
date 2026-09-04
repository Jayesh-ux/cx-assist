"""CX Assist — Application entrypoint. Wire the FastAPI app, routers, lifespan bootstrap."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (admin, auth, brands, conversations, health, knowledge,
                     orders, replies, review, search)
from app.core.config import settings
from app.core.logging import logger
from app.core.request_id import RequestIDMiddleware
from app.db.session import engine
from app.workers.jobs import worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure tables/collections + start the background job worker."""
    from app.db import base  # noqa: F401  (ensure models are imported for metadata)
    logger.info("CX Assist starting up")
    from app.services.vector_store import ensure_collection

    ensure_collection()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(worker_loop(stop_event))
    app.state.worker_stop = stop_event
    app.state.worker_task = worker_task
    yield
    stop_event.set()
    worker_task.cancel()
    logger.info("CX Assist shutting down")
    engine.dispose()


app = FastAPI(
    title="CX Assist",
    version="1.1.0",
    description="Production-grade AI-powered CX reply assistant with strict no-hallucination guardrails.",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(replies.router, prefix="/api/replies", tags=["replies"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge base"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/", include_in_schema=False)
def root():
    return {"service": "CX Assist", "docs": "/docs", "status": "running"}