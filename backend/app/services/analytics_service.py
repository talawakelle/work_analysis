from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.estate import Estate
from app.models.import_batch import ImportBatch
from app.models.job_code import JobCode
from app.models.work_record import WorkRecord


def _row_color(employment_type: str | None) -> str:
    normalized = (employment_type or "").strip().lower()
    if normalized == "registered":
        return "light-green"
    if normalized == "cash":
        return "red"
    if normalized == "bulk":
        return "amber"
    return "neutral"


@lru_cache(maxsize=1)
def _seed_job_name_map() -> dict[str, str]:
    seed_path = Path(__file__).resolve().parents[2] / "data" / "job_codes_seed.csv"
    if not seed_path.exists():
        return {}
    mapping: dict[str, str] = {}
    with seed_path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = (row.get("code") or "").strip()
            long_name = (row.get("long_name") or "").strip()
            if code and long_name:
                mapping[code] = long_name
    return mapping


def _job_name_map(db: Session) -> dict[str, str]:
    mapping = dict(_seed_job_name_map())
    for item in db.scalars(select(JobCode)).all():
        code = (item.code or "").strip()
        long_name = (item.long_name or "").strip()
        if code and long_name:
            mapping[code] = long_name
    return mapping


def _resolve_work_name(code: str | None, name: str | None, lookup: dict[str, str]) -> str | None:
    cleaned_code = (code or "").strip()
    cleaned_name = (name or "").strip()

    if cleaned_code.lower() == "plucker":
        return "Plucking"

    if cleaned_name:
        normalized_code = re.sub(r"\W+", "", cleaned_code).lower()
        normalized_name = re.sub(r"\W+", "", cleaned_name).lower()
        if normalized_code and normalized_name == normalized_code:
            cleaned_name = ""
        elif normalized_code and normalized_name.startswith(normalized_code):
            trimmed = cleaned_name[len(cleaned_code):].lstrip(" -–—:")
            cleaned_name = trimmed or cleaned_name

    if cleaned_name:
        return cleaned_name

    if cleaned_code:
        return lookup.get(cleaned_code)

    return None


