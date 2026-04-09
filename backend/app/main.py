from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal, create_db_and_tables
from app.services.seed_service import seed_job_codes


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    with SessionLocal() as db:
        seed_job_codes(db, settings.DEFAULT_JOB_CODE_SEED)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
