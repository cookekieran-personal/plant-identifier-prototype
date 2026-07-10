"""Storage for prototype judgement rows.

For deployed sharing, rows should go to Supabase so they survive app restarts
and do not depend on a laptop being on. A local CSV fallback is kept only for
development when Supabase insert credentials are not configured.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from prototype.models import EvaluationRecord
from prototype.settings import evaluations_table, secret, supabase_key


DEFAULT_OUTPUT_PATH = Path("prototype") / "evaluations.csv"
FIELDNAMES = (
    "timestamp_utc",
    "test_id",
    "verdict",
    "suggested_genus",
    "plantnet_score",
    "plantnet_scientific_name",
    "plantnet_common_name",
    "alternative_genera",
    "notes",
)
VALID_VERDICTS = {"correct", "incorrect", "unsure"}


def append_evaluation(record: EvaluationRecord) -> None:
    """Persist one evaluation row to Supabase or local CSV."""

    if record.verdict not in VALID_VERDICTS:
        raise ValueError(f"Unsupported verdict: {record.verdict}")

    if can_insert_to_supabase():
        insert_supabase_record(record)
    else:
        append_csv_record(record)


def can_insert_to_supabase() -> bool:
    """Return whether Supabase evaluation storage is configured."""

    return bool(secret("SUPABASE_URL") and supabase_key())


def insert_supabase_record(record: EvaluationRecord) -> None:
    """Insert an evaluation record into Supabase."""

    url = secret("SUPABASE_URL")
    key = supabase_key()
    if not url or not key:
        raise RuntimeError("Supabase storage is not configured.")

    response = requests.post(
        f"{url.rstrip('/')}/rest/v1/{evaluations_table()}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json=supabase_payload(record),
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        raise RuntimeError(f"Could not save evaluation row. Supabase returned HTTP {status}.") from None


def supabase_payload(record: EvaluationRecord) -> dict[str, Any]:
    """Convert a record to the Supabase table schema."""

    return {
        "test_id": record.test_id,
        "verdict": record.verdict,
        "suggested_genus": record.suggested_genus,
        "plantnet_score": record.plantnet_score,
        "plantnet_scientific_name": record.plantnet_scientific_name,
        "plantnet_common_name": record.plantnet_common_name,
        "alternative_genera": list(record.alternative_genera),
        "notes": record.notes,
    }


def append_csv_record(record: EvaluationRecord, path: Path = DEFAULT_OUTPUT_PATH) -> None:
    """Append one evaluation row to a local CSV file for development."""

    path.parent.mkdir(parents=True, exist_ok=True)
    row = serialize_csv_record(record)
    row["timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def serialize_csv_record(record: EvaluationRecord) -> dict[str, str]:
    """Convert a record to the flat local CSV schema."""

    row = asdict(record)
    row["plantnet_score"] = f"{record.plantnet_score:.6f}"
    row["alternative_genera"] = "|".join(record.alternative_genera)
    return row

