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
from .recipient import RuleRecipient
from .scoring import evaluate as evaluate_outcome
from .llm import SimulatorError


TRANSITIONS = {
    "new": {"needs_information", "queued", "failed"},
    "needs_information": {"queued", "failed"},
    "queued": {"working", "failed"},
    "working": {"queued", "waiting_internal", "replied", "failed"},
    "waiting_internal": {"queued", "failed"},
    "replied": set(), "failed": set(),
}

# The agent-facing tool surface every task starts from; serve.py allowlists
# per-task tool lists built from this plus EXTRA_TOOLS below. discover_tools
# is always available: per-task hidden tools are unlocked through it.
PUBLIC_TOOLS = ("observe", "recall_task", "web_search", "visit_page",
                "send_email", "call", "read_inbox", "wait_until",
                "discover_tools", "submit_answer")

# Optional task-specific tools. A task's public["tools"] may add any of these;
# they are sometimes useful and sometimes pure decoys, and the agent must decide
# from the tool descriptions and its own probing which ones carry information.
EXTRA_TOOLS = ("query_case_status", "fetch_document", "check_schedule",
               "lookup_directory", "request_callback", "leave_note")

# Per-task hidden tools (task["hidden_tools"]) are NOT part of public["tools"]:
# their names surface only inside authored NPC replies or page text, and the
# agent must call discover_tools(name) to learn their usage and unlock them.
# An unlocked tool's behavior is fully parameterized by its authored params.
HIDDEN_TOOL_KINDS = ("form", "status", "record", "catalog", "select", "dialogue")

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
    import unicodedata
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


