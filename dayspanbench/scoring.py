"""Deterministic outcome scoring: typed values, attestation attributes and capabilities."""

from datetime import date
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from .calendar import parse, stamp


def text_key(value):
    if not isinstance(value, str):
        raise ValueError("Expected text")
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


def normalize(value, spec):
    kind = spec.get("type", "text")
    if kind == "boolean":
        if type(value) is bool:
            return value
        key = text_key(value)
        choices = {"true": True, "是": True, "false": False, "否": False}
        if key not in choices:
            raise ValueError("Not a boolean")
        return choices[key]
    if kind == "number":
        if type(value) is bool:
            raise ValueError("Boolean is not a quantity")
        unit, factor = "", Decimal(1)
        if isinstance(value, dict):
            if set(value) != {"value", "unit"}:
                raise ValueError("Quantity requires value and unit")
            unit, value = text_key(value["unit"]), value["value"]
        if isinstance(value, str):
            raw = unicodedata.normalize("NFKC", value).strip()
            match = re.fullmatch(r"([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*([^\d\s]*)", raw)
            if not match:
                raise ValueError("Invalid quantity")
            value = match[1].replace(",", "")
            if match[2]:
                if unit:
                    raise ValueError("Two units")
                unit = text_key(match[2])
        if type(value) is bool:
            raise ValueError("Boolean is not a quantity")
        if unit:
            units = {text_key(k): Decimal(str(v)) for k, v in spec.get("units", {}).items()}
            if unit not in units:
                raise ValueError("Unsupported unit")
            factor = units[unit]
        result = Decimal(str(value)) * factor
        if not result.is_finite():
            raise ValueError("Nonfinite quantity")
        return result
    if kind == "date":
        raw = unicodedata.normalize("NFKC", value).strip()
        match = re.fullmatch(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", raw)
        if not match:
            raise ValueError("Expected calendar date")
        return date(*map(int, match.groups()))
    if kind == "datetime":
        return parse(value)
    if kind == "set":
        if not isinstance(value, list):
            raise ValueError("Expected list")
        normalized = [text_key(v) for v in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate list entry")
        return frozenset(normalized)
    key = text_key(value)
    for canonical, aliases in spec.get("aliases", {}).items():
        if key in {text_key(canonical), *(text_key(alias) for alias in aliases)}:
            return text_key(canonical)
    return key


def equivalent(a, b, spec):
    try:
        return normalize(a, spec) == normalize(b, spec)
    except (ValueError, TypeError, AttributeError, InvalidOperation, OverflowError):
        return False


def evidence_matches(ev, requirement, now, *, visible=True):
    """Only trusted engine-issued attestations can reach this function."""
    if visible and not ev.get("agent_visible"):
        return False
    if parse(ev["issued_at"]) > now or (ev.get("valid_until") and now >= parse(ev["valid_until"])):
        return False
    attrs = ev.get("attributes", {})
    if attrs.get("subject") != requirement["subject"] or attrs.get("predicate") != requirement["predicate"]:
        return False
    return bool(set(ev.get("authorities", [])) & set(requirement["authorities"]))


def pending_satisfied(env, condition):
    for case in env.cases.values():
        if case["state"] not in {"queued", "working", "waiting_internal"} or not case.get("admitted_at"):
            continue
        if condition["capability"] not in case["workflow"].get("capabilities", []):
            continue
        if any(case["fields"].get(k) != v for k, v in condition.get("fields_equal", {}).items()):
            continue
        # Any number of internal relays is valid, as is direct admitted contact.
        root, seen = case, set()
        while root.get("parent") and root["id"] not in seen:
            seen.add(root["id"])
            root = env.cases[root["parent"]]
        if root.get("parent") or root["state"] in {"failed", "needs_information"}:
            continue
        proofs = [env.evidence[e] for e in case.get("admission_evidence", []) if e in env.evidence]
        admitted_at = parse(case["admitted_at"])
        if all(any(evidence_matches(ev, requirement, admitted_at) for ev in proofs)
               for requirement in condition.get("required_evidence", [])):
            return True
    return False


def evaluate(env, answer):
    task = env.task
    claims, errors = {}, []
    if not isinstance(answer, dict) or set(answer) - {"conclusion", "claims"}:
        errors.append("invalid_answer_object")
    answer = answer if isinstance(answer, dict) else {}
    raw = answer.get("claims", [])
    if not isinstance(raw, list):
        errors.append("claims_must_be_list")
        raw = []
    keys = {g["key"] for g in task["goals"]}
    for claim in raw:
        if not isinstance(claim, dict):
            errors.append("invalid_claim")
            continue
        key = claim.get("key")
        if not isinstance(key, str) or key not in keys or key in claims:
            errors.append("unknown_or_duplicate_key")
            continue
        if set(claim) - {"key", "status", "value", "evidence_ids"}:
            errors.append("unknown_claim_field")
        if claim.get("status") not in ("confirmed", "unconfirmed"):
            errors.append("invalid_claim_status")
        if claim.get("status") == "unconfirmed" and (claim.get("value") is not None or claim.get("evidence_ids")):
            errors.append("unconfirmed_claim_must_not_assert_value_or_citations")
        ids = claim.get("evidence_ids", [])
        if not isinstance(ids, list) or any(not isinstance(e, str) for e in ids):
            errors.append("invalid_evidence_ids")
            claim = {**claim, "evidence_ids": []}
        claims[key] = claim
    results, obtained = [], 0
    fact_goals = [g for g in task["goals"] if g.get("status") != "unconfirmed"]
    for goal in task["goals"]:
        claim = claims.get(goal["key"], {})
        reasons = []
        if goal.get("status") == "unconfirmed":
            if claim.get("status") != "unconfirmed":
                reasons.append("must_report_unconfirmed")
            if env.now < env.deadline:
                reasons.append("deadline_not_reached")
            if not pending_satisfied(env, goal["pending_condition"]):
                reasons.append("qualified_pending_process_missing")
        else:
            spec = goal["normalization"]
            valid = [ev for ev in env.evidence.values() if evidence_matches(ev, goal["evidence_requirement"], env.now)]
            # Dynamic identifiers may vary across valid sources or document versions.
            if goal.get("match", "expected") == "expected":
                valid = [ev for ev in valid if equivalent(ev["value"], goal["expected"], spec)]
            obtained += bool(valid)
            cited = [ev for ev in valid if ev["id"] in claim.get("evidence_ids", [])]
            if claim.get("status") != "confirmed":
                reasons.append("must_report_confirmed")
            if not cited:
                reasons.append("no_valid_cited_evidence")
            if not any(equivalent(claim.get("value"), ev["value"], spec) for ev in cited):
                reasons.append("value_not_supported")
        results.append({"key": goal["key"], "passed": not reasons, "reasons": reasons})
    expected = task["expected_conclusion"]
    conclusion_ok = answer.get("conclusion") in (expected, task["public"]["conclusion_options"][expected])
    schema_valid = not errors
    complete = all(g["passed"] for g in results) and conclusion_ok and schema_valid
    return {"task_id": task["id"], "scoring_version": "0.3.0", "complete": complete,
            "information_sufficient": obtained == len(fact_goals) and task["completion_class"] == "resolved",
            "resolved_success": complete and task["completion_class"] == "resolved",
            "bounded_handling_success": complete and task["completion_class"] == "bounded_unresolved",
            "required_fact_coverage": round(obtained / len(fact_goals), 4) if fact_goals else 0,
            "answer_schema_valid": schema_valid, "schema_errors": errors,
            "goal_results": results, "conclusion_correct": conclusion_ok,
            "completion_class": task["completion_class"],
            "calendar_hours": round((env.now-parse(task["start_at"])).total_seconds()/3600, 2),
            "calendar_days": round((env.now-parse(task["start_at"])).total_seconds()/86400, 6),
            "agent_messages": env.agent_sends,
            "contacted_actors": len({c["actor"] for c in env.cases.values() if not c["parent"]}),
            "as_of": stamp(env.now)}
