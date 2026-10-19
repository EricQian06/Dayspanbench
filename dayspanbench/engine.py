"""Stateful recipients, scoped tools, FIFO workers, handoffs and event scheduling.

This module is trusted environment code. Agents get only AgentTools, never this
object, the task fixtures, the host filesystem, or the private audit log.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, timedelta
import heapq
import json
import re
import random
from pathlib import Path

from .calendar import Calendar, parse, stamp
from .comprehension import understood_evidence
from .director import DirectorState
from .recipient import RuleRecipient
from .scoring import evaluate as evaluate_outcome
from .llm import SimulatorError, key_tokens, missing_key_tokens
from .dialogue import role_state, condition_met
from .values import field_value_equivalent
from . import scheduling
from .tools import EXTRA_TOOLS, HIDDEN_TOOL_KINDS, PUBLIC_TOOLS, TOOL_REGISTRY
from .tools import hidden as hidden_tool_impl
from . import tools as _tools  # noqa: F401  (tool registrations run at import)


TRANSITIONS = {
    "new": {"needs_information", "queued", "failed"},
    "needs_information": {"queued", "failed"},
    "queued": {"working", "failed"},
    "working": {"queued", "waiting_internal", "replied", "failed"},
    "waiting_internal": {"queued", "failed"},
    "replied": set(), "failed": set(),
}

# PUBLIC_TOOLS / EXTRA_TOOLS / HIDDEN_TOOL_KINDS are defined in tools/base.py
# and re-exported here for existing import sites (serve.py, validation.py, tests).

# v0.5 milestone 2, dialogue-mode LLM: the engine injects the canonical fact
# (the matched rule's answer or the authored default); the model contributes
# only the persona's wording and continuity with the prior dialogue.
DIALOGUE_PROMPT = """You are a dialogue participant in a benchmark environment. Answer one Agent question according to persona, in English.
canonical_fact is the authoritative fact determined by the engine. Convey it fully: preserve every number, identifier, and quoted proper name exactly, without omission or modification. Add no facts or commitments beyond canonical_fact.
role_facts contains the information currently available to this role; current_state is the actual processing state. Both take precedence over historical dialogue and Agent speculation. Do not retain outdated incomplete states or describe an application or approval as successfully executed.
You may use prior_dialogue for phrasing, but do not invent forgetfulness or refusal. Base approval on authorization conditions in role_facts and current_state. Do not reject a qualifying plan because of an incorrect historical response, or describe approval as successful execution. Do not mention scoring or internal progress structures.
When matched_topic is false, canonical_fact is a guiding default reply: explain in persona that there is nothing further to add, and optionally invite a different question.
Output only schema-compliant JSON, without explanation or reasoning."""

# v0.5 club cases: understanding delegated to the model, judgment on the
# structured result. The engine never keyword-matches agent prose.
EXTRACT_PROMPT = """You are an environment recipient interpreting one Agent message in a benchmark environment.
Extract only the requested fields from the message (and, where it genuinely helps resolve an ellipsis like "any day is fine", the immediately preceding exchange in history). Each field states its type: boolean, string, or an enum of allowed values.
A boolean is true only when the message explicitly conveys it; absence, hedging, or an unrelated remark is false, never guessed. A string field is the message's own wording (dates as written); use null when the message does not say. An enum value must be one of the allowed values or null.
Extract what the message says, not what would be convenient. Do not infer unstated constraints. Output only schema-compliant JSON with exactly the requested keys, without explanation or reasoning."""


@dataclass
class ActorState:
    spec: dict
    calendar: Calendar
    free_at: object
    recipient: object = None
    inbox: list = field(default_factory=list)
    outbox: list = field(default_factory=list)
    cases: list = field(default_factory=list)
    history: list = field(default_factory=list)
    reservations: list = field(default_factory=list)


class Environment:
    def __init__(self, task: dict, recipient=None, seed=0):
        self.task = deepcopy(task)
        self.now = parse(task["start_at"])
        self.deadline = parse(task["deadline_at"])
        # Seeded pseudo-randomness keeps replay/validate deterministic while
        # agent-initiated handling latencies still vary per step.
        self.rng = random.Random(seed)
        # (min, max) business minutes of reply latency for agent-initiated mail,
        # sized per task: a same-day service desk replies in hours, not seconds.
        self.reply_delay = tuple(task["reply_delay"])
        self.actors = {
            actor["id"]: ActorState(actor, Calendar(task["calendars"][actor["calendar"]]), self.now,
                (recipient.get(actor["id"]) or RuleRecipient()) if isinstance(recipient, dict)
                else (recipient or RuleRecipient()))
            for actor in task["actors"]
        }
        # v0.5 milestone 2: when the episode runs under the LLM simulator, the
        # shared StructuredClient also powers dialogue-mode LLM hidden tools
        # (params.dialogue_mode == "llm"). Under the rule recipient there is
        # no client and dialogue stays in authored keyword mode.
        self.dialogue_client = None
        for state in self.actors.values():
            client = getattr(state.recipient, "client", None)
            if client is not None and hasattr(client, "complete"):
                self.dialogue_client = client
                break
        # Per hidden dialogue tool: the running question/answer history the
        # LLM persona sees, so an NPC can answer from prior interaction.
        self.dialogue_history = {}
        self.known_contacts = set(task["public"]["initial_contacts"])
        # Mailboxes are the addressing surface: an address that belongs to no
        # actor is a black hole that acknowledges delivery and never replies.
        self.email_to_actor = {a["contact_details"]["email"]: a["id"] for a in task["actors"] if "email" in a.get("contact_details", {})}
        self.cases = {}
        # v0.5: the EV-xxxx evidence ledger is gone. Established facts are
        # registered on the director (no citable numbering), and completions
        # hand the agent natural-language receipt artifacts instead.
        self.director = DirectorState(task)
        self.messages = []
        self.audit = []
        self.events = []
        self.serial = 0
        self.case_serial = 0
        self.finished = False
        self.agent_sends = 0
        self.simulator_failure = None
        self.final_answer = None
        # Web pages are not static: scheduled page_update events rewrite page
        # content at authored virtual times, so information the agent already
        # read can go stale and must be re-checked. The update schedule itself
        # is private; the page only carries its own last-updated timestamp.
        self.page_updated_at = {}
        for index, update in enumerate(task.get("page_updates", [])):
            self.enqueue(parse(update["at"]), "page_update", index)
        # Hidden tools: authored per task, never listed in public["tools"]. A
        # tool becomes callable only after discover_tools(name) unlocks it;
        # guessing the exact name is not enough.
        self.hidden_tools = {tool["name"]: deepcopy(tool) for tool in task.get("hidden_tools", [])}
        self.unlocked_tools = set()
        # Web forms declared on public pages, keyed by form id, with the page
        # carrying them and the hidden form tool (if any) that submits them.
        self.forms = {}
        self.form_specs = {}
        for tool in self.hidden_tools.values():
            if tool["kind"] == "form":
                self.form_specs[tool["params"]["form"]] = tool["params"]
        for page in task["public"]["pages"]:
            if "form" in page:
                self.forms[page["form"]["id"]] = (page, page["form"])
        # Form submission records: pending -> processed/rejected at the
        # authored virtual time via a form_processed event. No push channel:
        # the agent must re-visit the page or query the status tool.
        self.form_submissions = {}
        # Catalog inventories (kind="catalog") can be revised during the episode
        # at authored virtual times: rows are added/removed like LATCH's
        # inventory_changed events, so stale quotes a search once showed may
        # no longer be selectable.
        self.catalog_updates = {}
        for tool in self.hidden_tools.values():
            if tool["kind"] == "catalog":
                for index, update in enumerate(tool["params"].get("updates", [])):
                    self.enqueue(parse(update["at"]), "catalog_update", (tool["name"], index))
        # Selections made through kind="select" tools: pending -> processed /
        # rejected at an authored virtual time; an optional hold expiry can
        # cancel an unprocessed selection first.
        self.selections = {}
        # Inbox read high-water mark: everything above it counts as unread.
        self.inbox_read = 0
        # The assisted user (task["interactor"], private): voice of consult_user
        # and the consent gate in front of externally effective agent
        # actions. Attached separately like the recipients so rule-based
        # replay can run without a client.
        # Hidden kind="group" tools: per-group membership state (preview,
        # join requests, read position). Approval is an event, never instant.
        self.group_states = {}
        self.interactor = None

    def attach_interactor(self, interactor):
        if interactor is not None and not hasattr(interactor, "consent"):
            raise ValueError("An interactor needs consent/answer/reply_at")
        self.interactor = interactor

    @classmethod
    def load(cls, path, **kwargs):
        return cls(json.loads(Path(path).read_text()), **kwargs)

    def tools(self):
        return AgentTools(self)

    @property
    def evidence(self):
        """Deprecated compatibility view: established facts keyed by fact id.

        The EV-xxxx ledger is retired; this exposes the director's registered
        facts so the deterministic scoring/judge/reference layers keep running
        until their own milestones. Records carry authored fact ids, never
        citable EV numbers, and agent surfaces receive receipts instead."""
        return self.director.facts

    def record(self, kind, **data):
        self.audit.append({"at": stamp(self.now), "kind": kind, **deepcopy(data)})
        # Authored stage definitions advance deterministically from the audit
        # stream (tool_call / form_processed / fact_registered events).
        self.director.advance(self.audit[-1])

    def transition(self, case, state):
        old = case["state"]
        if state not in TRANSITIONS[old]:
            raise ValueError(f"Illegal case transition {old} -> {state}")
        case["state"] = state
        self.record("transition", case_id=case["id"], actor=case["actor"], old=old, new=state)

    def enqueue(self, at, kind, case_id):
        self.serial += 1
        heapq.heappush(self.events, (at, self.serial, kind, case_id))

    def emit(self, case, text, contacts=None, status="reply", internal_ok=False, receipts=None):
        if case.get("parent") and not internal_ok:
            raise ValueError("Internal cases must complete through handoff return")
        contacts = contacts or []
        receipts = receipts or []
        actor = self.actors[case["actor"]]
        if hasattr(actor.recipient, "render"):
            view = {"actor_id": case["actor"], "name": actor.spec["name"], "role": actor.spec["role"],
                    "persona": actor.spec.get("persona"),
                    "now": stamp(self.now), "case_id": case["id"], "case_state": case["state"],
                    "status": status, "canonical_text": text, "history": deepcopy(actor.history),
                    "stage_hint": self.director.snapshot()["hint"],
                    "contacts": [self.contact(cid) for cid in contacts],
                    "facts": [{k: deepcopy(self.director.facts[f][k]) for k in ("id", "text", "value", "issuer", "valid_until")}
                              for f in dict.fromkeys(case.get("facts", [])) if f in self.director.facts],
                    "receipts": deepcopy(receipts)}
            text = self.recipient_call(actor, "render", view)
        # Contacts are only spoken of in the natural-language text (the sender
        # shares their mailboxes in prose); structured contact cards never ride
        # along. The referral still registers them as discoverable, since
        # otherwise the agent could never follow up on the advice.
        self.known_contacts.update(contacts)
        message = {"id": f"MSG-{len(self.messages)+1:04d}", "at": stamp(self.now),
                   "from": actor.spec["contact_details"]["email"],
                   "case_id": case["id"], "status": status,
                   "channel": "phone" if case.get("origin") == "phone" else "email",
                   "text": text, "receipts": deepcopy(receipts)}
        # Facts stated in a written letter are established as agent-visible.
        for fact_id in case.get("facts", []):
            record = self.director.facts.get(fact_id)
            if record is not None:
                record["agent_visible"] = True
        self.messages.append(message)
        self.actors[case["actor"]].outbox.append(message["id"])
        actor.history.append({"role": "recipient", "text": text, "case_id": case["id"], "at": stamp(self.now)})
        self.record("delivery", message_id=message["id"], case_id=case["id"], status=status)

    def recipient_call(self, actor, method, view):
        try:
            return getattr(actor.recipient, method)(view)
        except SimulatorError as exc:
            self.simulator_failure = str(exc)
            self.finished = True
            self.record("simulator_failure", actor=actor.spec["id"], reason=str(exc))
            raise

    def render_dialogue(self, tool_name, params, question, canonical, matched, role_facts=None):
        """LLM rephrase of an authored dialogue answer (dialogue_mode="llm").
        The engine injects current role-scoped facts, service state and dialogue
        history. Key tokens survive verbatim; one repair retry is followed by
        the canonical answer if the model continues to lose those tokens."""
        history = self.dialogue_history.setdefault(tool_name, [])
        view = {"persona": params.get("persona", "the user"),
                "question": question, "canonical_fact": canonical,
                "matched_topic": matched,
                "prior_dialogue": deepcopy(history[-12:]),
                "stage_hint": None,
                "achieved_stages": [],
                "role_facts": deepcopy(role_facts or []),
                "current_state": role_state(self, params),
                "now": stamp(self.now)}
        schema = {"type": "object", "properties": {"answer": {"type": "string"}},
                  "required": ["answer"], "additionalProperties": False}
        tokens = key_tokens(canonical)
        for attempt in range(2):
            result = self.dialogue_client.complete(
                purpose="dialogue", actor_id=tool_name, system=DIALOGUE_PROMPT,
                view=view, schema=schema)
            answer = result.get("answer") if isinstance(result, dict) else None
            missing = missing_key_tokens(answer, tokens)
            if isinstance(answer, str) and answer.strip() and not missing:
                history.append({"question": question, "answer": answer,
                                "at": stamp(self.now)})
                return answer
            if attempt == 0:
                view = deepcopy(view)
                view["validation_feedback"] = {
                    "previous_answer": answer,
                    "error": "answer is empty or not a string"
                             if not isinstance(answer, str) or not answer.strip()
                             else "answer lost required key tokens: " + ", ".join(missing),
                    "requirements": "answer must be a nonempty string rephrasing canonical_fact while preserving all numbers, identifiers, and quoted proper names exactly."}
        # The persona rephrase is wording only; the canonical fact is
        # engine-determined. Two failed phrasings fall back to the canonical
        # text verbatim — the agent loses no information, so the episode stays
        # valid; the fallback is audited for environment-failure statistics.
        self.record("dialogue_fallback", source=tool_name,
                    reason="persona rephrase failed twice; canonical text used")
        history.append({"question": question, "answer": canonical,
                        "at": stamp(self.now)})
        return canonical

    def extract_fields(self, case, tool):
        """Extract authored fields from the agent's prose for an extract step.

        Structured values already on the case (reference policy or forwarded
        workflow fields) are authoritative. Remaining fields come from one
        LLM pass over the correspondence; on failure or with no client they
        fall back to the type's neutral value (False / None), so authored
        fallback branches match deterministically. Absence is never a
        keyword guess: the agent's exact wording decides nothing by itself.
        """
        spec = tool["extract"]
        extracted = {k: case["fields"][k] for k in spec if k in case["fields"]}
        missing = [k for k in spec if k not in extracted]
        if missing and self.dialogue_client is not None:
            actor = self.actors[case["actor"]]
            view = {"message": case["correspondence"][-1] if case["correspondence"] else "",
                    "history": deepcopy(actor.history[-12:]),
                    "instructions": actor.spec.get("description", ""),
                    "fields": {k: spec[k] for k in missing},
                    "now": stamp(self.now)}
            schema = {"type": "object", "additionalProperties": False,
                      "properties": {k: self._extract_schema(spec[k]) for k in missing},
                      "required": list(missing)}
            try:
                result = self.dialogue_client.complete(
                    purpose="extract", actor_id=case["actor"], system=EXTRACT_PROMPT,
                    view=view, schema=schema)
            except SimulatorError:
                self.record("extract_fallback", case_id=case["id"],
                            reason="LLM extraction failed; neutral defaults used")
                result = None
            if isinstance(result, dict):
                for k in missing:
                    v = self._extract_valid(spec[k], result.get(k))
                    if v is not None:
                        extracted[k] = v
        for k in missing:
            if k not in extracted:
                extracted[k] = False if spec[k].get("type") == "boolean" else None
        return extracted

    @staticmethod
    def _extract_schema(field):
        if field.get("type") == "boolean":
            return {"type": "boolean"}
        values = field.get("values")
        if values:
            return {"type": "string", "enum": values}
        return {"type": ["string", "null"]}

    @staticmethod
    def _extract_valid(field, value):
        if field.get("type") == "boolean":
            return value if isinstance(value, bool) else None
        values = field.get("values")
        if values:
            return value if value in values else None
        return value if isinstance(value, str) and value.strip() else None

    def contact(self, actor_id):
        actor = self.actors[actor_id].spec
        return {"id": actor["id"], "name": actor["name"], "role": actor["role"],
                "contact_details": deepcopy(actor["contact_details"])}

    def admission_at(self, actor):
        return scheduling.admission_at(self, actor)

    def enqueue_admission(self, actor, case_id):
        scheduling.enqueue_admission(self, actor, case_id)

    def new_case(self, actor_id, workflow_id, fields, parent=None, origin=None):
        actor = self.actors[actor_id]
        workflow = next(w for w in actor.spec["workflows"] if w["id"] == workflow_id)
        self.case_serial += 1
        case = {"id": f"CASE-{self.case_serial:04d}", "actor": actor_id, "workflow": deepcopy(workflow),
                "state": "new", "step": 0, "fields": deepcopy(fields), "facts": [],
                "contacts": [], "parent": parent, "origin": origin, "received_at": stamp(self.now),
                "correspondence": []}
        self.cases[case["id"]] = case
        actor.cases.append(case["id"])
        actor.inbox.append({"case_id": case["id"], "from": self.cases[parent]["actor"] if parent else "agent",
                            "fields": deepcopy(fields), "at": stamp(self.now)})
        self.record("case_created", case_id=case["id"], actor=actor_id, parent=parent, origin=origin)
        if origin == "agent" and parent is None:
            # No instant routing: the recipient reads the mail during work hours.
            # Internal handoffs carry no reading delay; the parent step already ran.
            self.enqueue(self.admission_at(actor), "admit", case["id"])
        else:
            self.start(case)
        return case

    def new_unrouted_case(self, actor_id, fields):
        """A delivered mail that matches none of the recipient's workflows.

        It occupies the mailbox like any other mail, is read during work hours,
        and is answered with a referral email instead of entering processing.
        """
        actor = self.actors[actor_id]
        self.case_serial += 1
        case = {"id": f"CASE-{self.case_serial:04d}", "actor": actor_id, "workflow": None,
                "state": "new", "step": 0, "fields": deepcopy(fields), "facts": [],
                "contacts": [], "parent": None, "origin": "agent", "received_at": stamp(self.now)}
        self.cases[case["id"]] = case
        actor.cases.append(case["id"])
        actor.inbox.append({"case_id": case["id"], "from": "agent", "fields": deepcopy(fields), "at": stamp(self.now)})
        self.record("case_created", case_id=case["id"], actor=actor_id, parent=None, origin="agent", routed=False)
        self.enqueue(self.admission_at(actor), "admit", case["id"])
        return case

    def canonicalize_fields(self, fields):
        """Rewrite scenario-field values that differ from user_fields only by a
        synonym unit into the canonical spelling, so a literal quote like
        "8公斤" still admits against the canonical "8kg". Anti-fabrication is
        unaffected: values that do not describe the user's case still mismatch."""
        canonical = {}
        for key, value in (fields or {}).items():
            expected = self.task["public"]["user_fields"].get(key)
            canonical[key] = expected if expected is not None and field_value_equivalent(value, expected) else value
        return canonical

    def referral_names(self, actor):
        """People this actor's own workflows hand requests over to."""
        targets = []
        for tool in actor.spec["tools"].values():
            if tool["kind"] == "refer":
                targets.extend(tool["contacts"])
        return list(dict.fromkeys(targets))

    def contact_mentions(self, actor_ids):
        """Names plus mailboxes in prose: the only channel contact details travel."""
        return ", ".join(f"{self.actors[c].spec['name']} ({self.actors[c].spec['contact_details']['email']})"
                         for c in actor_ids)

    def reply_referral(self, case):
        """Answer a misrouted mail: not my responsibility, contact someone else."""
        actor = self.actors[case["actor"]]
        referred = list(dict.fromkeys(self.referral_names(actor)))
        mentions = self.contact_mentions(referred)
        if mentions:
            body = f"Your request is outside my remit, so I cannot process it directly. Please contact {mentions} for further assistance. "
        else:
            body = 'Your request is outside my remit, so I cannot process it directly. Please find the relevant contact through public channels and write to them.'
        text = f"Hello, I am {actor.spec['name']}. {body} Please write again if you have other questions."
        # The misrouted mail walks the same visible lifecycle as a processed one.
        self.transition(case, "queued")
        self.transition(case, "working")
        self.transition(case, "replied")
        self.emit(case, text, contacts=referred, status="referral")



    def process_form(self, form_id):
        """Flip a submitted web form to its processed/rejected outcome at the
        authored virtual time: publish the result text, register the authored
        facts and issue a receipt artifact, then rewrite the carrying page. The
        agent is never notified; it must re-visit the page or query the status
        tool."""
        submission = self.form_submissions.get(form_id)
        params = self.form_specs.get(form_id)
        if submission is None or params is None or submission["status"] != "pending":
            return
        if submission["accepted"]:
            submission["status"] = "processed"
            submission["result_text"] = params.get("result_text") or 'Your application has been accepted and completed.'
            available = []
            for fact_id in params.get("facts", []):
                fact = self.task["facts"][fact_id]
                # A fact gated behind a later availability simply is not
                # published yet; the outcome text still lands.
                if fact.get("available_at") and self.now < parse(fact["available_at"]):
                    self.record("form_fact_pending", form=form_id, fact=fact_id)
                    continue
                available.append(fact_id)
            if available:
                submission["receipts"].append(self.issue_receipt(
                    params.get("receipt_title") or f"Form {form_id} completion receipt",
                    available, params["issuer"], submission["result_text"],
                    params.get("expect")))
        else:
            submission["status"] = "rejected"
            submission["result_text"] = params.get("reject_text") or 'Your submission does not match the registered information and has been returned. Check and resubmit.'
            # Name the fields that did not match the registered record, so a
            # correct submission is never rejected without a fixable pointer.
            mismatched = submission.get("mismatched") or list((params.get("expect") or {}))
            if mismatched:
                submission["result_text"] += ' Mismatched fields: ' + ", ".join(mismatched) + "."
        update = params.get("page_update")
        if update:
            page = next((p for p in self.task["public"]["pages"] if p["id"] == update["page"]), None)
            if page is not None:
                for key in ("title", "text", "snippet", "contacts", "documents"):
                    if key in update:
                        page[key] = deepcopy(update[key])
                self.page_updated_at[page["url"]] = self.now
                self.record("page_updated", page=update["page"], url=page["url"], cause="form")
        self.record("form_processed", form=form_id, accepted=submission["accepted"],
                    result=submission["result_text"])

    def apply_catalog_update(self, payload):
        """Swap catalog inventory at an authored virtual time (stale quotes,
        sold-out options, refreshed schedules). The update schedule stays
        private; the agent only sees that a previously returned row is gone."""
        tool_name, index = payload
        spec = self.hidden_tools[tool_name]
        update = spec["params"]["updates"][index]
        entries = spec["params"]["entries"]
        removed = set(update.get("remove", []))
        spec["params"]["entries"] = [e for e in entries if e["id"] not in removed] \
            + [deepcopy(e) for e in update.get("add", [])]
        self.record("catalog_updated", tool=tool_name, removed=sorted(removed),
                    added=[e["id"] for e in update.get("add", [])])

    def process_selection(self, tool_name):
        """Complete a pending selection: accepted only if the picked entry
        still satisfies the authored expectations; acceptance registers the
        facts and issues a receipt artifact exactly like a processed form."""
        selection = self.selections.get(tool_name)
        if not selection or selection["status"] != "pending":
            return
        params = selection["params"]
        entry = self._catalog_entry(selection["catalog"], selection["entry"])
        if selection["accepted"] and (entry is None or not self._entry_current(entry)):
            # The option disappeared from inventory between selection and
            # processing: the booking cannot be honored.
            selection["accepted"] = False
        if params.get("complete_before") and self.now >= parse(params["complete_before"]):
            selection["accepted"] = False
        if not condition_met(self, params.get("requires", {})):
            selection["accepted"] = False
        if selection["accepted"]:
            selection["status"] = "processed"
            selection["result_text"] = params.get("result_text") or "Your selection has been confirmed."
            available = []
            for fact_id in params.get("facts", []):
                fact = self.task["facts"][fact_id]
                if fact.get("available_at") and self.now < parse(fact["available_at"]):
                    self.record("selection_fact_pending", tool=tool_name, fact=fact_id)
                    continue
                available.append(fact_id)
            if available:
                selection["receipts"].append(self.issue_receipt(
                    params.get("receipt_title") or f"{tool_name} confirmation receipt",
                    available, params["issuer"], selection["result_text"],
                    params.get("expect")))
        else:
            selection["status"] = "rejected"
            selection["result_text"] = params.get("reject_text") or \
                "The submitted details do not match the current listing; the request was returned."
        update = params.get("page_update")
        if update:
            page = next((p for p in self.task["public"]["pages"] if p["id"] == update["page"]), None)
            if page is not None:
                for key in ("title", "text", "snippet", "contacts", "documents"):
                    if key in update:
                        page[key] = deepcopy(update[key])
                self.page_updated_at[page["url"]] = self.now
                self.record("page_updated", page=update["page"], url=page["url"], cause="selection")
        self.record("selection_processed", tool=tool_name, accepted=selection["accepted"],
                    result=selection["result_text"])

    def start(self, case):
        workflow = case["workflow"]
        # An acceptance window's opening edge only gates the agent's own mail:
        # a request filed before accept_after is answered with a registration-
        # only reply and never enters the queue, so early filing cannot
        # silently reserve a place in a later batch. Internal handoffs are
        # exempt; the parent step already ran inside the window.
        if (workflow.get("accept_after") and not case.get("parent")
                and self.now < parse(workflow["accept_after"])):
            self.transition(case, "queued")
            self.transition(case, "working")
            self.transition(case, "replied")
            self.record("early_reply", case_id=case["id"], actor=case["actor"],
                        accept_after=workflow["accept_after"])
            body = workflow.get("early_reply") or 'Intake for this matter has not opened. Please return later.'
            self.emit(case, f"Hello, I am {self.actors[case['actor']].spec['name']}. {body} Please write again if you have other questions.")
            return
        if workflow.get("accept_before") and self.now >= parse(workflow["accept_before"]):
            self.transition(case, "failed")
            self.complete_failure(case, 'The acceptance deadline for this round has passed; completion on the original schedule is unavailable.')
            return
        missing = [key for key in workflow.get("required_fields", []) if case["fields"].get(key) is None or case["fields"].get(key) == ""]
        # Scenario-specific identifiers must correspond to the user's actual case.
        # Free-form intent remains the recipient adapter's responsibility.
        # Mismatched values get their own feedback sentence: telling the applicant
        # to attach a credential for a value they merely misspelled sends them
        # into an unrecoverable loop (DSB-08 lesson).
        mismatched = []
        for key in workflow.get("required_fields", []):
            expected = self.task["public"]["user_fields"].get(key)
            if key not in missing and expected is not None and case["fields"].get(key) != expected:
                mismatched.append(key)
        admission_evidence = []
        for key, requirement in workflow.get("evidence_fields", {}).items():
            if key in missing or key in mismatched:
                continue
            # The recipient reads what the applicant actually submitted: the
            # structured field value plus the prose of their letters. Quoting
            # the confirmation, citing its evidence id, or restating its
            # substance all convey the credential; the anchor is always an
            # issued, agent-visible attestation.
            obtained = understood_evidence(case["fields"].get(key),
                                           case.get("correspondence") or [],
                                           requirement, self.evidence, self.now)
            admission_evidence.extend(obtained)
            if obtained:
                self.record("material_understood", case_id=case["id"], field=key, evidence=obtained)
            else:
                missing.append(key + '(valid verifiable evidence required first)')
        if missing or mismatched:
            missing += [key + '(does not match task information)' for key in mismatched]
            if case["state"] == "new":
                self.transition(case, "needs_information")
            if case.get("parent"):
                self.transition(case, "failed")
                self.complete_failure(case, 'Internal handoff is missing materials: ' + ", ".join(missing))
            else:
                absent = [item for item in missing if "(" not in item]
                unverifiable = [item.split("(")[0] for item in missing if item.endswith('(valid verifiable evidence required first)')]
                body = 'Your materials are incomplete. Supply the following before we continue: ' + ", ".join(absent) + ". " if absent else ""
                if mismatched:
                    body += 'The supplied ' + ", ".join(mismatched) + ' does not match the registered information. Check and resubmit.'
                if unverifiable:
                    body += 'The supplied ' + ", ".join(unverifiable) + " could not be verified against valid evidence. Resubmit with the other party's original written confirmation or its identifier."
                self.emit(case, f"Hello, I am {self.actors[case['actor']].spec['name']}. {body} Please write again if you have other questions.", status="needs_information")
            return
        case["admitted_at"] = stamp(self.now)
        case["admission_evidence"] = admission_evidence
        keys = workflow.get("deduplicate_by", [])
        if keys and all(case["fields"].get(k) is not None for k in keys):
            for existing in self.cases.values():
                if (existing["id"] == case["id"] or existing["actor"] != case["actor"]
                        or existing.get("linked_to") or not existing.get("workflow")
                        or existing["workflow"]["id"] != workflow["id"]
                        or existing["state"] not in {"queued", "working", "waiting_internal"}):
                    continue
                if (all(existing["fields"].get(k) == case["fields"][k] for k in keys)
                        and all(existing["fields"][k] == v for k, v in case["fields"].items()
                                if k in existing["fields"])):
                    case["linked_to"] = existing["id"]
                    self.transition(case, "queued")
                    self.transition(case, "working")
                    self.transition(case, "waiting_internal")
                    self.record("case_linked", case_id=case["id"], existing=existing["id"])
                    if not case.get("parent"):
                        self.emit(case, 'This matter is already in progress and has been linked to the existing process. A reply will follow completion.',
                                  status="acknowledgement")
                    return
        self.schedule_step(case)

    # Scheduling and ETA projection live in dayspanbench/scheduling.py
    # (JITTER_CEILING, ETA_THRESHOLD, ETA_REVISION_THRESHOLD included);
    # these delegators keep the Environment's method surface unchanged.

    def projected_delay(self, delay, origin):
        return scheduling.projected_delay(self, delay, origin)

    def estimate_completion(self, actor_id, workflow, from_step, now=None, origin=None):
        return scheduling.estimate_completion(self, actor_id, workflow, from_step, now, origin)

    def active_child(self, case, workflow_id):
        return scheduling.active_child(self, case, workflow_id)

    def case_completion(self, case):
        return scheduling.case_completion(self, case)

    def eta_clause(self, case, from_step=None):
        return scheduling.eta_clause(self, case, from_step)

    def notify_eta_slip(self, case):
        scheduling.notify_eta_slip(self, case)

    def jittered_delay(self, case, delay):
        return scheduling.jittered_delay(self, case, delay)

    def schedule_step(self, case):
        scheduling.schedule_step(self, case)

    def reserve_step(self, actor, now, tool, delay, reservations):
        return scheduling.reserve_step(self, actor, now, tool, delay, reservations)

    def register_fact(self, fact_id, issuer_id, agent_visible=True):
        """Establish a fact on the director: no EV numbering, just the authored
        fact id and its record for deterministic checks. Availability is still
        gated exactly like the retired evidence issuance was."""
        fact = self.task["facts"][fact_id]
        if fact.get("available_at") and self.now < parse(fact["available_at"]):
            raise ValueError(f"Fact {fact_id} not yet published")
        record = self.director.register_fact(fact_id, fact["value"], fact["text"], issuer_id,
            stamp(self.now), valid_until=fact.get("valid_until"),
            attributes=fact.get("attributes"),
            authorities=self.actors[issuer_id].spec.get("evidence_authorities"),
            agent_visible=agent_visible)
        self.record("fact_registered", fact=fact_id, issuer=issuer_id)
        return record

    def issue_receipt(self, title, fact_ids, issuer_id, base_text="", expect=None,
                      reregister=True):
        """Register the facts and issue one natural-language receipt artifact:
        full voucher text plus structured key fields (numbers, amounts, dates)
        derived from the facts and the channel's expect mapping. The receipt
        number is a bookkeeping label only; the agent must carry the key
        contents into its final summary in its own words.

        reregister=False covers facts already registered under the right
        issuer (e.g. an internal handoff attested them): the receipt cites the
        existing records instead of re-attesting them under this channel."""
        fields, texts = {}, []
        for fact_id in fact_ids or []:
            if reregister:
                record = self.register_fact(fact_id, issuer_id)
            else:
                record = self.director.facts.get(fact_id)
                if record is None:
                    continue
            fields[fact_id] = deepcopy(record["value"])
            texts.append(record["text"])
        for key, expected in (expect or {}).items():
            fields.setdefault(key, deepcopy(expected))
        text = base_text or ""
        if texts:
            text = (text + "\n" if text else "") + "\n".join(texts)
        return self.director.issue_receipt(title, text, fields, issuer_id, stamp(self.now))

    def _catalog_entry(self, catalog_name, entry_id):
        """The current inventory row for an id, or None if it is gone."""
        spec = self.hidden_tools[catalog_name]
        return next((e for e in spec["params"]["entries"] if e["id"] == entry_id), None)

    def _entry_current(self, entry):
        if entry.get("available_at") and self.now < parse(entry["available_at"]):
            return False
        if entry.get("expires_at") and self.now >= parse(entry["expires_at"]):
            return False
        return all(self.selections.get(name, {}).get("status") == status
                   for name, status in entry.get("requires_selections", {}).items())

    def execute_tool(self, case, tool_id):
        actor = self.actors[case["actor"]]
        if tool_id not in actor.spec["tools"]:
            raise PermissionError("Tool not available to this actor")
        tool = actor.spec["tools"][tool_id]
        self.record("tool_call", actor=case["actor"], case_id=case["id"], tool=tool_id, tool_kind=tool["kind"])
        if tool["kind"] == "lookup":
            for fact_id in tool["facts"]:
                if fact_id not in actor.spec["knowledge"]:
                    raise PermissionError("Cross-actor fact access")
                fact = self.task["facts"][fact_id]
                computed = fact.get("computed")
                if (computed and computed.get("tool") == tool_id
                        and fact_id not in self.director.facts):
                    fact["value"] = stamp(self.now)
                    fact["text"] = computed["text"].format(value=fact["value"])
                    for goal in self.task.get("goals", []):
                        if fact_id in goal.get("accepted_facts", []):
                            goal["expected"] = fact["value"]
                self.register_fact(fact_id, case["actor"], agent_visible=False)
                case["facts"].append(fact_id)
        elif tool["kind"] == "document":
            for fact_id in tool["facts"]:
                if fact_id not in actor.spec["knowledge"] and fact_id not in case["facts"]:
                    raise PermissionError("Document contains an unobserved fact")
                self.register_fact(fact_id, case["actor"], agent_visible=False)
                case["facts"].append(fact_id)
        elif tool["kind"] == "refer":
            case["contacts"].extend(tool["contacts"])
        elif tool["kind"] == "acknowledge":
            # Acceptance receipt issued mid-workflow: the case is confirmed as
            # admissible and continues to the next step without closing. Long
            # waits promise an earliest completion time so the agent can plan
            # instead of probing with follow-up mail.
            eta = self.eta_clause(case)
            self.emit(case, f"Hello, I am {actor.spec['name']}. Your materials have been verified as complete. The matter has been accepted and forwarded under the process. {eta or 'A written reply will follow completion.'}",
                      status="acknowledgement")
        elif tool["kind"] == "suggest":
            # A vague or guess-laden reply: the recipient answers from memory,
            # naming people or places that are only guesses. The case continues
            # (the real answer may still arrive later); the guesses are spoken
            # of in prose, which is how their mailboxes become discoverable.
            self.emit(case, tool["text"], contacts=tool.get("guesses", []), status="reply")
        elif tool["kind"] == "delegate":
            self.transition(case, "waiting_internal")
            self.new_case(tool["target"], tool["workflow"],
                          {k: case["fields"][k] for k in tool["forward_fields"] if k in case["fields"]},
                          parent=case["id"], origin=case.get("origin"))
            return "waiting"
        elif tool["kind"] == "consult":
            # A visible internal transfer: unlike the silent delegate, the
            # recipient first sends an interim reply saying they will ask a
            # colleague, then the real answer arrives later as a second letter.
            # The interim letter may come from an internal (delegated) case
            # too: its requester still deserves to see the transfer happening.
            target = self.actors[tool["target"]]
            self.transition(case, "waiting_internal")
            self.new_case(tool["target"], tool["workflow"],
                          {k: case["fields"][k] for k in tool["forward_fields"] if k in case["fields"]},
                          parent=case["id"], origin=case.get("origin"))
            text = tool.get("text") or f"I will first ask {target.spec['name']} to verify the details, then reply in writing."
            eta = self.eta_clause(case)
            self.emit(case, f"Hello, I am {actor.spec['name']}. {text}{eta}", status="acknowledgement", internal_ok=True)
            return "waiting"
        elif tool["kind"] == "deny":
            # A dead-end "不知道/不归我管" reply: the recipient plainly states
            # they cannot help, names no contacts, and the case closes as
            # replied. This is how a guess chain (suggest -> suggest -> deny)
            # terminates without a referral.
            self.transition(case, "replied")
            text = tool["text"]
            if case.get("parent"):
                parent = self.cases[case["parent"]]
                self.record("handoff_return", case_id=case["id"], parent=parent["id"])
                parent["step"] += 1
                self.schedule_step(parent)
            else:
                self.emit(case, f"Hello, I am {actor.spec['name']}. {text}")
            return "done"
        elif tool["kind"] == "reply":
            self.transition(case, "replied")
            if case.get("parent"):
                parent = self.cases[case["parent"]]
                parent["facts"].extend(case["facts"])
                parent["contacts"].extend(case["contacts"])
                self.record("handoff_return", case_id=case["id"], parent=parent["id"])
                parent["step"] += 1
                self.schedule_step(parent)
            else:
                # One natural-language email paragraph, assembled deterministically.
                parts = [f"Hello, I am {actor.spec['name']}. "]
                receipt = None
                if case["facts"]:
                    # The canonical result text plus a receipt artifact: the
                    # agent must remember the key contents and write them into
                    # its final summary itself. The facts were already attested
                    # under their original issuers; do not re-attest them here.
                    receipt = self.issue_receipt(
                        f"{case['workflow'].get('label', case['workflow']['id'])}Written verification receipt",
                        case["facts"], case["actor"], reregister=False)
                    parts.append('Your inquiry has been verified. Details: ')
                    parts.extend(record["text"] for record in
                                 (self.director.facts[f] for f in case["facts"]))
                    parts.append("These are the formal written verification determinations. A completion receipt is attached "
                                 f"(receipt number {receipt['receipt_no']}); include its key identifiers, quantities, and dates in the final summary.")
                else:
                    parts.append('Your matter has been completed under the process.')
                if case["contacts"]:
                    parts.append(f"For related matters, please also contact {self.contact_mentions(dict.fromkeys(case['contacts']))} for further assistance.")
                parts.append(' Please write again if you have other questions.')
                # Spoken answers carry information but never written receipts.
                self.emit(case, "".join(parts), list(dict.fromkeys(case["contacts"])),
                          receipts=None if case.get("origin") == "phone" else
                          ([receipt] if receipt else None))
            for linked in list(self.cases.values()):
                if linked.get("linked_to") != case["id"] or linked["state"] != "waiting_internal":
                    continue
                linked["facts"] = list(case["facts"])
                linked["contacts"] = list(case["contacts"])
                self.transition(linked, "queued")
                self.transition(linked, "working")
                self.execute_tool(linked, tool_id)
            return "done"
        elif tool["kind"] == "extract":
            # v0.5 club cases: the recipient first *understands* the letter.
            # An LLM pass extracts authored fields from the agent's prose;
            # branch matching then runs over the structured result, never
            # over keywords. Explicit structured fields (the reference
            # policy, or fields forwarded by a workflow step) are
            # authoritative and skip that extraction.
            extracted = self.extract_fields(case, tool)
            self.record("agent_extract", case_id=case["id"], tool=tool_id, fields=extracted)
            branch = None
            for candidate in tool["branches"]:
                if all(extracted.get(k) == v for k, v in candidate.get("when", {}).items()):
                    branch = candidate
                    break
            if branch is None:
                branch = tool["fallback"]
            for fact_id in branch.get("facts", []):
                self.register_fact(fact_id, case["actor"])
                if fact_id not in case["facts"]:
                    case["facts"].append(fact_id)
            case["contacts"].extend(branch.get("contacts", []))
            self.transition(case, "replied")
            if case.get("parent"):
                parent = self.cases[case["parent"]]
                parent["facts"].extend(case["facts"])
                parent["contacts"].extend(case["contacts"])
                self.record("handoff_return", case_id=case["id"], parent=parent["id"])
                parent["step"] += 1
                self.schedule_step(parent)
            else:
                text = branch["text"]
                receipt = None
                if case["facts"]:
                    receipt = self.issue_receipt(
                        f"{case['workflow'].get('label', case['workflow']['id'])}Written verification receipt",
                        case["facts"], case["actor"], reregister=False)
                self.emit(case, f"Hello, I am {actor.spec['name']}. {text}",
                          list(dict.fromkeys(case["contacts"])),
                          receipts=None if case.get("origin") == "phone" else
                          ([receipt] if receipt else None))
            return "done"
        else:
            raise ValueError("Unknown recipient tool")
        return "continue"

    def complete_failure(self, case, reason):
        for linked in list(self.cases.values()):
            if linked.get("linked_to") == case["id"] and linked["state"] == "waiting_internal":
                self.transition(linked, "failed")
                self.complete_failure(linked, reason)
        if case.get("parent"):
            parent = self.cases[case["parent"]]
            self.transition(parent, "failed")
            self.complete_failure(parent, reason)
        else:
            self.emit(case, f"Hello, I am {self.actors[case['actor']].spec['name']}. Unfortunately, {reason} Please write again with any questions.", status="failed")

    def process_event(self, event):
        at, _, kind, case_id = event
        self.now = at
        if kind == "page_update":
            update = self.task["page_updates"][case_id]
            page = next(p for p in self.task["public"]["pages"] if p["id"] == update["page"])
            for key in ("title", "text", "snippet", "contacts", "documents"):
                if key in update:
                    page[key] = deepcopy(update[key])
            self.page_updated_at[page["url"]] = at
            self.record("page_updated", page=update["page"], url=page["url"])
            return
        if kind == "form_processed":
            self.process_form(case_id)
            return
        if kind == "catalog_update":
            self.apply_catalog_update(case_id)
            return
        if kind == "selection_processed":
            self.process_selection(case_id)
            return
        if kind == "selection_expired":
            selection = self.selections.get(case_id)
            if selection and selection["status"] == "pending":
                selection["status"] = "expired"
                selection["result_text"] = selection["params"].get("expire_text") or \
                    "The selected option was held but not confirmed before it expired; the hold has lapsed and nothing was booked."
                self.record("selection_expired", tool=case_id)
            return
        if kind == "group_approved":
            # A reviewed join request finally lands: membership is granted and
            # a short system notice enters the agent's inbox.
            spec = self.hidden_tools.get(case_id)
            state = self.group_states.get(case_id)
            if spec is None or state is None or state["joined"]:
                return
            state["joined"], state["pending"] = True, None
            self.record("group_join_approved", group=case_id)
            self.messages.append({"id": f"MSG-{len(self.messages)+1:04d}", "at": stamp(self.now),
                                  "from": spec["params"].get("system_from", "messaging-app"),
                                  "case_id": None, "status": "reply", "channel": "chat",
                                  "text": f"Your join request for {spec['params']['group_name']} was approved. "
                                          "The timeline, pinned announcement and member list are readable now.",
                                  "receipts": []})
            return
        case = self.cases[case_id]
        if case["state"] in {"failed", "replied"}:
            return
        if kind == "admit":
            # Deferred email admission: routing and material checks happen
            # inside the recipient's work hours, never at send time.
            if case["state"] in {"new", "needs_information"}:
                if case.get("workflow") is None:
                    self.reply_referral(case)
                else:
                    self.start(case)
            return
        if kind == "start":
            self.transition(case, "working")
        elif kind == "complete":
            step = case["workflow"]["steps"][case["step"]]
            result = self.execute_tool(case, step["tool"])
            if result == "continue":
                case["step"] += 1
                self.schedule_step(case)

    def advance(self, until, wake_on_message=False):
        if self.simulator_failure:
            raise SimulatorError("Invalid episode: background environment failed")
        until = parse(until) if isinstance(until, str) else until
        if until < self.now:
            raise ValueError("Cannot move the clock backwards")
        until = min(until, self.deadline)
        message_count = len(self.messages)
        while self.events and self.events[0][0] <= until:
            event = heapq.heappop(self.events)
            try:
                self.process_event(event)
            except Exception as error:
                # This is background work, not a malformed agent request.
                # Keep the event for diagnosis; do not retry partially executed
                # side effects or silently classify an orphaned case as valid.
                heapq.heappush(self.events, event)
                self.simulator_failure = {"type": type(error).__name__, "message": str(error)}
                self.record("environment_failure", event_kind=event[2], target=event[3],
                            error=str(error))
                raise SimulatorError(f"Background event {event[2]} failed: {error}") from error
            if wake_on_message and len(self.messages) > message_count:
                return
        self.now = until

    def expected_conclusion(self):
        rule = self.task.get("conclusion_by_fact")
        if rule:
            fact = self.director.facts.get(rule["fact"])
            if not fact or not fact.get("agent_visible"):
                return rule["missing"]
            return rule["after"] if self.now >= parse(fact["value"]) else rule["before"]
        return self.task.get("expected_conclusion")

    def evaluate(self, answer):
        if self.simulator_failure:
            raise SimulatorError("Invalid episode: simulator failed")
        # v0.5 answer schema: {"conclusion": str, "summary": str}. The new
        # structure is stored for the milestone-3 scoring rewrite; the legacy
        # deterministic scorer still runs unchanged in the meantime.
        self.final_answer = deepcopy(answer)
        return evaluate_outcome(self, answer)