def field_value_equivalent(value, expected):
    """Exact match, the same quantity written with a synonym or no unit,
    or the same date in another common spelling."""
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
    return left_date is not None and left_date == normalize_field_date(expected, default_year)


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
        self.known_contacts = set(task["public"]["initial_contacts"])
        # Mailboxes are the addressing surface: an address that belongs to no
        # actor is a black hole that acknowledges delivery and never replies.
        self.email_to_actor = {a["contact_details"]["email"]: a["id"] for a in task["actors"] if "email" in a.get("contact_details", {})}
        self.cases = {}
        self.evidence = {}
        self.messages = []
        self.audit = []
        self.events = []
        self.serial = 0
        self.case_serial = 0
        self.finished = False
        self.agent_sends = 0
        self.simulator_failure = None
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

    @classmethod
    def load(cls, path, **kwargs):
        return cls(json.loads(Path(path).read_text()), **kwargs)

    def tools(self):
        return AgentTools(self)

    def record(self, kind, **data):
        self.audit.append({"at": stamp(self.now), "kind": kind, **deepcopy(data)})

    def transition(self, case, state):
        old = case["state"]
        if state not in TRANSITIONS[old]:
            raise ValueError(f"Illegal case transition {old} -> {state}")
        case["state"] = state
        self.record("transition", case_id=case["id"], actor=case["actor"], old=old, new=state)

    def enqueue(self, at, kind, case_id):
        self.serial += 1
        heapq.heappush(self.events, (at, self.serial, kind, case_id))

    def emit(self, case, text, evidence_ids=None, contacts=None, status="reply", internal_ok=False):
        if case.get("parent") and not internal_ok:
            raise ValueError("Internal cases must complete through handoff return")
        contacts = contacts or []
        actor = self.actors[case["actor"]]
        if hasattr(actor.recipient, "render"):
            view = {"actor_id": case["actor"], "name": actor.spec["name"], "role": actor.spec["role"],
                    "now": stamp(self.now), "case_id": case["id"], "case_state": case["state"],
                    "status": status, "canonical_text": text, "history": deepcopy(actor.history),
                    "contacts": [self.contact(cid) for cid in contacts],
                    "evidence": [{k: deepcopy(self.evidence[e][k]) for k in ("id", "text", "value", "issuer", "valid_until")}
                                 for e in evidence_ids or []]}
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
                   "text": text, "evidence": []}
        for evidence_id in evidence_ids or []:
            if case.get("origin") == "phone":
                # Spoken answers carry information but never written evidence.
                continue
            ev = self.evidence[evidence_id]
            ev["agent_visible"] = True
            message["evidence"].append({key: deepcopy(ev[key]) for key in
                ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")})
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

    def contact(self, actor_id):
        actor = self.actors[actor_id].spec
        return {"id": actor["id"], "name": actor["name"], "role": actor["role"],
                "contact_details": deepcopy(actor["contact_details"])}

    def admission_at(self, actor):
        """Email from the agent is read no sooner than the task's reply delay:
        first pushed to the recipient's earliest opening, then delayed by a
        random business duration of task-specific magnitude. Never instant."""
        low, high = self.reply_delay
        return actor.calendar.add_business(self.now, self.rng.randint(low, high))

    def enqueue_admission(self, actor, case_id):
        """Schedule admission unless one is already pending for this case."""
        if any(kind == "admit" and cid == case_id for _, _, kind, cid in self.events):
            return
        self.enqueue(self.admission_at(actor), "admit", case_id)

    def new_case(self, actor_id, workflow_id, fields, parent=None, origin=None):
        actor = self.actors[actor_id]
        workflow = next(w for w in actor.spec["workflows"] if w["id"] == workflow_id)
        self.case_serial += 1
        case = {"id": f"CASE-{self.case_serial:04d}", "actor": actor_id, "workflow": deepcopy(workflow),
                "state": "new", "step": 0, "fields": deepcopy(fields), "evidence": [],
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
                "state": "new", "step": 0, "fields": deepcopy(fields), "evidence": [],
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
        return "、".join(f"{self.actors[c].spec['name']}（{self.actors[c].spec['contact_details']['email']}）"
                         for c in actor_ids)

    def reply_referral(self, case):
        """Answer a misrouted mail: not my responsibility, contact someone else."""
        actor = self.actors[case["actor"]]
        referred = list(dict.fromkeys(self.referral_names(actor)))
        mentions = self.contact_mentions(referred)
        if mentions:
            body = f"您咨询的事项不属于我负责的范围，我无法直接办理；建议您联系{mentions}，由他们继续为您处理。"
        else:
            body = "您咨询的事项不属于我负责的范围，我无法直接办理；建议您通过公开渠道找到相应事项的对接人后再来信。"
        text = f"您好，我是{actor.spec['name']}。{body}如有其他问题，欢迎随时来信。"
        # The misrouted mail walks the same visible lifecycle as a processed one.
        self.transition(case, "queued")
        self.transition(case, "working")
        self.transition(case, "replied")
        self.emit(case, text, contacts=referred, status="referral")



    def process_form(self, form_id):
        """Flip a submitted web form to its processed/rejected outcome at the
        authored virtual time: publish the result text, optionally issue
        evidence facts and rewrite the carrying page. The agent is never
        notified; it must re-visit the page or query the status tool."""
        submission = self.form_submissions.get(form_id)
        params = self.form_specs.get(form_id)
        if submission is None or params is None or submission["status"] != "pending":
            return
        if submission["accepted"]:
            submission["status"] = "processed"
            submission["result_text"] = params.get("result_text") or "您提交的申请已受理办结。"
            for fact_id in params.get("facts", []):
                fact = self.task["facts"][fact_id]
                # A fact gated behind a later availability simply is not
                # published yet; the outcome text still lands.
                if fact.get("available_at") and self.now < parse(fact["available_at"]):
                    self.record("form_fact_pending", form=form_id, fact=fact_id)
                    continue
                submission["evidence"].append(self.issue_public(fact_id, params["issuer"]))
        else:
            submission["status"] = "rejected"
            submission["result_text"] = params.get("reject_text") or "您提交的信息与登记情况不符，已退回；请核对后重新提交。"
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
        still satisfies the authored expectations; acceptance issues written
        evidence exactly like a processed form."""
        selection = self.selections.get(tool_name)
        if not selection or selection["status"] != "pending":
            return
        params = selection["params"]
        entry = self._catalog_entry(selection["catalog"], selection["entry"])
        if selection["accepted"] and (entry is None or not self._entry_current(entry)):
            # The option disappeared from inventory between selection and
            # processing: the booking cannot be honored.
            selection["accepted"] = False
        if selection["accepted"]:
            selection["status"] = "processed"
            selection["result_text"] = params.get("result_text") or "Your selection has been confirmed."
            for fact_id in params.get("facts", []):
                fact = self.task["facts"][fact_id]
                if fact.get("available_at") and self.now < parse(fact["available_at"]):
                    self.record("selection_fact_pending", tool=tool_name, fact=fact_id)
                    continue
                selection["evidence"].append(self.issue_public(fact_id, params["issuer"]))
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
            body = workflow.get("early_reply") or "您咨询的事项还未开始受理，暂时无法办理，请稍后再来。"
            self.emit(case, f"您好，我是{self.actors[case['actor']].spec['name']}。{body}如有其他问题，欢迎随时来信。")
            return
        if workflow.get("accept_before") and self.now >= parse(workflow["accept_before"]):
            self.transition(case, "failed")
            self.complete_failure(case, "该轮受理截止时间已过，无法按原时间完成。")
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
                missing.append(key + "（须先取得有效可核验凭证）")
        if missing or mismatched:
            missing += [key + "（与任务信息不符）" for key in mismatched]
            if case["state"] == "new":
                self.transition(case, "needs_information")
            if case.get("parent"):
                self.transition(case, "failed")
                self.complete_failure(case, "内部转交缺少材料：" + ", ".join(missing))
            else:
                absent = [item for item in missing if "（" not in item]
                unverifiable = [item.split("（")[0] for item in missing if item.endswith("（须先取得有效可核验凭证）")]
                body = "您提交的材料尚不完整，请补充以下信息后我们再继续处理：" + ", ".join(absent) + "。" if absent else ""
                if mismatched:
                    body += "您提供的" + ", ".join(mismatched) + "与登记情况不一致，请核对相关信息后重新提交。"
                if unverifiable:
                    body += "您提供的" + ", ".join(unverifiable) + "未能与有效凭证核对，请随信附上对方的书面确认原文或其编号后再提交。"
                self.emit(case, f"您好，我是{self.actors[case['actor']].spec['name']}。{body}如有其他问题，欢迎随时来信。", status="needs_information")
            return
        case["admitted_at"] = stamp(self.now)
        case["admission_evidence"] = admission_evidence
        self.schedule_step(case)

    # Acknowledgements only promise an ETA when the remaining workflow is
    # genuinely long; short-turnaround receipts stay terse.
    ETA_THRESHOLD = timedelta(hours=24)

    # A promised earliest-completion slipping past the promise by more than
    # this (later queue contention pushing the chain's projection out) triggers
    # a revision email, so the agent never plans around a stale promise.
    ETA_REVISION_THRESHOLD = timedelta(hours=12)

    # Upper bound of the randomized surcharge jittered_delay adds to each
    # business step of an agent-initiated case.
    JITTER_CEILING = 25

    def projected_delay(self, delay, origin):
        """Delay as the ETA projection sees it: for agent-origin cases every
        business step is inflated to its worst-case jitter so the promised
        "earliest" completion is never beaten by the real run."""
        if origin != "agent":
            return delay
        adjusted = dict(delay)
        if adjusted.get("mode", "business") == "business":
            adjusted["minutes"] = max(adjusted.get("minutes", 0), 15) + self.JITTER_CEILING
        else:
            adjusted["minutes"] = max(adjusted.get("minutes", 0), 15)
        return adjusted

    def estimate_completion(self, actor_id, workflow, from_step, now=None, origin=None):
        """Nominal projection of when a workflow's final reply lands: remaining
        steps walked with their authored delays (worst-case jitter included for
        agent-origin cases, but no queue contention), recursing into delegate
        targets. A lower bound, used only for the ETA sentence in long-wait
        acknowledgements."""
        if now is None:
            now = self.now
        actor = self.actors[actor_id]
        free = actor.free_at
        t = now
        for i in range(from_step, len(workflow["steps"])):
            step = workflow["steps"][i]
            tool = actor.spec["tools"][step["tool"]]
            if tool["kind"] in {"delegate", "consult"}:
                _, t, free = actor.calendar.schedule(t, self.projected_delay(step["delay"], origin), free)
                target_wf = next(w for w in self.actors[tool["target"]].spec["workflows"]
                                 if w["id"] == tool["workflow"])
                t = max(t, self.estimate_completion(tool["target"], target_wf, 0, t, origin=origin))
            else:
                _, t, free = actor.calendar.schedule(t, self.projected_delay(step["delay"], origin), free)
        return t

    def active_child(self, case, workflow_id):
        """The latest not-yet-returned delegate child of a waiting case."""
        children = [c for c in self.cases.values()
                    if c.get("parent") == case["id"] and c["workflow"] is not None
                    and c["workflow"]["id"] == workflow_id and c["state"] not in {"replied", "failed"}]
        return children[-1] if children else None

    def case_completion(self, case):
        """Projection for a live case: the current step uses its already
        scheduled due time, a waiting_internal step follows the active child's
        real progress instead of re-simulating it from scratch — re-estimating
        a finished reviewer from "now" once pushed a DSB-02 receipt a whole
        weekly batch past its original promise."""
        t = self.now
        actor = self.actors[case["actor"]]
        workflow = case["workflow"]
        step_index = case["step"]
        if case["state"] in {"queued", "working"}:
            if case.get("due_at"):
                t = max(t, parse(case["due_at"]))
            step_index += 1
        elif case["state"] == "waiting_internal":
            step = workflow["steps"][step_index]
            tool = actor.spec["tools"][step["tool"]]
            if tool["kind"] not in {"delegate", "consult"}:
                raise ValueError("waiting_internal step must delegate or consult")
            child = self.active_child(case, tool.get("workflow", "main"))
            if child is not None:
                t = self.case_completion(child)
            else:
                _, t, _ = actor.calendar.schedule(t, step["delay"], actor.free_at)
                target_wf = next(w for w in self.actors[tool["target"]].spec["workflows"]
                                 if w["id"] == tool["workflow"])
                t = max(t, self.estimate_completion(tool["target"], target_wf, 0, t, origin=case.get("origin")))
            step_index += 1
        elif case["state"] in {"new", "needs_information"}:
            return self.estimate_completion(case["actor"], workflow, 0, origin=case.get("origin"))
        else:  # replied / failed: nothing left to promise
            return t
        return self.estimate_completion(case["actor"], workflow, step_index, t,
                                        origin=case.get("origin"))

    def eta_clause(self, case, from_step=None):
        """The promised earliest-completion sentence, or empty for short waits.
        An unrouted case has no workflow to project, so it promises nothing."""
        if case["workflow"] is None:
            return ""
        eta = self.case_completion(case)
        if eta - self.now <= self.ETA_THRESHOLD:
            return ""
        # A promise never shrinks: a later re-projection may look earlier
        # (a child finished, the remaining chain shortened), but the requester
        # already holds the earlier written promise, and the revision logic
        # must still watch the schedule against the tightest promise made.
        previous = case.get("promised_eta")
        if previous and parse(previous) > eta:
            eta = parse(previous)
        actor = self.actors[case["actor"]]
        local = eta.astimezone(actor.calendar.zone)
        # Every promise is remembered so a later schedule slip (queue
        # contention inserting work ahead of this chain) can be retracted.
        case["promised_eta"] = stamp(eta)
        case["eta_slip_notified"] = False
        return (f"预计最早将于{local.strftime('%Y-%m-%d %H:%M')}（当地时间）办结并书面回复您；"
                "该事项办理周期较长，可待回复送达后再联系，处理顺序不因催办提前。")

    def notify_eta_slip(self, case):
        """Retract promises the schedule has outgrown.

        The acknowledgement promised an earliest completion as a projection;
        later cases joining the same actor's queue can push the chain past it.
        The requester then deserves a revision instead of silently waiting on
        a broken promise (a DSB-10 agent waited to the deadline on a promise
        the queue had already pushed a week out)."""
        chain, current = [], case
        while current is not None:
            chain.append(current)
            current = self.cases.get(current.get("parent"))
        for member in chain:
            if not member.get("promised_eta") or member.get("eta_slip_notified") \
                    or member["state"] in {"replied", "failed"}:
                continue
            completion = self.case_completion(member)
            if completion - parse(member["promised_eta"]) <= self.ETA_REVISION_THRESHOLD:
                continue
            member["eta_slip_notified"] = True
            actor = self.actors[member["actor"]]
            local = completion.astimezone(actor.calendar.zone)
            self.record("eta_revised", case_id=member["id"], actor=member["actor"],
                        promised=member["promised_eta"], revised=stamp(completion))
            self.emit(member, f"您好，我是{actor.spec['name']}。您此前已受理事项的办理进度更新：因受理安排调整，"
                              f"预计最早办结时间调整为{local.strftime('%Y-%m-%d %H:%M')}（当地时间）。"
                              "处理顺序不因催办提前，可待回复送达后再联系。", status="acknowledgement")

    def jittered_delay(self, case, delay):
        """Agent-initiated email never gets instant handling: business delays get a
        randomized surcharge, other modes at least a 15-minute floor."""
        if case.get("origin") != "agent":
            return delay
        adjusted = dict(delay)
        if adjusted.get("mode", "business") == "business":
            adjusted["minutes"] = max(adjusted.get("minutes", 0), 15) + self.rng.randint(5, 25)
        else:
            adjusted["minutes"] = max(adjusted.get("minutes", 0), 15)
        return adjusted

    def schedule_step(self, case):
        self.transition(case, "queued")
        actor = self.actors[case["actor"]]
        step = case["workflow"]["steps"][case["step"]]
        start, end, resource_free = actor.calendar.schedule(self.now, self.jittered_delay(case, step["delay"]), actor.free_at)
        actor.free_at = resource_free
        case["due_at"] = stamp(end)
        self.record("scheduled", case_id=case["id"], actor=case["actor"], step=step["id"],
                    start_at=stamp(start), due_at=stamp(end), tool=step["tool"])
        self.enqueue(start, "start", case["id"])
        self.enqueue(end, "complete", case["id"])
        self.notify_eta_slip(case)

    def issue(self, case, fact_id, kind="fact"):
        fact = self.task["facts"][fact_id]
        if fact.get("available_at") and self.now < parse(fact["available_at"]):
            raise ValueError(f"Fact {fact_id} queried before its availability")
        ev_id = f"EV-{len(self.evidence)+1:04d}"
        self.evidence[ev_id] = {"id": ev_id, "fact_id": fact_id, "value": deepcopy(fact["value"]),
            "text": fact["text"], "issuer": case["actor"], "issued_at": stamp(self.now),
            "valid_until": fact.get("valid_until"), "kind": kind, "agent_visible": False,
            "attributes": deepcopy(fact["attributes"]),
            "authorities": deepcopy(self.actors[case["actor"]].spec["evidence_authorities"])}
        case["evidence"].append(ev_id)
        return ev_id

    def _catalog_entry(self, catalog_name, entry_id):
        """The current inventory row for an id, or None if it is gone."""
        spec = self.hidden_tools[catalog_name]
        return next((e for e in spec["params"]["entries"] if e["id"] == entry_id), None)

    def _entry_current(self, entry):
        if entry.get("available_at") and self.now < parse(entry["available_at"]):
            return False
        if entry.get("expires_at") and self.now >= parse(entry["expires_at"]):
            return False
        return True

    def issue_public(self, fact_id, issuer_id, kind="document"):
        """Issue engine attestation for a fact the agent retrieved itself by
        fetching a published document, outside any recipient case. The issuer's
        attestation authority still applies; availability is still gated."""
        fact = self.task["facts"][fact_id]
        if fact.get("available_at") and self.now < parse(fact["available_at"]):
            raise ValueError(f"Fact {fact_id} not yet published")
        ev_id = f"EV-{len(self.evidence)+1:04d}"
        self.evidence[ev_id] = {"id": ev_id, "fact_id": fact_id, "value": deepcopy(fact["value"]),
            "text": fact["text"], "issuer": issuer_id, "issued_at": stamp(self.now),
            "valid_until": fact.get("valid_until"), "kind": kind, "agent_visible": True,
            "attributes": deepcopy(fact["attributes"]),
            "authorities": deepcopy(self.actors[issuer_id].spec["evidence_authorities"])}
        return ev_id

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
                self.issue(case, fact_id)
        elif tool["kind"] == "document":
            for fact_id in tool["facts"]:
                if fact_id not in actor.spec["knowledge"] and not any(
                    self.evidence[e]["fact_id"] == fact_id for e in case["evidence"]
                ):
                    raise PermissionError("Document contains an unobserved fact")
                self.issue(case, fact_id, "document")
        elif tool["kind"] == "refer":
            case["contacts"].extend(tool["contacts"])
        elif tool["kind"] == "acknowledge":
            # Acceptance receipt issued mid-workflow: the case is confirmed as
            # admissible and continues to the next step without closing. Long
            # waits promise an earliest completion time so the agent can plan
            # instead of probing with follow-up mail.
            eta = self.eta_clause(case)
            self.emit(case, f"您好，我是{actor.spec['name']}。您提交的材料已核验齐全，本事项已受理并按流程转办。{eta or '办结后会书面回复您。'}",
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
            text = tool.get("text") or f"我先向{target.spec['name']}核实相关情况，核实后再书面回复您。"
            eta = self.eta_clause(case)
            self.emit(case, f"您好，我是{actor.spec['name']}。{text}{eta}", status="acknowledgement", internal_ok=True)
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
                self.emit(case, f"您好，我是{actor.spec['name']}。{text}")
            return "done"
        elif tool["kind"] == "reply":
            self.transition(case, "replied")
            if case.get("parent"):
                parent = self.cases[case["parent"]]
                parent["evidence"].extend(case["evidence"])
                parent["contacts"].extend(case["contacts"])
                self.record("handoff_return", case_id=case["id"], parent=parent["id"])
                parent["step"] += 1
                self.schedule_step(parent)
            else:
                # One natural-language email paragraph, assembled deterministically.
                parts = [f"您好，我是{actor.spec['name']}。"]
                texts = [self.evidence[e]["text"] for e in case["evidence"]]
                if texts:
                    parts.append("您咨询的事项已经核实，具体情况如下：")
                    parts.extend(texts)
                    # Positive confirmation: cited conclusions are backed by the
                    # structured written evidence attached to this letter.
                    parts.append("以上为正式书面核实结论，对应的结构化书面凭证已随本信送达（见evidence附件，含证据编号与签发人），其证据编号可在最终提交中引用。")
                else:
                    parts.append("您咨询的事项已经按流程处理完毕。")
                if case["contacts"]:
                    parts.append(f"此外，相关事项建议您联系{self.contact_mentions(dict.fromkeys(case['contacts']))}，他们可以继续为您处理。")
                parts.append("如有其他问题，欢迎随时来信。")
                self.emit(case, "".join(parts), case["evidence"], list(dict.fromkeys(case["contacts"])))
            return "done"
        else:
            raise ValueError("Unknown recipient tool")
        return "continue"

    def complete_failure(self, case, reason):
        if case.get("parent"):
            parent = self.cases[case["parent"]]
            self.transition(parent, "failed")
            self.complete_failure(parent, reason)
        else:
            self.emit(case, f"您好，我是{self.actors[case['actor']].spec['name']}。很抱歉，{reason}如有疑问欢迎再来信。", status="failed")

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
        until = parse(until) if isinstance(until, str) else until
        if until < self.now:
            raise ValueError("Cannot move the clock backwards")
        until = min(until, self.deadline)
        message_count = len(self.messages)
        while self.events and self.events[0][0] <= until:
            self.process_event(heapq.heappop(self.events))
            if wake_on_message and len(self.messages) > message_count:
                return
        self.now = until

    def evaluate(self, answer):
        if self.simulator_failure:
            raise SimulatorError("Invalid episode: simulator failed")
        return evaluate_outcome(self, answer)


class AgentTools:
    """Expose these RPC methods, not a Python object reference, to untrusted agents."""
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

    def recall_task(self):
        return deepcopy(self._brief)

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
                return self._call_hidden_tool(name, **kwargs)
            return hidden_call
        raise AttributeError(name)

    def discover_tools(self, name):
        """Look up a tool name mentioned in an NPC reply, page text, or a web
        search service mention. A hit returns the handwritten usage
        instructions and unlocks the tool; a miss never leaks the hidden tool
        list. Costs no message budget."""
        env = self._env
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        tool = env.hidden_tools.get(name.strip())
        if tool is None:
            env.record("agent_discover_tools", name=name, found=False)
            return {"found": False,
                    "text": "未找到该工具。工具名称以往来信件或网页正文中的原文为准，可核对后重试。"}
        env.unlocked_tools.add(tool["name"])
        env.record("agent_discover_tools", name=tool["name"], found=True, tool_kind=tool["kind"])
        return {"found": True, "name": tool["name"], "usage": tool["usage"],
                "note": "该工具已解锁：现在出现在observe()返回的工具列表中，可按上述用法调用。"}

    def observe(self):
        env = self._env
        return {"now": stamp(env.now), "tools": self.tool_list(),
                "unread_messages": max(0, len(env.messages) - env.inbox_read)}

    def web_search(self, query):
        # A page is only returned when the query matches its title or snippet;
        # an empty query matches nothing. Page bodies are not searchable: the
        # agent must find the page first, then visit it. Relevance is not
        # whole-term substring: Chinese terms are matched on character bigrams
        # (南屿共享实验室 vs 南屿实验室联系方式 share 南屿/实验室), while
        # latin terms must match whole.
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        units = set()
        for term in query.casefold().split():
            for run in re.findall(r"[a-z0-9]+|[一-鿿]+", term):
                if run[0].isascii() or len(run) == 1:
                    units.add(run)
                else:
                    units.update(run[i:i + 2] for i in range(len(run) - 1))
        if not units:
            results = []
        else:
            pages = self._env.task["public"]["pages"]
            results = [{"url": p["url"], "title": p["title"], "snippet": p.get("snippet", "")} for p in pages
                       if any(u in (p["title"] + p.get("snippet", "")).casefold() for u in units)]
        self._seen_pages.update(r["url"] for r in results)
        total = len(self._env.task["public"]["pages"])
        env = self._env
        # Some hidden tools are discoverable through search: authored keywords
        # embed a service mention in the results. The clue names the service
        # but says nothing about how to use it — the agent must still call
        # discover_tools to read the usage instructions and unlock it.
        mentions = []
        for name in sorted(env.hidden_tools):
            tool = env.hidden_tools[name]
            if name in env.unlocked_tools:
                continue
            keywords = tool.get("params", {}).get("keywords") or []
            if not keywords:
                continue
            haystack = " ".join(keywords).casefold()
            if any(u in haystack for u in units):
                mentions.append({"service": name,
                                 "text": tool["params"].get("clue") or
                                         f"A service named {name} is available for this kind of request.",
                                 "note": "A mentioned service can be looked up by name via discover_tools."})
        if mentions:
            env.record("agent_search_clue", query=query, services=[m["service"] for m in mentions])
        return {"results": results,
                "service_mentions": mentions,
                "hint": {"total_pages": total,
                         "undiscovered_pages": total - len(self._seen_pages)}}

    def visit_page(self, url):
        env = self._env
        # Only synthetic https://...bench/... addresses exist; anything else is
        # not a page in this scenario.
        if (not isinstance(url, str) or not url.startswith("https://")
                or ".bench/" not in url or " " in url):
            raise ValueError("url must be a https://*.bench/* page address")
        page = next((p for p in env.task["public"]["pages"] if p["url"] == url), None)
        if page is None:
            raise ValueError("Unknown page address")
        self._seen_pages.add(url)
        env.known_contacts.update(page.get("contacts", []))
        visible = {k: deepcopy(v) for k, v in page.items() if k != "id"}
        visible["contact_details"] = [env.contact(c) for c in page.get("contacts", [])]
        if "form" in page:
            # The page shows the form (fields, labels, instructions) plus its
            # current submission status; hidden fields exist for validation
            # only and are never rendered.
            form = deepcopy(page["form"])
            form["fields"] = [deepcopy(f) for f in page["form"]["fields"] if not f.get("hidden")]
            submission = env.form_submissions.get(page["form"]["id"])
            if submission is not None:
                form["submitted_at"] = submission["submitted_at"]
                if submission["status"] == "pending":
                    form["status"] = "已提交，待处理"
                else:
                    form["status"] = "已办结" if submission["status"] == "processed" else "已退回"
                    form["result_text"] = submission["result_text"]
                    if submission["evidence"]:
                        form["evidence"] = [{k: deepcopy(env.evidence[ev][k]) for k in
                            ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")}
                            for ev in submission["evidence"]]
                        # Positive confirmation: the processed form is an official
                        # conclusion channel and the receipt carries written evidence.
                        form["evidence_note"] = ("本表单办结结论为正式书面凭证，已随页面送达"
                                                 "（evidence，含编号、签发人与内容），其证据编号可在最终提交中引用。")
            visible["form"] = form
        # Pages can be revised during the episode; this is when the returned
        # content last changed (the task start for never-updated pages).
        visible["last_updated"] = stamp(env.page_updated_at.get(url)) if url in env.page_updated_at \
            else page.get("published_at", stamp(env.now))
        # Published documents linked from the page are listed but their content
        # only arrives through fetch_document.
        for document in visible.get("documents", []):
            document.pop("facts", None)
            document.pop("issuer", None)
        return visible

    def send_email(self, recipient, text, fields=None, case_id=None):
        """Send mail to a mailbox address. The receipt is issued at send time and
        is indistinguishable between delivery and a black-hole address; whether
        the recipient is responsible for the request is only decided when the
        mail is read, and mismatches are answered with a referral email."""
        env = self._env
        if not isinstance(text, str) or (fields is not None and not isinstance(fields, dict)):
            raise ValueError("text must be a string and fields must be an object")
        if not isinstance(recipient, str) or recipient.count("@") != 1 or not recipient.split("@")[0] or not recipient.split("@")[1]:
            raise ValueError("recipient must be an email address")
        if env.finished or env.now >= env.deadline:
            raise ValueError("Episode is closed for new messages")
        actor_id = env.email_to_actor.get(recipient)
        if actor_id is not None and actor_id not in env.known_contacts:
            raise PermissionError(
                "Contact has not been discovered; recipient must be the email address of "
                "an already discovered contact")
        if env.agent_sends >= env.task["public"]["message_budget"]:
            raise ValueError("Message budget exhausted")
        env.agent_sends += 1
        env.record("agent_send", recipient=recipient, text=text, fields=fields or {}, channel="email")
        existing = env.cases[case_id] if case_id else None
        if existing and (existing["actor"] != actor_id or existing["parent"]):
            raise PermissionError("Case is not this agent's conversation")
        if actor_id is None:
            # Unknown mailbox: the delivery receipt looks normal, but nobody
            # ever reads this mail and no case is opened. Waiting is the only
            # way for the agent to notice.
            env.case_serial += 1
            dead_id = f"CASE-{env.case_serial:04d}"
            env.record("dead_letter", case_id=dead_id, recipient=recipient)
            return {"case_id": dead_id, "status": "received", "at": stamp(env.now)}
        actor = env.actors[actor_id]
        view = {"actor_id": actor_id, "name": actor.spec["name"], "role": actor.spec["role"],
                "instructions": actor.spec["recipient"]["instructions"], "message": text,
                "fields": deepcopy(fields or {}), "now": stamp(env.now), "history": deepcopy(actor.history),
                "existing_workflow_id": existing["workflow"]["id"]
                    if existing and existing["workflow"] and existing["state"] in {"new", "needs_information"} else None,
                "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields", "accept_after", "accept_before") if k in w} for w in actor.spec["workflows"]],
                "local_cases": [{"id": cid, "state": env.cases[cid]["state"]} for cid in actor.cases]}
        actor.history.append({"role": "agent", "text": text, "fields": deepcopy(fields or {}), "case_id": case_id, "at": stamp(env.now)})
        if hasattr(actor.recipient, "route"):
            decision = env.recipient_call(actor, "route", view)
            workflow_id = decision["workflow_id"]
            fields = env.canonicalize_fields({**decision["fields"], **(fields or {})})
        elif existing and existing["workflow"] and existing["state"] in {"new", "needs_information"}:
            # Continuing an open case keeps its workflow; the routed followup
            # on a closed or in-flight case below is matched fresh instead.
            workflow_id = existing["workflow"]["id"]
            fields = env.canonicalize_fields(fields)
        else:
            workflow_id = env.recipient_call(actor, "choose", view)
            fields = env.canonicalize_fields(fields)
        if case_id is None and actor_id is not None:
            # A fresh letter that belongs to an already open conversation is a
            # follow-up, not a rival case: routing matched the same workflow
            # (progress ping, restated or corrected values), or matched nothing
            # while exactly one agent case is in flight here. Without this,
            # every ping without a case reference spawned a duplicate case
            # competing with the original queue, or drew a cold referral from
            # a person who is actively serving the sender.
            in_flight = [c for c in (env.cases[cid] for cid in actor.cases)
                         if c.get("origin") == "agent" and not c.get("parent")
                         and c["workflow"] is not None
                         and c["state"] not in {"replied", "failed"}]
            if workflow_id is not None:
                same = [c for c in in_flight if c["workflow"]["id"] == workflow_id]
                merged = same[-1] if same else None
            else:
                merged = in_flight[-1] if len(in_flight) == 1 else None
            if merged is not None:
                case_id = merged["id"]
                existing = merged
        if case_id:
            case = env.cases[case_id]
            if case["actor"] != actor_id or case["parent"]:
                raise PermissionError("Case is not this agent's conversation")
            if case["state"] in {"new", "needs_information"}:
                # A followup on an unadmitted or incomplete case supplies fields;
                # admission is deferred to the recipient's work hours either way.
                case["fields"].update(deepcopy(fields or {}))
                case["correspondence"].append(text)
                if case.get("origin") == "agent":
                    env.enqueue_admission(actor, case_id)
                else:
                    env.start(case)
            elif workflow_id is not None:
                # A follow-up on a closed or in-flight case carrying a genuinely
                # new or changed request is re-routed like any fresh mail: it
                # opens a new case with the normal admission delay, so it cannot
                # skip the recipient's queue or restart the original one. A
                # progress ping with unchanged fields only acknowledges; it must
                # not spawn a duplicate internal case that competes with (and
                # can push past the deadline) the original one.
                # A progress ping (empty or restated fields) only acknowledges;
                # only fields the follow-up actually carries and that change an
                # existing value count as material.
                new_fields = fields or {}
                material = (case["state"] in {"replied", "failed"}
                            or any(case["fields"].get(k) != v
                                   for k, v in new_fields.items()
                                   if k in case["fields"])
                            or any(k not in case["fields"] for k in new_fields))
                if not material:
                    eta = env.eta_clause(case)
                    env.emit(case, f"您好，我是{actor.spec['name']}。您的事项已在办理中，受理时间和处理顺序保持不变。{eta or '办结后会书面回复。'}如有其他问题，欢迎随时来信。",
                             status="acknowledgement")
                    return {"case_id": case_id, "status": "received", "at": stamp(env.now)}
                reopened = env.new_case(actor_id, workflow_id, fields or {}, origin="agent")
                reopened["correspondence"].append(text)
                env.record("followup_reopened", case_id=reopened["id"], original_case=case_id)
                return {"case_id": reopened["id"], "status": "received", "at": stamp(env.now)}
            else:
                # Following up is observable, but does not skip an internal queue.
                env.emit(case, f"您好，我是{actor.spec['name']}。已收到您的跟进邮件；原事项的受理时间和处理顺序保持不变。{env.eta_clause(case, case['step'])}这封邮件未匹配到我需处理的新事项；如需办理其他业务，请在邮件中说明具体内容。如有其他问题，欢迎随时来信。",
                         status="acknowledgement")
            return {"case_id": case_id, "status": "received", "at": stamp(env.now)}
        if workflow_id is None:
            # The request matches none of this person's workflows: not their
            # responsibility. The mismatch is noticed when the mail is read and
            # answered with a referral email, not at send time.
            case = env.new_unrouted_case(actor_id, fields or {})
            return {"case_id": case["id"], "status": "received", "at": stamp(env.now)}
        if workflow_id not in {w["id"] for w in actor.spec["workflows"]}:
            raise PermissionError("Undeclared workflow")
        case = env.new_case(actor_id, workflow_id, fields or {}, origin="agent")
        case["correspondence"].append(text)
        return {"case_id": case["id"], "status": "received", "at": stamp(env.now)}

    def call(self, recipient, text, fields=None):
        """Synchronous phone call: only answered inside the recipient's work hours.

        Quick interactions complete during the call; longer workflows continue
        asynchronously and the written reply later reaches the inbox without
        evidence attachments, since spoken answers issue no documents.
        """
        env = self._env
        if not isinstance(text, str) or (fields is not None and not isinstance(fields, dict)):
            raise ValueError("text must be a string and fields must be an object")
        if env.finished or env.now >= env.deadline:
            raise ValueError("Episode is closed for new calls")
        if recipient not in env.known_contacts:
            raise PermissionError(
                "Contact has not been discovered; recipient must be the contact's id "
                "from the contact card, not a name, email address, or phone number")
        actor = env.actors[recipient]
        if "phone" not in actor.spec["contact_details"]:
            raise ValueError("Contact has no phone number")
        if env.agent_sends >= env.task["public"]["message_budget"]:
            raise ValueError("Message budget exhausted")
        env.agent_sends += 1
        env.record("agent_call", recipient=recipient, text=text, fields=fields or {})
        if not actor.calendar.is_open(env.now):
            return {"status": "no_answer", "recipient": recipient, "at": stamp(env.now),
                    "text": "电话无人接听：当前不在对方的接听时段。"}
        view = {"actor_id": recipient, "name": actor.spec["name"], "role": actor.spec["role"],
                "instructions": actor.spec["recipient"]["instructions"], "message": "[电话] " + text,
                "fields": deepcopy(fields or {}), "now": stamp(env.now), "history": deepcopy(actor.history),
                "existing_workflow_id": None,
                "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields", "accept_after", "accept_before") if k in w} for w in actor.spec["workflows"]],
                "local_cases": [{"id": cid, "state": env.cases[cid]["state"]} for cid in actor.cases]}
        actor.history.append({"role": "agent", "text": "[电话] " + text, "fields": deepcopy(fields or {}),
                              "case_id": None, "at": stamp(env.now)})
        if hasattr(actor.recipient, "route"):
            decision = env.recipient_call(actor, "route", view)
            workflow_id = decision["workflow_id"]
            fields = env.canonicalize_fields({**decision["fields"], **(fields or {})})
        else:
            workflow_id = env.recipient_call(actor, "choose", view)
            fields = env.canonicalize_fields(fields)
        if workflow_id is None:
            prompt = "请说明要办理的事项：" + "；".join(w["label"] for w in actor.spec["workflows"])
            actor.history.append({"role": "recipient", "text": prompt, "at": stamp(env.now)})
            return {"status": "clarification_needed", "text": prompt}
        if workflow_id not in {w["id"] for w in actor.spec["workflows"]}:
            raise PermissionError("Undeclared workflow")
        case = env.new_case(recipient, workflow_id, fields or {}, origin="phone")
        case["correspondence"].append("[电话] " + text)
        limit = min(env.now + timedelta(minutes=60), env.deadline)
        before = len(env.messages)
        while case["state"] not in {"replied", "failed"} and not any(m["case_id"] == case["id"] for m in env.messages):
            if not env.events or env.events[0][0] > limit:
                break
            env.advance(min(env.events[0][0], limit), wake_on_message=True)
        result = {"status": "answered", "case_id": case["id"], "at": message["at"], "text": message["text"]} if (message := next((m for m in env.messages if m["case_id"] == case["id"]), None)) else {
            "status": "processing", "case_id": case["id"], "at": stamp(env.now),
            "text": "对方已记录事项并受理；处理结果稍后另行回复，请留意收件箱。"}
        if len(env.messages) > before:
            result["new_messages"] = len(env.messages) - before
            result["new_message_hint"] = "通话期间另有新邮件到达，建议调用 read_inbox 查看。"
        return result

    def read_inbox(self, after=0):
        self._env.inbox_read = max(self._env.inbox_read, len(self._env.messages))
        return {"messages": deepcopy(self._env.messages[after:]), "cursor": len(self._env.messages), "now": stamp(self._env.now)}

    def wait_until(self, until, wake_on_message=True):
        if self._env.finished:
            raise ValueError("Episode already finished")
        before = len(self._env.messages)
        self._env.advance(until, wake_on_message)
        return self.read_inbox(before)

    # ---- Optional per-task tools ------------------------------------------------    # Enabled by listing them in the task's public["tools"]. Some carry real
    # information for their task, others are decoys that only consume budget
    # or return nothing of value; the agent must decide which to rely on.

    def _check_optional(self, name):
        if name not in self.tool_list():
            raise PermissionError(f"Tool {name} is not available in this task")

    def _budgeted(self):
        """Communication-style optional tools consume the message budget."""
        env = self._env
        if env.agent_sends >= env.task["public"]["message_budget"]:
            raise ValueError("Message budget exhausted")
        env.agent_sends += 1

    def query_case_status(self, case_id):
        """Look up the current state of one of the agent's own cases."""
        self._check_optional("query_case_status")
        env = self._env
        if not isinstance(case_id, str):
            raise ValueError("case_id must be a string")
        case = env.cases.get(case_id)
        if case is None:
            raise ValueError("Unknown case id")
        actor = env.actors[case["actor"]]
        result = {"case_id": case_id, "state": case["state"], "recipient": actor.spec["name"],
                  "now": stamp(env.now)}
        if case.get("workflow"):
            result["subject"] = case["workflow"]["label"]
        if case.get("due_at"):
            result["due_at"] = case["due_at"]
        if case.get("promised_eta"):
            result["promised_eta"] = case["promised_eta"]
        if case["state"] == "waiting_internal" and case.get("workflow"):
            tool = actor.spec["tools"][case["workflow"]["steps"][case["step"]]["tool"]]
            if tool["kind"] in {"delegate", "consult"}:
                result["waiting_on"] = env.actors[tool["target"]].spec["name"]
        env.record("agent_query_case_status", case_id=case_id)
        return result

    def fetch_document(self, url):
        """Download a document file linked from a page. Page bodies only list
        the document; its content arrives through this tool. Some documents
        carry official figures and constitute written evidence."""
        self._check_optional("fetch_document")
        env = self._env
        if (not isinstance(url, str) or not url.startswith("https://")
                or ".bench/" not in url or " " in url):
            raise ValueError("url must be a https://*.bench/files/* document address")
        document = None
        for page in env.task["public"]["pages"]:
            for candidate in page.get("documents", []):
                if candidate["url"] == url:
                    document = candidate
        if document is None:
            raise ValueError("Unknown document address")
        result = {"url": url, "title": document["title"], "text": document["text"],
                  "at": stamp(env.now), "evidence": []}
        for fact_id in document.get("facts", []):
            ev_id = env.issue_public(fact_id, document["issuer"])
            ev = env.evidence[ev_id]
            result["evidence"].append({key: deepcopy(ev[key]) for key in
                ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")})
        if result["evidence"]:
            # Written material with attached records. The note deliberately
            # stays neutral and identical for formal and reference documents:
            # the environment never labels attestation authority per file —
            # the agent must check issuers itself (contract section on oral /
            # uncertain information states the general rule).
            result["note"] = ("书面材料已下载，随附本文件载明的记录与对应证据编号"
                              "（evidence，含编号、签发人与内容），其证据编号可在最终提交中引用。")
        else:
            result["note"] = "本文件为普通说明材料，不随下载签发书面凭证。"
        env.record("agent_fetch_document", url=url, facts=document.get("facts", []))
        return result

    def check_schedule(self, contact, date=None, days=7):
        """List a discovered contact's upcoming open hours in their local time."""
        self._check_optional("check_schedule")
        env = self._env
        if contact not in env.known_contacts:
            raise PermissionError("Contact has not been discovered")
        if days < 1 or days > 31:
            raise ValueError("days must be between 1 and 31")
        actor = env.actors[contact]
        if isinstance(date, str):
            from datetime import date as DateClass
            try:
                day = DateClass.fromisoformat(date)
            except ValueError:
                raise ValueError("date must be YYYY-MM-DD") from None
            if len(date) != 10:
                raise ValueError("date must be YYYY-MM-DD")
        else:
            day = env.now.astimezone(actor.calendar.zone).date()
        windows = []
        for _ in range(days):
            for start, end in actor.calendar.intervals(day):
                windows.append({"date": day.isoformat(),
                                "start": start.astimezone(actor.calendar.zone).strftime("%H:%M"),
                                "end": end.astimezone(actor.calendar.zone).strftime("%H:%M")})
            day += timedelta(days=1)
        env.record("agent_check_schedule", contact=contact, date=date, days=days)
        return {"contact": contact, "name": actor.spec["name"],
                "timezone": actor.calendar.spec["timezone"], "open_hours": windows}

    def lookup_directory(self, query):
        """Search the public organizational directory by name or role. Not
        everyone is listed on web pages; the directory is a separate channel."""
        self._check_optional("lookup_directory")
        env = self._env
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        needle = query.strip().casefold()
        results = []
        for actor in env.task["actors"]:
            if needle in actor["name"].casefold() or needle in actor["role"].casefold():
                env.known_contacts.add(actor["id"])
                results.append(env.contact(actor["id"]))
        env.record("agent_lookup_directory", query=query, matches=[r["id"] for r in results])
        return {"results": results,
                "note": "机构公开通讯录检索结果；未命中时不代表对方不存在，可更换关键词再试。"}

    def request_callback(self, contact, topic=None):
        """Register a callback request. No callback time is promised and the
        request does not advance any pending matter."""
        self._check_optional("request_callback")
        env = self._env
        if contact not in env.known_contacts:
            raise PermissionError("Contact has not been discovered")
        self._budgeted()
        env.record("agent_request_callback", contact=contact, topic=topic)
        return {"status": "registered", "at": stamp(env.now),
                "text": "回拨请求已登记，工作人员将在方便时与您联系；本渠道不承诺具体回电时间，也不影响邮件事项的办理进度。"}

    def leave_note(self, contact, text):
        """Leave a note for a contact. Notes are recorded but are not answered
        and do not advance any pending matter."""
        self._check_optional("leave_note")
        env = self._env
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        if contact not in env.known_contacts:
            raise PermissionError("Contact has not been discovered")
        self._budgeted()
        env.record("agent_leave_note", contact=contact, text=text)
        return {"status": "recorded", "at": stamp(env.now),
                "text": "留言已记录；留言不作为正式来件处理，也不会获得单独回复。"}

    # ---- Hidden per-task tools ---------------------------------------------------
    # Unlocked through discover_tools; behavior is parameterized entirely by
    # the authored params. The engine validates arguments per kind.

    def _call_hidden_tool(self, name, **kwargs):
        env = self._env
        spec = env.hidden_tools[name]
        if spec["kind"] == "form":
            return self._hidden_form(name, spec, kwargs)
        if spec["kind"] == "status":
            return self._hidden_status(name, spec, kwargs)
        if spec["kind"] == "catalog":
            return self._hidden_catalog(name, spec, kwargs)
        if spec["kind"] == "select":
            return self._hidden_select(name, spec, kwargs)
        if spec["kind"] == "dialogue":
            return self._hidden_dialogue(name, spec, kwargs)
        return self._hidden_record(name, spec, kwargs)

    def _hidden_form(self, name, spec, kwargs):
        """Submit a web form: required fields are validated against the form's
        own field list; an authored `expect` mapping decides accept/reject (any
        value passes for keys it omits). Processing completes later at an
        authored virtual time; until then the page shows 已提交，待处理."""
        env = self._env
        if set(kwargs) != {"fields"} or not isinstance(kwargs.get("fields"), dict):
            raise ValueError("hidden form tool takes a single object argument: fields")
        params = spec["params"]
        form_id = params["form"]
        _, form = env.forms[form_id]
        submission = env.form_submissions.get(form_id)
        if submission and submission["status"] in {"pending", "processed"}:
            raise ValueError("该表单此前已提交，不能重复提交；处理结果请重访页面或查询状态确认。")
        values = kwargs["fields"]
        missing = [f["label"] for f in form["fields"]
                   if f.get("required") and values.get(f["name"]) in (None, "")]
        if missing:
            raise ValueError("表单必填字段缺失：" + "、".join(missing))
        expect = params.get("expect") or {}
        accepted = all(field_value_equivalent(values.get(key), expected)
                       for key, expected in expect.items())
        if params.get("process_at"):
            at = max(env.now, parse(params["process_at"]))
        else:
            calendar = Calendar(env.task["calendars"][params.get("calendar", "office")])
            at = calendar.add_business(env.now, params.get("process_delay", 60))
        env.form_submissions[form_id] = {"status": "pending", "submitted_at": stamp(env.now),
                                         "values": deepcopy(values), "accepted": accepted,
                                         "result_text": None, "evidence": []}
        env.record("agent_form_submitted", tool=name, form=form_id, accepted=accepted)
        env.enqueue(at, "form_processed", form_id)
        return {"status": "submitted", "form": form_id, "at": stamp(env.now),
                "text": "表单已提交，等待处理；处理结果不会主动推送。办结后重访相关页面或查询状态，均可取得办结结论与书面凭证。"}

    def _hidden_status(self, name, spec, kwargs):
        """Query an authored external status record (permit/parcel/registration
        style): staged states keyed by virtual times, optionally superseded by
        a linked form submission's pending/processed/rejected outcome."""
        env = self._env
        query = kwargs.get("query")
        if set(kwargs) - {"query"} or (query is not None and not isinstance(query, str)):
            raise ValueError("hidden status tool takes a single optional string argument: query")
        needle = (query or "").strip().casefold()
        records = [r for r in spec["params"]["records"]
                   if not needle or needle in (r["key"] + " " + r.get("label", "")).casefold()]
        env.record("agent_hidden_status", tool=name, query=query,
                   keys=[r["key"] for r in records])
        if not records:
            return {"records": [], "now": stamp(env.now),
                    "note": "未查询到相关记录；可核对事项编号或关键词后重试。"}
        results = []
        for record in records:
            state = record.get("initial") or "暂无记录。"
            for entry in record.get("timeline", []):
                if parse(entry["at"]) <= env.now:
                    state = entry["text"]
            submission = env.form_submissions.get(record["form"]) if record.get("form") else None
            outcome = {"key": record["key"], "label": record.get("label", ""),
                       "state": state, "now": stamp(env.now)}
            if submission is not None:
                if submission["status"] == "pending":
                    outcome["state"] = f"该事项已提交，待处理（提交时间{submission['submitted_at']}）。"
                else:
                    outcome["state"] = submission["result_text"]
                    # A processed status query is an official confirmation channel
                    # and carries the issued written evidence, just like the
                    # carrying page does after a revisit (same field projection).
                    if submission["status"] == "processed" and submission["evidence"]:
                        outcome["evidence"] = [{k: deepcopy(env.evidence[ev][k]) for k in
                            ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")}
                            for ev in submission["evidence"]]
                        # Positive confirmation: the processed status query is an
                        # official channel and the written evidence is delivered.
                        outcome["evidence_note"] = ("本查询为正式办结渠道，书面凭证已随本查询送达"
                                                    "（evidence，含编号、签发人与内容），其证据编号可在最终提交中引用。")
            results.append(outcome)
        return {"records": results, "now": stamp(env.now)}

    def _hidden_record(self, name, spec, kwargs):
        """Retrieve an authored record that exists only after its precondition
        (a virtual time and/or a form having been processed); a hit issues
        evidence like fetch_document does, a miss explains why not."""
        env = self._env
        key = kwargs.get("key")
        if set(kwargs) - {"key"} or (key is not None and not isinstance(key, str)):
            raise ValueError("hidden record tool takes a single optional string argument: key")
        records = spec["params"]["records"]
        needle = (key or "").strip().casefold()
        matches = [r for r in records if not needle or needle in r["key"].casefold()] \
            if needle else (records if len(records) == 1 else [])
        if not matches:
            env.record("agent_hidden_record", tool=name, key=key, found=False)
            return {"found": False, "records": [], "note": "未查询到该记录；可核对记录编号后重试。"}
        results = []
        for record in matches:
            if record.get("available_at") and env.now < parse(record["available_at"]):
                results.append({"key": record["key"], "found": False,
                                "text": "该记录尚未生成，请稍后再查。"})
                continue
            submission = env.form_submissions.get(record["requires_form"]) if record.get("requires_form") else None
            if submission is None or submission["status"] != "processed":
                results.append({"key": record["key"], "found": False,
                                "text": "该记录尚未生成或暂不可查询，请稍后再查。"})
                continue
            entry = {"key": record["key"], "found": True, "title": record["title"],
                     "text": record["text"], "at": stamp(env.now), "evidence": []}
            for fact_id in record.get("facts", []):
                ev_id = env.issue_public(fact_id, record["issuer"])
                ev = env.evidence[ev_id]
                entry["evidence"].append({k: deepcopy(ev[k]) for k in
                    ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")})
            results.append(entry)
        env.record("agent_hidden_record", tool=name, key=key,
                   found=[r["key"] for r in results if r["found"]])
        return {"records": results, "now": stamp(env.now)}

    def _hidden_catalog(self, name, spec, kwargs):
        """Search an authored inventory (flights, menus, products, schedules):
        rows filtered by query terms, honoring per-row availability windows.
        A row may carry facts issued on retrieval (official listing evidence)."""
        env = self._env
        query = kwargs.get("query")
        if set(kwargs) - {"query"} or (query is not None and not isinstance(query, str)):
            raise ValueError("hidden catalog tool takes a single optional string argument: query")
        needle = (query or "").strip().casefold()
        rows = []
        for entry in spec["params"]["entries"]:
            if not env._entry_current(entry):
                continue
            if needle and not any(u in (entry["id"] + " " + entry["title"] + " "
                    + entry.get("text", "") + " " + " ".join(f"{k}:{v}" for k, v in entry.get("fields", {}).items())).casefold()
                    for u in self._query_units(needle)):
                continue
            row = {"id": entry["id"], "title": entry["title"], "text": entry.get("text", ""),
                   "fields": deepcopy(entry.get("fields", {}))}
            evidence = []
            for fact_id in entry.get("facts", []):
                fact = env.task["facts"][fact_id]
                if fact.get("available_at") and env.now < parse(fact["available_at"]):
                    continue
                ev_id = env.issue_public(fact_id, entry["issuer"])
                ev = env.evidence[ev_id]
                evidence.append({k: deepcopy(ev[k]) for k in
                    ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")})
            if evidence:
                row["evidence"] = evidence
                row["evidence_note"] = ("This listing is an official channel; the written evidence above "
                                        "has been delivered and its ids may be cited in the final submission.")
            rows.append(row)
        env.record("agent_hidden_catalog", tool=name, query=query,
                   entries=[r["id"] for r in rows])
        if not rows:
            return {"results": [], "now": stamp(env.now),
                    "note": "No matching listings right now; adjust the query or check back later."}
        return {"results": rows, "now": stamp(env.now)}

    def _query_units(self, needle):
        units = set()
        for term in needle.split():
            for run in re.findall(r"[a-z0-9]+|[一-鿿]+", term):
                if run[0].isascii() or len(run) == 1:
                    units.add(run)
                else:
                    units.update(run[i:i + 2] for i in range(len(run) - 1))
        return units

    def _hidden_select(self, name, spec, kwargs):
        """Pick one option out of a linked catalog tool and commit it: the
        entry must still be listed when the booking is processed; an authored
        hold can lapse first. Processing completes later at an authored virtual
        time and accepted selections issue written evidence, like a form."""
        env = self._env
        params = spec["params"]
        # Calling the select tool with {"query": ...} reads back the current
        # selection state (the agent's only channel for the processed outcome);
        # calling it with {"entry": ...} submits a new selection.
        if set(kwargs) == {"query"} and (kwargs["query"] is None or isinstance(kwargs["query"], str)):
            selection = env.selections.get(name)
            env.record("agent_selection_status", tool=name, query=kwargs["query"])
            if selection is None:
                return {"status": "no_selection", "now": stamp(env.now),
                        "note": "No selection has been made through this service yet."}
            outcome = {"status": selection["status"], "entry": selection["entry"],
                       "submitted_at": selection["submitted_at"], "now": stamp(env.now),
                       "state": selection["result_text"] or "The selection is being processed."}
            if selection["status"] == "processed" and selection["evidence"]:
                outcome["evidence"] = [{k: deepcopy(env.evidence[ev][k]) for k in
                    ("id", "issuer", "issued_at", "text", "value", "valid_until", "kind")}
                    for ev in selection["evidence"]]
                outcome["evidence_note"] = ("This query is an official confirmation channel; the written "
                                            "evidence above has been delivered and its ids may be cited "
                                            "in the final submission.")
            return outcome
        if set(kwargs) != {"entry"} or not isinstance(kwargs.get("entry"), str):
            raise ValueError("hidden select tool takes either {\"entry\": option_id} to select, "
                             "or {\"query\": text} to check the current selection status")
        selection = env.selections.get(name)
        if selection and selection["status"] in {"pending", "processed"}:
            raise ValueError("This service already has an active or completed selection; "
                             "check its status instead of selecting again.")
        entry = env._catalog_entry(params["catalog"], kwargs["entry"].strip())
        accepted = entry is not None and env._entry_current(entry)
        if accepted:
            expect_entry = params.get("expect_entry")
            if expect_entry is not None and entry["id"] != expect_entry:
                accepted = False
            for key, expected in (params.get("expect") or {}).items():
                if not field_value_equivalent(entry.get("fields", {}).get(key), expected):
                    accepted = False
        if params.get("process_at"):
            at = max(env.now, parse(params["process_at"]))
        else:
            calendar = Calendar(env.task["calendars"][params.get("calendar", "office")])
            at = calendar.add_business(env.now, params.get("process_delay", 60))
        env.selections[name] = {"entry": kwargs["entry"].strip(), "catalog": params["catalog"],
                                "status": "pending", "submitted_at": stamp(env.now),
                                "accepted": accepted, "result_text": None, "evidence": [],
                                "params": params}
        env.record("agent_selection_submitted", tool=name, entry=kwargs["entry"], accepted=accepted)
        env.enqueue(at, "selection_processed", name)
        if params.get("hold_minutes"):
            env.enqueue(env.now + timedelta(minutes=params["hold_minutes"]),
                        "selection_expired", name)
        hold_note = ""
        if params.get("hold_minutes"):
            hold_note = (f" The option is held until {stamp(env.now + timedelta(minutes=params['hold_minutes']))} "
                         "and lapses if not confirmed by then.")
        return {"status": "submitted", "service": name, "at": stamp(env.now),
                "text": "The selection has been submitted and is being processed; "
                        "the outcome will not be pushed. Query the service status or re-check later to "
                        "obtain the conclusion and any written confirmation." + hold_note}

    def _hidden_dialogue(self, name, spec, kwargs):
        """Ask the task's principal (the user being assisted) a question.
        Replies are authored canned answers matched by keyword: the agent must
        ask the right question to surface a fact that was never in any page.
        User statements are information, not attested evidence."""
        env = self._env
        question = kwargs.get("question")
        if set(kwargs) != {"question"} or not isinstance(question, str) or not question.strip():
            raise ValueError("hidden dialogue tool takes a single string argument: question")
        params = spec["params"]
        needle = question.casefold()
        matched = None
        for rule in params.get("rules", []):
            if any(k.casefold() in needle for k in rule.get("keywords", [])):
                matched = rule
                break
        if matched is None:
            answer = params.get("default") or \
                "I don't have anything more to say about that; please work from what you already have."
        else:
            answer = matched["answer"]
        env.record("agent_dialogue", tool=name, question=question,
                   matched=matched is not None)
        return {"speaker": params.get("persona", "the user"), "answer": answer, "at": stamp(env.now)}

    def submit_answer(self, answer):
        if self._env.finished:
            raise ValueError("Only one final submission is allowed")
        self._env.finished = True
        return self._env.evaluate(answer)
