"""The world-graph runtime: evidence-driven nodes replacing the case workflow.

v0.6 design (docs/graph-workflow-redesign.md). One static directed graph per
task, authored up front. Nodes are semantic units (an inquiry, an application,
an approval); each node declares the evidence it needs. Evidence arrives as
structured marks (an NPC's LLM parses agent prose into {node, key, value}) or
as environment backfill, accumulates across multiple letters, and lights the
node deterministically when complete. No runtime "case" or "instance" exists:
business identity was fixed at author time (two inquiries are two nodes), so
the duplicate-merge and follow-up-reopen heuristics of the case model have no
successor here.

This module is pure logic over an environment-shaped clock: scheduling
(activation events, calendars), side effects and LLM calls stay with the
engine, exactly like routing.py before it. The engine drives the runtime:

    runtime = GraphRuntime(task["graph"])
    marks   = <LLM interpretation of the agent's letters>          # engine-side
    report  = runtime.mark(node_id, marks, source=..., at=...)
    for node_id in report.newly_ready:
        fire = runtime.fire(node_id)          # picks the branch, if any
        <engine executes fire["effects"], renders fire["reply"] via LLM>
        runtime.fired(node_id)                # completed / self-loop reset

Evidence slots are three-state (unfilled / filled(true) / filled(false)):
"the agent addressed this point" is separate from "the value of what they
said", so an explicit "Wednesday works" and an explicit "Wednesday does not
work" are both evidence and both light the node. Absence never fills a slot
with False — that anti-fabrication rule lives here in the schema.
"""

from copy import deepcopy
from datetime import datetime
from itertools import product as _product


def _matches(value, condition):
    """Whether a concrete slot value satisfies a branch condition. The slot is
    filled by construction here (coverage runs over reachable combinations)."""
    if isinstance(condition, dict):
        return "value" not in condition or value == condition["value"]
    if condition == "filled":
        return True
    return value == condition


class GraphSpecError(ValueError):
    """The authored graph is malformed; validation must fail the task."""


_UNFILLED = object()  # sentinel: the slot has never been addressed


def _condition_met(slot, condition):
    """Whether one slot satisfies a requirement/branch condition.

    Conditions: ``"filled"`` (any value; the default), ``True``/``False`` or a
    plain value (filled and equal), or ``{"present": bool, "value": v}``.
    """
    if isinstance(condition, dict):
        if "present" in condition and bool(condition["present"]) != slot.filled:
            return False
        if "value" in condition and (not slot.filled or slot.value != condition["value"]):
            return False
        return True
    if condition == "filled":
        return slot.filled
    if isinstance(condition, bool):
        return slot.filled and slot.value is condition
    return slot.filled and slot.value == condition


class EvidenceSlot:
    """One evidence slot on a node: three-state, optionally time-limited."""

    def __init__(self, key, spec):
        if spec.get("type") == "boolean":
            self.kind = "boolean"
        elif spec.get("type") == "enum":
            self.kind = "enum"
            self.values = list(spec.get("values", []))
            if not self.values:
                raise GraphSpecError(f"Enum slot {key} lists no values")
        else:
            self.kind = "string"
        self.key = key
        self.description = spec.get("description", "")
        # The NPC's proactive follow-up question when this slot is still
        # missing after the agent wrote to the node (distinct from
        # `description`, which addresses the interpretation LLM).
        self.question = spec.get("question", "")
        self.volatile = bool(spec.get("volatile"))
        self.valid_until = spec.get("valid_until")  # authored absolute stamp
        self.value = _UNFILLED
        self.filled_at = None
        self.source = None

    @property
    def filled(self):
        return self.value is not _UNFILLED

    def validate(self, value):
        if self.kind == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"Evidence {self.key} must be a boolean")
        elif self.kind == "enum":
            if value not in self.values:
                raise ValueError(f"Evidence {self.key} must be one of {self.values}")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"Evidence {self.key} must be a nonempty string")
        return value

    def to_public(self):
        view = {"key": self.key, "type": self.kind, "filled": self.filled,
                "volatile": self.volatile, "description": self.description}
        if self.filled:
            view.update(value=self.value, filled_at=self.filled_at)
        if self.valid_until:
            view["valid_until"] = self.valid_until
        return view


