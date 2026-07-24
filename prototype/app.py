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
EXCEPTION_GENERA = {"rosa", "hydrangea", "clematis", "rhododendron"}
DISAMBIGUATION_FLOWS = {
    "rosa": {
        "title": "Help us choose the right rose group",
        "steps": {
            "habit": {
                "question": "Which best describes the plant?",
                "options": (
                    ("climbing", "Climbs / scrambles", "Grows on a wall, arch, trellis, or other support.", "climbing_pattern"),
                    ("groundcover", "Groundcover Rose", "Trails or spreads along the ground.", None),
                    ("patio", "Patio / Miniature Rose", "Stays compact, usually under about 45cm.", None),
                    ("bush", "Upright bush", "A freestanding rose bush.", "bush_pattern"),
                ),
            },
            "climbing_pattern": {
                "question": "How does it flower?",
                "options": (
                    ("rambler", "Rambler Rose", "One big early flush, long flexible canes, small clustered blooms.", None),
                    ("climbing", "Climbing Rose", "Repeat flowers through summer, stiffer canes, larger blooms.", None),
                ),
            },
            "bush_pattern": {
                "question": "How does it flower?",
                "options": (
                    ("single_flush", "Shrub Rose - Single Flush", "Flowers once in a big flush.", None),
                    ("repeat", "Repeat flowers through summer", "Blooms repeatedly through summer.", "bloom_style"),
                ),
            },
            "bloom_style": {
                "question": "Which bloom style fits best?",
                "options": (
                    ("hybrid_tea", "Hybrid Tea Rose", "One large bloom per stem.", None),
                    ("repeat_shrub", "Repeat Flowering Shrub Rose", "Clusters of smaller blooms.", None),
                ),
            },
        },
    },
    "hydrangea": {
        "title": "Help us choose the right hydrangea group",
        "steps": {
            "habit": {
                "question": "Which best describes the plant?",
                "options": (
                    ("petiolaris", "Vigorous Climber", "Climbs a wall or trellis and self-clings.", None),
                    ("shrub", "Free-standing shrub", "Grows as a bush rather than a climber.", "flower_shape"),
                ),
            },
            "flower_shape": {
                "question": "What shape are the flower heads?",
                "options": (
                    ("paniculata", "New-wood shrub group", "Cone-shaped or pointed panicle flower heads.", None),
                    ("round_flat", "Round ball or flat lacecap", "Mophead, ball-shaped, or lacecap flowers.", "old_or_new_wood"),
                ),
            },
            "old_or_new_wood": {
                "question": "Which matches best?",
                "options": (
                    ("macrophylla", "Old-wood shrub group", "Buds already visible on stems in spring, including lacecap types.", None),
                    ("arborescens", "New-wood shrub group", "Stems look bare or cut back in spring, like Annabelle types.", None),
                ),
            },
        },
    },
    "clematis": {
        "title": "Help us choose the right clematis group",
        "steps": {
            "flowering_time": {
                "question": "When does it flower?",
                "options": (
                    ("group_1", "Clematis Group 1", "Late winter to spring, often smaller nodding flowers.", None),
                    ("group_2", "Clematis Group 2", "Late spring or early summer, possibly with a second flush later.", None),
                    ("group_3", "Clematis Group 3", "Mid-summer through autumn only.", None),
                    ("unknown", "Clematis - unknown flowering time", "Not sure or have not seen it bloom yet.", None),
                ),
            },
        },
    },
    "rhododendron": {
        "title": "Help us choose the right rhododendron group",
        "steps": {
            "leaf_type": {
                "question": "Which best describes it?",
                "options": (
                    ("evergreen", "Evergreen Rhododendron / Azalea group", "Keeps leaves through winter.", None),
                    ("deciduous", "Deciduous Azalea group", "Drops leaves in winter.", None),
                ),
            },
        },
    },
}

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


def save_disambiguation_choice(group_label: str) -> None:
    """Save a card-flow resolution for an exception genus."""

    save_verdict(
        "genus_correct_species_incorrect",
        notes=f"Resolved through exception-genus card flow: {group_label}",
        selected_species=group_label,
    )
    st.session_state.disambiguation = None


def reset_judgement_flow() -> None:
    """Clear branch state before a fresh PlantNet identification."""

    st.session_state.saved = False
    st.session_state.needs_second_photo = False
    st.session_state.identification_attempt = "first"
    st.session_state.low_confidence_first_photo = False
    st.session_state.disambiguation = None


def start_disambiguation_if_needed() -> bool:
    """Start a card flow for exception genera and return whether one started."""

    candidates = st.session_state.get("candidates") or []
    if not candidates:
        return False
    genus_key = candidates[0].genus.strip().lower()
    if genus_key not in EXCEPTION_GENERA:
        return False
    first_step = next(iter(DISAMBIGUATION_FLOWS[genus_key]["steps"]))
    st.session_state.disambiguation = {"genus": genus_key, "step": first_step}
    return True


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

    if st.session_state.get("disambiguation"):
        show_disambiguation_flow()
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
                if start_disambiguation_if_needed():
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
                start_disambiguation_if_needed()
                st.rerun()
            except PlantNetClientError as error:
                show_safe_error(str(error))
                return
            except Exception:  # noqa: BLE001 - show sanitized user-facing errors only
                show_safe_error("The photos could not be identified right now. Please try again.")
                return


def show_disambiguation_flow() -> None:
    """Render card-style questions for exception genera."""

    flow_state = st.session_state.get("disambiguation") or {}
    genus_key = flow_state.get("genus")
    step_key = flow_state.get("step")
    flow = DISAMBIGUATION_FLOWS.get(genus_key or "")
    if not flow or step_key not in flow["steps"]:
        st.session_state.disambiguation = None
        show_safe_error("The plant could not be resolved right now. Please try again.")
        return

    top = st.session_state.candidates[0]
    st.subheader(flow["title"])
    st.caption(
        f"PlantNet suggested {top.genus} with {top.genus_score:.0%} genus confidence. "
        "Choose the card that best matches what you can see."
    )
    step = flow["steps"][step_key]
    st.markdown(f"**{step['question']}**")

    for value, label, descriptor, next_step in step["options"]:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.caption(descriptor)
            if st.button("Choose this", key=f"{genus_key}_{step_key}_{value}", use_container_width=True):
                if next_step:
                    st.session_state.disambiguation = {"genus": genus_key, "step": next_step}
                    st.rerun()
                try:
                    save_disambiguation_choice(label)
                except EvaluationStoreError:
                    show_safe_error("The evaluation could not be saved right now.")
                    return
                except Exception:  # noqa: BLE001 - unexpected storage errors are sanitized before display
                    show_safe_error("The evaluation could not be saved right now.")
                    return
                st.success("Saved. Take the next photo when ready.")
                return


if __name__ == "__main__":
    main()
