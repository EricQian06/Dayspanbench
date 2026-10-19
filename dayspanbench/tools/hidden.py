"""Hidden per-task tools, unlocked through discover_tools.

Their names and behavior are fully parameterized by the authored params in
task["hidden_tools"]; the handlers below dispatch on the authored kind and
validate arguments per kind. Behavior and error messages are frozen by the
environment contract; these are verbatim ports of the former AgentTools
methods, with ``ctx`` (the AgentTools instance) supplying the environment.
"""

from copy import deepcopy
from datetime import timedelta

from ..calendar import Calendar, parse, stamp
from ..dialogue import condition_met, current_facts, select_facts
from ..values import field_value_equivalent
from .common import query_units


def call_hidden_tool(ctx, name, **kwargs):
    env = ctx._env
    spec = env.hidden_tools[name]
    handler = KIND_HANDLERS[spec["kind"]]
    return handler(ctx, name, spec, kwargs)


def _hidden_form(ctx, name, spec, kwargs):
    """Submit a web form: required fields are validated against the form's
    own field list; an authored `expect` mapping decides accept/reject (any
    value passes for keys it omits). Processing completes later at an
    authored virtual time; until then the page shows Submitted, pending processing."""
    env = ctx._env
    if set(kwargs) != {"fields"} or not isinstance(kwargs.get("fields"), dict):
        raise ValueError("hidden form tool takes a single object argument: fields")
    params = spec["params"]
    form_id = params["form"]
    _, form = env.forms[form_id]
    submission = env.form_submissions.get(form_id)
    if submission and submission["status"] in {"pending", "processed"}:
        raise ValueError('This form was already submitted and cannot be submitted again. Revisit the page or check status for the result.')
    values = kwargs["fields"]
    missing = [f["label"] for f in form["fields"]
               if f.get("required") and values.get(f["name"]) in (None, "")]
    if missing:
        raise ValueError('Missing required form fields: ' + ", ".join(missing))
    expect = params.get("expect") or {}
    mismatched = [key for key, expected in expect.items()
                  if not field_value_equivalent(values.get(key), expected)]
    accepted = not mismatched
    if params.get("process_at"):
        at = max(env.now, parse(params["process_at"]))
    else:
        calendar = Calendar(env.task["calendars"][params.get("calendar", "office")])
        at = calendar.add_business(env.now, params.get("process_delay", 60))
    env.form_submissions[form_id] = {"status": "pending", "submitted_at": stamp(env.now),
                                     "values": deepcopy(values), "accepted": accepted,
                                     "mismatched": mismatched,
                                     "result_text": None, "receipts": []}
    env.record("agent_form_submitted", tool=name, form=form_id, accepted=accepted)
    env.enqueue(at, "form_processed", form_id)
    return {"status": "submitted", "form": form_id, "at": stamp(env.now),
            "text": 'Form submitted, pending processing. Results are not pushed automatically. After completion, revisit the relevant page or check status for the determination and written evidence.'}


def _hidden_status(ctx, name, spec, kwargs):
    """Query an authored external status record (permit/parcel/registration
    style): staged states keyed by virtual times, optionally superseded by
    a linked form submission's pending/processed/rejected outcome."""
    env = ctx._env
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
                "note": 'No matching record found. Check the matter ID or keywords and retry.'}
    results = []
    for record in records:
        state = record.get("initial") or 'No records yet.'
        for entry in record.get("timeline", []):
            if parse(entry["at"]) <= env.now:
                state = entry["text"]
        submission = env.form_submissions.get(record["form"]) if record.get("form") else None
        outcome = {"key": record["key"], "label": record.get("label", ""),
                   "state": state, "now": stamp(env.now)}
        if submission is not None:
            if submission["status"] == "pending":
                outcome["state"] = f"Submitted, pending processing (submitted at {submission['submitted_at']}). "
            else:
                outcome["state"] = submission["result_text"]
                # A processed status query is an official confirmation channel
                # and carries the issued receipts, just like the carrying
                # page does after a revisit.
                if submission["status"] == "processed" and submission["receipts"]:
                    outcome["receipts"] = deepcopy(submission["receipts"])
                    # Positive confirmation: the processed status query is an
                    # official channel and the receipt is the written voucher.
                    outcome["receipt_note"] = ("This lookup is a formal completion channel. Its receipt is delivered with this result; "
                                               "include key identifiers, quantities, and dates in the final summary.")
        results.append(outcome)
    return {"records": results, "now": stamp(env.now)}


