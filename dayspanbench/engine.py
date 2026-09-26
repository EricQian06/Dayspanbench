"""Stateful recipients, scoped tools, FIFO workers, handoffs and event scheduling.

This module is trusted environment code. Agents get only AgentTools, never this
object, the task fixtures, the host filesystem, or the private audit log.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import timedelta
import heapq
import json
import re
import random
from pathlib import Path

from .calendar import Calendar, parse, stamp
from .recipient import RuleRecipient
from .scoring import evidence_matches, equivalent, evaluate as evaluate_outcome
from .llm import SimulatorError


TRANSITIONS = {
    "new": {"needs_information", "queued", "failed"},
    "needs_information": {"queued", "failed"},
    "queued": {"working", "failed"},
    "working": {"queued", "waiting_internal", "replied", "failed"},
    "waiting_internal": {"queued", "failed"},
    "replied": set(), "failed": set(),
}

# The complete agent-facing tool surface; serve.py allowlists the same names.
PUBLIC_TOOLS = ("observe", "recall_task", "web_search", "visit_page",
                "send_email", "call", "read_inbox", "wait_until", "submit_answer")

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
    """Reduce a quantity-like string to (number, canonical unit); None otherwise."""
    import unicodedata
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKC", value).strip().casefold().replace(" ", "").replace("，", ",")
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([a-z一-鿿,]*)", text)
    if not match or match.group(2) not in _UNIT_LOOKUP:
        return None
    return (float(match.group(1)), _UNIT_LOOKUP[match.group(2)])


def field_value_equivalent(value, expected):
    """Exact match, or the same quantity written with a synonym unit."""
    if value == expected:
        return True
    return (isinstance(value, str) and isinstance(expected, str)
            and normalize_field_value(value) is not None
            and normalize_field_value(value) == normalize_field_value(expected))


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

    def emit(self, case, text, evidence_ids=None, contacts=None, status="reply"):
        if case.get("parent"):
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
                "contacts": [], "parent": parent, "origin": origin, "received_at": stamp(self.now)}
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



    def start(self, case):
        workflow = case["workflow"]
        if workflow.get("accept_before") and self.now >= parse(workflow["accept_before"]):
            self.transition(case, "failed")
            self.complete_failure(case, "该轮受理截止时间已过，无法按原时间完成。")
            return
        missing = [key for key in workflow.get("required_fields", []) if case["fields"].get(key) is None or case["fields"].get(key) == ""]
        # Scenario-specific identifiers must correspond to the user's actual case.
        # Free-form intent remains the recipient adapter's responsibility.
        for key in workflow.get("required_fields", []):
            expected = self.task["public"]["user_fields"].get(key)
            if key not in missing and expected is not None and case["fields"].get(key) != expected:
                missing.append(key + "（与任务信息不符）")
        admission_evidence = []
        for key, requirement in workflow.get("evidence_fields", {}).items():
            if key in missing:
                continue
            obtained = [ev["id"] for ev in self.evidence.values()
                        if evidence_matches(ev, requirement, self.now)
                        and equivalent(ev["value"], case["fields"].get(key), requirement["normalization"])]
            admission_evidence.extend(obtained)
            if not obtained:
                missing.append(key + "（须先取得有效可核验凭证）")
        if missing:
            if case["state"] == "new":
                self.transition(case, "needs_information")
            if case.get("parent"):
                self.transition(case, "failed")
                self.complete_failure(case, "内部转交缺少材料：" + ", ".join(missing))
            else:
                self.emit(case, f"您好，我是{self.actors[case['actor']].spec['name']}。您提交的材料尚不完整，请补充以下信息后我们再继续处理：{', '.join(missing)}。如有其他问题，欢迎随时来信。", status="needs_information")
            return
        case["admitted_at"] = stamp(self.now)
        case["admission_evidence"] = admission_evidence
        self.schedule_step(case)

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
        self.record("scheduled", case_id=case["id"], actor=case["actor"], step=step["id"],
                    start_at=stamp(start), due_at=stamp(end), tool=step["tool"])
        self.enqueue(start, "start", case["id"])
        self.enqueue(end, "complete", case["id"])

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
            # admissible and continues to the next step without closing.
            self.emit(case, f"您好，我是{actor.spec['name']}。您提交的材料已核验齐全，本事项已受理并按流程转办，办结后会书面回复您。",
                      status="acknowledgement")
        elif tool["kind"] == "delegate":
            self.transition(case, "waiting_internal")
            self.new_case(tool["target"], tool["workflow"],
                          {k: case["fields"][k] for k in tool["forward_fields"] if k in case["fields"]},
                          parent=case["id"], origin=case.get("origin"))
            return "waiting"
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

    def observe(self):
        env = self._env
        return {"now": stamp(env.now), "tools": list(PUBLIC_TOOLS),
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
        return {"results": results,
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
                "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields")} for w in actor.spec["workflows"]],
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
        if case_id:
            case = env.cases[case_id]
            if case["actor"] != actor_id or case["parent"]:
                raise PermissionError("Case is not this agent's conversation")
            if case["state"] in {"new", "needs_information"}:
                # A followup on an unadmitted or incomplete case supplies fields;
                # admission is deferred to the recipient's work hours either way.
                case["fields"].update(deepcopy(fields or {}))
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
                    env.emit(case, f"您好，我是{actor.spec['name']}。您的事项已在办理中，受理时间和处理顺序保持不变，办结后会书面回复。如有其他问题，欢迎随时来信。",
                             status="acknowledgement")
                    return {"case_id": case_id, "status": "received", "at": stamp(env.now)}
                reopened = env.new_case(actor_id, workflow_id, fields or {}, origin="agent")
                env.record("followup_reopened", case_id=reopened["id"], original_case=case_id)
                return {"case_id": reopened["id"], "status": "received", "at": stamp(env.now)}
            else:
                # Following up is observable, but does not skip an internal queue.
                env.emit(case, f"您好，我是{actor.spec['name']}。已收到您的跟进邮件；原事项的受理时间和处理顺序保持不变。这封邮件未匹配到我需处理的新事项；如需办理其他业务，请在邮件中说明具体内容。如有其他问题，欢迎随时来信。",
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
                "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields")} for w in actor.spec["workflows"]],
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
        limit = min(env.now + timedelta(minutes=60), env.deadline)
        while case["state"] not in {"replied", "failed"} and not any(m["case_id"] == case["id"] for m in env.messages):
            if not env.events or env.events[0][0] > limit:
                break
            env.advance(min(env.events[0][0], limit), wake_on_message=True)
        message = next((m for m in env.messages if m["case_id"] == case["id"]), None)
        if message:
            return {"status": "answered", "case_id": case["id"], "at": message["at"], "text": message["text"]}
        return {"status": "processing", "case_id": case["id"], "at": stamp(env.now),
                "text": "对方已记录事项并受理；处理结果稍后另行回复，请留意收件箱。"}

    def read_inbox(self, after=0):
        self._env.inbox_read = max(self._env.inbox_read, len(self._env.messages))
        return {"messages": deepcopy(self._env.messages[after:]), "cursor": len(self._env.messages), "now": stamp(self._env.now)}

    def wait_until(self, until, wake_on_message=True):
        if self._env.finished:
            raise ValueError("Episode already finished")
        before = len(self._env.messages)
        self._env.advance(until, wake_on_message)
        return self.read_inbox(before)

    def submit_answer(self, answer):
        if self._env.finished:
            raise ValueError("Only one final submission is allowed")
        self._env.finished = True
        return self._env.evaluate(answer)
