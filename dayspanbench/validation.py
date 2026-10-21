"""Schema and referential validation without third-party dependencies."""

import re

from .calendar import Calendar, parse
from .engine import TRANSITIONS, PUBLIC_TOOLS, EXTRA_TOOLS, HIDDEN_TOOL_KINDS
from .graph import GraphRuntime, GraphSpecError
from .scoring import equivalent


def _validate_graph(task, actors):
    """Referential checks for the v0.6 world graph beyond GraphRuntime's own
    spec validation: owners must exist, effects must cite real facts/contacts/
    nodes, and the graph must never leak into the public export."""
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    try:
        runtime = GraphRuntime(task["graph"])
    except GraphSpecError as error:
        return [f"graph: {error}"]
    check("graph" not in task["public"], "The world graph must stay private")
    # Real-time customer service: authored peak windows, clock times.
    for index, window in enumerate(task["graph"].get("peak_hours", [])):
        check(isinstance(window, list) and len(window) == 2
              and all(re.fullmatch(r"\d{2}:\d{2}", edge) for edge in window)
              and window[0] < window[1],
              f"graph peak_hours[{index}] must be two ascending HH:MM clock times")
    node_ids = set(runtime.nodes)
    for node in runtime.nodes.values():
        where = f"graph node {node.id}"
        check(node.owner in actors or node.owner == "environment",
              f"{where}: unknown owner {node.owner}")
        check(bool(node.title), f"{where}: missing title")
        for slot in node.slots.values():
            check(bool(slot.description), f"{where}: slot {slot.key} needs a description "
                  "(the interpretation LLM reads it to parse agent prose)")
            if node.kind != "environment":
                check(bool(slot.question), f"{where}: slot {slot.key} needs a question "
                      "(the NPC's proactive follow-up when the slot is still missing)")
        if slot.valid_until:
            check(parse(task["start_at"]) < parse(slot.valid_until),
                  f"{where}: slot {slot.key} expires before the episode starts")
        if node.kind == "inquiry":
            check(all(slot.volatile for slot in node.slots.values()),
                  f"{where}: an inquiry self-loop must clear all its slots (volatile)")
        if node.kind == "environment":
            check(bool(node.event), f"{where}: environment node without an event")
        for branch in node.branches:
            check(bool(branch.get("reply")), f"{where}: a branch without reply text")
        effect_sets = [node.effects] + [b.get("effects", []) for b in node.branches]
        for effects in effect_sets:
            for effect in effects:
                kind = effect.get("kind")
                if kind == "register_facts":
                    check(set(effect.get("facts", [])) <= set(task["facts"]),
                          f"{where}: register_facts cites unknown fact")
                    issuer = effect.get("issuer", node.owner)
                    if issuer != "environment":
                        check(issuer in actors, f"{where}: register_facts with unknown issuer")
                        if issuer in actors:
                            check(set(effect.get("facts", [])) <= set(actors[issuer]["knowledge"]),
                                  f"{where}: register_facts outside issuer knowledge")
                elif kind == "share_contacts":
                    check(set(effect.get("contacts", [])) <= set(actors),
                          f"{where}: share_contacts cites unknown contact")
                elif kind == "schedule_event":
                    target = effect.get("target_node")
                    check(target in node_ids, f"{where}: schedule_event targets unknown node")
                    check(bool(effect.get("at")), f"{where}: schedule_event without a time")
                    if effect.get("at"):
                        check(parse(task["start_at"]) <= parse(effect["at"]) < parse(task["deadline_at"]),
                              f"{where}: schedule_event outside the episode window")
                elif kind == "complete_node":
                    check(effect.get("target_node") in node_ids,
                          f"{where}: complete_node targets unknown node")
                    check(effect.get("target_node") != node.id,
                          f"{where}: complete_node targeting itself (use a terminal branch instead)")
                else:
                    check(False, f"{where}: unknown graph effect kind {kind}")
        for rule in node.derive:
            where_rule = f"{where}: derive rule"
            check(set(rule.get("when", {})) <= set(node.slots),
                  f"{where_rule} conditions a slot the node does not have")
            for target, marks in rule.get("marks", {}).items():
                check(target in node_ids, f"{where_rule} targets unknown node {target}")
                if target not in node_ids:
                    continue
                target_node = runtime.nodes[target]
                check(target_node.owner == node.owner,
                      f"{where_rule} targets {target} of a different owner")
                check(set(marks) <= set(target_node.slots),
                      f"{where_rule} marks a slot {target} does not have")
                for value in marks.values():
                    if isinstance(value, str) and value.startswith("="):
                        check(value[1:] in node.slots,
                              f"{where_rule} references unknown slot {value[1:]}")
    return errors

