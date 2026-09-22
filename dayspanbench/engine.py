"""Stateful recipients, scoped tools, FIFO workers, handoffs and event scheduling.

This module is trusted environment code. Agents get only AgentTools, never this
object, the task fixtures, the host filesystem, or the private audit log.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import timedelta
import heapq
import json
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
        self.actors = {
            actor["id"]: ActorState(actor, Calendar(task["calendars"][actor["calendar"]]), self.now,
                (recipient.get(actor["id"]) or RuleRecipient()) if isinstance(recipient, dict)
                else (recipient or RuleRecipient()))
            for actor in task["actors"]
        }
        self.known_contacts = set(task["public"]["initial_contacts"])
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
        self.known_contacts.update(contacts)
        message = {"id": f"MSG-{len(self.messages)+1:04d}", "at": stamp(self.now),
                   "from": case["actor"], "case_id": case["id"], "status": status,
                   "channel": "phone" if case.get("origin") == "phone" else "email",
                   "text": text, "evidence": [], "contacts": [self.contact(cid) for cid in contacts]}
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
        """Email from the agent is first read inside the recipient's work hours."""
        return actor.calendar.add_business(self.now, self.rng.randint(10, 40))

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
                self.emit(case, "请补充以下信息后继续处理：" + ", ".join(missing), status="needs_information")
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
                lines = [actor.spec["recipient"]["reply_prefix"]]
                lines += [self.evidence[e]["text"] for e in case["evidence"]]
                if case["contacts"]:
                    lines.append("可继续联系：" + "、".join(self.actors[c].spec["name"] for c in case["contacts"]))
                self.emit(case, "\n".join(lines), case["evidence"], list(dict.fromkeys(case["contacts"])))
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
            self.emit(case, reason, status="failed")

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

    def observe(self):
        env = self._env
        public = deepcopy(env.task["public"])
        # Search results only: page bodies and their contact cards require visit_page.
        public["pages"] = [{"id": p["id"], "title": p["title"], "snippet": p.get("snippet", "")}
                           for p in env.task["public"]["pages"]]
        return {"now": stamp(env.now), "deadline": stamp(env.deadline), "task": public,
                "contacts": [env.contact(c) for c in sorted(env.known_contacts)]}

    def web_search(self, query):
        terms = query.casefold().split()
        pages = self._env.task["public"]["pages"]
        return [{"id": p["id"], "title": p["title"], "snippet": p.get("snippet", "")} for p in pages
                if not terms or any(t in (p["title"] + p["text"] + p.get("snippet", "")).casefold() for t in terms)]

    def visit_page(self, page_id):
        env = self._env
        page = next(p for p in env.task["public"]["pages"] if p["id"] == page_id)
        env.known_contacts.update(page.get("contacts", []))
        return {**deepcopy(page), "contact_details": [env.contact(c) for c in page.get("contacts", [])]}

    def send_message(self, recipient, text, fields=None, channel="email", case_id=None):
        env = self._env
        if not isinstance(text, str) or (fields is not None and not isinstance(fields, dict)):
            raise ValueError("text must be a string and fields must be an object")
        if env.finished or env.now >= env.deadline:
            raise ValueError("Episode is closed for new messages")
        if recipient not in env.known_contacts:
            raise PermissionError("Contact has not been discovered")
        if channel != "email":
            raise ValueError("send_message only supports email; use call for phone")
        actor = env.actors[recipient]
        if "email" not in actor.spec["contact_details"]:
            raise ValueError("Contact has no email address")
        if env.agent_sends >= env.task["public"]["message_budget"]:
            raise ValueError("Message budget exhausted")
        env.agent_sends += 1
        env.record("agent_send", recipient=recipient, text=text, fields=fields or {}, channel=channel)
        existing = env.cases[case_id] if case_id else None
        if existing and (existing["actor"] != recipient or existing["parent"]):
            raise PermissionError("Case is not this agent's conversation")
        view = {"actor_id": recipient, "name": actor.spec["name"], "role": actor.spec["role"],
                "instructions": actor.spec["recipient"]["instructions"], "message": text,
                "fields": deepcopy(fields or {}), "now": stamp(env.now), "history": deepcopy(actor.history),
                "existing_workflow_id": existing["workflow"]["id"] if existing else None,
                "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields")} for w in actor.spec["workflows"]],
                "local_cases": [{"id": cid, "state": env.cases[cid]["state"]} for cid in actor.cases]}
        actor.history.append({"role": "agent", "text": text, "fields": deepcopy(fields or {}), "case_id": case_id, "at": stamp(env.now)})
        if hasattr(actor.recipient, "route"):
            decision = env.recipient_call(actor, "route", view)
            workflow_id = decision["workflow_id"]
            fields = {**decision["fields"], **(fields or {})}
        else:
            workflow_id = existing["workflow"]["id"] if existing else env.recipient_call(actor, "choose", view)
        if case_id:
            case = env.cases[case_id]
            if case["actor"] != recipient or case["parent"]:
                raise PermissionError("Case is not this agent's conversation")
            if case["state"] in {"new", "needs_information"}:
                # A followup on an unadmitted or incomplete case supplies fields;
                # admission is deferred to the recipient's work hours either way.
                case["fields"].update(deepcopy(fields or {}))
                if case.get("origin") == "agent":
                    env.enqueue_admission(actor, case_id)
                else:
                    env.start(case)
            else:
                # Following up is observable, but does not skip an internal queue.
                env.emit(case, "已收到跟进；原受理时间和处理队列保持不变。", status="acknowledgement")
            return {"case_id": case_id, "status": "received", "at": stamp(env.now)}
        if workflow_id is None:
            prompt = "请说明要办理的事项：" + "；".join(w["label"] for w in actor.spec["workflows"])
            actor.history.append({"role": "recipient", "text": prompt, "at": stamp(env.now)})
            return {"status": "clarification_needed", "text": prompt}
        if workflow_id not in {w["id"] for w in actor.spec["workflows"]}:
            raise PermissionError("Undeclared workflow")
        case = env.new_case(recipient, workflow_id, fields or {}, origin="agent")
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
            raise PermissionError("Contact has not been discovered")
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
            fields = {**decision["fields"], **(fields or {})}
        else:
            workflow_id = env.recipient_call(actor, "choose", view)
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
