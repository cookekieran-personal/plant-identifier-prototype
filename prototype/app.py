"""Streamlit phone prototype for PlantNet species evaluation.

Run with `streamlit run prototype/app.py`. The app lets a user take or upload a
plant photo, sends the temporary image to PlantNet, shows species-level evidence,
asks for another plant photo when confidence is low, and saves only a
correct/incorrect/unsure judgement. User photos are discarded after the PlantNet
call.
"""

from __future__ import annotations

from contextlib import ExitStack
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
from prototype.plantnet_client import PlantNetClientError, identify_plantnet_guesses
from prototype.settings import configure_environment_from_secrets, secret
from prototype.ui import show_alternatives, show_candidate, verdict_buttons


EXACT_SPECIES_CONFIDENCE = 0.70
SECOND_PHOTO_CONFIDENCE = 0.50
SECOND_PHOTO_ORGANS = ("flower", "leaf", "fruit", "bark", "auto")

st.set_page_config(page_title="Dear Garden Plant ID Prototype", page_icon="DG", layout="centered")
configure_environment_from_secrets()


@st.cache_data(show_spinner="Loading Dear Garden catalogue...")
def cached_catalogue():
    """Load catalogue once per Streamlit session."""

    return load_dear_garden_catalogue()


def identify_uploaded_photos(uploaded_photos: list, organs: list[str] | None = None) -> None:
    """Run PlantNet and store candidates in session state."""

    with ExitStack() as stack:
        image_paths = [
            stack.enter_context(temporary_image_file(photo, suffix=image_suffix(photo)))
            for photo in uploaded_photos
        ]
        guesses = identify_plantnet_guesses(
            image_paths,
            api_key=secret("PLANTNET_API_KEY"),
            organs=organs,
        )
    candidates = match_guesses_to_catalogue(guesses, cached_catalogue())
    if not candidates:
        raise RuntimeError("No plant suggestions were returned for this image.")
    st.session_state.test_id = uuid4().hex
    st.session_state.candidates = candidates
    st.session_state.needs_second_photo = candidates[0].score < SECOND_PHOTO_CONFIDENCE
    st.session_state.saved = False


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


def show_safe_error(message: str) -> None:
    """Display only fixed, secret-free messages in the public app."""

    st.error(message)


def main() -> None:
    """Render the app."""

    st.title("Dear Garden Plant ID Prototype")
    st.caption("Take a clear plant photo. If confidence is high, PlantNet can suggest the exact species.")

    uploaded_photo = st.camera_input("Take a plant photo", key="primary_camera")
    if uploaded_photo is None:
        uploaded_photo = st.file_uploader(
            "Or upload a plant photo",
            type=("jpg", "jpeg", "png"),
            key="primary_upload",
        )

    if uploaded_photo and st.button("Identify plant", type="primary", use_container_width=True):
        with st.spinner("Checking PlantNet..."):
            try:
                identify_uploaded_photos([uploaded_photo], organs=["auto"])
            except PlantNetClientError as error:
                show_safe_error(str(error))
                return
            except Exception as error:  # noqa: BLE001 - show sanitized user-facing errors only
                show_safe_error("The photo could not be identified right now. Please try again.")
                return

    candidates = st.session_state.get("candidates", [])
    if not candidates:
        return

    top_candidate = candidates[0]
    show_candidate(top_candidate, exact_species_threshold=EXACT_SPECIES_CONFIDENCE)
    show_confidence_guidance(top_candidate.score)
    show_alternatives(candidates)

    notes = st.text_input("Optional notes")
    verdict = verdict_buttons()
    if verdict:
        try:
            save_verdict(verdict, notes)
        except Exception as error:  # noqa: BLE001 - storage errors are sanitized before display
            show_safe_error("The evaluation could not be saved right now.")
            return
        if verdict == "incorrect":
            st.session_state.needs_second_photo = True

    if st.session_state.get("saved") and st.session_state.get("needs_second_photo"):
        st.success("Saved. Add another photo below to try again with more evidence.")
    elif st.session_state.get("saved"):
        st.success("Saved. Take the next photo when ready.")

    if st.session_state.get("needs_second_photo"):
        show_second_photo_prompt(uploaded_photo)


def show_confidence_guidance(score: float) -> None:
    """Explain whether the current PlantNet result is strong enough."""

    if score >= EXACT_SPECIES_CONFIDENCE:
        st.success("Confidence is high enough to use this as an exact species match.")
    elif score < SECOND_PHOTO_CONFIDENCE:
        st.warning(
            "Confidence is low. A second close-up can improve the identification, especially a sharp flower photo if the plant is flowering."
        )
    else:
        st.info("This is a plausible match, but not strong enough to treat as a confirmed exact species.")


def show_second_photo_prompt(primary_photo) -> None:
    """Ask for another image when the current result is weak or marked incorrect."""

    st.markdown("**Add another photo of the same plant**")
    st.caption(
        "Use the most identifiable part you can see: flower first, then fruit, leaf detail, bark, or the overall plant."
    )
    second_photo = st.camera_input("Take a close-up identification photo", key="second_camera")
    if second_photo is None:
        second_photo = st.file_uploader(
            "Or upload a second close-up photo",
            type=("jpg", "jpeg", "png"),
            key="second_upload",
        )
    organ = st.selectbox("What does the second photo show?", SECOND_PHOTO_ORGANS)
    if not second_photo:
        return

    if st.button("Identify again with both photos", type="primary", use_container_width=True):
        if primary_photo is None:
            show_safe_error("Please keep or retake the first plant photo before identifying again.")
            return
        with st.spinner("Checking PlantNet with both photos..."):
            try:
                identify_uploaded_photos([primary_photo, second_photo], organs=["auto", organ])
            except PlantNetClientError as error:
                show_safe_error(str(error))
                return
            except Exception:  # noqa: BLE001 - show sanitized user-facing errors only
                show_safe_error("The photos could not be identified right now. Please try again.")
                return


if __name__ == "__main__":
    main()
