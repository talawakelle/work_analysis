from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import AdminOverviewResponse, AuditEventListResponse
from app.services.access_service import resolve_access_context
from app.services.admin_service import build_admin_overview, list_admin_audit_events

router = APIRouter()


def _require_admin(request: Request, db: Session) -> None:
    access = resolve_access_context(db, request)
    if access.role != "admin":
        raise HTTPException(status_code=403, detail="Only ADMIN can open the admin page.")


@router.get("/overview", response_model=AdminOverviewResponse)
def admin_overview(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    return build_admin_overview(db)


@router.get("/audit", response_model=AuditEventListResponse)
def admin_audit(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _require_admin(request, db)
    return {"items": list_admin_audit_events(db, limit=limit)}
