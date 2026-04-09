from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_code import JobCode


def seed_job_codes(db: Session, seed_path: str | Path) -> None:
    path = Path(seed_path)
    if not path.exists():
        return

    with path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = (row.get("code") or "").strip()
            long_name = (row.get("long_name") or "").strip()
            if not code:
                continue

            existing = db.scalar(select(JobCode).where(JobCode.code == code))
            if existing:
                if long_name and not existing.long_name:
                    existing.long_name = long_name
                continue

            db.add(JobCode(code=code, long_name=long_name or None, source="seed"))
    db.commit()
