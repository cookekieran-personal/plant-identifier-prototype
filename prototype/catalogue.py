"""Dear Garden catalogue access for genus-level examples.

This module reads the public/deployed catalogue from Supabase using REST. It
only loads plant names, genera, and representative image URLs needed for visual
context; it does not fetch or store user photos.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
import urllib.parse

import requests

from prototype.models import PlantRecord
from prototype.settings import secret, supabase_key


PLANT_FIELDS = "id,botanical_name,common_name,genus,exclude_from_recs"
IMAGE_FIELDS = "plant_id,image_url,is_primary"


def load_dear_garden_catalogue() -> list[PlantRecord]:
    """Load Dear Garden plants with image URLs from Supabase."""

    plants = supabase_fetch("plants", PLANT_FIELDS)
    images = supabase_fetch("plant_images", IMAGE_FIELDS)
    image_by_plant = primary_image_by_plant(images)

    records: list[PlantRecord] = []
    for plant in plants:
        if plant.get("exclude_from_recs"):
            continue
        botanical_name = plant.get("botanical_name") or ""
        genus = plant.get("genus") or genus_from_name(botanical_name)
        image_url = image_by_plant.get(plant.get("id"))
        if not genus or not image_url:
            continue
        records.append(
            PlantRecord(
                id=str(plant.get("id") or ""),
                botanical_name=botanical_name,
                common_name=plant.get("common_name") or "",
                genus=genus,
                image_url=image_url,
            )
        )
    return records


def supabase_fetch(table: str, select: str, page_size: int = 1000) -> list[dict[str, Any]]:
    """Fetch all rows for a table/select pair using Supabase REST pagination."""

    url = secret("SUPABASE_URL")
    key = supabase_key()
    if not url or not key:
        raise RuntimeError("Supabase URL/key is not configured.")

    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        params = urllib.parse.urlencode({"select": select})
        response = requests.get(
            f"{url.rstrip('/')}/rest/v1/{table}?{params}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "Range": f"{start}-{start + page_size - 1}",
            },
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else "unknown"
            raise RuntimeError(f"Supabase catalogue request failed with HTTP status {status}.") from None
        page = response.json()
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def primary_image_by_plant(images: list[dict[str, Any]]) -> dict[str, str]:
    """Choose one representative image URL for each plant."""

    out: dict[str, str] = {}
    for image in sorted(images, key=lambda row: not bool(row.get("is_primary"))):
        plant_id = str(image.get("plant_id") or "")
        image_url = image.get("image_url") or ""
        if plant_id and image_url:
            out.setdefault(plant_id, image_url)
    return out


def group_by_genus(plants: list[PlantRecord]) -> dict[str, list[PlantRecord]]:
    """Group catalogue plants by normalized genus."""

    grouped: dict[str, list[PlantRecord]] = defaultdict(list)
    for plant in plants:
        if plant.genus:
            grouped[normalize_genus(plant.genus)].append(plant)
    return dict(grouped)


def normalize_genus(genus: str) -> str:
    """Normalize a genus name for lookup while preserving display elsewhere."""

    return genus.strip().lower()


def genus_from_name(scientific_name: str) -> str:
    """Extract the genus from a scientific name."""

    return scientific_name.strip().split(" ", 1)[0]

