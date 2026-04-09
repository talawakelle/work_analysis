from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from app.db.session import Base


TABLES = [
    "estates",
    "employees",
    "job_codes",
    "import_batches",
    "work_records",
    "audit_events",
]


def migrate(sqlite_url: str, postgres_url: str, truncate_first: bool = False) -> None:
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)

    Base.metadata.create_all(bind=postgres_engine)

    with postgres_engine.begin() as connection:
        if truncate_first:
            for table_name in reversed(TABLES):
                connection.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))

    for table_name in TABLES:
        frame = pd.read_sql_query(f'SELECT * FROM "{table_name}"', sqlite_engine)
        if frame.empty:
            print(f"{table_name}: 0 rows")
            continue
        frame.to_sql(table_name, postgres_engine, if_exists="append", index=False, method="multi", chunksize=1000)
        print(f"{table_name}: {len(frame):,} rows migrated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy Estate Workforce data from SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-url", default="sqlite:///./estate_workforce.db")
    parser.add_argument("--postgres-url", required=True)
    parser.add_argument("--truncate-first", action="store_true")
    args = parser.parse_args()

    migrate(args.sqlite_url, args.postgres_url, truncate_first=args.truncate_first)
