"""Common agent tools: the surface every task starts from.

Behavior and error messages are frozen by the environment contract; these are
verbatim ports of the former AgentTools methods, with ``ctx`` (the AgentTools
instance) supplying the environment reference.
"""

from copy import deepcopy
import re
from datetime import timedelta

from ..calendar import stamp
from ..routing import apply_followup, merge_target
from .base import tool_register


def query_units(needle):
    """Split a query into latin words and CJK character bigrams for matching.

    Relevance is not whole-term substring: Chinese terms are matched on
    character bigrams (南屿共享实验室 vs 南屿实验室联系方式 share 南屿/实验室),
    while latin terms must match whole.
    """
    units = set()
    for term in needle.split():
        for run in re.findall(r"[a-z0-9]+|[一-鿿]+", term):
            if run[0].isascii() or len(run) == 1:
                units.add(run)
            else:
                units.update(run[i:i + 2] for i in range(len(run) - 1))
    return units


@tool_register("recall_task", "common")
def recall_task(ctx, **kwargs):
    env = ctx._env
    return deepcopy(ctx._brief)


@tool_register("observe", "common")
def observe(ctx, **kwargs):
    env = ctx._env
    return {"now": stamp(env.now), "tools": ctx.tool_list(),
            "unread_messages": max(0, len(env.messages) - env.inbox_read)}


@tool_register("discover_tools", "common")
def discover_tools(ctx, name):
    """Look up a tool name mentioned in an NPC reply, page text, or a web
    search service mention. A hit returns the handwritten usage
    instructions and unlocks the tool; a miss never leaks the hidden tool
    list. Costs no message budget."""
    env = ctx._env
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    tool = env.hidden_tools.get(name.strip())
    if tool is None:
        env.record("agent_discover_tools", name=name, found=False)
        return {"found": False,
                "text": 'Tool not found. Check the exact tool name in correspondence or webpage text and retry.'}
    env.unlocked_tools.add(tool["name"])
    env.record("agent_discover_tools", name=tool["name"], found=True, tool_kind=tool["kind"])
    return {"found": True, "name": tool["name"], "usage": tool["usage"],
            "note": 'Tool unlocked. It now appears in observe() and can be called using the usage above.'}


@tool_register("web_search", "common")
def web_search(ctx, query):
    # A page is only returned when the query matches its title or snippet;
    # an empty query matches nothing. Page bodies are not searchable: the
    # agent must find the page first, then visit it.
    env = ctx._env
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    units = query_units(query.casefold())
    if not units:
        results = []
    else:
        pages = env.task["public"]["pages"]
        results = [{"url": p["url"], "title": p["title"], "snippet": p.get("snippet", "")} for p in pages
                   if any(u in (p["title"] + p.get("snippet", "")).casefold() for u in units)]
    ctx._seen_pages.update(r["url"] for r in results)
    total = len(env.task["public"]["pages"])
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
                     "undiscovered_pages": total - len(ctx._seen_pages)}}


@tool_register("visit_page", "common")
def visit_page(ctx, url):
    env = ctx._env
    # Only synthetic https://...bench/... addresses exist; anything else is
    # not a page in this scenario.
    if (not isinstance(url, str) or not url.startswith("https://")
            or ".bench/" not in url or " " in url):
        raise ValueError("url must be a https://*.bench/* page address")
    page = next((p for p in env.task["public"]["pages"] if p["url"] == url), None)
    if page is None:
        raise ValueError("Unknown page address")
    ctx._seen_pages.add(url)
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
                form["status"] = 'Submitted, pending processing'
            else:
                form["status"] = 'Completed' if submission["status"] == "processed" else 'Returned'
                form["result_text"] = submission["result_text"]
                if submission["receipts"]:
                    # Positive confirmation: the processed form is an official
                    # conclusion channel and the receipt is the written voucher.
                    form["receipts"] = deepcopy(submission["receipts"])
                    form["receipt_note"] = ("This completed form provides formal completion evidence. Its receipt is delivered with this page; "
                                             "include key identifiers, quantities, and dates in the final summary.")
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


@tool_register("send_email", "common")
def send_email(ctx, recipient, text, fields=None, case_id=None):
    """Send mail to a mailbox address. The receipt is issued at send time and
    is indistinguishable between delivery and a black-hole address; whether
    the recipient is responsible for the request is only decided when the
    mail is read, and mismatches are answered with a referral email."""
    env = ctx._env
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
    if env.graph is not None:
        # v0.6 graph mode: sending is transport only. The letter is parked on
        # the recipient's queue and interpreted at their next activation, so
        # no semantic parsing (and no parse failure) happens at send time.
        letter_id = env.graph_deliver(actor_id, text, fields, channel="email")
        return {"case_id": letter_id, "status": "received", "at": stamp(env.now)}
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
        # follow-up, not a rival case (see routing.merge_target).
        merged = merge_target(env, actor_id, workflow_id, existing)
        if merged is not None:
            case_id = merged["id"]
            existing = merged
    if case_id:
        case = env.cases[case_id]
        if case["actor"] != actor_id or case["parent"]:
            raise PermissionError("Case is not this agent's conversation")
        result = apply_followup(env, case, actor_id, workflow_id, text, fields)
        if result is not None:
            return result
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