def _hidden_record(ctx, name, spec, kwargs):
    """Retrieve an authored record that exists only after its precondition
    (a virtual time and/or a form having been processed); a hit issues a
    receipt like fetch_document does, a miss explains why not."""
    env = ctx._env
    key = kwargs.get("key")
    if set(kwargs) - {"key"} or (key is not None and not isinstance(key, str)):
        raise ValueError("hidden record tool takes a single optional string argument: key")
    records = spec["params"]["records"]
    needle = (key or "").strip().casefold()
    matches = [r for r in records if not needle or needle in r["key"].casefold()] \
        if needle else (records if len(records) == 1 else [])
    if not matches:
        env.record("agent_hidden_record", tool=name, key=key, found=False)
        return {"found": False, "records": [], "note": 'Record not found. Check the record ID and retry.'}
    results = []
    for record in matches:
        if record.get("available_at") and env.now < parse(record["available_at"]):
            results.append({"key": record["key"], "found": False,
                            "text": 'This record has not been generated. Check again later.'})
            continue
        submission = env.form_submissions.get(record["requires_form"]) if record.get("requires_form") else None
        if submission is None or submission["status"] != "processed":
            results.append({"key": record["key"], "found": False,
                            "text": 'This record is not yet generated or temporarily unavailable. Check again later.'})
            continue
        entry = {"key": record["key"], "found": True, "title": record["title"],
                 "text": record["text"], "at": stamp(env.now), "receipts": []}
        if record.get("facts"):
            entry["receipts"].append(env.issue_receipt(
                record["title"], record["facts"], record["issuer"], record["text"]))
            entry["receipt_note"] = 'This record is written material issued through an official channel. Include its key identifiers, quantities, and dates in the final summary.'
        results.append(entry)
    env.record("agent_hidden_record", tool=name, key=key,
               found=[r["key"] for r in results if r["found"]])
    return {"records": results, "now": stamp(env.now)}


def _hidden_catalog(ctx, name, spec, kwargs):
    """Search an authored inventory (flights, menus, products, schedules):
    rows filtered by query terms, honoring per-row availability windows.
    A row may carry facts registered on retrieval (an official listing
    receipt)."""
    env = ctx._env
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
                for u in query_units(needle)):
            continue
        row = {"id": entry["id"], "title": entry["title"], "text": entry.get("text", ""),
               "fields": deepcopy(entry.get("fields", {}))}
        available = []
        for fact_id in entry.get("facts", []):
            fact = env.task["facts"][fact_id]
            if fact.get("available_at") and env.now < parse(fact["available_at"]):
                continue
            available.append(fact_id)
        if available:
            row["receipts"] = [env.issue_receipt(entry["title"], available, entry["issuer"])]
            row["receipt_note"] = ("This listing is an official channel; the receipt above has been "
                                   "delivered. Its key contents (numbers, quantities, dates) must be "
                                   "recorded in your final summary.")
        rows.append(row)
    env.record("agent_hidden_catalog", tool=name, query=query,
               entries=[r["id"] for r in rows])
    if not rows:
        return {"results": [], "now": stamp(env.now),
                "note": "No matching listings right now; adjust the query or check back later."}
    return {"results": rows, "now": stamp(env.now)}


