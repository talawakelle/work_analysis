from fastapi import APIRouter

from app.api.routes import admin, analytics, auth, imports, meta

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
