"""Privileged authoring witness, NOT an agent or an LLM performance baseline."""

from copy import deepcopy
import json

from .engine import Environment
from .interactor import UserInteractor


def _resolve_fact_values(value, env):
    """Expand "$fact:<id>" placeholders to the latest agent-visible evidence
    value, recursively through dicts and lists, so privileged witnesses can
    quote material exactly like a real agent would."""
    if isinstance(value, str) and value.startswith("$fact:"):
        fact_id = value.split(":", 1)[1]
        matches = [ev for ev in env.evidence.values() if ev["fact_id"] == fact_id and ev["agent_visible"]]
        if not matches:
            raise AssertionError(f"Reference tries to supply unobserved fact {fact_id}")
        return deepcopy(matches[-1]["value"])
    if isinstance(value, dict):
        return {key: _resolve_fact_values(item, env) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_fact_values(item, env) for item in value]
    return deepcopy(value)


def run_reference(task, *, recipient=None):
    env = Environment(task, recipient)
    # Club cases: an authored assisted user answers consult_user questions and
    # gates sensitive actions. No client here — the deterministic policy
    # table decides consent, so replay stays API-free.
    if task.get("interactor"):
        env.attach_interactor(UserInteractor(task["interactor"], seed=env.rng.randint(0, 1 << 30)))
    api = env.tools()
    labels = {}
    for action in task["reference_actions"]:
        if action["op"] == "visit_page":
            # Reference actions keep the internal page id; resolve it to the
            # public URL the agent-facing tool requires.
            page = next(p for p in task["public"]["pages"] if p["id"] == action["page"])
            api.visit_page(page["url"])
        elif action["op"] == "advance":
            # The authored witness advances to exact times (no message wake), so
            # replay stays deterministic; only the evaluated agent's wait_until
            # intercepts jumps at delivered mail.
            env.advance(action["at"])
        elif action["op"] == "send":
            raw_fields = action.get("fields", "$user")
            fields = deepcopy(task["public"]["user_fields"] if raw_fields == "$user" else raw_fields)
            fields = _resolve_fact_values(fields, env)
            # The privileged witness addresses people by id and lets the engine
            # translate to their mailbox, exactly like a discovered contact card.
            mailbox = next(a["contact_details"]["email"] for a in task["actors"] if a["id"] == action["to"])
            result = api.send_email(mailbox, action["text"], fields, labels.get(action.get("followup")))
            if "case_id" not in result:
                raise AssertionError(f"Reference message not understood: {action}: {result}")
            # Graph mode returns a letter id; keep the target actor too, since
            # waiting means "until this person's graph activity drains", not a
            # case state machine.
            labels[action["label"]] = (result["case_id"], action["to"]) if env.graph is not None \
                else result["case_id"]
        elif action["op"] == "wait_for":
            if env.graph is not None:
                actor_id = labels[action["label"]][1]
                while env.graph_actor_pending(actor_id) and env.now < env.deadline:
                    api.wait_until(task["deadline_at"])
                continue
            case_id = labels[action["label"]]
            case = env.cases[case_id]
            while case["state"] not in {"failed", "replied"} and env.now < env.deadline:
                api.wait_until(task["deadline_at"])
            # Deferred admission means a freshly resubmitted case may still look
            # unadmitted; only a stuck needs_information after the clock ran out
            # is an authoring error.
            if case["state"] == "needs_information":
                raise AssertionError(f"Reference waits for missing materials: {case_id}")
            if case["state"] == "failed":
                raise AssertionError(f"Reference case failed: {case_id}")
        elif action["op"] == "discover":
            # Unlock a hidden tool whose name an NPC reply or page text revealed.
            result = api.discover_tools(action["name"])
            if not result.get("found"):
                raise AssertionError(f"Reference cannot discover tool: {action['name']}")
        elif action["op"] == "tool":
            # Generic privileged tool call (hidden form/status/record tools and
            # optional tools alike); "$fact:" placeholders expand to observed
            # evidence values just like send_email fields.
            getattr(api, action["name"])(**_resolve_fact_values(action.get("args", {}), env))
        else:
            raise ValueError(f"Unknown reference op {action['op']}")
    # A solvability witness files the v0.5 answer structure: the expected
    # conclusion label plus a mechanical summary stitched from the receipts
    # and established facts the episode actually produced (no LLM involved).
    # These answers must never be used as a model performance result.
    answer = {"conclusion": env.expected_conclusion(),
              "summary": _mechanical_summary(env, task)}
    result = api.submit_answer(answer)
    return env, answer, result


def _mechanical_summary(env, task):
    """Concatenate every agent-visible established fact and receipt the
    witness obtained, then state the deadline-blocked goals honestly. The
    result carries all deterministic anchor elements by construction."""
    lines, seen = [], set()

    def add(text):
        if isinstance(text, str) and text.strip() and text not in seen:
            seen.add(text)
            lines.append(text)

    for record in env.director.facts.values():
        if record.get("agent_visible"):
            add(record.get("text"))
    for receipt in env.director.receipts:
        add(receipt.get("text"))
        fields = receipt.get("fields") or {}
        if fields:
            add(f"{receipt.get('title') or 'Receipt'} key details: "
                + json.dumps(fields, ensure_ascii=False))
    for goal in task.get("goals", []):
        if goal.get("status") == "unconfirmed":
            lines.append(f"As of the deadline, {goal['key']} has no authoritative confirmation.")
    return "\n".join(lines)