def _hidden_select(ctx, name, spec, kwargs):
    """Pick one option out of a linked catalog tool and commit it: the
    entry must still be listed when the booking is processed; an authored
    hold can lapse first. Processing completes later at an authored virtual
    time and accepted selections register facts and issue a receipt, like
    a form."""
    env = ctx._env
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
        if selection["status"] == "processed" and selection["receipts"]:
            outcome["receipts"] = deepcopy(selection["receipts"])
            outcome["receipt_note"] = ("This query is an official confirmation channel; the receipt "
                                       "above has been delivered. Its key contents (numbers, "
                                       "quantities, dates) must be recorded in your final summary.")
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
    if params.get("complete_before") and at >= parse(params["complete_before"]):
        raise ValueError("This request cannot complete before the service deadline: "
                         + params["complete_before"])
    if not condition_met(env, params.get("requires", {})):
        raise ValueError("Required current evidence or prior service completion is missing")
    env.selections[name] = {"entry": kwargs["entry"].strip(), "catalog": params["catalog"],
                            "status": "pending", "submitted_at": stamp(env.now),
                            "accepted": accepted, "result_text": None, "receipts": [],
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


def _hidden_dialogue(ctx, name, spec, kwargs):
    """Ask the task's principal (the user being assisted) a question.
    All matching authored topics contribute facts, with semantic topic
    selection in LLM mode. Conditional variants replace stale statements.
    Only this role's current facts and explicitly scoped service state are
    supplied; user statements remain information, not attested evidence."""
    env = ctx._env
    question = kwargs.get("question")
    if set(kwargs) != {"question"} or not isinstance(question, str) or not question.strip():
        raise ValueError("hidden dialogue tool takes a single string argument: question")
    params = spec["params"]
    facts = current_facts(env, params)
    matched = select_facts(env, name, params, question, facts)
    if not matched:
        canonical = params.get("default") or \
            "I don't have anything more to say about that; please work from what you already have."
    else:
        canonical = "\n".join(f["text"] for f in matched)
    answer = canonical
    if params.get("dialogue_mode") == "llm" and env.dialogue_client is not None:
        answer = env.render_dialogue(name, params, question, canonical, bool(matched), facts)
    else:
        env.dialogue_history.setdefault(name, []).append({"question": question,
            "answer": answer, "at": stamp(env.now)})
    env.record("agent_dialogue", tool=name, question=question,
               matched=bool(matched), answer=answer)
    return {"speaker": params.get("persona", "the user"), "answer": answer, "at": stamp(env.now)}


def _hidden_group(ctx, name, spec, kwargs):
    """A chat group in the messaging app: preview (name, member count, join
    state), a join request (instant or admin review, with hidden capacity
    windows that can make joining impossible for a while), and — once
    joined — reading the message timeline, pinned announcements and the
    member list. Member counts grow on an authored schedule; the capacity
    windows and approval times are private."""
    env = ctx._env
    params = spec["params"]
    if set(kwargs) - {"reason", "query"}:
        raise ValueError("hidden group tool takes no arguments (preview), "
                         '{"reason": text} (join request), or {"query": text} (read)')
    state = env.group_states.setdefault(name, {"joined": False, "pending": None, "read": 0})
    if kwargs.get("reason") is not None:
        if not isinstance(kwargs["reason"], str) or not kwargs["reason"].strip():
            raise ValueError("reason must be a non-empty string")
        if state["joined"] or state["pending"]:
            raise ValueError("A join request already exists or you are already a member")
        join = params.get("join", {})
        # Hidden capacity schedule: authored windows decide whether joining
        # is possible at all right now; the agent only sees the failure.
        for window in join.get("windows", []):
            if parse(window["from"]) <= env.now < parse(window["until"]):
                if window["state"] != "open":
                    env.record("agent_group_join", group=name, state=window["state"])
                    return {"status": window["state"], "group": params["group_name"],
                            "member_count": _group_count(env, params, name),
                            "text": window.get("text") or
                                    "The group is not accepting new members right now; try again later."}
        if join.get("reason_required") and len(kwargs["reason"].strip()) < 5:
            return {"status": "rejected", "group": params["group_name"],
                    "text": "The join request needs a short reason for the admins to review."}
        if join.get("mode") == "review":
            state["pending"] = stamp(env.now)
            approved_at = parse(join["approval_at"])
            env.enqueue(max(env.now, approved_at), "group_approved", name)
            env.record("agent_group_join", group=name, state="pending")
            return {"status": "pending", "group": params["group_name"],
                    "member_count": _group_count(env, params, name),
                    "text": "Join request submitted with your reason; an admin will review it. "
                            "You are not a member until the request is approved."}
        state["joined"] = True
        env.record("agent_group_join", group=name, state="joined")
        return {"status": "joined", "group": params["group_name"],
                "member_count": _group_count(env, params, name),
                "text": "You joined the group; the timeline, pinned announcement and member list are readable now."}
    if kwargs.get("query") is not None:
        if not isinstance(kwargs["query"], str):
            raise ValueError("query must be a string")
        if not state["joined"]:
            raise PermissionError("Only group members can read the timeline; join first")
        needle = kwargs["query"].strip().casefold()
        result = {"group": params["group_name"], "member_count": _group_count(env, params, name),
                  "now": stamp(env.now), "messages": [], "announcements": [], "members": []}
        for message in params.get("messages", []):
            if parse(message["at"]) <= env.now:
                result["messages"].append({"speaker": message["speaker"],
                                           "text": message["text"], "at": message["at"]})
        for pinned in params.get("announcements", []):
            result["announcements"].append({"title": pinned["title"], "text": pinned["text"],
                                            "at": pinned.get("at", params.get("created_at", "1970-01-01T00:00:00+00:00"))})
        if not needle or "member" in needle or "list" in needle:
            for member in params.get("members", [])[:10]:
                result["members"].append({"name": member["name"], "handle": member["handle"],
                                          "note": member.get("note", "")})
        env.record("agent_group_read", group=name, query=kwargs["query"],
                   messages=len(result["messages"]))
        return result
    # No arguments: the group preview, as the invite link shows it.
    env.record("agent_group_preview", group=name)
    return {"group": params["group_name"], "member_count": _group_count(env, params, name),
            "joined": state["joined"], "pending": bool(state["pending"]),
            "now": stamp(env.now),
            "text": "Group preview. Join with a short reason to request membership."}


def _group_count(env, params, name):
    """The member count right now: authored growth schedule, stepwise."""
    count = params.get("initial_members", 20)
    for step in params.get("growth", []):
        if parse(step["at"]) <= env.now:
            count = step["count"]
    return count


KIND_HANDLERS = {
    "form": _hidden_form,
    "status": _hidden_status,
    "record": _hidden_record,
    "catalog": _hidden_catalog,
    "select": _hidden_select,
    "dialogue": _hidden_dialogue,
    "group": _hidden_group,
}