@tool_register("call", "common")
def call(ctx, recipient, text, fields=None):
    """Live customer-service chat (graph-mode tasks) / phone call (legacy
    tasks). The graph-mode session is answered inside the recipient's work
    hours: a short 0-3 minute wait normally, up to 30 minutes in queue during
    peak windows. Ten idle minutes cancel the session, and a still-queued
    message then loses its place and waits again from scratch."""
    env = ctx._env
    if not isinstance(text, str) or (fields is not None and not isinstance(fields, dict)):
        raise ValueError("text must be a string and fields must be an object")
    if env.finished or env.now >= env.deadline:
        raise ValueError("Episode is closed for new calls")
    if recipient not in env.known_contacts:
        raise PermissionError(
            "Contact has not been discovered; recipient must be the contact's id "
            "from the contact card, not a name, email address, or phone number")
    actor = env.actors[recipient]
    if env.graph is None and "phone" not in actor.spec["contact_details"]:
        raise ValueError("Contact has no phone number")
    if env.agent_sends >= env.task["public"]["message_budget"]:
        raise ValueError("Message budget exhausted")
    env.agent_sends += 1
    env.record("agent_call", recipient=recipient, text=text, fields=fields or {})
    if not actor.calendar.is_open(env.now):
        return {"status": "no_answer", "recipient": recipient, "at": stamp(env.now),
                "text": "No answer: outside the contact's service hours."}
    if env.graph is not None:
        letter_id = env.graph_chat_call(recipient, text, fields)
        return {"case_id": letter_id, "status": "queued", "recipient": recipient,
                "at": stamp(env.now),
                "text": "Connected to the live service queue; the reply arrives shortly."}
    view = {"actor_id": recipient, "name": actor.spec["name"], "role": actor.spec["role"],
            "instructions": actor.spec["recipient"]["instructions"], "message": '[Phone] ' + text,
            "fields": deepcopy(fields or {}), "now": stamp(env.now), "history": deepcopy(actor.history),
            "existing_workflow_id": None,
            "workflows": [{k: deepcopy(w[k]) for k in ("id", "label", "aliases", "required_fields", "accept_after", "accept_before") if k in w} for w in actor.spec["workflows"]],
            "local_cases": [{"id": cid, "state": env.cases[cid]["state"]} for cid in actor.cases]}
    actor.history.append({"role": "agent", "text": '[Phone] ' + text, "fields": deepcopy(fields or {}),
                          "case_id": None, "at": stamp(env.now)})
    if hasattr(actor.recipient, "route"):
        decision = env.recipient_call(actor, "route", view)
        workflow_id = decision["workflow_id"]
        fields = env.canonicalize_fields({**decision["fields"], **(fields or {})})
    else:
        workflow_id = env.recipient_call(actor, "choose", view)
        fields = env.canonicalize_fields(fields)
    if workflow_id is None:
        prompt = 'Please specify the matter: ' + "; ".join(w["label"] for w in actor.spec["workflows"])
        actor.history.append({"role": "recipient", "text": prompt, "at": stamp(env.now)})
        return {"status": "clarification_needed", "text": prompt}
    if workflow_id not in {w["id"] for w in actor.spec["workflows"]}:
        raise PermissionError("Undeclared workflow")
    case = env.new_case(recipient, workflow_id, fields or {}, origin="phone")
    case["correspondence"].append('[Phone] ' + text)
    limit = min(env.now + timedelta(minutes=60), env.deadline)
    before = len(env.messages)
    while case["state"] not in {"replied", "failed"} and not any(m["case_id"] == case["id"] for m in env.messages):
        if not env.events or env.events[0][0] > limit:
            break
        env.advance(min(env.events[0][0], limit), wake_on_message=True)
    result = {"status": "answered", "case_id": case["id"], "at": message["at"], "text": message["text"]} if (message := next((m for m in env.messages if m["case_id"] == case["id"]), None)) else {
        "status": "processing", "case_id": case["id"], "at": stamp(env.now),
        "text": 'The contact has recorded and accepted the matter. Results will follow separately; check your inbox.'}
    if len(env.messages) > before:
        result["new_messages"] = len(env.messages) - before
        result["new_message_hint"] = 'New email arrived during the call. Use read_inbox to read it.'
    return result


@tool_register("read_inbox", "common")
def read_inbox(ctx, after=0):
    env = ctx._env
    env.inbox_read = max(env.inbox_read, len(env.messages))
    return {"messages": deepcopy(env.messages[after:]), "cursor": len(env.messages), "now": stamp(env.now)}


@tool_register("wait_until", "common")
def wait_until(ctx, until, wake_on_message=True):
    # wake_on_message is kept for call-site compatibility but no longer
    # lets a wait skip past mail: any agent-visible message delivered during
    # the jump intercepts the clock at its delivery time. A deliberate
    # "sleep to the deadline" otherwise hides a mid-wait reply (or a
    # returned/rejected letter) until it is too late to act on it.
    env = ctx._env
    if env.finished:
        raise ValueError("Episode already finished")
    before = len(env.messages)
    env.advance(until, wake_on_message=True)
    return read_inbox(ctx, before)


@tool_register("submit_answer", "common")
def submit_answer(ctx, answer):
    env = ctx._env
    if env.finished:
        raise ValueError("Only one final submission is allowed")
    env.finished = True
    return env.evaluate(answer)
