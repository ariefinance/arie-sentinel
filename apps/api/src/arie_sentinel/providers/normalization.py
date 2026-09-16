"""Sentinel-owned normalization boundary, enhanced by rigour when installed."""

import re
import unicodedata

try:
    from rigour.names.tokenize import normalize_name as _rigour_normalize
except ImportError:  # ICU-backed optional extra is not required for local development.
    _rigour_normalize = None


def normalize_entity_name(value: str) -> str:
    """Normalize a name for comparison, never for authoritative identity."""
    if _rigour_normalize is not None:
        return _rigour_normalize(value) or value.strip().casefold()
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"\w+", normalized))
