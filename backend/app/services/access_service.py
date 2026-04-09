from __future__ import annotations

import csv
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.estate import Estate


USERNAME_HEADERS = (
    "x-auth-user",
    "x-forwarded-user",
    "x-remote-user",
    "remote-user",
    "x-user",
    "x-username",
    "x-auth-email",
    "x-email",
)
USERNAME_QUERY_KEYS = ("username", "user", "email", "login")
ESTATE_QUERY_KEYS = ("estate", "estate_name")
PLANTATION_QUERY_KEYS = ("plantation", "company", "group")
KNOWN_PLANTATIONS = ("TTEL", "KVPL", "HPL")


@dataclass(slots=True)
class AccessContext:
    username: str | None
    display_name: str | None
    role: str
    accessible_estates: list[str]
    resolved_estate: str | None
    can_upload: bool
    can_switch_estate: bool
    access_mode: str
    access_message: str | None
    source: str
    accessible_plantations: list[str]
    selected_plantation: str | None


def _normalize_token(value: str | None) -> str:
    if not value:
        return ""
    return "".join(char.lower() for char in value if char.isalnum())


def _first_value(request: Request, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = request.query_params.get(key)
        if value and value.strip():
            return value.strip()
    for key in keys:
        value = request.headers.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _extract_username(request: Request) -> tuple[str | None, str]:
    for key in USERNAME_QUERY_KEYS:
        value = request.query_params.get(key)
        if value and value.strip():
            return value.strip(), f"query:{key}"
    for key in USERNAME_HEADERS:
        value = request.headers.get(key)
        if value and value.strip():
            return value.strip(), f"header:{key}"
    return None, "anonymous"


def _normalize_plantation(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().upper()
    if not cleaned or cleaned == "ALL":
        return None
    if cleaned in KNOWN_PLANTATIONS:
        return cleaned
    return None


def _plantation_from_username(username: str | None) -> str | None:
    cleaned = (username or "").strip().upper()
    if not cleaned:
        return None
    if "@" in cleaned:
        cleaned = cleaned.split("@", 1)[0]
    return cleaned if cleaned in KNOWN_PLANTATIONS else None


def _read_json_or_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    records: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("entries"), list):
            records.extend(item for item in payload["entries"] if isinstance(item, dict))
        if isinstance(payload.get("users"), list):
            records.extend(item for item in payload["users"] if isinstance(item, dict))
        if isinstance(payload.get("admins"), list):
            for item in payload["admins"]:
                if isinstance(item, dict):
                    copied = dict(item)
                    copied.setdefault("role", "admin")
                    copied.setdefault("can_upload", True)
                    records.append(copied)
        if isinstance(payload.get("mappings"), dict):
            for key, value in payload["mappings"].items():
                if isinstance(value, dict):
                    copied = dict(value)
                    copied.setdefault("username", key)
                    records.append(copied)
                elif isinstance(value, str):
                    records.append({"username": key, "estate": value})

        for key, value in payload.items():
            if key in {"entries", "users", "admins", "mappings", "note"}:
                continue
            if isinstance(value, dict):
                copied = dict(value)
                copied.setdefault("username", key)
                records.append(copied)
            elif isinstance(value, str):
                records.append({"username": key, "estate": value})

    return records


def _read_access_file() -> list[dict[str, Any]]:
    return _read_json_or_csv_records(Path(settings.USER_ACCESS_FILE))


def _read_credentials_file() -> list[dict[str, Any]]:
    return _read_json_or_csv_records(Path(settings.USER_CREDENTIALS_FILE))


def _configured_estates() -> list[str]:
    estates: list[str] = []
    for row in _read_access_file():
        estates_raw = row.get("estates")
        if isinstance(estates_raw, list):
            estates.extend(str(item).strip() for item in estates_raw if str(item).strip())
        elif row.get("estate"):
            estate_name = str(row.get("estate")).strip()
            if estate_name:
                estates.append(estate_name)
    return list(dict.fromkeys(estates))


def _estate_plantation_map(records: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in records:
        plantation = _normalize_plantation(
            str(row.get("plantation") or row.get("company") or row.get("group") or "").strip()
        ) or _plantation_from_username(row.get("username"))
        if not plantation:
            continue

        estates_raw = row.get("estates")
        if isinstance(estates_raw, list):
            for estate in estates_raw:
                estate_name = str(estate).strip()
                if estate_name:
                    mapping[estate_name] = plantation
        elif row.get("estate"):
            estate_name = str(row.get("estate")).strip()
            if estate_name:
                mapping[estate_name] = plantation
    return mapping


def _match_record(records: list[dict[str, Any]], username: str | None) -> dict[str, Any] | None:
    if not username:
        return None

    normalized_username = _normalize_token(username)
    if not normalized_username:
        return None

    for row in records:
        keys = [
            row.get("username"),
            row.get("user"),
            row.get("email"),
            row.get("login"),
            row.get("alias"),
        ]
        aliases = row.get("aliases")
        if isinstance(aliases, list):
            keys.extend(aliases)

        if any(_normalize_token(str(item)) == normalized_username for item in keys if item):
            return row

    return None


def _find_mapping(username: str | None) -> dict[str, Any] | None:
    return _match_record(_read_access_file(), username)


def _find_credentials(username: str | None) -> dict[str, Any] | None:
    return _match_record(_read_credentials_file(), username)


def _infer_estate_from_username(username: str | None, all_estates: list[str]) -> str | None:
    normalized_username = _normalize_token(username)
    if not normalized_username:
        return None

    exact = [estate for estate in all_estates if _normalize_token(estate) == normalized_username]
    if exact:
        return exact[0]

    partial = [estate for estate in all_estates if _normalize_token(estate) in normalized_username]
    if len(partial) == 1:
        return partial[0]

    return None


def authenticate_credentials(username: str, password: str) -> dict[str, Any] | None:
    username_clean = (username or "").strip()
    password_clean = (password or "").strip()
    if not username_clean or not password_clean:
        return None

    match = _find_credentials(username_clean)
    if not match:
        return None

    stored_password = str(match.get("password") or "").strip()
    if not stored_password or not secrets.compare_digest(password_clean, stored_password):
        return None

    return match


def resolve_access_context_for_identity(
    db: Session,
    username: str | None,
    selected_estate: str | None = None,
    selected_plantation: str | None = None,
    source: str = "direct",
) -> AccessContext:
    access_records = _read_access_file()
    db_estates = db.scalars(select(Estate.name).order_by(Estate.name)).all()
    configured_estates = _configured_estates()
    all_estates = list(dict.fromkeys([*db_estates, *configured_estates]))
    estate_to_plantation = _estate_plantation_map(access_records)
    mapping = _match_record(access_records, username)

    role = "viewer"
    display_name = None
    can_upload = False
    full_accessible_estates: list[str] = []
    access_mode = "open"
    access_message = None

    if mapping:
        role = str(mapping.get("role") or "viewer").strip().lower() or "viewer"
        display_name = mapping.get("display_name") or mapping.get("name")
        can_upload = bool(mapping.get("can_upload", role == "admin"))

        estates_raw = mapping.get("estates")
        if isinstance(estates_raw, list):
            full_accessible_estates = [str(item).strip() for item in estates_raw if str(item).strip()]
        elif mapping.get("estate"):
            full_accessible_estates = [str(mapping["estate"]).strip()]
        elif role == "admin":
            full_accessible_estates = list(all_estates)

        full_accessible_estates = list(dict.fromkeys(full_accessible_estates))
        if not full_accessible_estates:
            inferred = _infer_estate_from_username(username, all_estates)
            if inferred:
                full_accessible_estates = [inferred]

        access_mode = "locked" if len(full_accessible_estates) == 1 else "scoped"
        source = f"{source}|mapping"
    elif username:
        inferred = _infer_estate_from_username(username, all_estates)
        if inferred:
            full_accessible_estates = [inferred]
            access_mode = "locked"
            access_message = "Estate resolved from authenticated username."
            source = f"{source}|inferred"
        elif settings.ACCESS_STRICT_MODE:
            access_mode = "restricted"
            access_message = f"No estate mapping found for user '{username}'."
            source = f"{source}|restricted"
        else:
            full_accessible_estates = list(all_estates)
            access_mode = "open"
            access_message = f"No estate mapping found for user '{username}'. Showing accessible data in open mode."
            source = f"{source}|open-fallback"
    else:
        if settings.ACCESS_STRICT_MODE:
            access_mode = "restricted"
            access_message = "No authenticated username was provided."
            source = f"{source}|restricted"
        else:
            full_accessible_estates = list(all_estates)
            access_mode = "open"

    if role == "admin" and not full_accessible_estates:
        full_accessible_estates = list(all_estates)

    accessible_plantations = list(
        dict.fromkeys(
            estate_to_plantation.get(estate)
            for estate in full_accessible_estates
            if estate_to_plantation.get(estate)
        )
    )
    accessible_plantations = [plantation for plantation in KNOWN_PLANTATIONS if plantation in accessible_plantations]

    selected_plantation_normalized = _normalize_plantation(selected_plantation)
    if selected_plantation_normalized and selected_plantation_normalized not in accessible_plantations:
        selected_plantation_normalized = None

    if selected_plantation_normalized:
        accessible_estates = [
            estate for estate in full_accessible_estates if estate_to_plantation.get(estate) == selected_plantation_normalized
        ]
    else:
        accessible_estates = list(full_accessible_estates)

    selected_estate_clean = (selected_estate or "").strip() or None
    if selected_estate_clean and selected_estate_clean not in accessible_estates:
        selected_estate_clean = None

    if access_mode == "restricted":
        resolved_estate = None
        can_switch_estate = False
    elif len(accessible_estates) == 1 and len(full_accessible_estates) == 1:
        resolved_estate = accessible_estates[0]
        can_switch_estate = False
    else:
        resolved_estate = selected_estate_clean
        can_switch_estate = len(accessible_estates) > 1

    return AccessContext(
        username=username,
        display_name=display_name,
        role=role,
        accessible_estates=accessible_estates,
        resolved_estate=resolved_estate,
        can_upload=can_upload,
        can_switch_estate=can_switch_estate,
        access_mode=access_mode,
        access_message=access_message,
        source=source,
        accessible_plantations=accessible_plantations,
        selected_plantation=selected_plantation_normalized,
    )


def resolve_access_context(db: Session, request: Request) -> AccessContext:
    selected_estate = _first_value(request, ESTATE_QUERY_KEYS)
    selected_plantation = _first_value(request, PLANTATION_QUERY_KEYS)
    username, source = _extract_username(request)
    return resolve_access_context_for_identity(
        db=db,
        username=username,
        selected_estate=selected_estate,
        selected_plantation=selected_plantation,
        source=source,
    )
