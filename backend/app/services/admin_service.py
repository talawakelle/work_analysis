from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_event import AuditEvent
from app.models.estate import Estate
from app.models.import_batch import ImportBatch
from app.models.work_record import WorkRecord
from app.services.audit_service import parse_event_details

KNOWN_PLANTATIONS = ("TTEL", "KVPL", "HPL")


def _read_access_file() -> list[dict[str, Any]]:
    path = Path(settings.USER_ACCESS_FILE)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for group in ("admins", "users"):
            items = payload.get(group)
            if isinstance(items, list):
                rows.extend(item for item in items if isinstance(item, dict))
    elif isinstance(payload, list):
        rows.extend(item for item in payload if isinstance(item, dict))
    return rows


def _estate_to_plantation() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in _read_access_file():
        plantation = str(item.get("plantation") or "").strip().upper()
        estates = item.get("estates")
        if isinstance(estates, list):
            for estate in estates:
                estate_name = str(estate).strip()
                if estate_name and plantation in KNOWN_PLANTATIONS:
                    mapping[estate_name] = plantation
        estate = str(item.get("estate") or "").strip()
        if estate and plantation in KNOWN_PLANTATIONS:
            mapping[estate] = plantation
    return mapping


def build_admin_overview(db: Session) -> dict[str, Any]:
    estate_map = _estate_to_plantation()
    configured_estates = sorted(estate_map.keys())
    db_estates = db.scalars(select(Estate.name).order_by(Estate.name)).all()
    all_estates = list(dict.fromkeys([*configured_estates, *db_estates]))

    estate_counts = {
        name: count
        for name, count in db.execute(
            select(Estate.name, func.count(WorkRecord.id))
            .select_from(Estate)
            .join(WorkRecord, WorkRecord.estate_id == Estate.id, isouter=True)
            .group_by(Estate.id, Estate.name)
        ).all()
    }

    coverage_rows = []
    for plantation in KNOWN_PLANTATIONS:
        estate_names = [estate for estate in all_estates if estate_map.get(estate) == plantation]
        with_data = sum(1 for estate in estate_names if estate_counts.get(estate, 0) > 0)
        coverage_rows.append(
            {
                "plantation": plantation,
                "total_estates": len(estate_names),
                "estates_with_data": with_data,
                "estates_missing_data": max(len(estate_names) - with_data, 0),
            }
        )

    total_records = db.scalar(select(func.count(WorkRecord.id))) or 0
    min_date, max_date = db.execute(select(func.min(WorkRecord.weighing_date), func.max(WorkRecord.weighing_date))).one()
    latest_import = db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(1)).first()
    months_loaded = db.scalar(select(func.count(func.distinct(ImportBatch.label)))) or 0
    estates_with_data = sum(1 for estate in all_estates if estate_counts.get(estate, 0) > 0)

    freshness_cards = [
        {"label": "Configured Estates", "value": len(all_estates)},
        {"label": "Estates With Data", "value": estates_with_data},
        {"label": "Loaded Months", "value": months_loaded},
        {"label": "Total Work Records", "value": int(total_records)},
        {"label": "Data Range", "value": f"{min_date or '-'} → {max_date or '-'}"},
        {
            "label": "Latest Import",
            "value": latest_import.label if latest_import else "No uploads yet",
        },
        {
            "label": "Latest Upload Time",
            "value": latest_import.created_at.strftime("%Y-%m-%d %H:%M") if latest_import else "-",
        },
        {
            "label": "Latest File",
            "value": latest_import.source_filename if latest_import else "-",
        },
    ]

    recent_imports = [
        {
            "id": item.id,
            "label": item.label,
            "source_filename": item.source_filename,
            "created_at": item.created_at,
            "rows_processed": item.rows_processed,
            "status": item.status,
            "month_start": item.month_start,
            "month_end": item.month_end,
        }
        for item in db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(12)).all()
    ]

    return {
        "freshness_cards": freshness_cards,
        "coverage": coverage_rows,
        "recent_imports": recent_imports,
    }


def list_admin_audit_events(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": item.id,
            "event_type": item.event_type,
            "actor_username": item.actor_username,
            "actor_display_name": item.actor_display_name,
            "actor_role": item.actor_role,
            "target_type": item.target_type,
            "target_value": item.target_value,
            "details": parse_event_details(item),
            "created_at": item.created_at,
        }
        for item in events
    ]
