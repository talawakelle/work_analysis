from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import DashboardResponse, EmployeeDetailResponse, EmployeeSearchItem, WorkAnalysisResponse
from app.services.access_service import resolve_access_context
from app.services.analytics_service import dashboard_summary, employee_detail, search_employees, work_analysis

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    request: Request,
    estate: str | None = Query(None),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    return dashboard_summary(
        db=db,
        estate=estate,
        accessible_estates=access.accessible_estates,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/work-analysis", response_model=WorkAnalysisResponse)
def work_analysis_route(
    request: Request,
    estate: str | None = Query(None),
    start_date: date = Query(...),
    end_date: date = Query(...),
    direction: str = Query(..., pattern="^(top|bottom)$"),
    metric: str = Query(..., pattern="^(workers|kilos|days)$"),
    value: int = Query(..., ge=1, le=500),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    try:
        return work_analysis(
            db=db,
            estate=estate,
            accessible_estates=access.accessible_estates,
            start_date=start_date,
            end_date=end_date,
            direction=direction,
            metric=metric,
            value=value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/employees/search", response_model=list[EmployeeSearchItem])
def employee_search(
    request: Request,
    estate: str | None = Query(None),
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    return search_employees(db=db, estate=estate, accessible_estates=access.accessible_estates, q=q)


@router.get("/employees/{employee_id}/detail", response_model=EmployeeDetailResponse)
def employee_detail_route(
    request: Request,
    employee_id: int,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    ym: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    division: str | None = Query(None),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    try:
        return employee_detail(
            db=db,
            employee_id=employee_id,
            accessible_estates=access.accessible_estates,
            start_date=start_date,
            end_date=end_date,
            ym=ym,
            division=division,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
