"""Streamlit phone prototype for PlantNet species evaluation.

Run with `streamlit run prototype/app.py`. The app lets a user take or upload a
plant photo, sends the temporary image to PlantNet, shows species-level evidence,
asks whether the genus and exact species are right, and saves only judgement
data. User photos are discarded after the PlantNet call.
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
from prototype.evaluation_store import EvaluationStoreError, append_evaluation
from prototype.matching import match_guesses_to_catalogue
from prototype.models import EvaluationRecord
from prototype.plantnet_client import PlantNetClientError, identify_plantnet_guesses
from prototype.settings import configure_environment_from_secrets, secret
from prototype.ui import show_candidate, verdict_buttons


CONFIDENCE_THRESHOLD = 0.50
SECOND_PHOTO_ORGANS = ("flower", "leaf", "fruit", "bark", "auto")

st.set_page_config(page_title="Dear Garden Plant ID Prototype", page_icon="DG", layout="centered")
configure_environment_from_secrets()


@st.cache_data(show_spinner="Loading Dear Garden catalogue...")
def cached_catalogue():
    """Load catalogue once per Streamlit session."""

    return load_dear_garden_catalogue()


def identify_uploaded_photo(uploaded_photo, organ: str = "auto") -> None:
    """Run PlantNet and store candidates in session state."""

    with ExitStack() as stack:
        image_path = stack.enter_context(temporary_image_file(uploaded_photo, suffix=image_suffix(uploaded_photo)))
        guesses = identify_plantnet_guesses(
            [image_path],
            api_key=secret("PLANTNET_API_KEY"),
            organs=[organ],
        )
    candidates = match_guesses_to_catalogue(guesses, cached_catalogue())
    if not candidates:
        raise RuntimeError("No plant suggestions were returned for this image.")
    st.session_state.test_id = uuid4().hex
    st.session_state.candidates = candidates
    st.session_state.needs_second_photo = False
    st.session_state.saved = False


def save_verdict(verdict: str, notes: str, selected_species: str = "") -> None:
    """Save the evaluator's judgement for the current top candidate."""

    top = st.session_state.candidates[0]
    alternatives = tuple(candidate.genus for candidate in st.session_state.candidates[1:])
    append_evaluation(
        EvaluationRecord(
            test_id=st.session_state.test_id,
            verdict=verdict,
            suggested_genus=top.genus,
            suggested_species=top.scientific_name,
            plantnet_genus_score=top.genus_score,
            plantnet_species_score=top.score,
            plantnet_scientific_name=top.scientific_name,
            plantnet_common_name=top.common_name,
            alternative_genera=alternatives,
            selected_species=selected_species,
            notes=notes,
        )
    )
    st.session_state.saved = True


def reset_judgement_flow() -> None:
    """Clear branch state before a fresh PlantNet identification."""

    st.session_state.saved = False
    st.session_state.needs_second_photo = False
    st.session_state.identification_attempt = "first"
    st.session_state.low_confidence_first_photo = False


def show_safe_error(message: str) -> None:
    """Display only fixed, secret-free messages in the public app."""

    st.error(message)


def main() -> None:
    """Render the app."""

    st.title("Dear Garden Plant ID Prototype")
    st.caption("Take a clear plant photo, then check whether the genus and exact species look right.")

    if st.session_state.get("needs_second_photo"):
        show_second_photo_prompt()
        return

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
                reset_judgement_flow()
                identify_uploaded_photo(uploaded_photo)
                if st.session_state.candidates[0].genus_score < CONFIDENCE_THRESHOLD:
                    st.session_state.needs_second_photo = True
                    st.session_state.low_confidence_first_photo = True
                    st.rerun()
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
    show_candidate(top_candidate, confidence_threshold=CONFIDENCE_THRESHOLD)

    notes = st.text_input("Optional notes")
    st.markdown("**Is this correct?**")
    verdict = verdict_buttons()
    if verdict:
        if verdict == "both_correct":
            try:
                save_verdict(verdict, notes, selected_species=top_candidate.scientific_name)
            except EvaluationStoreError:
                show_safe_error("The evaluation could not be saved right now.")
                return
            except Exception:  # noqa: BLE001 - unexpected storage errors are sanitized before display
                show_safe_error("The evaluation could not be saved right now.")
                return
            st.session_state.needs_second_photo = False
        elif verdict == "genus_correct_species_incorrect":
            try:
                save_verdict(verdict, notes)
            except EvaluationStoreError:
                show_safe_error("The evaluation could not be saved right now.")
                return
            except Exception:  # noqa: BLE001 - unexpected storage errors are sanitized before display
                show_safe_error("The evaluation could not be saved right now.")
                return
            st.session_state.needs_second_photo = False
        else:
            if st.session_state.get("identification_attempt") == "second":
                try:
                    save_verdict(verdict, notes)
                except EvaluationStoreError:
                    show_safe_error("The evaluation could not be saved right now.")
                    return
                except Exception:  # noqa: BLE001 - unexpected storage errors are sanitized before display
                    show_safe_error("The evaluation could not be saved right now.")
                    return
                st.session_state.needs_second_photo = False
            else:
                st.session_state.needs_second_photo = True
                st.session_state.saved = False
                st.rerun()

    if st.session_state.get("saved") and not st.session_state.get("needs_second_photo"):
        st.success("Saved. Take the next photo when ready.")


def show_second_photo_prompt() -> None:
    """Ask for another image when the current result is weak or marked incorrect."""

    if st.session_state.get("low_confidence_first_photo"):
        st.warning("Sorry, we are not very confident with this photo.")
    st.markdown("**Take another photo of the same plant**")
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

    if st.button("Identify again with this photo", type="primary", use_container_width=True):
        with st.spinner("Checking PlantNet with the new photo..."):
            try:
                st.session_state.low_confidence_first_photo = False
                st.session_state.saved = False
                st.session_state.needs_second_photo = False
                identify_uploaded_photo(second_photo, organ=organ)
                st.session_state.identification_attempt = "second"
                st.rerun()
            except PlantNetClientError as error:
                show_safe_error(str(error))
                return
            except Exception:  # noqa: BLE001 - show sanitized user-facing errors only
                show_safe_error("The photos could not be identified right now. Please try again.")
                return


if __name__ == "__main__":
    main()
