"""Schema and referential validation without third-party dependencies."""

import re

from .calendar import Calendar, parse
from .engine import TRANSITIONS
from .scoring import equivalent

# Must match BRIEF_DATE_RULE in scripts/author_tasks.py.
BRIEF_DATE_RULE_TEXT = "日期一律按委托信息原文的规范格式（YYYY-MM-DD"
# user_fields values must already use the canonical date form the brief mandates:
# YYYY-MM-DD, optionally slash-joined for date ranges like stay_dates.
CANONICAL_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:/\d{4}-\d{2}-\d{2})*")
DATE_LIKE = re.compile(r"\d{4}[-/年]|\d{1,2}月")


def validate_task(task):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(task["schema_version"] == "0.2", "Unsupported schema version; regenerate task fixtures")
    check(BRIEF_DATE_RULE_TEXT in task["public"]["brief"], "Public brief missing the canonical date-format communication rule")
    for key, value in task["public"]["user_fields"].items():
        if isinstance(value, str) and DATE_LIKE.search(value):
            check(CANONICAL_DATE.fullmatch(value) is not None, f"user_fields '{key}' must use the canonical date format the brief mandates")
    check(parse(task["deadline_at"]) > parse(task["start_at"]), "Deadline must follow start")
    check(task["expected_conclusion"] in task["public"]["conclusion_options"], "Correct conclusion label absent from public answer choices")
    check(len(task["public"]["conclusion_options"]) >= 2, "Conclusion choices reveal the answer")
    check(2 <= task["horizon_design"]["reference_days"] <= 300, "Reference horizon outside 2–300 days")
    check((parse(task["deadline_at"]) - parse(task["start_at"])).total_seconds() >= task["horizon_design"]["reference_days"] * 86400,
          "Deadline shorter than designed reference horizon")
    actors = {a["id"]: a for a in task["actors"]}
    check(len(actors) == len(task["actors"]), "Duplicate actor IDs")
    facts = task["facts"]
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
                elif tool["kind"] == "delegate":
                    check(tool["target"] in actors, f"{wid}: unknown delegate")
                    target = actors[tool["target"]]
                    child = next((w for w in target["workflows"] if w["id"] == tool["workflow"]), None)
                    check(child is not None, f"{wid}: missing child workflow")
                    if child:
                        check(set(child["required_fields"]) <= set(tool["forward_fields"]), f"{wid}: handoff drops required fields")
                    edges[wid].append((tool["target"], tool["workflow"]))
                elif tool["kind"] == "refer":
                    check(set(tool["contacts"]) <= set(actors), f"{wid}: nonexistent referral")
                else:
                    check(tool["kind"] == "reply", f"{wid}: unsupported tool")
            check(actor["tools"][workflow["steps"][-1]["tool"]]["kind"] == "reply", f"{wid}: workflow must terminate in reply")
    for spec in task["calendars"].values():
        Calendar(spec).next_open(parse(task["start_at"]))
    check(set(task["public"]["initial_contacts"]) <= set(actors), "Unknown initial contact")
    for page in task["public"]["pages"]:
        check(set(page["contacts"]) <= set(actors), "Unknown directory contact")
    check(len(set(g["key"] for g in task["goals"])) == len(task["goals"]), "Duplicate goal keys")
    for goal in task["goals"]:
        if goal.get("status") == "unconfirmed":
            condition = goal["pending_condition"]
            check(any(condition["capability"] in w.get("capabilities", []) for a in actors.values() for w in a["workflows"]), "No workflow offers required capability")
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
