"""Runtime settings and secret access.

Secrets are read from Streamlit Cloud secrets first, then environment variables
for local development. This module never renders secret values to the page.
"""

from __future__ import annotations

import os

import streamlit as st


SECRET_NAMES = (
    "PLANTNET_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_EVALUATIONS_TABLE",
)


def secret(name: str, default: str | None = None) -> str | None:
    """Read one secret without leaking it through UI text."""

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return str(value) if value else os.environ.get(name, default)


def configure_environment_from_secrets() -> None:
    """Expose Streamlit secrets to lower-level helpers via environment variables."""

    for name in SECRET_NAMES:
        value = secret(name)
        if value and not os.environ.get(name):
            os.environ[name] = value


def supabase_key() -> str | None:
    """Return the configured Supabase key.

    Prefer `SUPABASE_KEY` for the deployed prototype. The other names are kept
    as fallbacks so local experiments do not need duplicate values.
    """

    return (
        secret("SUPABASE_KEY")
        or secret("SUPABASE_ANON_KEY")
        or secret("SUPABASE_SERVICE_ROLE_KEY")
    )


def evaluations_table() -> str:
    """Return the Supabase table used for persisted evaluation labels."""

    return secret("SUPABASE_EVALUATIONS_TABLE", "prototype_evaluations") or "prototype_evaluations"

