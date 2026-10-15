"""Post-episode LLM review of the agent's final answer — the primary v0.5 score.

Each judged task carries authored ``judge_criteria``
    [{"id": "R1", "statement": "...", "pass_if": "...",
      "source": "final_answer" | "trace" | "final_state"}]
The judge grades every criterion against a compact, token-bounded view of the
episode: the agent's final answer ({"conclusion", "summary"}), the receipt
artifacts and established facts the environment actually issued, a trace
summary (tool calls, dialogue Q/A, form outcomes) derived from the audit, and
the letters the agent sent. It never sees private goals or hidden facts.

Validation and one retry behave like the simulator. An infrastructure failure
leaves the criteria ``pending`` (passed: null): pending episodes carry
``pending_criteria`` counts and are excluded from pass-rate denominators
upstream — they are never scored as agent failures.
"""

from copy import deepcopy
import json

from .llm import SimulatorError

EVIDENCE_SOURCES = ("tool_result", "trace", "final_state", "final_answer", "receipt")

# Token-control budgets for the judge view.
TRACE_LIMIT = 80        # most recent agent tool calls
DIALOGUE_LIMIT = 30     # most recent dialogue Q/A pairs
LETTER_LIMIT = 20       # most recent letters, each clipped
TEXT_CLIP = 400         # per-entry text clip for trace/receipt entries
LETTER_CLIP = 600

# audit kind -> (tool label, keys worth carrying into the trace summary)
_TRACE_KINDS = {
    "agent_send": ("send_email", ("recipient", "text")),
    "agent_call": ("call", ("recipient", "text")),
    "agent_search_clue": ("web_search", ("query",)),
    "agent_discover_tools": ("discover_tools", ("name", "found")),
    "agent_fetch_document": ("fetch_document", ("url",)),
    "agent_query_case_status": ("query_case_status", ("case_id",)),
    "agent_check_schedule": ("check_schedule", ("contact", "date")),
    "agent_lookup_directory": ("lookup_directory", ("query",)),
    "agent_request_callback": ("request_callback", ("contact",)),
    "agent_leave_note": ("leave_note", ("contact",)),
    "agent_form_submitted": ("form_submitted", ("tool", "form", "accepted")),
    "agent_hidden_status": ("status_query", ("tool", "query")),
    "agent_hidden_record": ("record_lookup", ("tool", "key", "found")),
    "agent_hidden_catalog": ("catalog_search", ("tool", "query")),
    "agent_selection_submitted": ("selection_submitted", ("tool", "entry", "accepted")),
    "agent_selection_status": ("selection_status", ("tool", "query")),
}


def _clip(text, limit=TEXT_CLIP):
    if not isinstance(text, str):
        return text
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


JUDGE_SCHEMA = _object_schema({
    "criteria": {"type": "array", "items": _object_schema({
        "criterion_id": {"type": "string"},
        "passed": {"type": "boolean"},
        "evidence": {"type": "array", "items": _object_schema({
            "source": {"type": "string", "enum": list(EVIDENCE_SOURCES)},
            "pointer": {"type": "string"},
            "quote_or_value": {"type": "string"}})},
        "reason": {"type": "string"}})}})


ANCHOR_SCHEMA = _object_schema({
    "tokens": {"type": "array", "items": _object_schema({
        "token": {"type": "string"},
        "present": {"type": "boolean"},
        "quote": {"type": "string"},
        "reason": {"type": "string"}})}})


JUDGE_PROMPT = """You are an independent reviewer grading ONE completed agent episode in a dialogue benchmark.
You grade only the criteria listed in the view, nothing else. Each criterion is a binary pass/fail claim about
the agent's final answer (or its conduct in the recorded trace, when the criterion says so).

Rules:
- Ground every verdict in the provided material only: the final answer (a conclusion label plus a natural-language
  summary), the receipt artifacts and established facts the environment issued (official written confirmations,
  with numbers, issuers and validity), the trace summary of what the agent did, and the letters the agent sent.
  Never use outside knowledge.
- A criterion fails when the agent's answer asserts something unsupported by the issued material, omits a caveat the
  criterion requires, invents results, misreports numbers/ids/dates, or leaks information the criterion forbids.
- Cite evidence for every verdict: source (tool_result | trace | final_state | final_answer), a pointer (e.g.
  "final_answer.summary", "receipt R-0003", or "letter 3"), and a short verbatim quote or the exact value. No
  verdict without at least one citation; do not invent pointers.
- Judge exactly the listed criterion ids, one verdict each. Do not add, drop or rename criteria.
- Keep "reason" to one short evidence-based sentence.
- Output only JSON matching the schema. No explanation outside the JSON."""


