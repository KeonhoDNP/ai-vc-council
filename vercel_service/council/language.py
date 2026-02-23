"""Language detection helpers for input-driven response localization."""

from __future__ import annotations

import re


_SUPPORTED = {"auto", "en", "ko"}


def _hangul_count(text: str) -> int:
    return len(re.findall(r"[가-힣]", text))


def detect_primary_language(text: str) -> str:
    """Return 'ko' when Korean dominates, otherwise 'en'."""
    sample = text[:80_000]
    if not sample.strip():
        return "en"

    hangul = _hangul_count(sample)
    non_space = max(1, len(re.sub(r"\s+", "", sample)))
    ratio = hangul / non_space

    # Require a minimum Korean character count plus small density threshold.
    # This catches short Korean summaries while avoiding accidental flips.
    if hangul >= 8 and ratio >= 0.01:
        return "ko"
    return "en"


def resolve_output_language(preference: str, startup_context: str) -> str:
    pref = (preference or "auto").strip().lower()
    if pref not in _SUPPORTED:
        pref = "auto"

    if pref == "auto":
        return detect_primary_language(startup_context)
    return pref


def output_language_label(lang: str) -> str:
    if lang == "ko":
        return "Korean"
    return "English"
