from __future__ import annotations

import io
import json
import re
from calendar import monthrange
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee
from app.models.estate import Estate
from app.models.import_batch import ImportBatch
from app.models.job_code import JobCode
from app.models.work_record import WorkRecord
from app.services.date_utils import parse_excel_date


STANDARD_COLUMNS = {
    "Plantation",
    "Crop",
    "Division",
    "Field Code",
    "Hectares_Plucked",
    "Gang",
    "Work_Hour",
    "Work_Type",
    "Employee_No",
    "Employee_Name",
    "Weighing_Date",
    "Kilos",
    "Gender",
    "Work_Code",
}

REQUIRED_UPLOAD_COLUMNS = {
    "Division",
    "Employee_No",
    "Employee_Name",
    "Weighing_Date",
    "Kilos",
    "Work_Code",
}

COLUMN_ALIASES = {
    "Field": "Field Code",
    "Field_Code": "Field Code",
    "Division_Code": "Division",
    "Division Code": "Division",
    "Hectares _Plucked": "Hectares_Plucked",
    "Hectares Plucked": "Hectares_Plucked",
    "Hect Plucked": "Hectares_Plucked",
    "Work _Type": "Work_Type",
    "Work TYpe": "Work_Type",
    "Work Type": "Work_Type",
    "Work Hour": "Work_Hour",
    "Work_-Hour": "Work_Hour",
    "Emp Internal No": "Employee_No",
    "Emp Name": "Employee_Name",
    "Weighing Date": "Weighing_Date",
    "Total Kg": "Kilos",
    "Sundry Code": "Work_Code",
    "Worker_Code": "Work_Code",
    "Worker Code": "Work_Code",
    "Employee_Name.1": "Weighing_Date",
}

MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

SHEET_CODE_TO_ESTATE = {
    "KVPLAN": "Annfield",
    "KVPLBG": "Battalgalla",
    "KVPLEB": "Edinburgh",
    "KVPLFD": "Fordyce",
    "KVPLGL": "Glassugh",
    "KVPLIG": "Ingestre",
    "KVPLIV": "Invery",
    "KVPLNE": "Nuwara Eliya",
    "KVPLOL": "Oliphant",
    "KVPLPD": "Pedro",
    "KVPLRO": "Robgill",
    "KVPLTI": "Tillyrie",
}

FILENAME_ESTATE_ALIASES = {
    "HPLNEUCHATEL": "Neuchatel",
    "HPLFAIRLAWN": "Fairlawn",
    "HPLFAIRLWAN": "Fairlawn",
    "HPLFIRLWAN": "Fairlawn",
    "HPLGOURAVILLA": "Gouravilla",
    "HPLHAL": "Halwatura",
    "HPLHALWATURA": "Halwatura",
}


def _normalized_identifier(value: str | None) -> str:
    return "".join(char.lower() for char in str(value or "") if char.isalnum())