ANCHOR_PROMPT = """You are an independent reviewer checking ONE final summary in a dialogue benchmark.
A deterministic checker could not find certain key elements (numbers, ids, dates, time spans) verbatim in the
summary; you decide whether the summary still carries each element's VALUE in an equivalent presentation.

Rules:
- Ground every verdict in the provided material only: the final answer and, for each missing token, the issued
  fact or receipt value it comes from. Never use outside knowledge.
- Equivalent presentations count: 236.00 USD / USD 236 / 236 (all satisfy 236.0), thousands separators,
  a time range written in prose ("from 12:00 to 13:00" satisfies 12:00-13:00), a date spelled out.
- present=true requires a short verbatim quote from the summary showing the value.
- present=false only when the value is genuinely absent, contradicted, or misreported in the summary.
- Judge exactly the listed missing tokens, one verdict each. Do not add, drop or rename tokens.
- Keep "reason" to one short sentence. Output only JSON matching the schema."""


def build_view(task, env, answer):
    """Compact, token-bounded judge view assembled from the environment state
    and the private audit. Key entries are kept whole or most-recent; long
    texts are clipped so the view stays within a judge context budget."""
    tool_calls, dialogue, form_outcomes = [], [], []
    for event in env.audit:
        kind = event.get("kind")
        if kind in _TRACE_KINDS:
            label, keys = _TRACE_KINDS[kind]
            entry = {"tool": label}
            for key in keys:
                value = event.get(key)
                entry[key] = _clip(value) if key == "text" else value
            tool_calls.append(entry)
        elif kind == "agent_dialogue":
            dialogue.append({"tool": event.get("tool"), "question": _clip(event.get("question")),
                             "answer": _clip(event.get("answer"))})
        elif kind in ("form_processed", "selection_processed"):
            outcome = {"form": event.get("form") or event.get("tool"), "accepted": event.get("accepted")}
            form_outcomes.append(outcome)
    facts = [{"id": record["fact_id"], "text": _clip(record.get("text"), 300),
              "value": deepcopy(record.get("value")), "issuer": record.get("issuer"),
              "issued_at": record.get("issued_at"), "valid_until": record.get("valid_until")}
             for record in env.director.facts.values() if record.get("agent_visible")]
    receipts = [{"receipt_no": r["receipt_no"], "title": r.get("title"), "text": _clip(r.get("text")),
                 "fields": deepcopy(r.get("fields")), "issuer": r.get("issuer"),
                 "issued_at": r.get("issued_at")}
                for r in env.director.receipts]
    return {
        "task_id": task["id"],
        "criteria": [{"id": c["id"], "statement": c["statement"],
                      "pass_if": c.get("pass_if", ""), "source": c.get("source", "final_answer")}
                     for c in task.get("judge_criteria") or []],
        "final_answer": deepcopy(answer) if answer is not None else None,
        "receipts": receipts,
        "established_facts": facts,
        "trace": {"tool_calls": tool_calls[-TRACE_LIMIT:],
                  "dialogue": dialogue[-DIALOGUE_LIMIT:],
                  "form_outcomes": form_outcomes},
        # The letters the agent itself sent, for conduct/redaction criteria
        # that look at the trace rather than the final answer.
        "agent_letters": [_clip(r.get("text"), LETTER_CLIP)
                          for r in env.audit if r.get("kind") == "agent_send"][-LETTER_LIMIT:],
    }


# Judge-side evidence-source aliases: models on lenient gateways invent
# plausible source names ("receipts", "established_facts"); the citation's
# content matters, so unknown sources are coerced instead of invalidating the
# whole grade into pending.
_EVIDENCE_SOURCE_ALIASES = {
    "receipts": "receipt", "receipt": "receipt",
    "established_facts": "trace", "facts": "trace", "director": "trace",
    "summary": "final_answer", "final_summary": "final_answer",
    "answer": "final_answer", "final answer": "final_answer",
    "tool": "tool_result", "tool_call": "tool_result", "tool_result": "tool_result",
    "trace": "trace", "final_state": "final_state", "final_answer": "final_answer",
}