class GraphNode:
    """Runtime state of one node: collecting -> ready -> firing -> completed.

    ``kind`` drives the terminal semantics: "inquiry" nodes are self-loops
    (their volatile slots clear after each fire, so they can trigger again —
    unless the fired branch declares ``terminal: True``, which settles the
    node into its completed state instead of resetting it); "service" and
    "environment" nodes stay completed (a completed node answers repeats
    from its authored on_completed_reply and never fires twice); "revoke"
    nodes are the conversation-flavored amend mechanism (pilot TODO).
    """

    def __init__(self, spec):
        self.id = spec["id"]
        self.kind = spec.get("kind", "service")
        if self.kind not in {"service", "inquiry", "environment", "revoke"}:
            raise GraphSpecError(f"Node {self.id} has unknown kind {self.kind}")
        self.owner = spec.get("owner")
        self.title = spec.get("title", self.id)
        self.activation = spec.get("activation", {})
        self.event = spec.get("event")  # environment nodes: what backfills them
        self.branches = [deepcopy(b) for b in spec.get("branches", [])]
        # Authored derivation rules: evidence on this node that implies
        # evidence on companion nodes (e.g. confirming an evening also
        # fills the swap-check node), so one LLM mark never strands its
        # partner unfilled. Evaluated by the engine after each mark batch.
        self.derive = [deepcopy(r) for r in spec.get("derive", [])]
        if spec.get("default_branch"):
            # Removed by design: branches must cover every future direction
            # of the evidence (validated exhaustively below), so an authored
            # catch-all question would only mask an incomplete branch table.
            raise GraphSpecError(f"Node {self.id} declares a default_branch; "
                                 "author branches that cover all directions instead")
        self.effects = [deepcopy(e) for e in spec.get("effects", [])]
        self.on_completed_reply = spec.get("on_completed_reply")
        self.prerequisites = [item for item in spec.get("requires", []) if isinstance(item, str)]
        slot_specs = [item for item in spec.get("requires", []) if isinstance(item, dict)]
        self.requirements = {s["key"]: s.get("require", "filled") for s in slot_specs}
        self.slots = {s["key"]: EvidenceSlot(s["key"], s) for s in slot_specs}
        # Prerequisites and evidence slots may be declared in any order; the
        # mixed list is an authoring convenience confirmed in the design doc.
        self.state = "collecting"
        self.fire_count = 0
        self.last_fired_at = None
        for branch in self.branches:
            if branch.get("terminal") and self.kind != "inquiry":
                raise GraphSpecError(
                    f"Node {self.id}: only an inquiry self-loop may declare a "
                    "terminal branch (other kinds complete on every fire anyway)")
        # Set by fire() and consumed by fired(): whether the chosen branch
        # settles this inquiry instead of resetting it for another round.
        self._pending_terminal = False

    @property
    def satisfied(self):
        for key, requirement in self.requirements.items():
            slot = self.slots[key]
            if not slot.filled or not _condition_met(slot, requirement):
                return False
        return True  # prerequisite completion is checked by the runtime

    def clear_volatile(self, at):
        for slot in self.slots.values():
            if slot.volatile:
                slot.value, slot.filled_at, slot.source = _UNFILLED, None, None

    def to_public(self):
        return {"id": self.id, "owner": self.owner, "kind": self.kind, "state": self.state,
                "title": self.title, "fire_count": self.fire_count,
                "slots": {k: s.to_public() for k, s in self.slots.items()},
                "prerequisites": list(self.prerequisites)}


class MarkReport:
    """What one mark batch changed: the engine's cue to schedule activations."""

    def __init__(self, node_id, changed):
        self.node_id = node_id
        self.changed = list(changed)
        self.newly_ready = [node_id] if changed else []