def _infer_estate_from_filename(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None

    identifier = _normalized_identifier(Path(cleaned).stem)
    if not identifier:
        return None

    alias = FILENAME_ESTATE_ALIASES.get(identifier.upper()) or FILENAME_ESTATE_ALIASES.get(identifier)
    if alias:
        return _canonical_estate_name(alias)

    for prefix in ("labourattendance", "attendance", "hpl", "ttel", "kvpl"):
        if identifier.startswith(prefix):
            candidate = identifier[len(prefix):]
            direct = _canonical_estate_name(candidate)
            if direct:
                return direct

    direct = _canonical_estate_name(identifier)
    if direct:
        return direct

    return None


def _infer_period_from_values(values) -> tuple[int | None, int | None]:
    samples = []
    for value in values:
        if pd.isna(value):
            continue
        samples.append(value)
        if len(samples) >= 2000:
            break

    if not samples:
        return None, None

    orientation = None
    first_gt_12 = 0
    second_gt_12 = 0
    token_rows: list[tuple[int, int, int]] = []
    for value in samples:
        if isinstance(value, str):
            match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", value.strip())
            if match:
                first, second, year = map(int, match.groups())
                if year < 100:
                    year += 2000
                token_rows.append((first, second, year))
                if first > 12 and second <= 12:
                    first_gt_12 += 1
                if second > 12 and first <= 12:
                    second_gt_12 += 1

    if first_gt_12 and not second_gt_12:
        orientation = "dayfirst"
    elif second_gt_12 and not first_gt_12:
        orientation = "monthfirst"

    period_counts: dict[tuple[int, int], int] = {}
    for value in samples:
        year = month = None
        if isinstance(value, str):
            match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", value.strip())
            if match:
                first, second, year = map(int, match.groups())
                if year < 100:
                    year += 2000
                if first > 12 and 1 <= second <= 12:
                    month = second
                elif second > 12 and 1 <= first <= 12:
                    month = first
                elif 1 <= first <= 12 and 1 <= second <= 12:
                    month = second if orientation == "dayfirst" else first
                else:
                    month = None
        if year is None or month is None:
            parsed = parse_excel_date(value)
            if parsed is not None:
                year, month = parsed.year, parsed.month
        if year and month:
            period_counts[(year, month)] = period_counts.get((year, month), 0) + 1

    if not period_counts:
        return None, None

    (year, month), _ = max(period_counts.items(), key=lambda item: item[1])
    return year, month


def _infer_period_from_dataframe(df: pd.DataFrame) -> tuple[int | None, int | None]:
    normalized = _canonicalize_columns(df)
    if "Weighing_Date" not in normalized.columns:
        return None, None
    return _infer_period_from_values(normalized["Weighing_Date"].tolist())


def _infer_period_from_workbook(workbook: pd.ExcelFile) -> tuple[int | None, int | None]:
    period_counts: dict[tuple[int, int], int] = {}
    for sheet_name in workbook.sheet_names:
        try:
            sheet_df = pd.read_excel(workbook, sheet_name=sheet_name)
        except Exception:
            continue
        if sheet_df.empty and len(sheet_df.columns) == 0:
            continue
        year, month = _infer_period_from_dataframe(sheet_df)
        if year and month:
            period_counts[(year, month)] = period_counts.get((year, month), 0) + 1
    if not period_counts:
        return None, None
    return max(period_counts.items(), key=lambda item: item[1])[0]


@dataclass(slots=True)
class ValidationSheetResult:
    sheet_name: str
    estate: str | None
    rows: int
    missing_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ImportValidationReport:
    is_valid: bool
    filename: str
    detected_period: str | None
    total_rows: int
    sheet_count: int
    validated_estates: list[str] = field(default_factory=list)
    sheets: list[ValidationSheetResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def validation_message(self) -> str:
        parts: list[str] = []
        if self.detected_period:
            parts.append(f"Period {self.detected_period}")
        parts.append(f"{self.sheet_count} sheet{'s' if self.sheet_count != 1 else ''}")
        parts.append(f"{self.total_rows:,} rows")
        if self.validated_estates:
            parts.append(f"{len(self.validated_estates)} estate{'s' if len(self.validated_estates) != 1 else ''}")
        prefix = "Validated" if self.is_valid else "Validation failed"
        return f"{prefix}: " + " • ".join(parts)


def _to_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_string(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _canonical_column_name(value: object) -> str:
    return COLUMN_ALIASES.get(str(value).strip(), str(value).strip())


def _canonical_column_names(columns) -> set[str]:
    return {_canonical_column_name(column) for column in columns}


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns={column: _canonical_column_name(column) for column in df.columns})
    for required in STANDARD_COLUMNS:
        if required not in renamed.columns:
            renamed[required] = None
    return renamed


@lru_cache(maxsize=1)
def _configured_estates() -> list[str]:
    path = Path(settings.USER_ACCESS_FILE)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    estates: list[str] = []
    if isinstance(payload, dict):
        for group in ("users", "admins"):
            items = payload.get(group)
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if isinstance(item.get("estates"), list):
                        estates.extend(str(value).strip() for value in item["estates"] if str(value).strip())
                    elif item.get("estate"):
                        estates.append(str(item["estate"]).strip())
    return list(dict.fromkeys(estates))


def _canonical_estate_name(name: str | None) -> str | None:
    cleaned = (name or "").strip()
    if not cleaned:
        return None

    normalized = "".join(char.lower() for char in cleaned if char.isalnum())
    if not normalized:
        return cleaned

    for estate_name in _configured_estates():
        estate_normalized = "".join(char.lower() for char in estate_name if char.isalnum())
        if normalized == estate_normalized:
            return estate_name

    return cleaned


def _infer_period(
    filename: str,
    label: str | None = None,
    extra_text: str | None = None,
) -> tuple[int | None, int | None]:
    text = f"{label or ''} {filename} {extra_text or ''}".lower()
    month = None
    for key, month_number in MONTH_NAME_TO_NUMBER.items():
        if re.search(rf"\b{re.escape(key)}\b", text):
            month = month_number
            break

    year_match = re.search(r"(20\d{2})", text)
    year = int(year_match.group(1)) if year_match else None

    compact_date_match = re.search(r"(20\d{2})(0[1-9]|1[0-2])(?:[0-3]\d)?", text)
    if compact_date_match:
        year = year or int(compact_date_match.group(1))
        month = month or int(compact_date_match.group(2))

    return year, month


def _extract_workbook_hint_text(workbook: pd.ExcelFile) -> str:
    chunks: list[str] = []
    for sheet_name in workbook.sheet_names[:10]:
        try:
            sample = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=3)
        except Exception:
            continue
        if sample.empty:
            continue
        values = []
        for value in sample.fillna("").astype(str).to_numpy().ravel().tolist():
            value = value.strip()
            if value and value.lower() != "nan":
                values.append(value)
        if values:
            chunks.append(" ".join(values[:12]))
    return " ".join(chunks)


def _period_to_label(year: int | None, month: int | None) -> str | None:
    if year and month:
        return f"{year:04d}-{month:02d}"
    return None


def _normalize_weighing_date(value, target_year: int | None, target_month: int | None):
    parsed = parse_excel_date(value)
    if parsed is None:
        return None

    if target_year is None and target_month is None:
        return parsed

    year = target_year or parsed.year

    if target_month is None:
        try:
            return parsed.replace(year=year)
        except ValueError:
            return parsed

    max_day = monthrange(year, target_month)[1]

    if parsed.month == target_month:
        day = min(parsed.day, max_day)
    elif parsed.day == target_month and 1 <= parsed.month <= max_day:
        day = parsed.month
    elif 1 <= parsed.day <= max_day:
        day = parsed.day
    elif 1 <= parsed.month <= max_day:
        day = parsed.month
    else:
        day = 1

    try:
        return parsed.replace(year=year, month=target_month, day=day)
    except ValueError:
        return parsed


def _infer_estate_from_sheet_name(sheet_name: str, fallback: str | None = None) -> str | None:
    cleaned = (sheet_name or "").strip()
    if not cleaned:
        return _canonical_estate_name(fallback)

    configured = set(_configured_estates())
    direct = _canonical_estate_name(cleaned)
    if direct and (not configured or direct in configured):
        return direct

    upper = re.sub(r"[^A-Z0-9]", "", cleaned.upper())
    for prefix, estate_name in SHEET_CODE_TO_ESTATE.items():
        if upper.startswith(prefix):
            return _canonical_estate_name(estate_name)

    return _canonical_estate_name(fallback or cleaned)


def _resolve_estate_for_frame(
    sheet_name: str,
    df: pd.DataFrame,
    fallback: str | None = None,
) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    configured = set(_configured_estates())

    filename_candidate = _infer_estate_from_filename(fallback)
    if filename_candidate and (not configured or filename_candidate in configured):
        return filename_candidate, warnings

    candidate = _infer_estate_from_sheet_name(sheet_name, fallback)
    if candidate and (not configured or candidate in configured):
        return candidate, warnings

    canonical_columns = _canonical_column_names(df.columns)
    plantation_column = "Plantation" if "Plantation" in canonical_columns else None
    if plantation_column:
        normalized = _canonicalize_columns(df)
        plantation_values = [
            _canonical_estate_name(value)
            for value in normalized["Plantation"].dropna().astype(str).str.strip().unique().tolist()
            if str(value).strip()
        ]
        plantation_values = [value for value in plantation_values if value]
        configured_values = [value for value in plantation_values if (not configured or value in configured)]
        unique_values = list(dict.fromkeys(configured_values or plantation_values))
        if len(unique_values) == 1:
            return unique_values[0], warnings

    if candidate:
        warnings.append(
            f"Sheet '{sheet_name}' did not match a configured estate exactly. Imported as '{candidate}'."
        )
        return candidate, warnings

    warnings.append(f"Could not confidently resolve an estate for sheet '{sheet_name}'.")
    return None, warnings


def _normalize_sheet(
    df: pd.DataFrame,
    target_year: int | None = None,
    target_month: int | None = None,
) -> pd.DataFrame:
    canonical_columns = _canonical_column_names(df.columns)
    missing = sorted(REQUIRED_UPLOAD_COLUMNS - canonical_columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    normalized = _canonicalize_columns(df).copy()
    normalized["Weighing_Date"] = normalized["Weighing_Date"].apply(
        lambda value: _normalize_weighing_date(value, target_year=target_year, target_month=target_month)
    )
    normalized = normalized.dropna(subset=["Weighing_Date", "Employee_No", "Employee_Name"])
    normalized["Employee_No"] = normalized["Employee_No"].astype(str).str.strip()
    normalized["Employee_Name"] = normalized["Employee_Name"].astype(str).str.strip()
    normalized = normalized[
        normalized["Employee_No"].astype(bool)
        & normalized["Employee_Name"].astype(bool)
    ]
    normalized["Division"] = normalized["Division"].apply(_clean_string)
    normalized["Plantation"] = normalized["Plantation"].apply(_clean_string)
    normalized["Crop"] = normalized["Crop"].apply(_clean_string)
    normalized["Field Code"] = normalized["Field Code"].apply(_clean_string)
    normalized["Gang"] = normalized["Gang"].apply(_clean_string)
    normalized["Gender"] = normalized["Gender"].apply(_clean_string)
    normalized["Work_Type"] = normalized["Work_Type"].apply(_clean_string)
    normalized["Work_Code"] = normalized["Work_Code"].apply(_clean_string)
    normalized["Kilos"] = pd.to_numeric(normalized["Kilos"], errors="coerce").fillna(0)
    normalized["Work_Hour"] = pd.to_numeric(normalized["Work_Hour"], errors="coerce")
    normalized["Hectares_Plucked"] = pd.to_numeric(normalized["Hectares_Plucked"], errors="coerce")
    return normalized


def _read_csv(content: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read CSV file encoding.")


def _estimate_usable_rows(df: pd.DataFrame) -> int:
    canonical_columns = _canonical_column_names(df.columns)
    if not REQUIRED_UPLOAD_COLUMNS.issubset(canonical_columns):
        return 0

    normalized = _canonicalize_columns(df)
    employee_no = normalized["Employee_No"].fillna("").astype(str).str.strip()
    employee_name = normalized["Employee_Name"].fillna("").astype(str).str.strip()
    weighing_date = normalized["Weighing_Date"]

    usable_mask = weighing_date.notna() & employee_no.astype(bool) & employee_name.astype(bool)
    return int(usable_mask.sum())


def _get_or_create_estate(db: Session, name: str, cache: dict[str, Estate]) -> Estate:
    estate = cache.get(name)
    if estate:
        return estate

    estate = db.scalar(select(Estate).where(Estate.name == name))
    if estate:
        cache[name] = estate
        return estate

    estate = Estate(name=name)
    db.add(estate)
    db.flush()
    cache[name] = estate
    return estate


def _get_or_create_employee(
    db: Session,
    estate_id: int,
    employee_no: str,
    employee_name: str,
    gender: str | None,
    gang: str | None,
    cache: dict[tuple[int, str], Employee],
) -> Employee:
    cache_key = (estate_id, employee_no)
    employee = cache.get(cache_key)
    if employee:
        employee.employee_name = employee_name or employee.employee_name
        employee.gender = gender or employee.gender
        employee.gang = gang or employee.gang
        return employee

    employee = db.scalar(
        select(Employee).where(Employee.estate_id == estate_id, Employee.employee_no == employee_no)
    )
    if employee:
        employee.employee_name = employee_name or employee.employee_name
        employee.gender = gender or employee.gender
        employee.gang = gang or employee.gang
        cache[cache_key] = employee
        db.flush()
        return employee

    employee = Employee(
        estate_id=estate_id,
        employee_no=employee_no,
        employee_name=employee_name,
        gender=gender,
        gang=gang,
    )
    db.add(employee)
    db.flush()
    cache[cache_key] = employee
    return employee


def _job_name_lookup(db: Session) -> dict[str, str]:
    seed_path = Path(__file__).resolve().parents[2] / "data" / "job_codes_seed.csv"
    mapping: dict[str, str] = {}
    if seed_path.exists():
        seed_df = pd.read_csv(seed_path)
        for _, row in seed_df.iterrows():
            code = _clean_string(row.get("code"))
            long_name = _clean_string(row.get("long_name"))
            if code and long_name:
                mapping[code] = long_name
    for item in db.scalars(select(JobCode)).all():
        if item.code and item.long_name:
            mapping[item.code] = item.long_name
    mapping.setdefault("Plucker", "Plucking")
    return mapping


def _append_records_for_dataframe(
    db: Session,
    import_batch: ImportBatch,
    normalized: pd.DataFrame,
    job_name_map: dict[str, str],
    estate_cache: dict[str, Estate],
    employee_cache: dict[tuple[int, str], Employee],
    estate_name_override: str | None = None,
) -> tuple[int, list]:
    rows_processed = 0
    all_dates = []

    for row_index, row in normalized.iterrows():
        estate_name = _canonical_estate_name(estate_name_override or _clean_string(row["Plantation"]))
        if not estate_name:
            continue

        plantation_name = _clean_string(row["Plantation"])
        estate = _get_or_create_estate(db, estate_name, estate_cache)
        employee = _get_or_create_employee(
            db=db,
            estate_id=estate.id,
            employee_no=row["Employee_No"],
            employee_name=row["Employee_Name"],
            gender=_clean_string(row["Gender"]),
            gang=_clean_string(row["Gang"]),
            cache=employee_cache,
        )

        work_code = _clean_string(row["Work_Code"])
        work_name = job_name_map.get(work_code or "", None)
        if work_code == "Plucker" and not work_name:
            work_name = "Plucking"

        record = WorkRecord(
            import_batch_id=import_batch.id,
            estate_id=estate.id,
            employee_id=employee.id,
            division=_clean_string(row["Division"]),
            plantation=plantation_name,
            crop=_clean_string(row["Crop"]),
            field_code=_clean_string(row["Field Code"]),
            hectares_plucked=_to_float(row["Hectares_Plucked"]),
            gang=_clean_string(row["Gang"]),
            work_hour=_to_float(row["Work_Hour"]),
            employment_type=_clean_string(row["Work_Type"]),
            work_code=work_code,
            work_name=work_name,
            weighing_date=row["Weighing_Date"],
            kilos=float(row["Kilos"] or 0),
            gender=_clean_string(row["Gender"]),
            source_row=int(row_index) + 2,
        )
        db.add(record)
        rows_processed += 1
        all_dates.append(row["Weighing_Date"])

    db.flush()
    return rows_processed, all_dates


def _resolve_label(label: str | None, filename: str, dates: list) -> str:
    cleaned = (label or "").strip()
    if cleaned:
        return cleaned
    valid_dates = [value for value in dates if value is not None]
    if valid_dates:
        latest = max(valid_dates)
        earliest = min(valid_dates)
        if earliest.strftime("%Y-%m") == latest.strftime("%Y-%m"):
            return latest.strftime("%Y-%m")
    inferred_year, inferred_month = _infer_period(filename, label)
    if inferred_year and inferred_month:
        return f"{inferred_year:04d}-{inferred_month:02d}"
    stem = Path(filename).stem.strip()
    return stem or "upload"


def _finalize_batch(
    db: Session,
    import_batch: ImportBatch,
    rows_processed: int,
    all_dates: list,
    filename: str,
    label: str | None,
) -> ImportBatch:
    import_batch.label = _resolve_label(label, filename, all_dates)
    import_batch.month_start = min(all_dates) if all_dates else None
    import_batch.month_end = max(all_dates) if all_dates else None
    import_batch.rows_processed = rows_processed
    import_batch.status = "completed"
    db.commit()
    db.refresh(import_batch)
    return import_batch


def validate_csv_dataframe(
    dataframe: pd.DataFrame,
    filename: str,
    label: str | None = None,
) -> ImportValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    sheets: list[ValidationSheetResult] = []

    if dataframe.empty and len(dataframe.columns) == 0:
        return ImportValidationReport(
            is_valid=False,
            filename=filename,
            detected_period=_period_to_label(*_infer_period(filename, label)),
            total_rows=0,
            sheet_count=0,
            errors=["The uploaded CSV file is empty."],
        )

    canonical_columns = _canonical_column_names(dataframe.columns)
    missing = sorted(REQUIRED_UPLOAD_COLUMNS - canonical_columns)
    if missing:
        errors.append(f"CSV is missing required columns: {', '.join(missing)}")

    estate_name, estate_warnings = _resolve_estate_for_frame(Path(filename).stem, dataframe, Path(filename).stem)
    warnings.extend(estate_warnings)
    target_year, target_month = _infer_period(filename, label)
    if not (target_year and target_month):
        target_year, target_month = _infer_period_from_dataframe(dataframe)

    usable_rows = _estimate_usable_rows(dataframe)
    if usable_rows == 0:
        warnings.append("No usable rows were found after checking employee and date fields.")

    sheets.append(
        ValidationSheetResult(
            sheet_name="CSV",
            estate=estate_name,
            rows=usable_rows,
            missing_columns=missing,
            warnings=estate_warnings.copy(),
        )
    )

    period_year, period_month = _infer_period(filename, label)
    if not (period_year and period_month):
        period_year, period_month = _infer_period_from_dataframe(dataframe)
    period = _period_to_label(period_year, period_month)
    validated_estates = [estate_name] if estate_name else []
    return ImportValidationReport(
        is_valid=not errors and usable_rows > 0,
        filename=filename,
        detected_period=period,
        total_rows=usable_rows,
        sheet_count=1,
        validated_estates=validated_estates,
        sheets=sheets,
        warnings=list(dict.fromkeys(warnings)),
        errors=errors,
    )


def validate_workbook_excel_file(
    workbook: pd.ExcelFile,
    filename: str,
    label: str | None = None,
) -> ImportValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    sheets: list[ValidationSheetResult] = []
    validated_estates: list[str] = []
    total_rows = 0
    non_empty_sheet_count = 0

    extra_text = " ".join(workbook.sheet_names) + " " + _extract_workbook_hint_text(workbook)
    detected_year, detected_month = _infer_period(filename, label, extra_text)
    if not (detected_year and detected_month):
        detected_year, detected_month = _infer_period_from_workbook(workbook)
    detected_period = _period_to_label(detected_year, detected_month)

    for sheet_name in workbook.sheet_names:
        sheet_df = pd.read_excel(workbook, sheet_name=sheet_name)
        if sheet_df.empty and len(sheet_df.columns) == 0:
            warnings.append(f"Skipped empty sheet '{sheet_name}'.")
            continue

        non_empty_sheet_count += 1
        canonical_columns = _canonical_column_names(sheet_df.columns)
        missing = sorted(REQUIRED_UPLOAD_COLUMNS - canonical_columns)

        estate_name, estate_warnings = _resolve_estate_for_frame(sheet_name.strip(), sheet_df, Path(filename).stem.strip())
        warnings.extend(estate_warnings)

        rows = _estimate_usable_rows(sheet_df)
        if rows == 0:
            warnings.append(f"Sheet '{sheet_name}' has no usable rows after checking employee and date fields.")

        if missing:
            errors.append(f"Sheet '{sheet_name}' is missing required columns: {', '.join(missing)}")

        if estate_name:
            validated_estates.append(estate_name)

        total_rows += rows
        sheets.append(
            ValidationSheetResult(
                sheet_name=sheet_name,
                estate=estate_name,
                rows=rows,
                missing_columns=missing,
                warnings=estate_warnings.copy(),
            )
        )

    if non_empty_sheet_count == 0:
        errors.append("The workbook does not contain any data sheets.")

    if total_rows == 0:
        errors.append("The workbook does not contain any usable data rows.")

    if not detected_period:
        warnings.append("Could not detect the workbook month from the file name or header text. The upload can still continue.")

    return ImportValidationReport(
        is_valid=not errors,
        filename=filename,
        detected_period=detected_period,
        total_rows=total_rows,
        sheet_count=non_empty_sheet_count,
        validated_estates=list(dict.fromkeys([estate for estate in validated_estates if estate])),
        sheets=sheets,
        warnings=list(dict.fromkeys(warnings)),
        errors=list(dict.fromkeys(errors)),
    )


def validate_workbook_bytes(content: bytes, filename: str, label: str | None = None) -> ImportValidationReport:
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        dataframe = _read_csv(content)
        return validate_csv_dataframe(dataframe, filename=filename, label=label)

    workbook = pd.ExcelFile(io.BytesIO(content))
    return validate_workbook_excel_file(workbook=workbook, filename=filename, label=label)


def import_workbook_bytes(db: Session, content: bytes, filename: str, label: str | None = None) -> ImportBatch:
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        dataframe = _read_csv(content)
        return import_csv_dataframe(db, dataframe=dataframe, filename=filename, label=label)

    workbook = pd.ExcelFile(io.BytesIO(content))
    return import_workbook_excel_file(db, workbook=workbook, filename=filename, label=label)


def import_workbook_path(db: Session, path: str | Path, label: str | None = None) -> ImportBatch:
    file_path = Path(path)
    if file_path.suffix.lower() == ".csv":
        dataframe = pd.read_csv(file_path)
        return import_csv_dataframe(db, dataframe=dataframe, filename=file_path.name, label=label)

    workbook = pd.ExcelFile(path)
    return import_workbook_excel_file(db, workbook=workbook, filename=file_path.name, label=label)


def import_csv_dataframe(db: Session, dataframe: pd.DataFrame, filename: str, label: str | None = None) -> ImportBatch:
    job_name_map = _job_name_lookup(db)
    target_year, target_month = _infer_period(filename, label)
    if not (target_year and target_month):
        target_year, target_month = _infer_period_from_dataframe(dataframe)
    normalized = _normalize_sheet(dataframe, target_year=target_year, target_month=target_month)
    import_batch = ImportBatch(
        label=(label or Path(filename).stem or "upload").strip(),
        source_filename=filename,
        status="processing",
        rows_processed=0,
    )
    db.add(import_batch)
    db.flush()

    estate_cache: dict[str, Estate] = {}
    employee_cache: dict[tuple[int, str], Employee] = {}

    estate_name, _ = _resolve_estate_for_frame(Path(filename).stem, dataframe, Path(filename).stem)

    rows_processed, all_dates = _append_records_for_dataframe(
        db=db,
        import_batch=import_batch,
        normalized=normalized,
        job_name_map=job_name_map,
        estate_cache=estate_cache,
        employee_cache=employee_cache,
        estate_name_override=estate_name,
    )
    return _finalize_batch(db, import_batch, rows_processed, all_dates, filename, label)


def import_workbook_excel_file(db: Session, workbook: pd.ExcelFile, filename: str, label: str | None = None) -> ImportBatch:
    job_name_map = _job_name_lookup(db)
    extra_text = " ".join(workbook.sheet_names) + " " + _extract_workbook_hint_text(workbook)
    target_year, target_month = _infer_period(filename, label, extra_text)
    if not (target_year and target_month):
        target_year, target_month = _infer_period_from_workbook(workbook)
    all_dates = []
    rows_processed = 0
    estate_cache: dict[str, Estate] = {}
    employee_cache: dict[tuple[int, str], Employee] = {}
    import_batch = ImportBatch(
        label=(label or Path(filename).stem or "upload").strip(),
        source_filename=filename,
        status="processing",
        rows_processed=0,
    )
    db.add(import_batch)
    db.flush()

    for sheet_name in workbook.sheet_names:
        sheet_df = pd.read_excel(workbook, sheet_name=sheet_name)
        if sheet_df.empty and len(sheet_df.columns) == 0:
            continue

        normalized = _normalize_sheet(sheet_df, target_year=target_year, target_month=target_month)
        estate_name, _ = _resolve_estate_for_frame(sheet_name.strip(), sheet_df, Path(filename).stem.strip())
        batch_rows, batch_dates = _append_records_for_dataframe(
            db=db,
            import_batch=import_batch,
            normalized=normalized,
            job_name_map=job_name_map,
            estate_cache=estate_cache,
            employee_cache=employee_cache,
            estate_name_override=estate_name,
        )
        rows_processed += batch_rows
        all_dates.extend(batch_dates)

    return _finalize_batch(db, import_batch, rows_processed, all_dates, filename, label)
