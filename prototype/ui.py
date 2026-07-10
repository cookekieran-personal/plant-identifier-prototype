"""Reusable Streamlit UI components for the genus prototype.

The main app owns the flow; this file owns display details such as candidate
cards and verdict buttons. Keeping UI rendering here prevents the entrypoint
from becoming one long script.
"""

from __future__ import annotations

import streamlit as st

from prototype.models import GenusCandidate


VERDICTS = (
    ("correct", "Correct"),
    ("incorrect", "Incorrect"),
    ("unsure", "Unsure"),
)


def show_candidate(candidate: GenusCandidate) -> None:
    """Render the top suggested genus with PlantNet and relevant catalogue images."""

    st.subheader(f"We think the genus is {candidate.genus}")
    st.caption(f"PlantNet score {candidate.score:.0%} from {candidate.scientific_name}.")
    if candidate.common_name:
        st.write(candidate.common_name)

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
    """Render lower-ranked genus candidates with one PlantNet image each."""

    if len(candidates) <= 1:
        return
    with st.expander("Other possible genera"):
        for candidate in candidates[1:]:
            columns = st.columns([1, 3])
            with columns[0]:
                if candidate.plantnet_image_urls:
                    st.image(candidate.plantnet_image_urls[0], use_container_width=True)
            with columns[1]:
                st.write(f"**{candidate.genus}**")
                st.caption(f"{candidate.score:.0%} - {candidate.scientific_name}")


def verdict_buttons() -> str | None:
    """Show verdict buttons and return the selected verdict."""

    columns = st.columns(len(VERDICTS))
    for column, (value, label) in zip(columns, VERDICTS):
        if column.button(label, use_container_width=True):
            return value
    return None

