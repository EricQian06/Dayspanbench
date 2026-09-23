"""Privileged authoring witness, NOT an agent or an LLM performance baseline."""

from copy import deepcopy

from .engine import Environment


def run_reference(task, *, recipient=None):
    env = Environment(task, recipient)
    api = env.tools()
    labels = {}
    for action in task["reference_actions"]:
        if action["op"] == "visit_page":
            # Reference actions keep the internal page id; resolve it to the
            # public URL the agent-facing tool requires.
            page = next(p for p in task["public"]["pages"] if p["id"] == action["page"])
            api.visit_page(page["url"])
        elif action["op"] == "advance":
            api.wait_until(action["at"], wake_on_message=False)
        elif action["op"] == "send":
            raw_fields = action.get("fields", "$user")
            fields = deepcopy(task["public"]["user_fields"] if raw_fields == "$user" else raw_fields)
            for key, value in list(fields.items()):
                if isinstance(value, str) and value.startswith("$fact:"):
                    fact_id = value.split(":", 1)[1]
                    matches = [ev for ev in env.evidence.values() if ev["fact_id"] == fact_id and ev["agent_visible"]]
                    if not matches:
                        raise AssertionError(f"Reference tries to supply unobserved fact {fact_id}")
                    fields[key] = deepcopy(matches[-1]["value"])
            # The privileged witness addresses people by id and lets the engine
            # translate to their mailbox, exactly like a discovered contact card.
            mailbox = next(a["contact_details"]["email"] for a in task["actors"] if a["id"] == action["to"])
            result = api.send_email(mailbox, action["text"], fields, labels.get(action.get("followup")))
            if "case_id" not in result:
                raise AssertionError(f"Reference message not understood: {action}: {result}")
            labels[action["label"]] = result["case_id"]
        elif action["op"] == "wait_for":
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
        else:
            raise ValueError(f"Unknown reference op {action['op']}")
    # A solvability witness uses private goal labels, but only actually obtained
    # evidence. These answers must never be used as a model performance result.
    claims = []
    for goal in task["goals"]:
        if goal.get("status") == "unconfirmed":
            claims.append({"key": goal["key"], "status": "unconfirmed"})
        else:
            ids = [ev["id"] for ev in env.evidence.values() if ev["fact_id"] in goal["accepted_facts"] and ev["agent_visible"]]
            claims.append({"key": goal["key"], "status": "confirmed", "value": deepcopy(goal["expected"]), "evidence_ids": ids})
    answer = {"conclusion": task["expected_conclusion"], "claims": claims}
    result = api.submit_answer(answer)
    return env, answer, result
