"""Streamlit phone prototype for genus-level PlantNet evaluation.

Run with `streamlit run prototype/app.py`. The app lets a user take or upload a
plant photo, sends the temporary image to PlantNet, shows genus-level evidence,
and saves only a correct/incorrect/unsure judgement. User photos are discarded
after the PlantNet call.
"""

from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototype.camera import image_suffix, temporary_image_file
from prototype.catalogue import load_dear_garden_catalogue
from prototype.evaluation_store import append_evaluation
from prototype.matching import match_guesses_to_catalogue
from prototype.models import EvaluationRecord
from prototype.plantnet_client import identify_genus_guesses
from prototype.settings import configure_environment_from_secrets, secret
from prototype.ui import show_alternatives, show_candidate, verdict_buttons


st.set_page_config(page_title="Dear Garden Genus Prototype", page_icon="DG", layout="centered")
configure_environment_from_secrets()


@st.cache_data(show_spinner="Loading Dear Garden catalogue...")
def cached_catalogue():
    """Load catalogue once per Streamlit session."""

    return load_dear_garden_catalogue()


def identify_uploaded_photo(uploaded_photo) -> None:
    """Run PlantNet and store genus candidates in session state."""

    with temporary_image_file(uploaded_photo, suffix=image_suffix(uploaded_photo)) as image_path:
        guesses = identify_genus_guesses(image_path, api_key=secret("PLANTNET_API_KEY"))
    candidates = match_guesses_to_catalogue(guesses, cached_catalogue())
    if not candidates:
        raise RuntimeError("No genus suggestions were returned for this image.")
    st.session_state.test_id = uuid4().hex
    st.session_state.candidates = candidates


def save_verdict(verdict: str, notes: str) -> None:
    """Save the evaluator's judgement for the current top candidate."""

    top = st.session_state.candidates[0]
    alternatives = tuple(candidate.genus for candidate in st.session_state.candidates[1:])
    append_evaluation(
        EvaluationRecord(
            test_id=st.session_state.test_id,
            verdict=verdict,
            suggested_genus=top.genus,
            plantnet_score=top.score,
            plantnet_scientific_name=top.scientific_name,
            plantnet_common_name=top.common_name,
            alternative_genera=alternatives,
            notes=notes,
        )
    )
    st.session_state.saved = True


def main() -> None:
    """Render the app."""

    st.title("Dear Garden Genus Prototype")
    st.caption("Take a plant photo, check the suggested genus, and label whether it was right.")

    uploaded_photo = st.camera_input("Take a plant photo")
    if uploaded_photo is None:
        uploaded_photo = st.file_uploader("Or upload a plant photo", type=("jpg", "jpeg", "png"))

    if uploaded_photo and st.button("Identify genus", type="primary", use_container_width=True):
        with st.spinner("Checking PlantNet..."):
            try:
                identify_uploaded_photo(uploaded_photo)
                st.session_state.saved = False
            except Exception as error:  # noqa: BLE001 - show sanitized user-facing errors only
                st.error(str(error))
                return

    candidates = st.session_state.get("candidates", [])
    if not candidates:
        return

    show_candidate(candidates[0])
    show_alternatives(candidates)

    notes = st.text_input("Optional notes")
    verdict = verdict_buttons()
    if verdict:
        try:
            save_verdict(verdict, notes)
        except Exception as error:  # noqa: BLE001 - storage errors are sanitized before display
            st.error(str(error))
            return

    if st.session_state.get("saved"):
        st.success("Saved. Take the next photo when ready.")


if __name__ == "__main__":
    main()

