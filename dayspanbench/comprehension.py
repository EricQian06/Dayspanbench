"""Deterministic comprehension of applicant-submitted credential material.

The strict admission check (typed equivalence between the field value and the
attested value) is the first layer. When it fails, the recipient reads what the
applicant actually wrote: a human rarely submits a bare boolean or code — they
quote the confirmation letter, cite its evidence id, or restate its substance
in prose. This module extracts what the material says and matches it against
engine-issued, agent-visible evidence. Pure rules, no model calls: replaying an
episode yields the same decisions.

Every layer requires a valid, visible attestation as its anchor; prose alone,
without a matching issued evidence, never admits.
"""

import re

from .scoring import evidence_matches, equivalent, text_key

EVIDENCE_ID = re.compile(r"EV-\d{4}", re.IGNORECASE)
# Quantity inside prose: number immediately followed by an optional unit run.
QUANTITY = re.compile(r"([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*([A-Za-z一-鿿%]{0,6})")
# Affirmative predicates and the negation markers that can flip them.
AFFIRMATIVE = ("获准", "批准", "同意", "许可", "准予", "准许", "允许", "确认", "包含", "通过", "可行", "approved", "allowed", "confirmed")
NEGATIVE = ("未", "不", "没", "无", "非", "not")


def _as_text(value):
    """Coerce any field value into prose the comprehension layers can read."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value if isinstance(value, str) else str(value)


def _quoted_fact_text(material_keyed, evidence):
    """Layer 2: the material quotes a substantial contiguous piece of the
    attestation's own wording (whitespace/case-insensitive)."""
    fact_keyed = text_key(evidence["text"])
    if not fact_keyed:
        return False
    threshold = max(8, len(fact_keyed) // 3)
    if len(fact_keyed) < threshold:  # very short attestations quote whole
        return fact_keyed in material_keyed
    # Longest common substring by DP; both strings are short paragraphs.
    rows = len(fact_keyed)
    best = 0
    previous = [0] * (len(material_keyed) + 1)
    for i in range(1, rows + 1):
        current = [0] * (len(material_keyed) + 1)
        ch = fact_keyed[i - 1]
        for j in range(1, len(material_keyed) + 1):
            if ch == material_keyed[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
        previous = current
    return best >= threshold


def _restated_value(material, material_keyed, evidence, normalization):
    """Layer 3: the material restates the attested value in its own words."""
    kind = normalization.get("type", "text")
    value = evidence["value"]
    if kind == "boolean":
        # Any affirmative occurrence whose polarity matches the attested value.
        words = "|".join(re.escape(w) for w in AFFIRMATIVE)
        for match in re.finditer(words, material_keyed):
            prefix = material_keyed[max(0, match.start() - 3):match.start()]
            polarity = not any(n in prefix for n in NEGATIVE if n.strip())
            if polarity == value:
                return True
        return False
    if kind == "number":
        for number, unit in QUANTITY.findall(material):
            candidates = [number]
            if unit:
                candidates.append({"value": number, "unit": unit})
            for candidate in candidates:
                if equivalent(candidate, value, normalization):
                    return True
        return False
    # text / date / datetime: the canonical spelling appears inside the prose.
    return text_key(str(value)) in material_keyed


def _restates(field_value, material, material_keyed, evidence, normalization):
    """Does this material correctly convey what the evidence attests?"""
    # Layer 0: strict typed equivalence with the structured field value.
    if field_value is not None and field_value != "" and equivalent(field_value, evidence["value"], normalization):
        return True
    if not material_keyed:
        return False
    # Layer 1: the applicant cites the evidence id they received.
    cited = {token.casefold() for token in EVIDENCE_ID.findall(material)}
    if evidence["id"].casefold() in cited:
        return True
    # An English negation such as "not approved" shares a long substring
    # with "approved". Check its polarity before accepting a partial quote.
    if normalization.get("type") == "boolean":
        words = "|".join(re.escape(w) for w in AFFIRMATIVE)
        polarities = [not any(n in material_keyed[max(0, m.start()-3):m.start()]
                             for n in NEGATIVE)
                      for m in re.finditer(words, material_keyed)]
        if polarities and evidence["value"] not in polarities:
            return False
    # Layer 2: the applicant quotes the attestation's own wording.
    if _quoted_fact_text(material_keyed, evidence):
        return True
    # Layer 3: the applicant restates the attested value in prose.
    try:
        return _restated_value(material, material_keyed, evidence, normalization)
    except (ValueError, TypeError):
        return False


def understood_evidence(field_value, correspondence, requirement, evidence_pool, now):
    """Evidence ids whose attested content the submitted material conveys.

    field_value: the structured value the applicant supplied for the field.
    correspondence: the applicant's message texts on this case (prose quotes).
    Only evidence matching the requirement (attributes, authority, visibility,
    validity) is considered; absent that anchor nothing is understood.
    """
    material = "\n".join([_as_text(field_value), *correspondence])
    material_keyed = text_key(material) if material else ""
    hits = []
    normalization = requirement.get("normalization") or {}
    for evidence in evidence_pool.values():
        if not evidence_matches(evidence, requirement, now):
            continue
        if _restates(field_value, material, material_keyed, evidence, normalization):
            hits.append(evidence["id"])
    return hits
