from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AccessConfigUploadResponse, LoginRequest, LoginResponse
from app.services.access_config_service import apply_access_document
from app.services.access_service import authenticate_credentials, resolve_access_context, resolve_access_context_for_identity
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    credentials = authenticate_credentials(payload.username, payload.password)
    if not credentials:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    access = resolve_access_context_for_identity(
        db=db,
        username=payload.username.strip(),
        source="login",
    )
    if access.access_mode == "restricted" or not access.accessible_estates:
        raise HTTPException(status_code=403, detail="This user does not have estate access configured.")

    log_audit_event(
        db,
        event_type="auth.login",
        actor_username=access.username,
        actor_display_name=access.display_name,
        actor_role=access.role,
        target_type="scope",
        target_value=access.resolved_estate or ",".join(access.accessible_plantations) or "all",
        details={
            "accessible_estates": access.accessible_estates,
            "accessible_plantations": access.accessible_plantations,
            "access_mode": access.access_mode,
        },
    )

    return {
        "username": access.username,
        "display_name": access.display_name,
        "resolved_estate": access.resolved_estate,
        "accessible_estates": access.accessible_estates,
        "accessible_plantations": access.accessible_plantations,
        "selected_plantation": access.selected_plantation,
        "role": access.role,
        "can_upload": access.can_upload or access.role == "admin",
        "can_switch_estate": access.can_switch_estate,
        "access_mode": access.access_mode,
        "access_message": access.access_message,
    }


@router.post("/access-config/upload", response_model=AccessConfigUploadResponse)
async def upload_access_config(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    access = resolve_access_context(db, request)
    if access.role != "admin":
        raise HTTPException(status_code=403, detail="Only ADMIN can upload the access document.")

    if not file.filename.lower().endswith((".docx", ".csv", ".json")):
        raise HTTPException(status_code=400, detail="Upload the access list as a DOCX, CSV, or JSON file.")

    content = await file.read()
    try:
        summary = apply_access_document(content=content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_audit_event(
        db,
        event_type="access-config.upload",
        actor_username=access.username,
        actor_display_name=access.display_name,
        actor_role=access.role,
        target_type="access_document",
        target_value=file.filename,
        details={
            "estates_count": summary.estates_count,
            "users_count": summary.users_count,
            "plantation_codes": summary.plantation_codes,
        },
    )

    return {
        "source_filename": summary.source_filename,
        "estates_count": summary.estates_count,
        "estate_user_count": summary.estate_user_count,
        "plantation_codes": summary.plantation_codes,
        "users_count": summary.users_count,
        "message": summary.message,
        "warnings": summary.warnings,
    }