class GraphRuntime:
    """All nodes of one task's world graph and the transitions between them."""

    def __init__(self, spec):
        self.nodes = {}
        for node_spec in spec.get("nodes", []):
            node = GraphNode(node_spec)
            if node.id in self.nodes:
                raise GraphSpecError(f"Duplicate node id {node.id}")
            self.nodes[node.id] = node
        self._validate_references()
        self.audit = []

    # -- spec validation ---------------------------------------------------

    def _validate_references(self):
        for node in self.nodes.values():
            for prereq in node.prerequisites:
                if prereq not in self.nodes:
                    raise GraphSpecError(f"Node {node.id} requires unknown node {prereq}")
            self._validate_branch_coverage(node)
        # Cycle check: prerequisites must not loop (self-edges of inquiry nodes
        # are not expressed as prerequisites, so any cycle here is a bug).
        visiting, done = set(), set()
        def visit(node_id):
            if node_id in done:
                return
            if node_id in visiting:
                raise GraphSpecError(f"Prerequisite cycle through {node_id}")
            visiting.add(node_id)
            for prereq in self.nodes[node_id].prerequisites:
                visit(prereq)
            visiting.discard(node_id)
            done.add(node_id)
        for node_id in self.nodes:
            visit(node_id)

    def _validate_branch_coverage(self, node):
        """Branches must cover every future direction of the evidence: there
        is no default fallback, so for every combination of reachable values
        of the conditioned slots some branch must match. Reachability follows
        the slot requirements (a slot with require: True can only complete at
        True), and conditioned slots must be boolean or enum — a string slot
        cannot be enumerated and may not steer a branch."""
        if not node.branches:
            return
        conditioned = set()
        for branch in node.branches:
            for key, condition in branch.get("when", {}).items():
                slot = node.slots.get(key)
                if slot is None:
                    raise GraphSpecError(
                        f"Branch of {node.id} conditions on unknown slot {key}")
                if slot.kind == "string":
                    raise GraphSpecError(
                        f"Branch of {node.id} conditions on string slot {key}; "
                        "only boolean/enum slots may steer branches")
                if isinstance(condition, str) and condition != "filled":
                    raise GraphSpecError(
                        f"Branch of {node.id} uses unsupported condition {condition!r} on {key}")
                conditioned.add(key)
        reachable = {}
        for key in conditioned:
            slot, requirement = node.slots[key], node.requirements.get(key, "filled")
            values = [True, False] if slot.kind == "boolean" else list(slot.values)
            # A slot whose requirement pins one value can never complete at
            # the other: only the pinned value is reachable.
            if isinstance(requirement, bool) and slot.kind == "boolean":
                values = [requirement]
            elif requirement not in (None, "filled") and requirement in values:
                values = [requirement]
            reachable[key] = values
        keys = sorted(conditioned)
        combos = [dict(zip(keys, combo))
                  for combo in _product(*(reachable[k] for k in keys))] if keys else [{}]
        for combo in combos:
            if not any(all(_matches(combo[key], branch["when"].get(key, "filled"))
                           for key in keys) for branch in node.branches):
                raise GraphSpecError(
                    f"Branches of {node.id} do not cover the evidence combination "
                    f"{combo}; author a branch for it (there is no default)")

    # -- evidence marking --------------------------------------------------

    def mark(self, node_id, marks, *, source=None, at=None):
        """Apply structured evidence marks (one parsed letter batch) to a node.

        A later letter overwrites an earlier slot value: that is the amend
        semantics for not-yet-lit nodes. Absent keys are left untouched —
        absence never becomes False. Returns a MarkReport; ``newly_ready`` is
        nonempty when the node's own slots all filled for the first time and
        the engine should schedule its activation.
        """
        node = self._node(node_id)
        if not isinstance(marks, dict):
            raise ValueError("Marks must be an object of slot values")
        changed = []
        for key, value in marks.items():
            slot = node.slots.get(key)
            if slot is None:
                raise ValueError(f"Node {node.id} has no evidence slot {key}")
            value = slot.validate(value)
            if slot.filled and slot.value == value:
                continue  # a restated value is not new evidence
            changed.append(key)
            slot.value, slot.filled_at, slot.source = value, at, source
        if changed:
            self.audit.append({"kind": "evidence_marked", "node": node.id, "keys": changed,
                               "source": source, "at": at})
        return MarkReport(node.id, changed)

    def derived_marks(self, node_id):
        """Marks this node's fresh evidence implies on companion nodes.

        Evaluates the authored ``derive`` rules against the node's *current*
        slot values: a rule fires when every ``when`` condition is met, and
        contributes its ``marks`` to the target nodes. Values of the form
        ``"=<slot_key>"`` reference this node's own slots; a rule whose
        reference is unfilled is skipped whole (it will be re-evaluated when
        the referenced slot arrives, since any mark on this node re-runs
        derivation). Returns ``{target_node_id: {slot_key: value}}``.
        """
        node = self._node(node_id)
        out = {}
        for rule in node.derive:
            if not all(_condition_met(node.slots[key], cond)
                       for key, cond in rule.get("when", {}).items()):
                continue
            resolved = {}
            skip = False
            for target, marks in rule.get("marks", {}).items():
                for key, value in marks.items():
                    if isinstance(value, str) and value.startswith("="):
                        ref = node.slots.get(value[1:])
                        if ref is None or not ref.filled:
                            skip = True
                            break
                        value = ref.value
                    resolved.setdefault(target, {})[key] = value
                if skip:
                    break
            if not skip:
                for target, marks in resolved.items():
                    out.setdefault(target, {}).update(marks)
        return out

    def env_backfill(self, node_id, *, at=None, source="environment"):
        """Complete an environment node: its event fired and supplies evidence.

        Environment nodes carry no agent-facing slots; the engine calls this
        when the authored event (form processed, announcement posted, approval
        due) happens. The node fires immediately, completing the prerequisite
        edge for downstream nodes.
        """
        node = self._node(node_id)
        if node.kind != "environment":
            raise ValueError(f"{node_id} is not an environment node")
        if node.state == "completed":
            return None
        return self.fire(node_id, at=at, source=source)

    # -- readiness and firing ----------------------------------------------

    def prerequisites_met(self, node, now=None):
        """A prerequisite counts as met once it has fired (a completed service
        node, or an inquiry that has answered at least once)."""
        for prereq in node.prerequisites:
            target = self.nodes[prereq]
            if target.state != "completed" and target.fire_count < 1:
                return False
        return True

    def is_ready(self, node, now=None):
        return (node.state == "collecting" and node.satisfied
                and self.prerequisites_met(node, now)
                and not self.expired_slots(node, now))

    def expired_slots(self, node, now=None):
        if now is None:
            return []
        expired = []
        for slot in node.slots.values():
            until = slot.valid_until
            if slot.filled and until and _stamp_datetime(now) >= _parse_stamp(until):
                expired.append(slot.key)
        return expired

    def requirements_status(self, node, now=None):
        """What the node still needs, in agent-facing words: the NPC's input
        for its proactive follow-up questions (missing or expired evidence)."""
        missing = [key for key, slot in node.slots.items() if not slot.filled]
        expired = self.expired_slots(node, now)
        unmet_prereqs = [p for p in node.prerequisites if not self.prerequisites_met(node, now)]
        return {"node": node.id, "missing_evidence": missing,
                "expired_evidence": [k for k in expired if k not in missing],
                "waiting_for_nodes": unmet_prereqs,
                "satisfied": not missing and not expired and not unmet_prereqs}

    def fire(self, node_id, *, at=None, source=None):
        """Light a ready node: choose the branch deterministically and hand
        the engine the canonical reply plus the effects to execute. The node
        enters ``firing``; the engine must call ``fired`` after the effects
        have run. Firing a completed node returns its authored repeat answer
        instead (one-shot semantics; no second processing)."""
        node = self._node(node_id)
        if node.state == "completed":
            return {"node": node.id, "status": "already_completed",
                    "reply": node.on_completed_reply
                    or f"The {node.title} matter has already been completed."}
        if node.state == "firing":
            raise ValueError(f"Node {node_id} is already firing")
        branch = None
        if node.branches:
            for candidate in node.branches:
                if all(_condition_met(node.slots[key], condition)
                       for key, condition in candidate.get("when", {}).items()):
                    branch = candidate
                    break
            if branch is None:
                # Validation enforces full branch coverage over the reachable
                # evidence combinations, so landing here is an authoring bug.
                raise GraphSpecError(
                    f"No branch of {node.id} matches its completed evidence; "
                    "the branch table does not cover all directions")
        node.state = "firing"
        node._pending_terminal = bool(branch and branch.get("terminal"))
        self.audit.append({"kind": "node_lit", "node": node.id, "branch":
                           branch.get("label") if branch else None, "at": at, "source": source})
        reply = branch.get("reply", node.on_completed_reply) if branch else node.on_completed_reply
        effects = list(branch.get("effects", [])) if branch else list(node.effects)
        if branch:
            # Node-level effects (e.g. downstream supplies) run on every
            # branch; branch effects are the branch-specific part.
            effects = list(node.effects) + effects
        return {"node": node.id, "status": "fired", "branch":
                branch.get("label") if branch else None,
                "reply": reply, "effects": effects}

    def fired(self, node_id, *, at=None):
        """The engine executed the fire's effects: settle the node.

        Inquiry nodes reset to collecting with volatile evidence cleared (the
        self-loop) — unless the fired branch declared ``terminal``, in which
        case the node settles into its completed state (a concluded
        conversation: repeats are answered from on_completed_reply)."""
        node = self._node(node_id)
        if node.state != "firing":
            raise ValueError(f"Node {node_id} is not firing")
        node.state = "completed"
        node.fire_count += 1
        node.last_fired_at = at
        if node.kind == "inquiry" and not node._pending_terminal:
            node.state = "collecting"
            node.clear_volatile(at)
        node._pending_terminal = False
        self.audit.append({"kind": "node_completed", "node": node.id,
                           "fire_count": node.fire_count, "at": at})

    def force_complete(self, node_id, *, at=None):
        """Force a collecting node into its completed state: the engine-side
        ``complete_node`` effect, how one node's terminal fire closes another
        node's conversation (e.g. a settled swap closes the negotiation loop).
        A completed node needs nothing; a firing node is mid-fire by
        construction and cannot be closed underneath its own effects."""
        node = self._node(node_id)
        if node.state == "completed":
            return False
        if node.state == "firing":
            raise ValueError(f"Node {node_id} is firing; it cannot be force-completed")
        node.state = "completed"
        node._pending_terminal = False
        self.audit.append({"kind": "node_completed", "node": node.id,
                           "forced": True, "at": at})
        return True

    def completed_reply(self, node_id):
        """The canonical answer for a repeat request on a completed node."""
        node = self._node(node_id)
        return node.on_completed_reply or \
            f"The {node.title} matter has already been completed."

    # -- views -------------------------------------------------------------

    def nodes_owned_by(self, owner):
        return [n for n in self.nodes.values() if n.owner == owner]

    def snapshot(self):
        """The god-view progress state (director input); never agent-visible."""
        return {n.id: n.to_public() for n in self.nodes.values()}

    def drain_audit(self):
        records, self.audit = self.audit, []
        return records

    def _node(self, node_id):
        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Unknown graph node {node_id}")
        return node


def _parse_stamp(value):
    if isinstance(value, datetime):
        return value
    from .calendar import parse
    return parse(value)


def _stamp_datetime(value):
    return value if isinstance(value, datetime) else _parse_stamp(value)
