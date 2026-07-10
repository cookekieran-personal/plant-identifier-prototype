"""Local storage for prototype judgement rows.

The Dear Garden Supabase project is read-only for this prototype. Evaluation
labels are not written to Dear Garden's database. For local/cloud testing this
module appends labels to a CSV file; if durable shared storage is needed later,
use a separate database/project that is only for prototype evaluations.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from prototype.models import EvaluationRecord


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


def append_evaluation(record: EvaluationRecord, path: Path = DEFAULT_OUTPUT_PATH) -> None:
    """Append one evaluation row to the local CSV file."""

    if record.verdict not in VALID_VERDICTS:
        raise ValueError(f"Unsupported verdict: {record.verdict}")

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