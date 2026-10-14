"""Author-directed progress state (v0.5): stage tracking, registered facts and receipts.

The DirectorState replaces the retired EV-xxxx evidence ledger. Facts the
environment actually established are registered here under their authored
fact ids (no numbering scheme answers may cite), completion artifacts are
issued as natural-language receipts (R-xxxx is a receipt label only, never a
citation handle), and authored stage definitions advance deterministically
from the audit event stream. Milestone 2's LLM interactors read snapshot()
to know where the episode stands.
"""

from copy import deepcopy

# Achievement conditions an authored stage may declare, mapped to the audit
# event kind(s) that satisfy them and the audit data key carrying the target.
# "tool_call" matches any audit event that records a named tool being invoked:
# actor-side workflow tool calls and the agent's own hidden-tool calls (a
# dialogue question, a form submission, a catalog query, a selection, a status
# check) alike. "form_processed"/"selection_processed" match the deterministic
# completion events (target = form id / select tool name); "fact_registered"
# matches fact issuance (target = fact id). A stage may further declare
# "keywords": then a matching dialogue question must contain one of them, so a
# stage can sit on "the principal was shown the exact plan for approval"
# without firing on every question to the same tool.
STAGE_KINDS = {
    "tool_call": [("tool_call", "tool"),
                  ("agent_dialogue", "tool"),
                  ("agent_form_submitted", "tool"),
                  ("agent_selection_submitted", "tool"),
                  ("agent_selection_status", "tool"),
                  ("agent_hidden_status", "tool"),
                  ("agent_hidden_record", "tool"),
                  ("agent_hidden_catalog", "tool")],
    "form_processed": [("form_processed", "form")],
    "selection_processed": [("selection_processed", "tool")],
    "fact_registered": [("fact_registered", "fact")],
}


class DirectorState:
    """Per-task progress state: authored stages, established facts, receipts."""

    def __init__(self, task=None):
        stages = (task or {}).get("stages", [])
        self.stages = [deepcopy(stage) for stage in stages]
        # Index of the current (not yet achieved) stage in the authored order.
        self.stage_index = 0
        self.achieved_stages = []
        # fact_id -> established-fact record. The record shape stays compatible
        # with the comprehension/scoring layers (id, value, text, issuer,
        # issued_at, valid_until, agent_visible, attributes, authorities) so
        # deterministic admission checks keep working without EV numbering.
        self.facts = {}
        # Receipt artifacts: natural-language vouchers handed to the agent.
        self.receipts = []
        self._receipt_serial = 0

    def register_fact(self, fact_id, value, text, issuer, at,
                      valid_until=None, attributes=None, authorities=None,
                      agent_visible=True):
        """Record an established fact. Re-registering a fact refreshes its
        issuance metadata but never hides an already agent-visible record, and
        attestation authorities accumulate (the fact has genuinely been
        attested by each registering issuer)."""
        existing = self.facts.get(fact_id)
        merged = sorted(set(existing.get("authorities") or []) | set(authorities or [])) \
            if existing else list(authorities or [])
        record = {
            "id": fact_id,
            "fact_id": fact_id,
            "value": deepcopy(value),
            "text": text,
            "issuer": issuer,
            "issued_at": at,
            "valid_until": valid_until,
            "attributes": deepcopy(attributes or {}),
            "authorities": merged,
            "agent_visible": bool(agent_visible) or bool(existing and existing.get("agent_visible")),
        }
        self.facts[fact_id] = record
        return record

    def issue_receipt(self, title, text, fields, issuer, issued_at):
        """Create a receipt artifact. receipt_no (R-xxxx) identifies the
        receipt for the agent's bookkeeping only; it is never a citation
        handle for scoring."""
        self._receipt_serial += 1
        receipt = {
            "receipt_no": f"R-{self._receipt_serial:04d}",
            "title": title,
            "text": text,
            "fields": deepcopy(fields or {}),
            "issuer": issuer,
            "issued_at": issued_at,
        }
        self.receipts.append(deepcopy(receipt))
        return receipt

    def advance(self, audit_event):
        """Advance the current authored stage if the audit event satisfies it.

        Stages advance strictly in the authored order; one event can satisfy
        at most one stage. A stage with "keywords" only fires when the
        triggering event carries a question (a dialogue call) that mentions
        one of them. Returns the achieved stage id, or None."""
        while self.stage_index < len(self.stages):
            stage = self.stages[self.stage_index]
            mapping = STAGE_KINDS.get(stage.get("kind"))
            if mapping is None:
                # Unknown condition kinds never block later stages.
                self.stage_index += 1
                continue
            for event_kind, target_key in mapping:
                if audit_event.get("kind") != event_kind \
                        or audit_event.get(target_key) != stage.get("target"):
                    continue
                keywords = stage.get("keywords")
                if keywords:
                    question = audit_event.get("question")
                    if not isinstance(question, str) \
                            or not any(k.casefold() in question.casefold() for k in keywords):
                        continue
                self.stage_index += 1
                self.achieved_stages.append(stage["id"])
                return stage["id"]
            return None
        return None

    def snapshot(self):
        """Current stage (with its hint), stage progress and established facts,
        for LLM interactors and later scoring milestones."""
        current = self.stages[self.stage_index] if self.stage_index < len(self.stages) else None
        return {
            "current_stage": deepcopy(current),
            "hint": current.get("hint") if current else None,
            "achieved_stages": list(self.achieved_stages),
            "stages": [{"id": s["id"], "kind": s.get("kind"), "target": s.get("target"),
                        "done": index < self.stage_index}
                       for index, s in enumerate(self.stages)],
            "achieved_facts": sorted(self.facts),
            "receipts": deepcopy(self.receipts),
        }