class AgentTools:
    """Expose these RPC methods, not a Python object reference, to untrusted agents.

    Thin facade over the tool registry: implementations live in dayspanbench/tools/
    (common, optional, hidden). Keeping the dispatch here preserves the exact
    RPC surface (method names, arguments, error messages) that serve.py and
    evaluation.py rely on via getattr(api, name)(**arguments).
    """
    def __init__(self, env):
        self._env = env
        # Snapshot of the initial task brief, handed out by the system message and
        # re-issued verbatim by recall_task; it never reflects later progress.
        public = deepcopy(env.task["public"])
        # Pages are discovered through web_search, never listed in the brief.
        public.pop("pages", None)
        self._brief = {"task": public, "deadline": stamp(env.deadline),
                       "contacts": [env.contact(c) for c in sorted(env.task["public"]["initial_contacts"])]}
        # Pages the agent has already discovered (surfaced by web_search or
        # visited); used to hint how many pages remain undiscovered.
        self._seen_pages = set()

    def tool_list(self):
        """The per-task agent tool surface: the common tools plus whichever
        optional tools this task declares (they may or may not be useful),
        plus any hidden tools the agent has unlocked via discover_tools."""
        tools = self._env.task["public"].get("tools")
        tools = list(tools) if tools else list(PUBLIC_TOOLS)
        return tools + [name for name in sorted(self._env.unlocked_tools) if name not in tools]

    def __getattr__(self, name):
        # Hidden per-task tools: callable only after discover_tools unlocked
        # them; a guessed-but-locked name still fails with "not available".
        if name.startswith("_"):
            raise AttributeError(name)
        env = self.__dict__.get("_env")
        if env is not None and name in env.hidden_tools:
            if name not in env.unlocked_tools:
                raise PermissionError(f"Tool {name} is not available in this task")
            def hidden_call(**kwargs):
                spec = env.hidden_tools[name]
                refusal = self._consent("hidden_" + spec["kind"],
                                        {"tool": name, "args": deepcopy(kwargs)})
                if refusal is not None:
                    return refusal
                return hidden_tool_impl.call_hidden_tool(self, name, **kwargs)
            return hidden_call
        raise AttributeError(name)

    def _consent(self, action, detail):
        """Consent gate: when this task's assisted user must approve an
        externally effective action, ask before executing. Approval lets the
        call proceed; a refusal is a normal return value (the user's words),
        never an exception, so the agent can adapt its plan."""
        env = self.__dict__["_env"]
        if env.interactor is None:
            return None
        outcome = env.interactor.consent(action, detail, env.now)
        env.record("agent_action_consent", action=action, detail=detail,
                   approve=outcome["approve"])
        if outcome["approve"]:
            return None
        return {"status": "refused", "by": "user", "action": action,
                "text": outcome["say"] or "The user declined this action."}

    # Common tools (every task) -- implementations in tools/common.py.
    def recall_task(self):
        return TOOL_REGISTRY["recall_task"].handler(self)

    def observe(self):
        return TOOL_REGISTRY["observe"].handler(self)

    def discover_tools(self, name):
        return TOOL_REGISTRY["discover_tools"].handler(self, name)

    def web_search(self, query):
        return TOOL_REGISTRY["web_search"].handler(self, query)

    def visit_page(self, url):
        return TOOL_REGISTRY["visit_page"].handler(self, url)

    def send_email(self, recipient, text, fields=None, case_id=None):
        refusal = self._consent("send_email",
                                {"recipient": recipient, "text": text, "fields": fields})
        if refusal is not None:
            return refusal
        return TOOL_REGISTRY["send_email"].handler(self, recipient, text, fields, case_id)

    def call(self, recipient, text, fields=None):
        refusal = self._consent("call", {"recipient": recipient, "text": text})
        if refusal is not None:
            return refusal
        return TOOL_REGISTRY["call"].handler(self, recipient, text, fields)

    def read_inbox(self, after=0):
        return TOOL_REGISTRY["read_inbox"].handler(self, after)

    def wait_until(self, until, wake_on_message=True):
        return TOOL_REGISTRY["wait_until"].handler(self, until, wake_on_message)

    def submit_answer(self, answer):
        return TOOL_REGISTRY["submit_answer"].handler(self, answer)

    # Optional per-task tools -- implementations in tools/optional.py.
    def query_case_status(self, case_id):
        return TOOL_REGISTRY["query_case_status"].handler(self, case_id)

    def fetch_document(self, url):
        return TOOL_REGISTRY["fetch_document"].handler(self, url)

    def check_schedule(self, contact, date=None, days=7):
        return TOOL_REGISTRY["check_schedule"].handler(self, contact, date, days)

    def lookup_directory(self, query):
        return TOOL_REGISTRY["lookup_directory"].handler(self, query)

    def request_callback(self, contact, topic=None):
        return TOOL_REGISTRY["request_callback"].handler(self, contact, topic)

    def leave_note(self, contact, text):
        return TOOL_REGISTRY["leave_note"].handler(self, contact, text)

    def consult_user(self, question):
        return TOOL_REGISTRY["consult_user"].handler(self, question)
