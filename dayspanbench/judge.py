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
- The final answer is the agent's own claim, never proof that the agent did something. When a criterion requires
  the agent to have contacted someone, submitted something, or obtained a written confirmation, that action counts
  only if it actually appears in the trace summary, the agent letters, or the receipts/established facts. If the
  summary asserts a confirmation but no matching receipt/fact was issued and no matching letter was sent, the
  criterion FAILS — absence of the recorded action or artifact is failure, whatever the summary says.
- Every quote must be copied verbatim from the provided material. If you cannot find text to quote for a claim,
  the claim is unsupported.
- Judge exactly the listed criterion ids, one verdict each. Do not add, drop or rename criteria.
- Keep "reason" to one short evidence-based sentence.
- Output only JSON matching the schema. No explanation outside the JSON."""

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

    # -- citation grounding ---------------------------------------------
    # A judge model can pass a criterion by citing actions or artifacts that
    # never happened (observed on trace-based criteria: "the trace shows the
    # agent wrote to X" when no such letter exists). Every passed verdict
    # must carry at least one citation whose quote is actually findable in
    # the graded material; otherwise the verdict is a fabrication and the
    # deterministic layer flips it to failed after one retry.

    @staticmethod
    def _squash(text):
        return " ".join(text.lower().split())

    @classmethod
    def _corpus(cls, view):
        # Everything the judge was shown except the criteria statements
        # themselves: quoting the criterion's own pass_if text back is not
        # evidence, it is the claim restated.
        graded = {k: v for k, v in view.items() if k not in ("criteria", "validation_feedback")}
        return cls._squash(json.dumps(graded, ensure_ascii=False, sort_keys=True))

    @classmethod
    def _quote_found(cls, quote, corpus):
        if not isinstance(quote, str):
            quote = json.dumps(quote, ensure_ascii=False)
        q = cls._squash(quote.strip().strip('"“”'))
        # Short values (booleans, ids, numbers) are treated as found: the
        # threat model is fabricated sentences, not terse values.
        return len(q) < 8 or q in corpus

    @classmethod
    def _ungrounded_ids(cls, verdicts, corpus):
        # World claims only: citations about what the agent did (trace), what
        # the environment issued (receipt/final_state), or evidence the judge
        # synthesized from its own reason. A verdict that cites the agent's
        # final answer (final_answer/tool_result) is judged on that answer's
        # content and may reference it loosely — quoting one's own grading
        # material loosely is benign; inventing world events is not.
        def world_claim(e):
            # judge.reason evidence is the verdict's own paraphrase restated
            # (provider quirk: no evidence array); it is not a quote of the
            # material and cannot be verbatim-verified. Fabrication along
            # that path is caught by the deterministic anchors instead.
            return e.get("source") in ("trace", "receipt", "final_state")

        out = []
        for v in verdicts:
            if not v.get("passed") or not v.get("evidence"):
                continue
            if not all(world_claim(e) for e in v["evidence"]):
                continue
            if not any(cls._quote_found(e.get("quote_or_value"), corpus) for e in v["evidence"]):
                out.append(v["criterion_id"])
        return out

    def _grounding_feedback(self, verdicts, corpus):
        bad = self._ungrounded_ids(verdicts, corpus)
        if not bad:
            return None
        return ("These passed verdicts cite no quote that exists in the provided material: "
                f"{', '.join(bad)}. Re-grade them against the material only, quoting verbatim "
                "from the final answer, receipts, established facts, trace or agent letters. "
                "If the cited action or artifact is absent from the material, the criterion FAILS.")

    def _validated(self, view, criteria_ids):
        current = deepcopy(view)
        corpus = self._corpus(view)
        feedback = None
        for _ in range(self.validation_retries + 1):
            if feedback:
                current["validation_feedback"] = feedback
            result = self.client.complete(purpose="judge", actor_id=view["task_id"],
                                          system=JUDGE_PROMPT, view=current, schema=JUDGE_SCHEMA)
            normalized = self._normalize(result)
            structural = self._check(normalized, criteria_ids)
            grounding = None if structural else \
                self._grounding_feedback(normalized.get("criteria") or [], corpus)
            if structural is None and grounding is None:
                return result
            feedback = structural or grounding
            if self.client.calls:
                self.client.calls[-1]["validation_error"] = feedback
        if structural is not None:
            # Malformed beyond retries: infrastructure-shaped, grade pending.
            raise ValueError(structural)
        # Grounding still failing after retries is the model's fabrication,
        # not an infrastructure fault: flip the ungrounded passes to failed
        # instead of dropping the episode to pending.
        for verdict in normalized.get("criteria") or []:
            if verdict.get("passed") and verdict["criterion_id"] in self._ungrounded_ids(
                    normalized["criteria"], corpus):
                verdict["passed"] = False
                verdict["reason"] = f"Judge citation not found in graded material: {verdict.get('reason', '')}"
                verdict["evidence_unverified"] = True
        return {"criteria": normalized["criteria"]}

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
            if "criterion_id" not in v and "criterion" in v:
                v["criterion_id"] = v.pop("criterion")
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
                              "evidence_unverified": by_id[c["id"]].get("evidence_unverified", False),
                              "reason": by_id[c["id"]]["reason"]} for c in criteria]}
