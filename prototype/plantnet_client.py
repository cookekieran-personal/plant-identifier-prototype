"""PlantNet client for genus-level evaluation.

This calls PlantNet using a server-side secret and returns genus-level guesses.
HTTP errors are sanitized so the API key cannot appear in the Streamlit page.
"""

from __future__ import annotations

from pathlib import Path

import requests

from prototype.models import GenusGuess
from prototype.settings import secret


API_URL = "https://my-api.plantnet.org/v2/identify/all"
PLANTNET_TIMEOUT = (10, 60)
PLANTNET_UNAVAILABLE_MESSAGE = (
    "PlantNet could not be reached right now. Please try again in a few minutes."
)
PLANTNET_FAILED_MESSAGE = "PlantNet could not identify this photo right now."


class PlantNetClientError(RuntimeError):
    """A safe, user-displayable PlantNet error."""


def identify_genus_guesses(image_path: Path, api_key: str | None = None, limit: int = 5) -> list[GenusGuess]:
    """Call PlantNet and return distinct genus guesses in score order."""

    raw = request_plantnet(image_path, api_key=api_key)
    return distinct_genus_guesses(raw.get("results", []), limit=limit)


def request_plantnet(image_path: Path, api_key: str | None = None, organs: str = "auto") -> dict:
    """Call PlantNet with a runtime API key."""

    resolved_key = api_key or secret("PLANTNET_API_KEY")
    if not resolved_key:
        raise PlantNetClientError("PlantNet API key is not configured.")

    try:
        with image_path.open("rb") as file:
            response = requests.post(
                API_URL,
                params={"api-key": resolved_key, "lang": "en", "include-related-images": "true"},
                files=[("images", (image_path.name, file, "application/octet-stream"))],
                data=[("organs", organs)],
                timeout=PLANTNET_TIMEOUT,
            )
    except requests.Timeout:
        raise PlantNetClientError(PLANTNET_UNAVAILABLE_MESSAGE) from None
    except requests.RequestException:
        raise PlantNetClientError("PlantNet request failed before a response was received.") from None
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        raise PlantNetClientError(f"PlantNet request failed with HTTP status {status}.") from None
    try:
        return response.json()
    except ValueError:
        raise PlantNetClientError(PLANTNET_FAILED_MESSAGE) from None


def distinct_genus_guesses(results: list[dict], limit: int = 5) -> list[GenusGuess]:
    """Collapse PlantNet species results to one best row per genus."""

    guesses: list[GenusGuess] = []
    seen: set[str] = set()
    for result in results:
        species = result.get("species") or {}
        scientific_name = species.get("scientificNameWithoutAuthor") or species.get("scientificName") or ""
        genus = genus_from_species(species) or genus_from_name(scientific_name)
        if not genus or genus.lower() in seen:
            continue
        seen.add(genus.lower())
        guesses.append(
            GenusGuess(
                genus=genus,
                score=float(result.get("score") or 0),
                scientific_name=scientific_name,
                common_name=first_common_name(species),
                plantnet_image_urls=related_image_urls(result.get("images") or []),
            )
        )
        if len(guesses) >= limit:
            break
    return guesses


def genus_from_species(species: dict) -> str:
    """Read PlantNet's explicit genus object when available."""

    genus = species.get("genus") or {}
    return genus.get("scientificNameWithoutAuthor") or genus.get("scientificName") or ""


def genus_from_name(scientific_name: str) -> str:
    """Extract the genus from a scientific name."""

    return scientific_name.strip().split(" ", 1)[0]


def first_common_name(species: dict) -> str:
    """Return the first common name from a PlantNet species payload."""

    common_names = species.get("commonNames") or []
    return common_names[0] if common_names else ""


def related_image_urls(images: list[dict], limit: int = 4) -> tuple[str, ...]:
    """Return a small de-duplicated set of PlantNet reference image URLs."""

    urls: list[str] = []
    seen: set[str] = set()
    for image in images:
        url = (image.get("url") or {}).get("m") or (image.get("url") or {}).get("o")
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= limit:
            break
    return tuple(urls)