def _employee_work_summary(records: list[WorkRecord], lookup: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    day_sets: dict[tuple[str, str], set[date]] = defaultdict(set)

    for record in records:
        code = (record.work_code or "").strip() or "Unknown"
        resolved_name = _resolve_work_name(record.work_code, record.work_name, lookup)
        name = (resolved_name or "").strip()

        key = (code, name)
        if key not in grouped:
            grouped[key] = {
                "work_code": code,
                "work_name": name,
                "days": 0,
                "kilos": 0.0,
            }

        grouped[key]["kilos"] += float(record.kilos or 0)
        day_sets[key].add(record.weighing_date)

    for key, dates in day_sets.items():
        grouped[key]["days"] = len(dates)

    items = list(grouped.values())
    for item in items:
        item["kilos"] = round(item["kilos"], 2)
    items.sort(key=lambda item: (-item["days"], -item["kilos"], item["work_code"]))
    return items


def _is_plucking(record: WorkRecord, lookup: dict[str, str]) -> bool:
    code = (record.work_code or "").strip().lower()
    name = (_resolve_work_name(record.work_code, record.work_name, lookup) or "").strip().lower()
    return code in {"plk", "opl", "pkg", "plucker"} or "pluck" in name


def _division_plucking_kilo_share(
    db: Session,
    employee: Employee,
    records: list[WorkRecord],
    lookup: dict[str, str],
    start_date: date,
    end_date: date,
    selected_division: str | None = None,
) -> dict[str, Any]:
    division_name = selected_division
    if not division_name or division_name.upper() == "ALL":
        division_counter = Counter(record.division for record in records if record.division)
        division_name = division_counter.most_common(1)[0][0] if division_counter else None

    employee_plucking_kilos = round(
        sum(float(record.kilos or 0) for record in records if _is_plucking(record, lookup)),
        2,
    )

    if not division_name:
        return {
            "division": None,
            "division_plucking_kilos": employee_plucking_kilos,
            "employee_plucking_kilos": employee_plucking_kilos,
            "other_division_plucking_kilos": 0.0,
        }

    division_records = db.scalars(
        select(WorkRecord).where(
            WorkRecord.estate_id == employee.estate_id,
            WorkRecord.division == division_name,
            WorkRecord.weighing_date.between(start_date, end_date),
        )
    ).all()
    division_plucking_kilos = round(
        sum(float(record.kilos or 0) for record in division_records if _is_plucking(record, lookup)),
        2,
    )
    other_division_plucking_kilos = round(max(division_plucking_kilos - employee_plucking_kilos, 0.0), 2)
    return {
        "division": division_name,
        "division_plucking_kilos": division_plucking_kilos,
        "employee_plucking_kilos": employee_plucking_kilos,
        "other_division_plucking_kilos": other_division_plucking_kilos,
    }


def _weekly_plucking_summary(
    records: list[WorkRecord],
    start_date: date,
    end_date: date,
    lookup: dict[str, str],
) -> list[dict[str, Any]]:
    weekly: dict[int, dict[str, Any]] = {}

    for record in records:
        if not _is_plucking(record, lookup):
            continue
        if not (start_date <= record.weighing_date <= end_date):
            continue

        week_index = ((record.weighing_date.day - 1) // 7) + 1
        item = weekly.setdefault(
            week_index,
            {
                "week_label": f"Week {week_index}",
                "week_number": week_index,
                "weekday_dates": set(),
                "sunday_dates": set(),
                "weekday_total_kilos": 0.0,
                "weekend_total_kilos": 0.0,
            },
        )

        kilos = float(record.kilos or 0)
        if record.weighing_date.weekday() == 6:
            item["sunday_dates"].add(record.weighing_date)
            item["weekend_total_kilos"] += kilos
        else:
            item["weekday_dates"].add(record.weighing_date)
            item["weekday_total_kilos"] += kilos

    items = []
    for week_index in sorted(weekly):
        item = weekly[week_index]
        weekday_days = len(item["weekday_dates"])
        sunday_days = len(item["sunday_dates"])
        weekday_total = round(item["weekday_total_kilos"], 2)
        sunday_total = round(item["weekend_total_kilos"], 2)

        items.append(
            {
                "week_label": item["week_label"],
                "week_number": item["week_number"],
                "weekday_total_kilos": weekday_total,
                "weekend_total_kilos": sunday_total,
                "weekday_days": weekday_days,
                "weekend_days": sunday_days,
                "weekday_avg_kilos": round(weekday_total / weekday_days, 2) if weekday_days else 0.0,
                "weekend_avg_kilos": round(sunday_total / sunday_days, 2) if sunday_days else 0.0,
            }
        )

    return items


def _apply_estate_scope(query, estate: str | None, accessible_estates: list[str] | None):
    if accessible_estates is not None:
        if not accessible_estates:
            return query.where(False)
        query = query.where(Estate.name.in_(accessible_estates))
    if estate:
        query = query.where(Estate.name == estate)
    return query


def get_filters(db: Session, access) -> dict[str, Any]:
    if access.access_mode == "restricted":
        estates: list[str] = []
        min_date = None
        max_date = None
    else:
        estates = access.accessible_estates if access.accessible_estates else db.scalars(select(Estate.name).order_by(Estate.name)).all()

        date_query = select(func.min(WorkRecord.weighing_date), func.max(WorkRecord.weighing_date)).join(
            Estate, Estate.id == WorkRecord.estate_id
        )
        if estates:
            date_query = date_query.where(Estate.name.in_(estates))
        min_date, max_date = db.execute(date_query).one()

        if not estates:
            min_date, max_date = db.execute(
                select(func.min(WorkRecord.weighing_date), func.max(WorkRecord.weighing_date))
            ).one()

    import_labels = db.scalars(select(ImportBatch.label).order_by(ImportBatch.created_at.desc())).all() if access.can_upload or access.role == "admin" else []

    return {
        "estates": estates,
        "min_date": min_date,
        "max_date": max_date,
        "import_labels": import_labels,
        "resolved_user": access.username,
        "display_name": access.display_name,
        "resolved_estate": access.resolved_estate,
        "accessible_estates": estates,
        "accessible_plantations": access.accessible_plantations,
        "selected_plantation": access.selected_plantation,
        "role": access.role,
        "can_switch_estate": access.can_switch_estate,
        "can_upload": access.can_upload or access.role == "admin",
        "access_mode": access.access_mode,
        "access_message": access.access_message,
    }


def dashboard_summary(
    db: Session,
    estate: str | None,
    accessible_estates: list[str] | None,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    query = (
        select(WorkRecord)
        .join(Estate, Estate.id == WorkRecord.estate_id)
        .where(WorkRecord.weighing_date.between(start_date, end_date))
    )
    query = _apply_estate_scope(query, estate, accessible_estates)
    records = db.scalars(query).all()

    unique_workers = {record.employee_id for record in records}
    registered_workers = {record.employee_id for record in records if (record.employment_type or "").lower() == "registered"}
    cash_workers = {record.employee_id for record in records if (record.employment_type or "").lower() == "cash"}
    divisions = {record.division for record in records if record.division}
    worked_days = {record.weighing_date for record in records}

    return {
        "summary": [
            {"label": "Workers", "value": len(unique_workers)},
            {"label": "Total Kilos", "value": round(sum(float(record.kilos or 0) for record in records), 2)},
            {"label": "Divisions", "value": len(divisions)},
            {"label": "Worked Days", "value": len(worked_days)},
            {"label": "Registered", "value": len(registered_workers)},
            {"label": "Cash", "value": len(cash_workers)},
        ],
        "work_code_summary": [],
    }


def work_analysis(
    db: Session,
    estate: str | None,
    accessible_estates: list[str] | None,
    start_date: date,
    end_date: date,
    direction: str,
    metric: str,
    value: int,
) -> dict[str, Any]:
    record_query = (
        select(WorkRecord)
        .join(Estate, Estate.id == WorkRecord.estate_id)
        .join(Employee, Employee.id == WorkRecord.employee_id)
        .where(WorkRecord.weighing_date.between(start_date, end_date))
        .order_by(Employee.employee_name, WorkRecord.weighing_date)
    )
    record_query = _apply_estate_scope(record_query, estate, accessible_estates)
    records = db.scalars(record_query).all()
    lookup = _job_name_map(db)
    weekly_plucking = _weekly_plucking_summary(records, start_date, end_date, lookup)

    grouped: dict[int, dict[str, Any]] = {}
    for record in records:
        if record.employee_id not in grouped:
            grouped[record.employee_id] = {
                "employee_id": record.employee_id,
                "employee_no": record.employee.employee_no,
                "employee_name": record.employee.employee_name,
                "division": record.division,
                "estate": record.estate.name,
                "employment_type": record.employment_type,
                "total_kilos": 0.0,
                "dates": set(),
            }
        grouped[record.employee_id]["total_kilos"] += float(record.kilos or 0)
        grouped[record.employee_id]["dates"].add(record.weighing_date)

    rows = []
    for payload in grouped.values():
        total_days = len(payload["dates"])
        total_kilos = round(payload["total_kilos"], 2)
        avg = round(total_kilos / total_days, 2) if total_days else 0.0
        row = {
            "employee_id": payload["employee_id"],
            "employee_no": payload["employee_no"],
            "employee_name": payload["employee_name"],
            "division": payload["division"],
            "estate": payload["estate"],
            "employment_type": payload["employment_type"],
            "total_kilos": total_kilos,
            "total_days": total_days,
            "avg_kilos_per_day": avg,
            "row_color": _row_color(payload["employment_type"]),
        }

        if metric == "workers":
            rows.append(row)
        elif metric == "kilos":
            if direction == "top" and total_kilos >= value:
                rows.append(row)
            elif direction == "bottom" and total_kilos <= value:
                rows.append(row)
        elif metric == "days":
            if direction == "top" and total_days >= value:
                rows.append(row)
            elif direction == "bottom" and total_days <= value:
                rows.append(row)

    reverse = direction == "top"
    if metric == "workers":
        rows.sort(key=lambda item: (item["total_kilos"], item["total_days"], item["employee_name"]), reverse=reverse)
        rows = rows[:value]
    else:
        sort_key = "total_kilos" if metric == "kilos" else "total_days"
        rows.sort(key=lambda item: (item[sort_key], item["employee_name"]), reverse=reverse)

    return {
        "summary": [
            {"label": "Rows", "value": len(rows)},
            {"label": "Employees", "value": len(grouped)},
            {"label": "Plucking Weeks", "value": len(weekly_plucking)},
        ],
        "work_code_summary": [],
        "weekly_plucking": weekly_plucking,
        "rows": rows,
    }


def search_employees(
    db: Session,
    estate: str | None,
    accessible_estates: list[str] | None,
    q: str,
) -> list[dict[str, Any]]:
    query = (
        select(Employee, Estate.name, WorkRecord.division)
        .join(Estate, Estate.id == Employee.estate_id)
        .join(WorkRecord, WorkRecord.employee_id == Employee.id, isouter=True)
        .where(or_(Employee.employee_no.ilike(f"%{q}%"), Employee.employee_name.ilike(f"%{q}%")))
    )
    query = _apply_estate_scope(query, estate, accessible_estates)
    query = query.group_by(Employee.id, Estate.name, WorkRecord.division).order_by(Employee.employee_name).limit(20)

    items = []
    seen = set()
    for employee, estate_name, division in db.execute(query).all():
        if employee.id in seen:
            continue
        seen.add(employee.id)
        items.append(
            {
                "employee_id": employee.id,
                "employee_no": employee.employee_no,
                "employee_name": employee.employee_name,
                "estate": estate_name,
                "division": division,
            }
        )
    return items


def _month_bounds(ym: str) -> tuple[date, date]:
    year, month = map(int, ym.split("-"))
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = next_month - timedelta(days=1)
    return start, end


def employee_detail(
    db: Session,
    employee_id: int,
    accessible_estates: list[str] | None,
    start_date: date | None = None,
    end_date: date | None = None,
    ym: str | None = None,
    division: str | None = None,
) -> dict[str, Any]:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise ValueError("Employee not found.")

    if accessible_estates is not None and employee.estate.name not in accessible_estates:
        raise ValueError("Employee not found for the signed-in user's estate.")

    if ym:
        start_date, end_date = _month_bounds(ym)
    elif not start_date or not end_date:
        latest = db.scalar(
            select(func.max(WorkRecord.weighing_date)).where(WorkRecord.employee_id == employee_id)
        )
        if not latest:
            raise ValueError("Employee has no records.")
        start_date, end_date = _month_bounds(latest.strftime("%Y-%m"))
        ym = latest.strftime("%Y-%m")
    else:
        ym = start_date.strftime("%Y-%m")

    query = select(WorkRecord).where(
        WorkRecord.employee_id == employee_id,
        WorkRecord.weighing_date.between(start_date, end_date),
    )
    if division and division.upper() != "ALL":
        query = query.where(WorkRecord.division == division)
    records = db.scalars(query.order_by(WorkRecord.weighing_date.asc(), WorkRecord.id.asc())).all()
    lookup = _job_name_map(db)

    present_dates = {record.weighing_date for record in records}
    total_days = len(present_dates)

    company_days_query = select(func.count(func.distinct(WorkRecord.weighing_date))).where(
        WorkRecord.estate_id == employee.estate_id,
        WorkRecord.weighing_date.between(start_date, end_date),
    )
    if division and division.upper() != "ALL":
        company_days_query = company_days_query.where(WorkRecord.division == division)

    company_total_days = db.scalar(company_days_query) or 0
    absent_days = max(company_total_days - total_days, 0)

    daily_grouped: dict[date, list[WorkRecord]] = defaultdict(list)
    for record in records:
        daily_grouped[record.weighing_date].append(record)

    calendar = []
    current = start_date
    while current <= end_date:
        day_records = daily_grouped.get(current, [])
        if day_records:
            total_kilos = round(sum(float(record.kilos or 0) for record in day_records), 2)
            total_hours = round(sum(float(record.work_hour or 0) for record in day_records), 2) or None
            main_record = max(day_records, key=lambda record: float(record.kilos or 0))
            employment_type = Counter((record.employment_type or "Unknown") for record in day_records).most_common(1)[0][0]
            codes = sorted({(record.work_code or "").strip() for record in day_records if (record.work_code or "").strip()})
            names = sorted(
                {
                    _resolve_work_name(record.work_code, record.work_name, lookup)
                    for record in day_records
                    if _resolve_work_name(record.work_code, record.work_name, lookup)
                }
            )
            color = "neutral"
            if total_kilos > 0 or total_hours:
                color = "red" if any(float(record.work_hour or 0) == 0.5 for record in day_records) else "green"
            calendar.append(
                {
                    "date": current,
                    "kilos": total_kilos,
                    "worked": total_kilos > 0 or bool(total_hours),
                    "work_hour": total_hours,
                    "work_code": ", ".join(codes) or None,
                    "work_name": ", ".join(name for name in names if name) or None,
                    "employment_type": employment_type,
                    "division": main_record.division,
                    "field_code": main_record.field_code,









                    
                    "gang": main_record.gang or employee.gang,
                    "plantation": main_record.plantation,
                    "crop": main_record.crop,
                    "hectare": round(float(main_record.hectares_plucked), 2) if main_record.hectares_plucked is not None else None,
                    "gender": main_record.gender or employee.gender,
                    "color": color,
                }
            )
        else:
            calendar.append(
                {
                    "date": current,
                    "kilos": 0,
                    "worked": False,
                    "work_hour": None,
                    "work_code": None,
                    "work_name": None,
                    "employment_type": None,
                    "division": None,
                    "field_code": None,
                    "gang": None,
                    "plantation": None,
                    "crop": None,
                    "hectare": None,
                    "gender": None,
                    "color": "neutral",
                }
            )
        current += timedelta(days=1)

    division_counter = Counter(record.division for record in records if record.division)
    gang_counter = Counter((record.gang or employee.gang) for record in records if (record.gang or employee.gang))
    gender_counter = Counter((record.gender or employee.gender) for record in records if (record.gender or employee.gender))
    total_kilos = round(sum(float(record.kilos or 0) for record in records), 2)
    total_hours = round(sum(float(record.work_hour or 0) for record in records), 2)

    records_payload = [
        {
            "date": record.weighing_date,
            "division": record.division,
            "plantation": record.plantation,
            "crop": record.crop,
            "field_code": record.field_code,
            "gang": record.gang,
            "kilos": round(float(record.kilos or 0), 2),
            "work_hour": float(record.work_hour) if record.work_hour is not None else None,
            "hectare": round(float(record.hectares_plucked), 2) if record.hectares_plucked is not None else None,
            "work_code": record.work_code,
            "work_name": _resolve_work_name(record.work_code, record.work_name, lookup),
            "employment_type": record.employment_type,
            "gender": record.gender or employee.gender,
        }
        for record in reversed(records)
    ]

    work_summary = _employee_work_summary(records, lookup)
    plucking_kilo_share = _division_plucking_kilo_share(
        db=db,
        employee=employee,
        records=records,
        lookup=lookup,
        start_date=start_date,
        end_date=end_date,
        selected_division=division,
    )

    return {
        "employee": {
            "employee_id": employee.id,
            "employee_no": employee.employee_no,
            "employee_name": employee.employee_name,
            "estate": employee.estate.name,
            "gender": (gender_counter.most_common(1)[0][0] if gender_counter else employee.gender),
            "primary_division": division_counter.most_common(1)[0][0] if division_counter else None,
            "primary_gang": gang_counter.most_common(1)[0][0] if gang_counter else employee.gang,
        },
        "period": ym,
        "summary": [
            {"label": "Worked Days", "value": total_days},
            {"label": "Absent Days", "value": absent_days},
            {"label": "Total Kilos", "value": total_kilos},
            {"label": "Work Hours", "value": total_hours},
        ],
        "work_code_summary": [],
        "work_summary": work_summary,
        "attendance": {
            "present_days": total_days,
            "absent_days": absent_days,
            "total_days": company_total_days,
        },
        "plucking_kilo_share": plucking_kilo_share,
        "calendar": calendar,
        "records": records_payload,
    }
