from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.import_batch import ImportBatch
from app.schemas.imports import ImportBatchResponse, ImportListResponse, ImportValidationResponse
from app.services.access_service import resolve_access_context
from app.services.audit_service import log_audit_event
from app.services.import_service import import_workbook_bytes, validate_workbook_bytes

router = APIRouter()


def _serialize_batch(batch: ImportBatch, validation=None) -> dict:
    payload = {
        "id": batch.id,
        "label": batch.label,
        "source_filename": batch.source_filename,
        "month_start": batch.month_start,
        "month_end": batch.month_end,
        "rows_processed": batch.rows_processed,
        "status": batch.status,
        "created_at": batch.created_at,
        "validation_message": None,
        "validated_period": None,
        "validated_rows": None,
        "validated_sheets": None,
        "validated_estates": [],
        "validation_warnings": [],
        "validation_errors": [],
        "validation_sheet_results": [],
    }
    if validation is not None:
        payload.update(
            {
                "validation_message": validation.validation_message,
                "validated_period": validation.detected_period,
                "validated_rows": validation.total_rows,
                "validated_sheets": validation.sheet_count,
                "validated_estates": validation.validated_estates,
                "validation_warnings": validation.warnings,
                "validation_errors": validation.errors,
                "validation_sheet_results": [
                    {
                        "sheet_name": item.sheet_name,
                        "estate": item.estate,
                        "rows": item.rows,
                        "missing_columns": item.missing_columns,
                        "warnings": item.warnings,
                    }
                    for item in validation.sheets
                ],
            }
        )
    return payload


def _serialize_validation(filename: str, validation) -> dict:
    return {
        "source_filename": filename,
        "validation_message": validation.validation_message,
        "validated_period": validation.detected_period,
        "validated_rows": validation.total_rows,
        "validated_sheets": validation.sheet_count,
        "validated_estates": validation.validated_estates,
        "validation_warnings": validation.warnings,
        "validation_errors": validation.errors,
        "validation_sheet_results": [
            {
                "sheet_name": item.sheet_name,
                "estate": item.estate,
                "rows": item.rows,
                "missing_columns": item.missing_columns,
                "warnings": item.warnings,
            }
            for item in validation.sheets
        ],
    }


@router.get("", response_model=ImportListResponse)
def list_imports(request: Request, db: Session = Depends(get_db)):
    access = resolve_access_context(db, request)
    if not access.can_upload and access.role != "admin":
        return {"items": []}

    items = db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc())).all()
    return {"items": [_serialize_batch(item) for item in items]}


@router.post("/validate", response_model=ImportValidationResponse)
async def validate_import(
    request: Request,
    label: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    if not access.can_upload and access.role != "admin":
        raise HTTPException(status_code=403, detail="This user cannot validate datasets.")

    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Upload an Excel workbook or CSV file.")

    content = await file.read()
    try:
        validation = validate_workbook_bytes(content, file.filename, label=label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_audit_event(
        db,
        event_type="import.validate",
        actor_username=access.username,
        actor_display_name=access.display_name,
        actor_role=access.role,
        target_type="dataset",
        target_value=file.filename,
        details={
            "label": (label or "").strip() or None,
            "validated_period": validation.detected_period,
            "validated_rows": validation.total_rows,
            "validated_sheets": validation.sheet_count,
            "errors": validation.errors,
            "warnings": validation.warnings[:10],
        },
    )
    return _serialize_validation(file.filename, validation)


@router.post("/upload", response_model=ImportBatchResponse)
async def upload_import(
    request: Request,
    label: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    if not access.can_upload and access.role != "admin":
        raise HTTPException(status_code=403, detail="This user cannot upload datasets.")

    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Upload an Excel workbook or CSV file.")

    content = await file.read()
    try:
        validation = validate_workbook_bytes(content, file.filename, label=label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not validation.is_valid:
        detail = validation.errors[0] if validation.errors else "The upload validation failed."
        raise HTTPException(status_code=400, detail=detail)

    batch = import_workbook_bytes(db, content, file.filename, label=label)
    log_audit_event(
        db,
        event_type="import.upload",
        actor_username=access.username,
        actor_display_name=access.display_name,
        actor_role=access.role,
        target_type="dataset",
        target_value=file.filename,
        details={
            "label": batch.label,
            "rows_processed": batch.rows_processed,
            "validated_period": validation.detected_period,
            "validated_estates": validation.validated_estates,
        },
    )
    return _serialize_batch(batch, validation)
