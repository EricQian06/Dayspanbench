"""Work scheduling and ETA projection, extracted from the environment.

Pure virtual-time logic over environment state: admission delays, step
scheduling with queue reservations, and completion projections that back the
promised-ETA sentences. These are the pieces where time-ordering bugs live
(DSB-23-style confirmation windows), so they are unit-testable here against
a lightweight environment stub. Behavior is a verbatim port of the former
Environment methods; the Environment delegates to these functions.
"""

from datetime import timedelta

from .calendar import parse, stamp


# Upper bound of the randomized surcharge jittered_delay adds to each
# agent-origin business step, mirrored by projected_delay so the promised
# "earliest" completion is never beaten by the real run.
JITTER_CEILING = 25

# Promises below this horizon are not worth a sentence in acknowledgements.
ETA_THRESHOLD = timedelta(hours=24)

# A retraction is only sent once the projection slips past the promise by
# this much, so borderline drift does not spam the requester.
ETA_REVISION_THRESHOLD = timedelta(hours=12)


def admission_at(env, actor):
    """Email from the agent is read no sooner than the task's reply delay:
    first pushed to the recipient's earliest opening, then delayed by a
    random business duration of task-specific magnitude. Never instant."""
    low, high = env.reply_delay
    return actor.calendar.add_business(env.now, env.rng.randint(low, high))


def enqueue_admission(env, actor, case_id):
    """Schedule admission unless one is already pending for this case."""
    if any(kind == "admit" and cid == case_id for _, _, kind, cid in env.events):
        return
    env.enqueue(admission_at(env, actor), "admit", case_id)


def projected_delay(env, delay, origin):
    """Delay as the ETA projection sees it: for agent-origin cases every
    business step is inflated to its worst-case jitter so the promised
    "earliest" completion is never beaten by the real run."""
    if origin != "agent":
        return delay
    adjusted = dict(delay)
    if adjusted.get("mode", "business") == "business":
        adjusted["minutes"] = max(adjusted.get("minutes", 0), 15) + JITTER_CEILING
    else:
        adjusted["minutes"] = max(adjusted.get("minutes", 0), 15)
    return adjusted


def reserve_step(env, actor, now, tool, delay, reservations):
    """Do the work, then wait for publication without occupying the worker.

    A release gates completion, not the start of all preceding work. Moving
    the whole operation after publication unnecessarily delays long reviews.
    Explicit not_before remains a start constraint in Calendar.reserve.
    """
    start, end = actor.calendar.reserve(now, delay, reservations)
    for fid in tool.get("facts", []):
        release = env.task["facts"][fid].get("available_at")
        if release:
            end = max(end, parse(release))
    return start, end


def estimate_completion(env, actor_id, workflow, from_step, now=None, origin=None):
    """Nominal projection of when a workflow's final reply lands: remaining
    steps walked with their authored delays (worst-case jitter included for
    agent-origin cases, but no queue contention), recursing into delegate
    targets. A lower bound, used only for the ETA sentence in long-wait
    acknowledgements."""
    if now is None:
        now = env.now
    actor = env.actors[actor_id]
    reservations = list(actor.reservations)
    t = now
    for i in range(from_step, len(workflow["steps"])):
        step = workflow["steps"][i]
        tool = actor.spec["tools"][step["tool"]]
        if tool["kind"] in {"delegate", "consult"}:
            _, t = reserve_step(env, actor, t, tool,
                projected_delay(env, step["delay"], origin), reservations)
            target_wf = next(w for w in env.actors[tool["target"]].spec["workflows"]
                             if w["id"] == tool["workflow"])
            t = max(t, estimate_completion(env, tool["target"], target_wf, 0, t, origin=origin))
        else:
            _, t = reserve_step(env, actor, t, tool,
                projected_delay(env, step["delay"], origin), reservations)
    return t


def active_child(env, case, workflow_id):
    """The latest not-yet-returned delegate child of a waiting case."""
    children = [c for c in env.cases.values()
                if c.get("parent") == case["id"] and c["workflow"] is not None
                and c["workflow"]["id"] == workflow_id and c["state"] not in {"replied", "failed"}]
    return children[-1] if children else None