# The agent protocol (AGENT_PROMPT in dayspanbench/evaluation.py and
# docs/environment-contract.md) requires dates in messages to use the canonical
# YYYY-MM-DD form. user_fields must already comply: optionally slash-joined for
# date ranges like stay_dates.
CANONICAL_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:/\d{4}-\d{2}-\d{2})*")
DATE_LIKE = re.compile(r"\d{4}[-/年]|\d{1,2}月")


def validate_task(task):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(task["schema_version"] == "0.2", "Unsupported schema version; regenerate task fixtures")
    for key, value in task["public"]["user_fields"].items():
        if isinstance(value, str) and DATE_LIKE.search(value):
            check(CANONICAL_DATE.fullmatch(value) is not None, f"user_fields '{key}' must use the canonical date format the agent protocol mandates")
    check(parse(task["deadline_at"]) > parse(task["start_at"]), "Deadline must follow start")
    check(task["expected_conclusion"] in task["public"]["conclusion_options"], "Correct conclusion label absent from public answer choices")
    check(len(task["public"]["conclusion_options"]) >= 2, "Conclusion choices reveal the answer")
    check(2 <= task["horizon_design"]["reference_days"] <= 300, "Reference horizon outside 2–300 days")
    check((parse(task["deadline_at"]) - parse(task["start_at"])).total_seconds() >= task["horizon_design"]["reference_days"] * 86400,
          "Deadline shorter than designed reference horizon")
    actors = {a["id"]: a for a in task["actors"]}
    check(len(actors) == len(task["actors"]), "Duplicate actor IDs")
    if task.get("graph") is not None:
        errors.extend(_validate_graph(task, actors))
        node_ids = {n["id"] for n in task["graph"].get("nodes", [])}
    else:
        node_ids = set()
    facts = task["facts"]
    hidden = {t["name"]: t for t in task.get("hidden_tools", [])}

    def check_selections(requirements, where):
        for name, status in requirements.items():
            check(hidden.get(name, {}).get("kind") == "select", f"{where}: unknown selection service {name}")
            check(status in {"pending", "processed", "rejected", "expired"}, f"{where}: unknown selection status")

    def check_condition(condition, where):
        check(set(condition) <= {"not_before", "before", "facts", "selections", "catalog_entry"},
              f"{where}: unsupported condition")
        check(set(condition.get("facts", [])) <= set(facts), f"{where}: unknown prerequisite fact")
        check_selections(condition.get("selections", {}), where)
        item = condition.get("catalog_entry")
        if item:
            catalog = hidden.get(item.get("catalog"), {})
            entries = catalog.get("params", {}).get("entries", []) + [
                e for u in catalog.get("params", {}).get("updates", []) for e in u.get("add", [])]
            check(catalog.get("kind") == "catalog" and any(e["id"] == item.get("entry") for e in entries),
                  f"{where}: unknown conditional catalog entry")

    for name, tool in hidden.items():
        params = tool["params"]
        check_condition(params.get("requires", {}), name)
        if tool["kind"] == "catalog":
            for entry in params.get("entries", []) + [e for u in params.get("updates", []) for e in u.get("add", [])]:
                check_selections(entry.get("requires_selections", {}), name)
    all_tools = {name: tool for actor in actors.values() for name, tool in actor["tools"].items()}
    for fid, fact in facts.items():
        if fact.get("computed"):
            source = all_tools.get(fact["computed"].get("tool"), {})
            check(source.get("kind") == "lookup" and fid in source.get("facts", []),
                  f"{fid}: computed fact must name its producing lookup")
            check("{value}" in fact["computed"].get("text", ""),
                  f"{fid}: computed fact text must include its actual timestamp")
    if task.get("conclusion_by_fact"):
        rule = task["conclusion_by_fact"]
        check(rule.get("fact") in facts, "conclusion_by_fact: unknown fact")
        check(all(rule.get(k) in task["public"]["conclusion_options"] for k in ("before", "after", "missing")),
              "conclusion_by_fact: unknown conclusion label")
    def check_requirement(req):
        check(bool(req.get("subject")) and bool(req.get("predicate")) and bool(req.get("authorities")), "Incomplete evidence requirement")
        check(any(f["attributes"]["subject"] == req["subject"] and f["attributes"]["predicate"] == req["predicate"] for f in facts.values()), "Evidence requirement has no fixture")
    edges = {}
    for actor in actors.values():
        aid = actor["id"]
        check(actor["calendar"] in task["calendars"], f"{aid}: missing calendar")
        check(bool(actor["recipient"]["instructions"]), f"{aid}: missing receiver instructions")
        check(set(actor["process_engine"]["states"]) == set(TRANSITIONS), f"{aid}: incompatible state machine")
        check(actor["process_engine"]["workers"] == 1, f"{aid}: only one worker supported")
        check(set(actor["knowledge"]) <= set(facts), f"{aid}: unknown knowledge fact")
        check("email" in actor["contact_details"], f"{aid}: missing email address; send_email requires one")
        check(set(actor["channels"]) == set(actor["contact_details"]), f"{aid}: channels disagree with contact details")
        check(bool(actor["contact_details"]["email"].endswith("@bench.example")), f"{aid}: email not in the bench.example domain")
        for fid in actor["knowledge"]:
            check("attest:" + facts[fid]["attributes"]["predicate"] in actor["evidence_authorities"], f"{aid}: missing attestation authority")
        check(bool(actor["channels"]), f"{aid}: no channel")
        flows = {w["id"]: w for w in actor["workflows"]}
        check(len(flows) == len(actor["workflows"]), f"{aid}: duplicate workflows")
        for workflow in flows.values():
            wid = (aid, workflow["id"])
            edges[wid] = []
            check(bool(workflow["aliases"]), f"{wid}: no rule routing aliases")
            check(bool(workflow["steps"]), f"{wid}: no steps")
            if workflow.get("deduplicate_by"):
                check(set(workflow["deduplicate_by"]) <= set(workflow["required_fields"]),
                      f"{wid}: deduplication identity must use required fields")
                check(all(actor["tools"][s["tool"]]["kind"] != "deny" for s in workflow["steps"]),
                      f"{wid}: shared workflows must complete through reply")
            for field, requirement in workflow.get("evidence_fields", {}).items():
                check(field in workflow["required_fields"], f"{wid}: bad evidence gate")
                check_requirement(requirement)
            for step in workflow["steps"]:
                check(step["tool"] in actor["tools"], f"{wid}: tool outside actor allowlist")
                tool = actor["tools"][step["tool"]]
                delay = step["delay"]
                check(delay["mode"] in {"business", "elapsed", "weekly"}, f"{wid}: invalid delay")
                check(isinstance(delay["minutes"], int) and delay["minutes"] >= 0, f"{wid}: negative/non-integer duration")
                if tool["kind"] in {"lookup", "document"}:
                    check(set(tool["facts"]) <= set(actor["knowledge"]), f"{wid}: undeclared local facts")
                elif tool["kind"] == "suggest":
                    check(bool(tool.get("text")), f"{wid}: vague reply without text")
                    check(set(tool.get("guesses", [])) <= set(actors), f"{wid}: nonexistent guess")
                    check(all("email" in actors[c]["contact_details"] for c in tool.get("guesses", [])),
                          f"{aid}: guessed contact without a mailbox")
                elif tool["kind"] in {"delegate", "consult"}:
                    check(tool["target"] in actors, f"{wid}: unknown delegate")
                    target = actors[tool["target"]]
                    child = next((w for w in target["workflows"] if w["id"] == tool["workflow"]), None)
                    check(child is not None, f"{wid}: missing child workflow")
                    if child:
                        check(set(child["required_fields"]) <= set(tool["forward_fields"]), f"{wid}: handoff drops required fields")
                    edges[wid].append((tool["target"], tool["workflow"]))
                elif tool["kind"] == "refer":
                    check(set(tool["contacts"]) <= set(actors), f"{wid}: nonexistent referral")
                elif tool["kind"] == "deny":
                    check(bool(tool.get("text")), f"{wid}: deny reply without text")
                elif tool["kind"] == "acknowledge":
                    pass  # mid-workflow acceptance receipt; no extra structure
                elif tool["kind"] == "extract":
                    # v0.5 club cases: LLM extraction of authored fields,
                    # then branch matching on the structured result.
                    check(isinstance(tool.get("extract"), dict) and tool["extract"],
                          f"{wid}: extract tool without field spec")
                    for key, field in tool["extract"].items():
                        check(field.get("type") in {"boolean", "string", "enum"},
                              f"{wid}: extract field {key} without a known type")
                        if field.get("type") == "enum":
                            check(bool(field.get("values")), f"{wid}: enum field {key} without values")
                    check(isinstance(tool.get("branches"), list) and tool["branches"],
                          f"{wid}: extract tool without branches")
                    for branch in tool["branches"]:
                        check(bool(branch.get("when")) and bool(branch.get("text")),
                              f"{wid}: extract branch needs when-conditions and text")
                        check(set(branch["when"]) <= set(tool["extract"]),
                              f"{wid}: branch condition on unextracted field")
                        check(set(branch.get("facts", [])) <= set(task["facts"]),
                              f"{wid}: extract branch cites unknown fact")
                        check(set(branch.get("contacts", [])) <= set(actors),
                              f"{wid}: extract branch cites unknown contact")
                    check(bool(tool.get("fallback") and tool["fallback"].get("text")),
                          f"{wid}: extract tool without fallback branch")
                else:
                    check(tool["kind"] == "reply", f"{wid}: unsupported tool")
            check(actor["tools"][workflow["steps"][-1]["tool"]]["kind"] in {"reply", "deny", "extract"},
                  f"{wid}: workflow must terminate in reply, deny, or extract")
    for spec in task["calendars"].values():
        Calendar(spec).next_open(parse(task["start_at"]))
    check(set(task["public"]["initial_contacts"]) <= set(actors), "Unknown initial contact")
    delay = task.get("reply_delay")
    check(isinstance(delay, list) and len(delay) == 2
          and all(isinstance(m, int) and m > 0 for m in delay) and delay[0] <= delay[1],
          "reply_delay must be two ascending positive business minutes [min, max]")
    # The random admission delay must stay within 25% of every recipient's
    # shortest contiguous work window, so a reply never spills into the next
    # window because of randomness alone.
    def _minutes(span):
        start, end = span
        return int(end[:2]) * 60 + int(end[3:]) - int(start[:2]) * 60 - int(start[3:])
    used = {actor["calendar"] for actor in task["actors"]}
    min_window = min(_minutes(span) for name, spec in task["calendars"].items()
                     if name in used for span in spec["hours"])
    check(delay[1] <= min_window // 4,
          f"reply_delay max {delay[1]}min exceeds 25% of shortest work window {min_window}min")
    # Every actor that some workflow refers to, or that the agent may need to
    # follow up on, must be reachable by mail: referral prose carries mailboxes.
    for actor in actors.values():
        for tool in actor["tools"].values():
            if tool["kind"] == "refer":
                check(all("email" in actors[c]["contact_details"] for c in tool["contacts"]),
                      f"{actor['id']}: referral target without a mailbox")
    phones = [a["contact_details"]["phone"] for a in task["actors"] if "phone" in a["contact_details"]]
    check(len(phones) == len(set(phones)), "Duplicate phone numbers")
    emails = [a["contact_details"]["email"] for a in task["actors"]]
    check(len(emails) == len(set(emails)), "Duplicate email addresses")
    urls = []
    doc_urls = []
    page_ids = set()
    form_ids = set()
    form_field_names = {}
    for page in task["public"]["pages"]:
        page_ids.add(page["id"])
        check(set(page["contacts"]) <= set(actors), "Unknown directory contact")
        check(bool(page.get("snippet")), f"Page {page['id']}: missing search snippet")
        check(bool(page.get("url", "")) and page["url"].startswith("https://") and ".bench/" in page["url"],
              f"Page {page['id']}: missing or malformed URL")
        urls.append(page["url"])
        if "form" in page:
            form = page["form"]
            check(form["id"] not in form_ids, f"Duplicate form id: {form['id']}")
            form_ids.add(form["id"])
            check(bool(form.get("title")) and bool(form.get("submit_instructions")),
                  f"Form {form['id']}: missing title or submit_instructions")
            check(bool(form.get("fields")), f"Form {form['id']}: no fields")
            names = [f["name"] for f in form["fields"]]
            check(len(names) == len(set(names)), f"Form {form['id']}: duplicate field names")
            form_field_names[form["id"]] = set(names)
            for field in form["fields"]:
                check(bool(field.get("name")) and bool(field.get("label")),
                      f"Form {form['id']}: field without name or label")
                check(isinstance(field.get("required", True), bool) and isinstance(field.get("hidden", False), bool),
                      f"Form {form['id']}: required/hidden must be booleans")
        for document in page.get("documents", []):
            check(bool(document.get("url", "").startswith("https://")) and ".bench/" in document["url"]
                  and "/files/" in document["url"], f"Page {page['id']}: malformed document URL")
            check(bool(document.get("title")) and bool(document.get("text")),
                  f"Page {page['id']}: document without title or text")
            doc_urls.append(document["url"])
            issuer = actors.get(document.get("issuer"))
            if document.get("facts"):
                check(issuer is not None, f"Page {page['id']}: evidenced document without issuer")
                if issuer is not None:
                    for fid in document.get("facts", []):
                        # Deliberate evidence-discrimination trap: a document may
                        # publish a figure the issuer has no attestation authority
                        # for. Scoring rejects the resulting evidence because the
                        # issuer never gains the predicate authority; such facts
                        # must stay outside every actor's knowledge.
                        if facts.get(fid, {}).get("unauthorized_attestation"):
                            continue
                        check(fid in issuer["knowledge"],
                              f"Page {page['id']}: document facts outside issuer knowledge")
    check(len(urls) == len(set(urls)), "Duplicate page URLs")
    check(len(doc_urls) == len(set(doc_urls)), "Duplicate document URLs")
    # Out-of-authority trap facts may only exist as published decoy documents:
    # if any actor knew them, that actor would gain the predicate authority and
    # the decoy would become valid evidence.
    for fid, fact in facts.items():
        if fact.get("unauthorized_attestation"):
            check(not any(fid in actor["knowledge"] for actor in actors.values()),
                  f"Fact {fid}: unauthorized-attestation trap must stay outside actor knowledge")
    for index, update in enumerate(task.get("page_updates", [])):
        check(update["page"] in page_ids, f"page_updates[{index}]: unknown page")
        check(parse(task["start_at"]) <= parse(update["at"]) < parse(task["deadline_at"]),
              f"page_updates[{index}]: update outside the episode window")
        check(set(update) <= {"page", "at", "title", "text", "snippet", "contacts", "documents"},
              f"page_updates[{index}]: unsupported field")
        check(set(update.get("contacts", [])) <= set(actors), f"page_updates[{index}]: unknown contact")
    if "page_updates" in task:
        check("page_updates" not in task["public"], "The page update schedule must stay private")
    # Hidden tools: private definitions. Their names/usage must never leak into
    # the public export (they are revealed per-task inside NPC replies or page
    # text and unlocked via discover_tools).
    check("hidden_tools" not in task["public"], "Hidden tool definitions must stay private")
    # Authored LLM-judge criteria: private review rubric, never exported.
    check("judge_criteria" not in task["public"], "Judge criteria must stay private")
    for index, criterion in enumerate(task.get("judge_criteria", [])):
        cwhere = f"judge_criteria[{index}]"
        check(set(criterion) == {"id", "statement", "pass_if", "source"}, f"{cwhere}: unsupported field")
        check(bool(criterion["id"]) and bool(criterion["statement"]), f"{cwhere}: missing id or statement")
        check(criterion["source"] in {"final_answer", "trace", "final_state"}, f"{cwhere}: unknown source")
    check(len({c["id"] for c in task.get("judge_criteria", [])}) == len(task.get("judge_criteria", [])),
          "Duplicate judge criterion id")
    # Authored director stages: private progress graph for NPC wording hints.
    check("stages" not in task["public"], "Authored stages must stay private")
    check(len({s["id"] for s in task.get("stages", [])}) == len(task.get("stages", [])),
          "Duplicate stage id")
    for index, stage in enumerate(task.get("stages", [])):
        swhere = f"stages[{index}]"
        check(set(stage) <= {"id", "kind", "target", "hint", "keywords"},
              f"{swhere}: unsupported field")
        check(bool(stage.get("id")), f"{swhere}: missing id")
        check(stage.get("kind") in {"tool_call", "form_processed", "selection_processed", "fact_registered", "node_completed"},
              f"{swhere}: unknown stage kind")
        check(bool(stage.get("target")), f"{swhere}: missing target")
        if stage.get("kind") == "form_processed":
            check(stage.get("target") in form_ids, f"{swhere}: form_processed target must be a form id")
        if stage.get("kind") == "node_completed":
            check(task.get("graph") is not None and stage.get("target") in node_ids,
                  f"{swhere}: node_completed target must be a graph node id")
        if stage.get("keywords"):
            check(isinstance(stage["keywords"], list)
                  and all(isinstance(k, str) and k.strip() for k in stage["keywords"]),
                  f"{swhere}: keywords must be non-empty strings")
    hidden_names = []
    for index, tool in enumerate(task.get("hidden_tools", [])):
        where = f"hidden_tools[{index}]"
        check(set(tool) == {"name", "usage", "kind", "params"}, f"{where}: unsupported field")
        check(bool(tool["name"]), f"{where}: missing name")
        check(bool(tool["usage"]), f"{where}: missing usage instructions")
        check(tool["kind"] in HIDDEN_TOOL_KINDS, f"{where}: unknown hidden tool kind")
        check(tool["name"] not in hidden_names, f"{where}: duplicate hidden tool name")
        hidden_names.append(tool["name"])
        check(tool["name"] not in set(PUBLIC_TOOLS) | set(EXTRA_TOOLS), f"{where}: name collides with a common/optional tool")
        params = tool.get("params", {})
        if tool["kind"] == "form":
            check(params.get("form") in form_ids, f"{where}: unknown form page target")
            if params.get("form") in form_ids:
                check(set(params.get("expect", {})) <= form_field_names[params["form"]],
                      f"{where}: expect key outside the form's fields")
            check(not (params.get("process_at") and "process_delay" in params),
                  f"{where}: process_at and process_delay are mutually exclusive")
            if "process_at" in params:
                check(bool(params.get("process_at")) and parse(task["start_at"]) <= parse(params["process_at"]) < parse(task["deadline_at"]),
                      f"{where}: process_at outside the episode window")
            else:
                check(isinstance(params.get("process_delay", 60), int) and params.get("process_delay", 60) >= 0,
                      f"{where}: process_delay must be non-negative business minutes")
            for window_key in ("available_from", "available_until"):
                if params.get(window_key):
                    check(parse(task["start_at"]) <= parse(params[window_key]) < parse(task["deadline_at"]),
                          f"{where}: {window_key} outside the episode window")
            if params.get("available_from") and params.get("available_until"):
                check(parse(params["available_from"]) < parse(params["available_until"]),
                      f"{where}: available_from must be before available_until")
            check(params.get("calendar", "office") in task["calendars"], f"{where}: unknown processing calendar")
            if params.get("facts"):
                check(set(params["facts"]) <= set(facts), f"{where}: unknown evidence fact")
                check(params.get("issuer") in actors, f"{where}: evidenced form without issuer")
                issuer = actors.get(params.get("issuer"))
                if issuer is not None:
                    check(set(params["facts"]) <= set(issuer["knowledge"]), f"{where}: form facts outside issuer knowledge")
            if params.get("page_update"):
                check(params["page_update"].get("page") in page_ids, f"{where}: page_update targets an unknown page")
        elif tool["kind"] == "status":
            records = params.get("records", [])
            check(bool(records), f"{where}: status tool without records")
            keys = [r.get("key") for r in records]
            check(all(keys) and len(keys) == len(set(keys)), f"{where}: missing or duplicate record keys")
            for record in records:
                check(bool(record.get("initial")), f"{where}: record without initial text")
                for entry in record.get("timeline", []):
                    check(bool(entry.get("at")) and bool(entry.get("text")), f"{where}: incomplete timeline entry")
                    check(parse(task["start_at"]) <= parse(entry["at"]) < parse(task["deadline_at"]),
                          f"{where}: timeline entry outside the episode window")
                if record.get("form"):
                    check(record["form"] in form_ids, f"{where}: record linked to an unknown form")
        elif tool["kind"] == "catalog":
            entries = params.get("entries", [])
            check(bool(entries), f"{where}: catalog tool without entries")
            ids = [e.get("id") for e in entries]
            check(all(ids) and len(ids) == len(set(ids)), f"{where}: missing or duplicate entry ids")
            for entry in entries:
                check(bool(entry.get("title")), f"{where}: entry without title")
                for stamp_key in ("available_at", "expires_at"):
                    if entry.get(stamp_key):
                        check(parse(task["start_at"]) <= parse(entry[stamp_key]) < parse(task["deadline_at"]),
                              f"{where}: entry {stamp_key} outside the episode window")
                if entry.get("facts"):
                    check(set(entry["facts"]) <= set(facts), f"{where}: unknown evidence fact")
                    check(entry.get("issuer") in actors, f"{where}: entry facts without issuer")
                    issuer = actors.get(entry["issuer"])
                    if issuer is not None:
                        check(set(entry["facts"]) <= set(issuer["knowledge"]),
                              f"{where}: entry facts outside issuer knowledge")
            for index, update in enumerate(params.get("updates", [])):
                uwhere = f"{where}: updates[{index}]"
                check(bool(update.get("at")), f"{uwhere}: missing at")
                check(parse(task["start_at"]) <= parse(update["at"]) < parse(task["deadline_at"]),
                      f"{uwhere}: outside the episode window")
                check(bool(update.get("remove") or update.get("add")), f"{uwhere}: no add or remove")
                for entry in update.get("add", []):
                    check(bool(entry.get("id")) and bool(entry.get("title")), f"{uwhere}: entry without id or title")
        elif tool["kind"] == "select":
            catalog = params.get("catalog")
            catalogs = {t["name"] for t in task.get("hidden_tools", []) if t["kind"] == "catalog"}
            check(catalog in catalogs, f"{where}: select without a linked catalog tool")
            required = params.get("requires", {}).get("facts", [])
            check(set(required) <= set(facts), f"{where}: unknown prerequisite fact")
            if params.get("complete_before"):
                deadline = parse(params["complete_before"])
                check(parse(task["start_at"]) < deadline <= parse(task["deadline_at"]),
                      f"{where}: service deadline outside episode")
                if params.get("process_at"):
                    check(parse(params["process_at"]) < deadline,
                          f"{where}: processing is scheduled after service deadline")
                for fid in required + params.get("facts", []):
                    release = facts.get(fid, {}).get("available_at")
                    check(not release or parse(release) < deadline,
                          f"{where}: fact {fid} is published after service deadline")
            check(not (params.get("process_at") and "process_delay" in params),
                  f"{where}: process_at and process_delay are mutually exclusive")
            if "process_at" in params:
                check(bool(params.get("process_at")) and parse(task["start_at"]) <= parse(params["process_at"]) < parse(task["deadline_at"]),
                      f"{where}: process_at outside the episode window")
            else:
                check(isinstance(params.get("process_delay", 60), int) and params.get("process_delay", 60) >= 0,
                      f"{where}: process_delay must be non-negative business minutes")
            check(params.get("calendar", "office") in task["calendars"], f"{where}: unknown processing calendar")
            if params.get("facts"):
                check(set(params["facts"]) <= set(facts), f"{where}: unknown evidence fact")
                check(params.get("issuer") in actors, f"{where}: evidenced selection without issuer")
                issuer = actors.get(params.get("issuer"))
                if issuer is not None:
                    check(set(params["facts"]) <= set(issuer["knowledge"]), f"{where}: select facts outside issuer knowledge")
            if params.get("page_update"):
                check(params["page_update"].get("page") in page_ids, f"{where}: page_update targets an unknown page")
        elif tool["kind"] == "dialogue":
            rules = params.get("rules", [])
            check(bool(rules), f"{where}: dialogue tool without rules")
            check(all(hidden.get(n, {}).get("kind") == "select" for n in params.get("state_tools", [])),
                  f"{where}: role state must name existing selection services")
            for index, rule in enumerate(rules):
                check(bool(rule.get("keywords")) and bool(rule.get("answer")),
                      f"{where}: rules[{index}] without keywords or answer")
                check_condition(rule.get("when", {}), where)
                for variant in rule.get("variants", []):
                    check(bool(variant.get("when")) and bool(variant.get("answer")),
                          f"{where}: conditional dialogue requires when and answer")
                    check_condition(variant.get("when", {}), where)
        elif tool["kind"] == "group":
            check(bool(params.get("group_name")), f"{where}: group tool without a name")
            join = params.get("join", {})
            for index, window in enumerate(join.get("windows", [])):
                wwhere = f"{where}: join.windows[{index}]"
                check(bool(window.get("from")) and bool(window.get("until")),
                      f"{wwhere}: missing from or until")
                check(parse(window["from"]) < parse(window["until"]),
                      f"{wwhere}: window ends before it starts")
                for edge in ("from", "until"):
                    if window.get(edge):
                        check(parse(task["start_at"]) <= parse(window[edge]) < parse(task["deadline_at"]),
                              f"{wwhere}: window edge outside the episode window")
                check(window.get("state") in {"open", "full", "invite_only"},
                      f"{wwhere}: unknown window state")
            if join.get("mode") == "review":
                check(bool(join.get("approval_at")), f"{where}: review-mode group without approval_at")
            if join.get("approval_at"):
                check(parse(task["start_at"]) <= parse(join["approval_at"]) < parse(task["deadline_at"]),
                      f"{where}: approval_at outside the episode window")
            for index, step in enumerate(params.get("growth", [])):
                gwhere = f"{where}: growth[{index}]"
                check(bool(step.get("at")) and isinstance(step.get("count"), int),
                      f"{gwhere}: needs at and integer count")
                check(parse(task["start_at"]) <= parse(step["at"]) < parse(task["deadline_at"]),
                      f"{gwhere}: outside the episode window")
            for index, message in enumerate(params.get("messages", [])):
                mwhere = f"{where}: messages[{index}]"
                check(bool(message.get("at")) and bool(message.get("speaker"))
                      and bool(message.get("text")), f"{mwhere}: incomplete timeline message")
                check(parse(task["start_at"]) <= parse(message["at"]) < parse(task["deadline_at"]),
                      f"{mwhere}: outside the episode window")
            for index, member in enumerate(params.get("members", [])):
                check(bool(member.get("name")) and bool(member.get("handle")),
                      f"{where}: members[{index}] without name or handle")
            check(not (params.get("messages") and not params.get("members")),
                  f"{where}: group with timeline but without members")
        else:  # record
            records = params.get("records", [])
            check(bool(records), f"{where}: record tool without records")
            keys = [r.get("key") for r in records]
            check(all(keys) and len(keys) == len(set(keys)), f"{where}: missing or duplicate record keys")
            for record in records:
                check(bool(record.get("title")) and bool(record.get("text")), f"{where}: record without title or text")
                if record.get("requires_form"):
                    check(record["requires_form"] in form_ids, f"{where}: record gated on an unknown form")
                if record.get("facts"):
                    check(set(record["facts"]) <= set(facts), f"{where}: unknown evidence fact")
                    check(record.get("issuer") in actors, f"{where}: evidenced record without issuer")
                    issuer = actors.get(record.get("issuer"))
                    if issuer is not None:
                        check(set(record["facts"]) <= set(issuer["knowledge"]), f"{where}: record facts outside issuer knowledge")
    tools = task["public"].get("tools")
    if tools is not None:
        check(set(tools) <= set(PUBLIC_TOOLS) | set(EXTRA_TOOLS), "Unknown optional tool declared")
        check(set(PUBLIC_TOOLS) <= set(tools), "Common tools cannot be removed")
        check(len(tools) == len(set(tools)), "Duplicate tool entry")
    check(len(set(g["key"] for g in task["goals"])) == len(task["goals"]), "Duplicate goal keys")
    for goal in task["goals"]:
        if goal.get("status") == "unconfirmed":
            condition = goal["pending_condition"]
            check(task.get("graph") is not None
                  or any(condition["capability"] in w.get("capabilities", []) for a in actors.values() for w in a["workflows"]), "No workflow offers required capability")
            for req in condition.get("required_evidence", []):
                check_requirement(req)
        else:
            check_requirement(goal["evidence_requirement"])
            check(goal["match"] in {"expected", "evidence"}, "Unknown value matching rule")
            check(bool(goal["accepted_facts"]), "Goal without authoring witness")
            for fid in goal["accepted_facts"]:
                check(fid in facts and equivalent(facts[fid]["value"], goal["expected"], goal["normalization"]), f"Goal/fact disagreement: {fid}")

    def visit(node, stack):
        if node in stack:
            errors.append(f"Internal delegation cycle: {node}")
            return
        for child in edges.get(node, []):
            visit(child, stack | {node})
    for node in edges:
        visit(node, set())
    return errors