def _normalize_evidence(e):
    if not isinstance(e, dict):
        return e
    out = dict(e)
    source = str(out.get("source", "")).strip().lower()
    out["source"] = _EVIDENCE_SOURCE_ALIASES.get(source, "final_answer")
    return out


class LLMJudge:
    """Wraps a StructuredClient; validates the model's verdict against the
    authored criterion list and retries malformed output like the simulator."""

    def __init__(self, client, *, validation_retries=1):
        if not 0 <= validation_retries <= 3:
            raise ValueError("validation_retries must be 0..3")
        self.client = client
        self.validation_retries = validation_retries

    def _validated(self, view, criteria_ids):
        current = deepcopy(view)
        feedback = None
        for _ in range(self.validation_retries + 1):
            if feedback:
                current["validation_feedback"] = feedback
            result = self.client.complete(purpose="judge", actor_id=view["task_id"],
                                          system=JUDGE_PROMPT, view=current, schema=JUDGE_SCHEMA)
            feedback = self._check(self._normalize(result), criteria_ids)
            if feedback is None:
                return result
            if self.client.calls:
                self.client.calls[-1]["validation_error"] = feedback
        raise ValueError(feedback)

    @staticmethod
    def _normalize(result):
        """Provider-quirk normalization before strict validation: some models
        return the verdict list under a different key ("verdicts"), spell the
        boolean as "pass", or omit the evidence array while citing pointers
        inline in "reason". The verdicts' content is what matters; dropping a
        gradeable episode to pending over key spelling would be an environment
        failure, not an agent failure. Evidence synthesized from "reason" is
        flagged so the audit trail stays honest."""
        if not isinstance(result, dict):
            return result
        verdicts = result.get("criteria")
        if not isinstance(verdicts, list) and isinstance(result.get("verdicts"), list):
            verdicts = result["verdicts"]
        if not isinstance(verdicts, list):
            return result
        normalized = []
        for verdict in verdicts:
            if not isinstance(verdict, dict):
                normalized.append(verdict)
                continue
            v = dict(verdict)
            if "passed" not in v and "pass" in v:
                v["passed"] = v.pop("pass")
            if isinstance(v.get("evidence"), list):
                v["evidence"] = [_normalize_evidence(e) for e in v["evidence"]]
            if not isinstance(v.get("evidence"), list) or not v["evidence"]:
                reason = v.get("reason")
                if isinstance(reason, str) and reason.strip():
                    v["evidence"] = [{"source": "final_answer", "pointer": "judge.reason",
                                      "quote_or_value": reason}]
                    v["evidence_synthesized"] = True
            normalized.append(v)
        return {"criteria": normalized}

    @staticmethod
    def _check(result, criteria_ids):
        verdicts = result.get("criteria")
        if not isinstance(verdicts, list) or len(verdicts) != len(criteria_ids):
            return "Verdicts must cover exactly the listed criteria, one each."
        seen = set()
        for verdict in verdicts:
            if not set(verdict) <= {"criterion_id", "passed", "evidence", "reason", "evidence_synthesized"} \
                    or not {"criterion_id", "passed", "evidence", "reason"} <= set(verdict):
                return "Each verdict has exactly criterion_id, passed, evidence, reason."
            if verdict["criterion_id"] not in criteria_ids or verdict["criterion_id"] in seen:
                return "criterion_id must be one of the listed ids, without duplicates."
            seen.add(verdict["criterion_id"])
            if not isinstance(verdict["passed"], bool):
                return "passed must be a boolean."
            if not verdict["evidence"] or not all(
                set(e) == {"source", "pointer", "quote_or_value"}
                and e["source"] in EVIDENCE_SOURCES for e in verdict["evidence"]):
                return "Every verdict cites at least one {source, pointer, quote_or_value}."
        return None

    def judge(self, task, env, answer):
        """Returns {"status": "graded"|"pending"|"skipped", "criteria": [...]} — never
        raises: an infrastructure failure grades as pending; the caller marks
        the episode's pending criteria count and drops it from pass-rate
        denominators instead of scoring it as a failure."""
        criteria = task.get("judge_criteria") or []
        if not criteria:
            return {"status": "skipped", "criteria": []}
        ids = [c["id"] for c in criteria]
        view = build_view(task, env, answer)
        try:
            result = self._validated(view, ids)
        except (SimulatorError, ValueError):
            return {"status": "pending",
                    "criteria": [{"id": c["id"], "passed": None, "reason": "judge call failed; pending"}
                                 for c in criteria]}
        by_id = {v["criterion_id"]: v for v in self._normalize(result)["criteria"]}
        return {"status": "graded",
                "criteria": [{"id": c["id"], "statement": c["statement"],
                              "passed": by_id[c["id"]]["passed"],
                              "evidence": by_id[c["id"]]["evidence"],
                              "evidence_synthesized": by_id[c["id"]].get("evidence_synthesized", False),
                              "reason": by_id[c["id"]]["reason"]} for c in criteria]}

    # ---- anchor review: value-level equivalence for tokens the literal
    # ---- summary-anchor check could not find (scoring 0.5.1).

    def review_anchors(self, task, env, answer, missing):
        """Second judge pass over anchor tokens the deterministic check marks
        missing from the summary. The literal check is a format-level safety
        net; this review decides whether the summary carries the same VALUE in
        an equivalent presentation (236.00 USD for 236.0, "from 12:00 to
        13:00" for 12:00-13:00). Returns {"status": "graded"|"pending",
        "confirmed": bool, "tokens": [...]}; never raises — an infrastructure
        failure grades as pending and the deterministic verdict stands."""
        from .scoring import anchor_tokens
        if not missing or not isinstance(answer, dict):
            return {"status": "skipped", "confirmed": False, "tokens": []}
        origins = anchor_tokens(env)
        items = []
        for token in missing:
            origin = origins.get(token, "")
            record = None
            if origin.startswith("fact:"):
                record = env.director.facts.get(origin[5:])
            items.append({"token": token,
                          "origin": origin,
                          "fact_value": deepcopy(record.get("value")) if record else None,
                          "fact_text": _clip(record.get("text"), 300) if record else None})
        view = {"task_id": task["id"],
                "final_answer": deepcopy(answer),
                "missing_anchors": items,
                "hint": ("Each missing_anchors entry is a key element (number, id, date or time span) that an "
                         "issued fact or receipt carries and that the final summary should state. Decide per "
                         "token whether the summary carries the same value in an equivalent presentation "
                         "(trailing zeros, currency units, thousands separators, or a time range written in "
                         "prose). Quote the summary passage that carries it; mark present=false only when the "
                         "value is genuinely absent, contradicted, or misreported.")}
        try:
            result = self._validated_anchors(view, list(missing))
        except (SimulatorError, ValueError):
            return {"status": "pending", "confirmed": False,
                    "tokens": [{"token": t, "present": None, "quote": "",
                                "reason": "anchor review call failed; pending"} for t in missing]}
        by_token = {v["token"]: v for v in result["tokens"]}
        tokens = [{"token": t, "present": by_token[t]["present"], "quote": by_token[t]["quote"],
                   "reason": by_token[t]["reason"]} for t in missing]
        return {"status": "graded",
                "confirmed": all(t["present"] is True for t in tokens),
                "tokens": tokens}

    def _validated_anchors(self, view, tokens):
        current = deepcopy(view)
        feedback = None
        for _ in range(self.validation_retries + 1):
            if feedback:
                current["validation_feedback"] = feedback
            result = self.client.complete(purpose="anchor_review", actor_id=view["task_id"],
                                          system=ANCHOR_PROMPT, view=current, schema=ANCHOR_SCHEMA)
            feedback = self._check_anchors(result, tokens)
            if feedback is None:
                return result
            if self.client.calls:
                self.client.calls[-1]["validation_error"] = feedback
        raise ValueError(feedback)

    @staticmethod
    def _check_anchors(result, tokens):
        verdicts = result.get("tokens")
        if not isinstance(verdicts, list) or len(verdicts) != len(tokens):
            return "Verdicts must cover exactly the listed missing tokens, one each."
        seen = set()
        for verdict in verdicts:
            if set(verdict) != {"token", "present", "quote", "reason"}:
                return "Each verdict has exactly token, present, quote, reason."
            if verdict["token"] not in tokens or verdict["token"] in seen:
                return "token must be one of the listed missing tokens, without duplicates."
            seen.add(verdict["token"])
            if not isinstance(verdict["present"], (bool, type(None))):
                return "present must be a boolean."
            if not verdict["quote"] and verdict["present"] is True:
                return "present=true requires a quote from the summary."
        return None
