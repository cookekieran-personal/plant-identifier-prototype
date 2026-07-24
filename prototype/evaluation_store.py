"""Storage for prototype judgement rows.

Dear Garden Supabase is read-only for this prototype. Evaluation labels are
written to a separate evaluation Supabase project when `EVAL_SUPABASE_*` secrets
are configured. A local CSV fallback is kept for laptop-only development.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from prototype.models import EvaluationRecord
from prototype.settings import eval_supabase_key, eval_supabase_table, eval_supabase_url


DEFAULT_OUTPUT_PATH = Path("prototype") / "evaluations.csv"
FIELDNAMES = (
    "timestamp_utc",
    "test_id",
    "verdict",
    "suggested_genus",
    "suggested_species",
    "plantnet_genus_score",
    "plantnet_species_score",
    "plantnet_scientific_name",
    "plantnet_common_name",
    "alternative_genera",
    "selected_species",
    "notes",
)
VALID_VERDICTS = {
    "both_correct",
    "genus_correct_species_incorrect",
    "both_incorrect",
    "unsure",
}


def append_evaluation(record: EvaluationRecord) -> None:
    """Persist one evaluation row to the eval Supabase project or local CSV."""

    if record.verdict not in VALID_VERDICTS:
        raise ValueError(f"Unsupported verdict: {record.verdict}")

    if can_insert_to_eval_supabase():
        insert_eval_supabase_record(record)
    else:
        append_csv_record(record)


def can_insert_to_eval_supabase() -> bool:
    """Return whether separate evaluation Supabase storage is configured."""

    return bool(eval_supabase_url() and eval_supabase_key())


def insert_eval_supabase_record(record: EvaluationRecord) -> None:
    """Insert an evaluation record into the separate evaluation Supabase project."""

    url = eval_supabase_url()
    key = eval_supabase_key()
    if not url or not key:
        raise RuntimeError("Evaluation Supabase storage is not configured.")

    response = requests.post(
        f"{url.rstrip('/')}/rest/v1/{eval_supabase_table()}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json=eval_supabase_payload(record),
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        raise RuntimeError(f"Could not save evaluation row. Evaluation Supabase returned HTTP {status}.") from None


def eval_supabase_payload(record: EvaluationRecord) -> dict[str, Any]:
    """Convert a record to the evaluation Supabase table schema."""

    return {
        "test_id": record.test_id,
        "verdict": record.verdict,
        "suggested_genus": record.suggested_genus,
        "suggested_species": record.suggested_species,
        "plantnet_score": record.plantnet_species_score,
        "plantnet_genus_score": record.plantnet_genus_score,
        "plantnet_species_score": record.plantnet_species_score,
        "plantnet_scientific_name": record.plantnet_scientific_name,
        "plantnet_common_name": record.plantnet_common_name,
        "alternative_genera": list(record.alternative_genera),
        "selected_species": record.selected_species,
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
    row["plantnet_genus_score"] = f"{record.plantnet_genus_score:.6f}"
    row["plantnet_species_score"] = f"{record.plantnet_species_score:.6f}"
    row["alternative_genera"] = "|".join(record.alternative_genera)
    return row
