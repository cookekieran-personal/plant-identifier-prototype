"""Shared data models for the standalone genus-level prototype.

The app, API clients, matching logic, UI, and storage layer all use these
dataclasses so the result shape is defined once. The prototype evaluates only
genus-level correctness; it does not identify exact species or cultivars.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenusGuess:
    """One genus-level guess derived from a PlantNet result."""

    genus: str
    score: float
    scientific_name: str
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
    """A genus shown to the evaluator with PlantNet and Dear Garden evidence."""

    genus: str
    score: float
    scientific_name: str
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

