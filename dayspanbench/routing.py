"""Follow-up routing heuristics for agent mail, extracted from send_email.

This is the historically bug-prone surface (duplicate-case spawning, cold
referrals to the person actively serving the sender, follow-ups restarting
in-flight workflows), so the heuristics live here in isolation, unit-testable
against a lightweight environment stub. Behavior is a verbatim port of the
former send_email branches; tools/common.py calls these functions.
"""

from copy import deepcopy

from .calendar import stamp


def merge_target(env, actor_id, workflow_id, existing):
    """A fresh letter that belongs to an already open conversation is a
    follow-up, not a rival case: routing matched the same workflow (progress
    ping, restated or corrected values), or matched nothing while exactly one
    agent case is in flight here. Without this, every ping without a case
    reference spawned a duplicate case competing with the original queue, or
    drew a cold referral from a person who is actively serving the sender.

    Returns the merged (existing) case when one is found, else None.
    """
    in_flight = [c for c in (env.cases[cid] for cid in env.actors[actor_id].cases)
                 if c.get("origin") == "agent" and not c.get("parent")
                 and c["workflow"] is not None
                 and c["state"] not in {"replied", "failed"}]
    if workflow_id is not None:
        same = [c for c in in_flight if c["workflow"]["id"] == workflow_id]
        merged = same[-1] if same else None
    else:
        merged = in_flight[-1] if len(in_flight) == 1 else None
    return merged


def apply_followup(env, case, actor_id, workflow_id, text, fields):
    """Apply one follow-up letter to an existing case.

    Returns the send result for branches that answer immediately (a material
    new request reopens a fresh case; a ping acknowledges), or None when the
    letter only supplies fields to an unadmitted/incomplete case and the
    caller should fall through to the standard received receipt.
    """
    actor = env.actors[actor_id]
    if case["state"] in {"new", "needs_information"}:
        # A followup on an unadmitted or incomplete case supplies fields;
        # admission is deferred to the recipient's work hours either way.
        case["fields"].update(deepcopy(fields or {}))
        case["correspondence"].append(text)
        if case.get("origin") == "agent":
            env.enqueue_admission(actor, case["id"])
        else:
            env.start(case)
        return None
    if workflow_id is not None:
        # A follow-up on a closed or in-flight case carrying a genuinely
        # new or changed request is re-routed like any fresh mail: it opens
        # a new case with the normal admission delay, so it cannot skip
        # the recipient's queue or restart the original one. A progress
        # ping with unchanged fields only acknowledges; it must not spawn a
        # duplicate internal case that competes with (and can push past the
        # deadline) the original one.
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
            env.emit(case, f"Hello, I am {actor.spec['name']}. Your matter is in progress; acceptance time and queue order are unchanged. {eta or 'A written reply will follow completion.'} Please write again if you have other questions.",
                     status="acknowledgement")
            return {"case_id": case["id"], "status": "received", "at": stamp(env.now)}
        reopened = env.new_case(actor_id, workflow_id, fields or {}, origin="agent")
        reopened["correspondence"].append(text)
        env.record("followup_reopened", case_id=reopened["id"], original_case=case["id"])
        return {"case_id": reopened["id"], "status": "received", "at": stamp(env.now)}
    # Following up is observable, but does not skip an internal queue.
    env.emit(case, f"Hello, I am {actor.spec['name']}. Your follow-up email has been received; the original acceptance time and queue order are unchanged. {env.eta_clause(case, case['step'])}This email did not match a new matter within my remit. For other services, explain the specific request in your email. Please write again if you have other questions.",
             status="acknowledgement")
    return None

