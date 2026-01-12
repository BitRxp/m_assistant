from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from .api.health import router as health_router
from .api.ws import router as ws_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("startup")
    yield


app = FastAPI(title="m_assistant backend", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(ws_router)
