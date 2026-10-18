"""Optional per-task tools, enabled by listing them in the task's public["tools"].

Some carry real information for their task, others are decoys that only consume
budget or return nothing of value; the agent must decide which to rely on.
Behavior and error messages are frozen by the environment contract; these are
verbatim ports of the former AgentTools methods.
"""

from copy import deepcopy
from datetime import timedelta

from ..calendar import stamp
from .base import tool_register


def _check_optional(ctx, name):
    if name not in ctx.tool_list():
        raise PermissionError(f"Tool {name} is not available in this task")


def _budgeted(ctx):
    """Communication-style optional tools consume the message budget."""
    env = ctx._env
    if env.agent_sends >= env.task["public"]["message_budget"]:
        raise ValueError("Message budget exhausted")
    env.agent_sends += 1


@tool_register("query_case_status", "optional")
def query_case_status(ctx, case_id):
    """Look up the current state of one of the agent's own cases."""
    _check_optional(ctx, "query_case_status")
    env = ctx._env
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


@tool_register("fetch_document", "optional")
def fetch_document(ctx, url):
    """Download a document file linked from a page. Page bodies only list
    the document; its content arrives through this tool. Some documents
    carry official figures and constitute written evidence."""
    _check_optional(ctx, "fetch_document")
    env = ctx._env
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
              "at": stamp(env.now), "receipts": []}
    if document.get("facts"):
        result["receipts"].append(env.issue_receipt(
            f"{document['title']} - written document receipt", document["facts"], document["issuer"]))
    if result["receipts"]:
        # Written material with an attached receipt. The note deliberately
        # stays neutral and identical for formal and reference documents:
        # the environment never labels attestation authority per file —
        # the agent must check issuers itself (contract section on oral /
        # uncertain information states the general rule).
        result["note"] = ("Document downloaded with a receipt stating its contents. "
                          "Include key identifiers, quantities, and dates in the final summary.")
    else:
        result["note"] = 'This is an informational document; downloading it does not issue a written credential.'
    env.record("agent_fetch_document", url=url, facts=document.get("facts", []))
    return result


@tool_register("check_schedule", "optional")
def check_schedule(ctx, contact, date=None, days=7):
    """List a discovered contact's upcoming open hours in their local time."""
    _check_optional(ctx, "check_schedule")
    env = ctx._env
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


@tool_register("lookup_directory", "optional")
def lookup_directory(ctx, query):
    """Search the public organizational directory by name or role. Not
    everyone is listed on web pages; the directory is a separate channel."""
    _check_optional(ctx, "lookup_directory")
    env = ctx._env
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
            "note": 'Public organization directory results. No match does not establish absence; try different keywords.'}


@tool_register("request_callback", "optional")
def request_callback(ctx, contact, topic=None):
    """Register a callback request. No callback time is promised and the
    request does not advance any pending matter."""
    _check_optional(ctx, "request_callback")
    env = ctx._env
    if contact not in env.known_contacts:
        raise PermissionError("Contact has not been discovered")
    _budgeted(ctx)
    env.record("agent_request_callback", contact=contact, topic=topic)
    return {"status": "registered", "at": stamp(env.now),
            "text": 'Callback request registered. Staff will contact you when convenient; no callback time is promised, and email processing progress is unaffected.'}


@tool_register("leave_note", "optional")
def leave_note(ctx, contact, text):
    """Leave a note for a contact. Notes are recorded but are not answered
    and do not advance any pending matter."""
    _check_optional(ctx, "leave_note")
    env = ctx._env
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if contact not in env.known_contacts:
        raise PermissionError("Contact has not been discovered")
    _budgeted(ctx)
    env.record("agent_leave_note", contact=contact, text=text)
    return {"status": "recorded", "at": stamp(env.now),
            "text": 'Note recorded. Notes are not formal submissions and receive no separate reply.'}
