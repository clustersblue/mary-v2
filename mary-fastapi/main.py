from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn

from app.core.config import settings, validate_for_runtime
from app.core.sessions import session_store
from app.db.session import engine, Base
from app.api.v1.api import api_router
# Import models so SQLAlchemy metadata registers them
import app.models.master_data
import app.models.user
import app.models.service_user
import app.models.shift
import app.models.attendance
import app.models.finance
import app.models.audit

logger = logging.getLogger(__name__)
IS_PRODUCTION = settings.ENVIRONMENT.strip().lower() == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_for_runtime(settings)
    if settings.AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    elif IS_PRODUCTION:
        logger.info("AUTO_CREATE_TABLES is off. Expecting an existing MySQL schema.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI Backend for Mary Care Management System (UK Health & Social Care)",
    version=settings.VERSION,
    openapi_url=None if IS_PRODUCTION else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.host_list())

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/healthz", tags=["Health Check"])
async def health_check():
    if not await session_store.ready():
        raise HTTPException(status_code=503, detail="session store unavailable")
    return {"status": "ok", "service": "mary-api-fastapi", "version": settings.VERSION}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
