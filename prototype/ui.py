"""Reusable Streamlit UI components for the PlantNet prototype.

The main app owns the flow; this file owns display details such as candidate
cards and verdict buttons. Keeping UI rendering here prevents the entrypoint
from becoming one long script.
"""

from __future__ import annotations

import streamlit as st

from prototype.models import GenusCandidate


VERDICTS = (
    ("both_correct", "Genus and species are both correct"),
    ("genus_correct_species_incorrect", "Genus is correct, species is incorrect"),
    ("both_incorrect", "Both are incorrect"),
    ("unsure", "Not sure"),
)


def show_candidate(candidate: GenusCandidate, confidence_threshold: float) -> None:
    """Render the top PlantNet suggestion with PlantNet and catalogue images."""

    if candidate.genus_score >= confidence_threshold:
        st.subheader(f"We think the plant is {candidate.scientific_name}")
    else:
        st.subheader(f"This might be {candidate.scientific_name}")
        st.write(f"We are {candidate.genus_score:.0%} confident that it is this.")
    st.caption(
        f"Genus confidence: {candidate.genus_score:.0%} for {candidate.genus}. "
        f"Exact species confidence: {candidate.score:.0%} for {candidate.scientific_name}."
    )
    if candidate.common_name:
        st.write(candidate.common_name)
    if candidate.scientific_name_with_author and candidate.scientific_name_with_author != candidate.scientific_name:
        st.caption(candidate.scientific_name_with_author)

    show_image_row("PlantNet reference images", candidate.plantnet_image_urls)

    if candidate.example_image_urls:
        st.markdown(f"**Dear Garden examples from {candidate.genus}**")
        st.caption(f"{candidate.catalogue_plant_count} Dear Garden catalogue plants share this genus.")
        show_image_row("", candidate.example_image_urls, captions=candidate.example_names)


def show_image_row(title: str, image_urls: tuple[str, ...], captions: tuple[str, ...] = ()) -> None:
    """Render a compact row of images with optional captions."""

    if not image_urls:
        return
    if title:
        st.markdown(f"**{title}**")
    columns = st.columns(len(image_urls))
    for index, (column, image_url) in enumerate(zip(columns, image_urls)):
        with column:
            st.image(image_url, use_container_width=True)
            if index < len(captions):
                st.caption(captions[index])


def show_alternatives(candidates: list[GenusCandidate]) -> None:
    """Render lower-ranked PlantNet candidates with one PlantNet image each."""

    if len(candidates) <= 1:
        return
    with st.expander("Other possible matches"):
        for candidate in candidates[1:]:
            columns = st.columns([1, 3])
            with columns[0]:
                if candidate.plantnet_image_urls:
                    st.image(candidate.plantnet_image_urls[0], use_container_width=True)
            with columns[1]:
                st.write(f"**{candidate.scientific_name}**")
                st.caption(
                    f"{candidate.genus_score:.0%} genus confidence; {candidate.score:.0%} species confidence"
                )


def verdict_buttons() -> str | None:
    """Show verdict buttons and return the selected verdict."""

    for value, label in VERDICTS:
        if st.button(label, use_container_width=True):
            return value
    return None
