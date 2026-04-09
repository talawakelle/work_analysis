from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def log_audit_event(
    db: Session,
    *,
    event_type: str,
    actor_username: str | None = None,
    actor_display_name: str | None = None,
    actor_role: str | None = None,
    target_type: str | None = None,
    target_value: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor_username=(actor_username or "").strip() or None,
        actor_display_name=(actor_display_name or "").strip() or None,
        actor_role=(actor_role or "").strip() or None,
        target_type=(target_type or "").strip() or None,
        target_value=(target_value or "").strip() or None,
        details_json=json.dumps(details or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit_events(db: Session, limit: int = 100) -> list[AuditEvent]:
    return db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()


def parse_event_details(event: AuditEvent) -> dict[str, Any]:
    if not event.details_json:
        return {}
    try:
        payload = json.loads(event.details_json)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
