"""PlantNet client for species-level evaluation.

This calls PlantNet using a server-side secret and returns species-level guesses.
HTTP errors are sanitized so the API key cannot appear in the Streamlit page.
"""

from __future__ import annotations

from pathlib import Path

import requests

from prototype.models import PlantNetGuess
from prototype.settings import secret


API_URL = "https://my-api.plantnet.org/v2/identify/all"
PLANTNET_TIMEOUT = (10, 60)
PLANTNET_UNAVAILABLE_MESSAGE = (
    "PlantNet could not be reached right now. Please try again in a few minutes."
)
PLANTNET_FAILED_MESSAGE = "PlantNet could not identify this photo right now."


class PlantNetClientError(RuntimeError):
    """A safe, user-displayable PlantNet error."""


def identify_plantnet_guesses(
    image_paths: list[Path],
    api_key: str | None = None,
    organs: list[str] | None = None,
    limit: int = 5,
) -> list[PlantNetGuess]:
    """Call PlantNet and return distinct species guesses in score order."""

    raw = request_plantnet(image_paths, api_key=api_key, organs=organs)
    return distinct_species_guesses(raw.get("results", []), limit=limit)


def request_plantnet(
    image_paths: list[Path],
    api_key: str | None = None,
    organs: list[str] | None = None,
) -> dict:
    """Call PlantNet with a runtime API key."""

    resolved_key = api_key or secret("PLANTNET_API_KEY")
    if not resolved_key:
        raise PlantNetClientError("PlantNet API key is not configured.")
    if not image_paths:
        raise PlantNetClientError("No plant photo was provided.")
    if len(image_paths) > 5:
        raise PlantNetClientError("PlantNet accepts up to 5 photos of one plant.")

    organ_values = organs or ["auto"] * len(image_paths)
    if len(organ_values) != len(image_paths):
        raise PlantNetClientError("Each plant photo must have one organ label.")

    try:
        open_files = [image_path.open("rb") for image_path in image_paths]
        try:
            files = [
                ("images", (image_path.name, file, "application/octet-stream"))
                for image_path, file in zip(image_paths, open_files)
            ]
            response = requests.post(
                API_URL,
                params={"api-key": resolved_key, "lang": "en", "include-related-images": "true"},
                files=files,
                data=[("organs", organ) for organ in organ_values],
                timeout=PLANTNET_TIMEOUT,
            )
        finally:
            for file in open_files:
                file.close()
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


def distinct_species_guesses(results: list[dict], limit: int = 5) -> list[PlantNetGuess]:
    """Return one best PlantNet row per species."""

    guesses: list[PlantNetGuess] = []
    seen: set[str] = set()
    for result in results:
        species = result.get("species") or {}
        scientific_name = species.get("scientificNameWithoutAuthor") or species.get("scientificName") or ""
        genus = genus_from_species(species) or genus_from_name(scientific_name)
        normalized_name = scientific_name.strip().lower()
        if not genus or not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        guesses.append(
            PlantNetGuess(
                genus=genus,
                score=float(result.get("score") or 0),
                scientific_name=scientific_name,
                scientific_name_with_author=species.get("scientificName") or scientific_name,
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
