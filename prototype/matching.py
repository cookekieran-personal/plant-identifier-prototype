"""Genus-level matching between PlantNet and the Dear Garden catalogue.

Every PlantNet genus can be shown with PlantNet reference images. Dear Garden
examples are included only when the guessed genus exists in the catalogue.
"""

from __future__ import annotations

from prototype.catalogue import group_by_genus, normalize_genus
from prototype.models import GenusCandidate, GenusGuess, PlantRecord


def match_guesses_to_catalogue(
    guesses: list[GenusGuess],
    plants: list[PlantRecord],
    *,
    examples_per_genus: int = 3,
) -> list[GenusCandidate]:
    """Return UI-ready genus candidates for PlantNet guesses."""

    plants_by_genus = group_by_genus(plants)
    candidates = [
        build_candidate(guess, plants_by_genus.get(normalize_genus(guess.genus), []), examples_per_genus)
        for guess in guesses
    ]
    return sorted(candidates, key=lambda candidate: -candidate.score)


def build_candidate(guess: GenusGuess, plants: list[PlantRecord], examples_per_genus: int) -> GenusCandidate:
    """Build one UI-ready candidate from a PlantNet guess and catalogue plants."""

    examples = sorted(plants, key=lambda plant: plant.botanical_name)[:examples_per_genus]
    return GenusCandidate(
        genus=guess.genus,
        score=guess.score,
        scientific_name=guess.scientific_name,
        common_name=guess.common_name,
        plantnet_image_urls=guess.plantnet_image_urls,
        catalogue_plant_count=len(plants),
        example_names=tuple(plant.botanical_name for plant in examples),
        example_image_urls=tuple(plant.image_url for plant in examples if plant.image_url),
    )

