from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd


def parse_excel_date(value) -> date | None:
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        if float(value) > 20000:
            # Excel serial date
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()
