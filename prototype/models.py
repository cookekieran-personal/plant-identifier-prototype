"""Shared data models for the standalone PlantNet prototype.

The app, API clients, matching logic, UI, and storage layer all use these
dataclasses so the result shape is defined once.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlantNetGuess:
    """One species-level guess returned by PlantNet."""

    genus: str
    score: float
    scientific_name: str
    scientific_name_with_author: str = ""
    common_name: str = ""
    plantnet_image_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlantRecord:
    """One Dear Garden catalogue plant used as a genus example."""

    id: str
    botanical_name: str
    common_name: str
    genus: str
    image_url: str


@dataclass(frozen=True)
class GenusCandidate:
    """A PlantNet candidate shown with relevant Dear Garden genus evidence."""

    genus: str
    score: float
    scientific_name: str
    scientific_name_with_author: str
    common_name: str
    plantnet_image_urls: tuple[str, ...]
    catalogue_plant_count: int
    example_names: tuple[str, ...]
    example_image_urls: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationRecord:
    """One saved judgement from the phone prototype."""

    test_id: str
    verdict: str
    suggested_genus: str
    plantnet_score: float
    plantnet_scientific_name: str
    plantnet_common_name: str
    alternative_genera: tuple[str, ...]
    notes: str = ""
