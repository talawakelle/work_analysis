from __future__ import annotations

import argparse

from app.db.session import SessionLocal, create_db_and_tables
from app.services.import_service import import_workbook_path
from app.services.seed_service import seed_job_codes
from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Import estate workbook or CSV into the database.")
    parser.add_argument("path", help="Path to workbook (.xlsx/.xls) or CSV (.csv)")
    parser.add_argument("--label", required=False, help="Optional import label. If omitted, month is detected automatically.")
    args = parser.parse_args()

    create_db_and_tables()
    with SessionLocal() as db:
        seed_job_codes(db, settings.DEFAULT_JOB_CODE_SEED)
        batch = import_workbook_path(db=db, path=args.path, label=args.label)
        print(
            f"Imported {batch.rows_processed} rows from {batch.source_filename} "
            f"({batch.month_start} to {batch.month_end})"
        )


if __name__ == "__main__":
    main()
