"""
Manual CSV importer for 7taps Analytics (idempotent).

Reads focus-group style CSV rows and converts them into xAPI statements,
then uses the DataNormalizer pipeline to write into the normalized tables.

Idempotency:
- Deterministic statement IDs for CSV rows based on a natural key
  (actor_id + activity_id + response text).
- Before inserting, checks for an equivalent statement already present
  (same actor_id, activity_id, and response). If present, skips.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from app.config import get_extension_key, get_lesson_name, get_lesson_url, settings
from app.data_normalization import DataNormalizer


@dataclass
class FocusGroupRow:
    learner: str
    card: str
    card_type: str
    lesson_number: int
    global_q: int
    pdf_page: Optional[int]
    response: str


def _normalize_actor_id(name_or_email: str) -> str:
    return name_or_email.strip().lower().replace(" ", "_")


def _extract_card_info(card_text: str) -> Dict[str, Any]:
    card_number = None
    card_type = None
    question_text = card_text
    try:
        if "Card " in card_text:
            # e.g., "Card 6 (Form): Question text"
            after = card_text.split("Card ", 1)[1]
            num_part = after.split(" ", 1)[0]
            if num_part.isdigit():
                card_number = int(num_part)
        if "(" in card_text and ")" in card_text:
            card_type = card_text.split("(", 1)[1].split(")", 1)[0]
        if ":" in card_text:
            question_text = card_text.split(":", 1)[1].strip()
    except Exception:
        pass
    return {
        "card_number": card_number,
        "card_type": card_type,
        "question_text": question_text,
        "full_card_text": card_text,
    }


def _activity_id_for(row: FocusGroupRow, card_number: Optional[int]) -> str:
    # Keep consistent with existing conventions
    n = card_number if card_number is not None else row.global_q
    return f"{settings.SEVENTAPS_DOMAIN}/activities/focus_group_card_{n}"


def _deterministic_statement_id(actor_id: str, activity_id: str, response: str) -> str:
    basis = f"{actor_id}|{activity_id}|{response.strip()}".encode("utf-8")
    h = hashlib.sha1(basis).hexdigest()
    return f"csv:{h}"


def _xapi_for_row(row: FocusGroupRow, base_time: datetime) -> Dict[str, Any]:
    card_info = _extract_card_info(row.card)
    actor_id = _normalize_actor_id(row.learner)
    activity_id = _activity_id_for(row, card_info.get("card_number"))

    # Space timestamps per global question for readability
    ts = base_time + timedelta(minutes=int(row.global_q) * 2)

    statement: Dict[str, Any] = {
        "actor": {
            "objectType": "Agent",
            "name": row.learner,
            "account": {"name": actor_id, "homePage": settings.SEVENTAPS_DOMAIN},
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered",
            "display": {"en-US": "answered"},
        },
        "object": {
            "objectType": "Activity",
            "id": activity_id,
            "definition": {
                "name": {"en-US": card_info["question_text"] or row.card},
                "description": {
                    "en-US": f"Focus group {row.card_type} question from lesson {row.lesson_number}"
                },
                "type": f"http://adlnet.gov/expapi/activities/{row.card_type.lower()}",
                "extensions": {
                    get_extension_key("lesson_number"): str(row.lesson_number),
                    get_extension_key("lesson_name"): get_lesson_name(str(row.lesson_number)),
                    get_extension_key("lesson_url"): get_lesson_url(str(row.lesson_number)),
                    get_extension_key("global_q"): str(row.global_q),
                    get_extension_key("card_number"): str(card_info["card_number"]) if card_info["card_number"] else "",
                    get_extension_key("card_type"): row.card_type,
                    get_extension_key("pdf_page"): str(row.pdf_page) if row.pdf_page is not None else "",
                    get_extension_key("source"): "focus_group_csv",
                },
            },
        },
        "result": {"response": row.response, "success": True, "completion": True},
        "context": {"platform": "7taps", "language": "en-US"},
        "timestamp": ts.isoformat() + "Z",
        "version": "1.0.3",
    }

    # Deterministic ID for idempotency
    statement["id"] = _deterministic_statement_id(actor_id, activity_id, row.response)
    return statement


def parse_focus_group_csv_text(csv_text: str) -> List[FocusGroupRow]:
    df = pd.read_csv(pd.io.common.StringIO(csv_text))
    required = [
        "Learner",
        "Card",
        "Card type",
        "Lesson Number",
        "Global Q#",
        "PDF Page #",
        "Response",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out: List[FocusGroupRow] = []
    for _, r in df.iterrows():
        out.append(
            FocusGroupRow(
                learner=str(r["Learner"]).strip(),
                card=str(r["Card"]).strip(),
                card_type=str(r["Card type"]).strip(),
                lesson_number=int(r["Lesson Number"]),
                global_q=int(r["Global Q#"]),
                pdf_page=(int(r["PDF Page #"]) if pd.notna(r["PDF Page #"]) else None),
                response=str(r["Response"]) if pd.notna(r["Response"]) else "",
            )
        )
    return out


async def import_focus_group_csv_text(
    csv_text: str,
    *,
    normalizer: Optional[DataNormalizer] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Import focus group CSV text via normalizer with idempotency.

    Returns summary dict: { imported, skipped, errors }.
    """
    rows = parse_focus_group_csv_text(csv_text)
    base_time = datetime.utcnow().replace(microsecond=0)

    norm = normalizer or DataNormalizer()

    imported = 0
    skipped = 0
    errors: List[str] = []
    matches: List[Dict[str, Any]] = []
    would_import: List[Dict[str, Any]] = []

    for row in rows:
        try:
            stmt = _xapi_for_row(row, base_time)

            # Dedupe: skip if an equivalent statement already exists
            actor_id = stmt["actor"]["account"]["name"]
            activity_id = stmt["object"]["id"]
            response = (stmt.get("result") or {}).get("response") or ""

            exists = await norm.exists_equivalent_statement(actor_id, activity_id, response)
            if exists:
                skipped += 1
                matches.append({
                    "actor_id": actor_id,
                    "activity_id": activity_id,
                    "response": response,
                    "statement_id": stmt.get("id"),
                })
                continue

            if dry_run:
                would_import.append({
                    "actor_id": actor_id,
                    "activity_id": activity_id,
                    "response": response,
                    "statement_id": stmt.get("id"),
                })
                imported += 1
            else:
                await norm.process_statement_normalization(stmt)
                imported += 1
        except Exception as e:
            errors.append(str(e))

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "matches": matches,
        "would_import": would_import,
        "dry_run": dry_run,
    }
