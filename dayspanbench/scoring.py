"""v0.5 outcome scoring: deterministic process anchors + judge subparts.

The LLM judge is the primary score (milestone 3): each task's authored
``judge_criteria`` are graded against the agent's natural-language final
summary. This module contributes only the deterministic layer:

- ``evaluate(env, answer)`` checks process anchors: the answer object shape
  ({"conclusion": str, "summary": str}), the conclusion label, form/selection
  outcomes recorded in the audit, whether the key receipt elements appear
  (literally or lightly normalized) in the summary, and the pending-process
  state for deadline-blocked tasks. These never decide success on their own
  for judged tasks; they feed ``deterministic_anchors_ok`` and the legacy
  alias fields.
- ``score_with_judge(env, review)`` composes the final score from a judge
  review: ``complete`` := all subparts passed AND anchors ok.

Legacy field names (resolved_success, bounded_handling_success, complete,
information_sufficient, required_fact_coverage) are kept as compatibility
aliases so historical report scripts keep working; their semantics are the
v0.5 ones documented above each definition.

The typed-value normalizers (normalize/equivalent) and the admission-time
helpers (evidence_matches/pending_satisfied) stay: the engine's deterministic
comprehension/admission layer still uses them over director fact records.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata

from .calendar import parse, stamp
from .llm import key_tokens, missing_key_tokens

SCORING_VERSION = "0.5.0"


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
    """Only director-registered facts (trusted engine state) reach this."""
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
        if case["state"] not in {"queued", "working", "waiting_internal"} or not case.get("admitted_at") or not case.get("workflow"):
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


# --- deterministic summary anchors -----------------------------------------

def _fact_still_valid(env, record):
    return not record.get("valid_until") or env.now < parse(record["valid_until"])


def anchor_tokens(env):
    """Key elements (ids, numbers, quoted names) the final summary should carry.

    The deterministic anchor set is the *value* of every still-valid,
    agent-visible established fact that a task goal grades on (goals'
    accepted_facts). Only the value is used, never the fact's prose — prose
    carries contextual and distractor numbers (a decoy price breakdown, a
    stale year) that the agent is free to mention or omit; whether the agent
    fell for a decoy is the judge's call, not this check's. Facts and receipts
    outside the graded goals (decoy quotes, contextual certificates) are
    deliberately not anchored for the same reason. Values are stringified
    without json.dumps: added quotes would turn every string value into a
    "quoted name" anchor wholesale. Returns {token: origin} for readable
    check details."""
    graded = set()
    for goal in env.task.get("goals", []):
        graded.update(goal.get("accepted_facts", []))
    tokens = {}
    for fact_id in sorted(graded):
        record = env.director.facts.get(fact_id)
        if not record or not record.get("agent_visible") or not _fact_still_valid(env, record):
            continue
        for token in key_tokens(str(record.get("value"))):
            tokens.setdefault(token, f"fact:{fact_id}")
    return tokens


def token_present(summary, token, summary_tokens=frozenset()):
    """Literal presence with light numeric normalization: thousands grouping
    and surrounding punctuation in the summary do not break an anchor. A token
    that the same tokenizer extracts from the summary (e.g. "15" inside
    "09:00-15:00") also counts: extraction and matching stay symmetric."""
    if not isinstance(summary, str):
        return False
    if not missing_key_tokens(summary, [token]):
        return True
    if token in summary_tokens:
        return True
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", token):
        flat = re.sub(r"[,\s]", "", unicodedata.normalize("NFKC", summary))
        if re.search(r"(?<![0-9a-z_.-])" + re.escape(token) + r"(?![0-9.])", flat):
            return True
        grouped = f"{int(token):,}" if token.isdigit() else None
        if grouped and not missing_key_tokens(summary, [grouped]):
            return True
    return False


def _fact_goals_covered(env, task):
    """How many fact goals have a usable (visible, still valid) accepted fact.
    Informational only: the alias information_sufficient/required_fact_coverage."""
    fact_goals = [g for g in task.get("goals", []) if g.get("status") != "unconfirmed"]
    covered = 0
    for goal in fact_goals:
        for fact_id in goal.get("accepted_facts", []):
            record = env.director.facts.get(fact_id)
            if record and record.get("agent_visible") and _fact_still_valid(env, record):
                covered += 1
                break
    return covered, len(fact_goals)


def evaluate(env, answer):
    """Deterministic process score for one episode. The answer object is the
    v0.5 structure {"conclusion": str, "summary": str}; legacy claims/evidence
    citations are gone. Judge composition happens in score_with_judge."""
    task = env.task
    errors = []
    conclusion = summary = None
    if not isinstance(answer, dict) or set(answer) - {"conclusion", "summary"}:
        errors.append("invalid_answer_object")
    if isinstance(answer, dict):
        conclusion, summary = answer.get("conclusion"), answer.get("summary")
        if not isinstance(conclusion, str) or not conclusion.strip():
            errors.append("invalid_conclusion")
        if not isinstance(summary, str) or not summary.strip():
            errors.append("invalid_summary")
    schema_valid = not errors

    options = task["public"].get("conclusion_options", {}) or {}
    legal_labels = set(options) | set(options.values())
    label_legal = isinstance(conclusion, str) and conclusion in legal_labels
    expected = task.get("expected_conclusion")
    conclusion_correct = (conclusion in (expected, options.get(expected))
                          if expected is not None else label_legal)

    # Form/selection process outcomes straight from the audit: an authored
    # expect is enforced by the engine at processing time; here we only verify
    # nothing the agent started ended rejected or lapsed.
    outcomes = [e for e in env.audit if e["kind"] in ("form_processed", "selection_processed")]
    # Per-channel final state: a rejected submission the agent corrected and
    # re-submitted successfully is fine; a channel that ended with no accepted
    # outcome fails. Lapsed holds are authored traps (the agent must report
    # them), so they are reported but never fail this process anchor.
    channels = {}
    for e in outcomes:
        channel = e.get("form") or e.get("tool") or "<unnamed>"
        channels[channel] = channels.get(channel, False) or bool(e.get("accepted"))
    forms_ok = all(channels.values())
    accepted = sum(1 for e in outcomes if e.get("accepted"))
    expired = sum(1 for e in env.audit if e["kind"] == "selection_expired")

    anchors = anchor_tokens(env)
    summary_tokens = frozenset(key_tokens(summary)) if isinstance(summary, str) else frozenset()
    missing = [t for t in sorted(anchors) if not token_present(summary, t, summary_tokens)]
    summary_anchors_ok = not missing

    # Deadline-blocked tasks: the pending process must have been followed and
    # the clock must have reached the deadline before the verdict was filed.
    pending_goals = [g for g in task.get("goals", []) if g.get("status") == "unconfirmed"]
    pending_ok = all(pending_satisfied(env, goal["pending_condition"]) for goal in pending_goals)
    deadline_ok = (not pending_goals) or env.now >= env.deadline

    covered, fact_goal_count = _fact_goals_covered(env, task)
    anchors_ok = schema_valid and conclusion_correct and forms_ok \
        and summary_anchors_ok and pending_ok and deadline_ok
    criteria = task.get("judge_criteria") or []

    deterministic_checks = {
        "conclusion_label_legal": label_legal,
        "conclusion_correct": conclusion_correct,
        "answer_schema_valid": schema_valid,
        "form_outcomes": {"processed": len(outcomes), "accepted": accepted, "expired_holds": expired},
        "forms_all_accepted": forms_ok,
        "summary_anchor_tokens": len(anchors),
        "summary_anchor_missing": missing,
        "summary_anchors_ok": summary_anchors_ok,
        "pending_process_satisfied": pending_ok,
        "pending_deadline_reached": deadline_ok,
    }
    return {
        "task_id": task["id"],
        "scoring_version": SCORING_VERSION,
        # Until the judge runs (or for tasks without judge_criteria) the score
        # is deterministic-only; score_with_judge upgrades scored_by.
        "scored_by": "deterministic_only" if not criteria else "awaiting_judge",
        "answer_schema_valid": schema_valid,
        "schema_errors": errors,
        "deterministic_checks": deterministic_checks,
        "deterministic_anchors_ok": anchors_ok,
        "subparts_passed": 0,
        "subparts_total": len(criteria),
        "pending_criteria": 0,
        # Legacy aliases (v0.5 semantics):
        # complete := all judge subparts passed AND anchors ok (deterministic
        # phase: anchors only). resolved/bounded split by completion_class.
        "complete": anchors_ok,
        "information_sufficient": covered == fact_goal_count and fact_goal_count > 0
                                  and task["completion_class"] == "resolved",
        "resolved_success": anchors_ok and task["completion_class"] == "resolved",
        "bounded_handling_success": anchors_ok and task["completion_class"] == "bounded_unresolved",
        "required_fact_coverage": round(covered / fact_goal_count, 4) if fact_goal_count else 0,
        "conclusion_correct": conclusion_correct,
        "completion_class": task["completion_class"],
        "calendar_hours": round((env.now - parse(task["start_at"])).total_seconds() / 3600, 2),
        "calendar_days": round((env.now - parse(task["start_at"])).total_seconds() / 86400, 6),
        "agent_messages": env.agent_sends,
        "contacted_actors": len({c["actor"] for c in env.cases.values() if not c["parent"]}),
        "as_of": stamp(env.now),
    }


def score_with_judge(env, review, base=None):
    """Compose the final score from an LLMJudge review
    ({"status": "graded"|"pending"|"skipped", "criteria": [...]}) on top of the
    deterministic evaluate() output. Pending reviews never count as passes and
    are reported explicitly (pending_criteria) so callers can drop the episode
    from pass-rate denominators instead of scoring it as a failure."""
    task = env.task
    base = dict(base if base is not None else evaluate(env, getattr(env, "final_answer", None)))
    criteria = task.get("judge_criteria") or []
    base["subparts_total"] = len(criteria)
    if not criteria or not review or review.get("status") == "skipped":
        base["scored_by"] = "deterministic_only"
        base["subparts_passed"], base["pending_criteria"] = 0, 0
        return base
    verdicts = review.get("criteria", [])
    passed = sum(1 for c in verdicts if c.get("passed") is True)
    pending = sum(1 for c in verdicts if c.get("passed") is None)
    base["subparts_passed"], base["pending_criteria"] = passed, pending
    if review.get("status") == "pending" or pending:
        base["scored_by"] = "judge_pending"
        base["complete"] = False
        base["resolved_success"] = False
        base["bounded_handling_success"] = False
        return base
    base["scored_by"] = "judge"
    all_passed = passed == len(criteria) and len(verdicts) == len(criteria)
    complete = all_passed and base["deterministic_anchors_ok"]
    base["complete"] = complete
    base["resolved_success"] = complete and task["completion_class"] == "resolved"
    base["bounded_handling_success"] = complete and task["completion_class"] == "bounded_unresolved"
    base["information_sufficient"] = all_passed
    base["required_fact_coverage"] = round(passed / len(criteria), 4) if criteria else 0
    return base