def case_completion(env, case):
    """Projection for a live case: the current step uses its already
    scheduled due time, a waiting_internal step follows the active child's
    real progress instead of re-simulating it from scratch — re-estimating
    a finished reviewer from "now" once pushed a DSB-02 receipt a whole
    weekly batch past its original promise."""
    if case.get("linked_to"):
        return case_completion(env, env.cases[case["linked_to"]])
    t = env.now
    actor = env.actors[case["actor"]]
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
        child = active_child(env, case, tool.get("workflow", "main"))
        if child is not None:
            t = case_completion(env, child)
        else:
            _, t = reserve_step(env, actor, t, tool, step["delay"],
                                 list(actor.reservations))
            target_wf = next(w for w in env.actors[tool["target"]].spec["workflows"]
                             if w["id"] == tool["workflow"])
            t = max(t, estimate_completion(env, tool["target"], target_wf, 0, t, origin=case.get("origin")))
        step_index += 1
    elif case["state"] in {"new", "needs_information"}:
        return estimate_completion(env, case["actor"], workflow, 0, origin=case.get("origin"))
    else:  # replied / failed: nothing left to promise
        return t
    return estimate_completion(env, case["actor"], workflow, step_index, t,
                               origin=case.get("origin"))


def eta_clause(env, case, from_step=None):
    """The promised earliest-completion sentence, or empty for short waits.
    An unrouted case has no workflow to project, so it promises nothing."""
    if case["workflow"] is None:
        return ""
    eta = case_completion(env, case)
    if eta - env.now <= ETA_THRESHOLD:
        return ""
    # A promise never shrinks: a later re-projection may look earlier
    # (a child finished, the remaining chain shortened), but the requester
    # already holds the earlier written promise, and the revision logic
    # must still watch the schedule against the tightest promise made.
    previous = case.get("promised_eta")
    if previous and parse(previous) > eta:
        eta = parse(previous)
    actor = env.actors[case["actor"]]
    local = eta.astimezone(actor.calendar.zone)
    # Every promise is remembered so a later schedule slip (queue
    # contention inserting work ahead of this chain) can be retracted.
    case["promised_eta"] = stamp(eta)
    case["eta_slip_notified"] = False
    return (f"The earliest expected completion is {local.strftime('%Y-%m-%d %H:%M')} local time, followed by a written reply. "
            "This is a lengthy process; wait for the reply before contacting us again. Reminders do not change queue order.")


def notify_eta_slip(env, case):
    """Retract promises the schedule has outgrown.

    The acknowledgement promised an earliest completion as a projection;
    later cases joining the same actor's queue can push the chain past it.
    The requester then deserves a revision instead of silently waiting on
    a broken promise (a DSB-10 agent waited to the deadline on a promise
    the queue had already pushed a week out)."""
    chain, current = [], case
    while current is not None:
        chain.append(current)
        current = env.cases.get(current.get("parent"))
    for member in chain:
        if not member.get("promised_eta") or member.get("eta_slip_notified") \
                or member["state"] in {"replied", "failed"}:
            continue
        completion = case_completion(env, member)
        if completion - parse(member["promised_eta"]) <= ETA_REVISION_THRESHOLD:
            continue
        member["eta_slip_notified"] = True
        actor = env.actors[member["actor"]]
        local = completion.astimezone(actor.calendar.zone)
        env.record("eta_revised", case_id=member["id"], actor=member["actor"],
                    promised=member["promised_eta"], revised=stamp(completion))
        env.emit(member, f"Hello, I am {actor.spec['name']}. Progress update for your accepted matter: due to an intake schedule change, "
                          f"the earliest expected completion is now {local.strftime('%Y-%m-%d %H:%M')} local time. "
                          "Reminders do not change queue order; wait for the reply before contacting us again.", status="acknowledgement")


def jittered_delay(env, case, delay):
    """Agent-initiated email never gets instant handling: business delays get a
    randomized surcharge, other modes at least a 15-minute floor."""
    if case.get("origin") != "agent":
        return delay
    adjusted = dict(delay)
    if adjusted.get("mode", "business") == "business":
        adjusted["minutes"] = max(adjusted.get("minutes", 0), 15) + env.rng.randint(5, 25)
    else:
        adjusted["minutes"] = max(adjusted.get("minutes", 0), 15)
    return adjusted


def schedule_step(env, case):
    env.transition(case, "queued")
    actor = env.actors[case["actor"]]
    step = case["workflow"]["steps"][case["step"]]
    delay = jittered_delay(env, case, step["delay"])
    start, end = reserve_step(env, actor, env.now, actor.spec["tools"][step["tool"]],
                               delay, actor.reservations)
    actor.free_at = max((b for _, b in actor.reservations), default=env.now)
    case["due_at"] = stamp(end)
    env.record("scheduled", case_id=case["id"], actor=case["actor"], step=step["id"],
               start_at=stamp(start), due_at=stamp(end), tool=step["tool"])
    env.enqueue(start, "start", case["id"])
    env.enqueue(end, "complete", case["id"])
    notify_eta_slip(env, case)
