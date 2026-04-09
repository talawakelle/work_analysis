from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meta import MetaFiltersResponse
from app.services.access_service import resolve_access_context
from app.services.analytics_service import get_filters

router = APIRouter()


@router.get("/filters", response_model=MetaFiltersResponse)
def filters(request: Request, db: Session = Depends(get_db)):
    access = resolve_access_context(db, request)
    return get_filters(db, access)
