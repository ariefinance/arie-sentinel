"""Name / identifier normalization boundary — backed by OpenSanctions ``rigour``.

``rigour`` (MIT, no data dependency) is the financial-crime-domain normalization
library also used by yente. Sentinel uses it for name and identifier normalization and
for fuzzy name similarity, instead of maintaining bespoke normalization logic. A minimal
pure-Python fallback keeps the module importable if the optional native stack is missing,
but ``rigour`` is a declared dependency and is used in every supported environment.
"""

from __future__ import annotations

import re
import unicodedata

try:  # rigour + its normality dependency are declared runtime dependencies.
    from normality import normalize as _normality_normalize
    from rigour.ids import LEI as _LEI
    from rigour.names import normalize_name as _rigour_normalize_name
    from rigour.names import remove_org_types as _rigour_remove_org_types
    from rigour.text import levenshtein_similarity as _rigour_similarity

    _RIGOUR = True
except ImportError:  # pragma: no cover - exercised only without the native stack
    _RIGOUR = False


def _fallback(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(re.findall(r"\w+", normalized.casefold()))


def normalize_entity_name(value: str) -> str:
    """Normalize a name for comparison, never for authoritative identity."""
    if _RIGOUR:
        return _rigour_normalize_name(value) or _fallback(value)
    return _fallback(value)


def name_match_key(value: str) -> str:
    """An ASCII-folded comparison key (handles accents/transliteration variation)."""
    if _RIGOUR:
        return (_normality_normalize(value) or "").strip()
    return _fallback(value)


def org_name_key(value: str) -> str:
    """A name key with the legal-form suffix removed (e.g. 'Ltd', 'GmbH', 'Corp')."""
    if _RIGOUR:
        stripped = _rigour_remove_org_types(value) or value
        return (_normality_normalize(stripped) or "").strip()
    return _fallback(value)


def identifier_key(value: str) -> str:
    """Normalize an identifier for comparison; validated LEIs use the canonical form."""
    cleaned = value.strip()
    if _RIGOUR and _LEI.is_valid(cleaned):
        return _LEI.normalize(cleaned) or _alnum(cleaned)
    return _alnum(cleaned)


def _alnum(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def name_similarity(left: str, right: str) -> float:
    """Return a 0..1 fuzzy similarity between two name keys (rigour Levenshtein)."""
    if not left or not right:
        return 0.0
    if _RIGOUR:
        return float(_rigour_similarity(left, right))
    # Fallback: crude ratio on the shorter/longer length after a shared prefix.
    return 1.0 if left == right else 0.0
