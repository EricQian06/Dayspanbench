"""Scalar value normalization and equivalence for scenario field matching.

Shared by the engine (workflow admission, form/select accept checks) and the
tool layer (hidden form and select validation). Pure functions, no state.
"""

import re
import unicodedata
from datetime import date

# Unit synonyms for scenario field values: a value written with a different but
# equivalent unit ("8公斤") still describes the user's actual case, so admission
# must not bounce it against the canonical user_fields spelling ("8kg").
UNIT_SYNONYMS = (
    ("kg", ("kg", "公斤", "千克")),
    ("cny", ("cny", "rmb", "元", "人民币")),
    ("g", ("g", "克", "公克")),
    ("km", ("km", "公里", "千米")),
    ("m", ("m", "米", "公尺")),
    ("cm", ("cm", "厘米", "公分")),
)

_UNIT_LOOKUP = {unit: canon for canon, synonyms in UNIT_SYNONYMS for unit in synonyms}


def normalize_field_value(value):
    """Reduce a quantity-like string to (number, canonical unit); None otherwise.

    A bare number ("8") keeps unit None: it still describes the user's case
    ("8kg"), so quantity equivalence treats None as matching any unit.
    """
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKC", value).strip().casefold().replace(" ", "").replace("，", ",")
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([a-z一-鿿,]*)", text)
    if not match:
        return None
    unit = match.group(2)
    if unit == "":
        return (float(match.group(1)), None)
    return (float(match.group(1)), _UNIT_LOOKUP[unit]) if unit in _UNIT_LOOKUP else None


def normalize_field_date(value, default_year):
    """Reduce a date-like string to datetime.date; None otherwise.

    Handles ISO (2026-11-12), slashes, and Chinese spellings (11月12日,
    2026年11月12日); a year-less spelling borrows the reference value's year.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = re.fullmatch(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?", text)
    if not match:
        match = re.fullmatch(r"(\d{1,2})[-/月.](\d{1,2})日?", text)
        if not match:
            return None
        year = default_year
    else:
        year = int(match.group(1))
    try:
        return date(year, int(match.group(2) if match.lastindex == 3 else match.group(1)),
                    int(match.group(3) if match.lastindex == 3 else match.group(2)))
    except ValueError:
        return None


_TEXT_STOPWORDS = {"the", "a", "an", "of", "to", "for", "in", "on", "at", "by",
                   "under", "with", "and", "or", "only", "这", "该", "的"}


def _text_word_set(value):
    """Word multiset of a text with articles/prepositions/fillers dropped."""
    text = unicodedata.normalize("NFKC", value).strip().casefold()
    text = re.sub(r"\.pdf\b", "", text)
    words = re.findall(r"[a-z一-鿿0-9-]+", text)
    return sorted(w for w in words if w not in _TEXT_STOPWORDS)


def field_value_equivalent(value, expected):
    """Exact match, the same quantity written with a synonym or no unit,
    the same date in another common spelling, or the same text with
    articles/prepositions/file extensions spelled differently. An expected
    list accepts any of its entries."""
    if isinstance(expected, list):
        return any(field_value_equivalent(value, item) for item in expected)
    # Number/boolean vs string spelling of the same scalar (310 vs "310",
    # True vs "true") is the same value, not a wrong one.
    if isinstance(value, bool) and isinstance(expected, str):
        return value == {"true": True, "false": False}.get(expected.strip().casefold(), None)
    if isinstance(expected, bool) and isinstance(value, str):
        return expected == {"true": True, "false": False}.get(value.strip().casefold(), None)
    if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and isinstance(expected, str) and normalize_field_value(expected) is not None:
        return normalize_field_value(expected)[0] == float(value)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool) \
            and isinstance(value, str) and normalize_field_value(value) is not None:
        return normalize_field_value(value)[0] == float(expected)
    if value == expected:
        return True
    if not (isinstance(value, str) and isinstance(expected, str)):
        return False
    left = normalize_field_value(value)
    right = normalize_field_value(expected)
    if left is not None and right is not None:
        if left[0] != right[0]:
            return False
        return left[1] is None or right[1] is None or left[1] == right[1]
    year_match = re.match(r"\s*(\d{4})", expected)
    default_year = int(year_match.group(1)) if year_match else None
    left_date = normalize_field_date(value, default_year)
    if left_date is not None and left_date == normalize_field_date(expected, default_year):
        return True
    # Free text: tolerate articles, prepositions, "only" and file extensions
    # ("the landlord" == "landlord", "masked-id-token.pdf" == "masked-id-token")
    # but not genuinely different wording.
    return _text_word_set(value) == _text_word_set(expected)
