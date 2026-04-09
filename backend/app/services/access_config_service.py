from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.services.import_service import _configured_estates as _import_configured_estates_cache

KNOWN_PLANTATIONS = ("TTEL", "KVPL", "HPL")
REFERENCE_DOC_NAME = "estate_username_password_list.docx"


@dataclass(slots=True)
class AccessConfigUploadSummary:
    source_filename: str
    estates_count: int
    estate_user_count: int
    plantation_codes: list[str]
    users_count: int
    message: str
    warnings: list[str]


def _normalize_plantation(value: str | None) -> str | None:
    cleaned = (value or "").strip().upper()
    return cleaned if cleaned in KNOWN_PLANTATIONS else None


def _plantation_from_username(username: str | None) -> str | None:
    cleaned = (username or "").strip().upper()
    if not cleaned:
        return None
    if "@" in cleaned:
        cleaned = cleaned.split("@", 1)[0]
    return cleaned if cleaned in KNOWN_PLANTATIONS else None


def _iter_docx_text(content: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    values = []
    for node in root.findall(".//w:t", ns):
        text = (node.text or "").strip()
        if text:
            values.append(text)
    return values


def _parse_docx_entries(content: bytes) -> list[dict[str, str]]:
    values = _iter_docx_text(content)
    start_index = None
    for index in range(len(values) - 2):
        if values[index:index + 3] == ["Estate", "Username", "Password"]:
            start_index = index + 3
            break
    if start_index is None:
        raise ValueError("Could not find Estate / Username / Password columns in the access document.")

    rows: list[dict[str, str]] = []
    index = start_index
    while index + 2 < len(values):
        estate, username, password = values[index:index + 3]
        rows.append(
            {
                "estate": estate.strip(),
                "username": username.strip(),
                "password": password.strip(),
            }
        )
        index += 3

    return rows


def _parse_csv_entries(content: bytes) -> list[dict[str, str]]:
    handle = io.StringIO(content.decode("utf-8-sig"))
    reader = csv.DictReader(handle)
    rows = []
    for row in reader:
        estate = str(row.get("Estate") or row.get("estate") or "").strip()
        username = str(row.get("Username") or row.get("username") or "").strip()
        password = str(row.get("Password") or row.get("password") or "").strip()
        if estate and username and password:
            rows.append({"estate": estate, "username": username, "password": password})
    return rows


def _parse_json_entries(content: bytes) -> list[dict[str, str]]:
    payload = json.loads(content.decode("utf-8"))
    if isinstance(payload, dict):
        if isinstance(payload.get("entries"), list):
            source = payload["entries"]
        elif isinstance(payload.get("users"), list):
            source = payload["users"]
        else:
            source = []
    elif isinstance(payload, list):
        source = payload
    else:
        source = []

    rows: list[dict[str, str]] = []
    for item in source:
        if not isinstance(item, dict):
            continue
        estate = str(item.get("estate") or item.get("Estate") or "").strip()
        username = str(item.get("username") or item.get("Username") or "").strip()
        password = str(item.get("password") or item.get("Password") or "").strip()
        if estate and username and password:
            rows.append({"estate": estate, "username": username, "password": password})
    return rows


def _parse_entries(content: bytes, filename: str) -> list[dict[str, str]]:
    lower = filename.lower()
    if lower.endswith(".docx"):
        return _parse_docx_entries(content)
    if lower.endswith(".csv"):
        return _parse_csv_entries(content)
    if lower.endswith(".json"):
        return _parse_json_entries(content)
    raise ValueError("Upload a DOCX, CSV, or JSON access document.")


def _alias_list(username: str, estate: str) -> list[str]:
    normalized_username = username.lower()
    plantation = _plantation_from_username(username)
    aliases = [
        estate,
        estate.lower(),
        username,
        normalized_username,
    ]
    if plantation and "@" in username:
        aliases.append(f"{plantation.lower()}{username.split('@', 1)[1].lower()}")
    deduped = []
    seen = set()
    for item in aliases:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped


def _build_payloads(entries: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    regular_entries = []
    estates_by_plantation: dict[str, list[str]] = {key: [] for key in KNOWN_PLANTATIONS}

    seen_usernames: set[str] = set()
    for item in entries:
        estate = str(item["estate"]).strip()
        username = str(item["username"]).strip()
        password = str(item["password"]).strip()
        if not estate or not username or not password:
            continue
        if username.upper() in {"ADMIN", "TTEL", "KVPL", "HPL", "MD"}:
            continue
        normalized_username = username.upper()
        if normalized_username in seen_usernames:
            continue
        seen_usernames.add(normalized_username)

        plantation = _plantation_from_username(username) or ""
        if plantation in estates_by_plantation and estate not in estates_by_plantation[plantation]:
            estates_by_plantation[plantation].append(estate)

        regular_entries.append(
            {
                "estate": estate,
                "username": username,
                "password": password,
                "plantation": plantation or None,
            }
        )

    all_estates = [item["estate"] for item in regular_entries]
    system_credentials = [
        {
            "estate": "All Estates",
            "username": "ADMIN",
            "password": "admin123",
            "role": "admin",
            "can_upload": True,
        },
        {
            "estate": "TTEL Executive Scope",
            "username": "TTEL",
            "password": "ttel@123",
            "role": "ceo",
            "plantation": "TTEL",
        },
        {
            "estate": "KVPL Executive Scope",
            "username": "KVPL",
            "password": "kvpl@123",
            "role": "ceo",
            "plantation": "KVPL",
        },
        {
            "estate": "HPL Executive Scope",
            "username": "HPL",
            "password": "hpl@123",
            "role": "ceo",
            "plantation": "HPL",
        },
        {
            "estate": "All Plantations",
            "username": "MD",
            "password": "md123",
            "role": "md",
            "plantations": list(KNOWN_PLANTATIONS),
        },
    ]

    credentials_payload = {
        "note": "Estate credentials supplied by the user. The application login screen validates these usernames and passwords, including ADMIN and executive accounts.",
        "entries": system_credentials + regular_entries,
    }

    user_rows = [
        {
            "username": item["username"],
            "display_name": f'{item["estate"]} User',
            "estate": item["estate"],
            "plantation": item["plantation"],
            "aliases": _alias_list(item["username"], item["estate"]),
        }
        for item in regular_entries
    ]

    executive_rows = [
        {
            "username": "TTEL",
            "display_name": "TTEL CEO",
            "role": "ceo",
            "plantation": "TTEL",
            "estates": estates_by_plantation["TTEL"],
            "aliases": ["ttel", "TTEL"],
        },
        {
            "username": "KVPL",
            "display_name": "KVPL CEO",
            "role": "ceo",
            "plantation": "KVPL",
            "estates": estates_by_plantation["KVPL"],
            "aliases": ["kvpl", "KVPL"],
        },
        {
            "username": "HPL",
            "display_name": "HPL CEO",
            "role": "ceo",
            "plantation": "HPL",
            "estates": estates_by_plantation["HPL"],
            "aliases": ["hpl", "HPL"],
        },
        {
            "username": "MD",
            "display_name": "Managing Director",
            "role": "md",
            "plantations": list(KNOWN_PLANTATIONS),
            "estates": all_estates,
            "aliases": ["md", "MD"],
        },
    ]

    access_payload = {
        "admins": [
            {
                "username": "ADMIN",
                "display_name": "System Admin",
                "role": "admin",
                "can_upload": True,
                "aliases": ["admin", "ADMIN"],
            }
        ],
        "users": user_rows + executive_rows,
    }

    plantations = [code for code in KNOWN_PLANTATIONS if estates_by_plantation[code]]
    return access_payload, credentials_payload, plantations


def apply_access_document(content: bytes, filename: str) -> AccessConfigUploadSummary:
    rows = _parse_entries(content, filename)
    if not rows:
        raise ValueError("No access rows were found in the uploaded document.")

    access_payload, credentials_payload, plantations = _build_payloads(rows)

    access_path = Path(settings.USER_ACCESS_FILE)
    credentials_path = Path(settings.USER_CREDENTIALS_FILE)
    reference_doc_path = credentials_path.with_name(REFERENCE_DOC_NAME)
    access_path.parent.mkdir(parents=True, exist_ok=True)

    access_path.write_text(json.dumps(access_payload, indent=2), encoding="utf-8")
    credentials_path.write_text(json.dumps(credentials_payload, indent=2), encoding="utf-8")

    if filename.lower().endswith(".docx"):
        reference_doc_path.write_bytes(content)

    try:
        _import_configured_estates_cache.cache_clear()
    except Exception:
        pass

    estates = sorted(
        {
            str(item.get("estate")).strip()
            for item in rows
            if str(item.get("estate") or "").strip() and str(item.get("estate")).strip().lower() != "admin"
        }
    )

    estate_user_count = len(
        [item for item in rows if str(item.get("username") or "").strip().upper() not in {"ADMIN", "TTEL", "KVPL", "HPL", "MD"}]
    )
    total_users = estate_user_count + 5  # ADMIN + 3 CEOs + MD
    message = f"Updated access list for {len(estates)} estates and {total_users} users."

    warnings = []
    if not filename.lower().endswith(".docx"):
        warnings.append("The upload updated JSON access files, but the reference DOCX was not replaced because the uploaded file was not a DOCX.")

    return AccessConfigUploadSummary(
        source_filename=filename,
        estates_count=len(estates),
        estate_user_count=estate_user_count,
        plantation_codes=plantations,
        users_count=total_users,
        message=message,
        warnings=warnings,
    )
