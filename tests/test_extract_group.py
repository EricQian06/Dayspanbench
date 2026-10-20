"""v0.5 club-case mechanisms: the hidden group tool (preview / join with
capacity windows and admin review / timeline reading) and the extract
recipient tool (LLM field extraction from agent prose, then branch matching
over the structured result)."""

from copy import deepcopy
import json
import unittest

from dayspanbench.calendar import parse
from dayspanbench.engine import Environment
from dayspanbench.llm import LLMConfig, SimulatorError, StructuredClient
from dayspanbench.recipient import RuleRecipient
from dayspanbench.validation import validate_task

from test_environment import load


def _client(result_object, fail=False):
    """A StructuredClient whose transport returns one canned extraction."""
    def transport(url, payload):
        if fail:
            raise SimulatorError("gateway down")
        return {"choices": [{"message": {"content": json.dumps(result_object)},
                             "finish_reason": "stop"}]}
    return StructuredClient(LLMConfig("judge-model", base_url="http://localhost:9", api_key="k"),
                            transport=transport)


class ClientRecipient(RuleRecipient):
    """A rule recipient that also carries the shared dialogue client."""
    def __init__(self, client):
        self.client = client


def group_task():
    task = deepcopy(load(1))
    task["hidden_tools"] = task.get("hidden_tools", []) + [
        {"name": "club_group", "usage":
            "The club's chat group. No arguments to preview, "
            '{"reason": text} to request joining, {"query": text} to read '
            "the timeline once a member.",
         "kind": "group", "params": {
             "group_name": "Badminton Club 2026",
             "initial_members": 198,
             "growth": [{"at": "2026-11-06T12:00:00+08:00", "count": 201}],
             "join": {"mode": "review", "reason_required": True,
                      "approval_at": "2026-11-06T14:00:00+08:00",
                      "windows": [
                          {"from": "2026-11-06T10:00:00+08:00",
                           "until": "2026-11-06T12:00:00+08:00",
                           "state": "full", "text": "The group is full right now."}]},
             "messages": [
                 {"at": "2026-11-06T11:00:00+08:00", "speaker": "Lin (President)",
                  "text": "Welcome, new members! Interview slots are announced on Friday."}],
             "announcements": [
                 {"title": "Recruitment open", "text": "Fill the recruitment form by Sunday.",
                  "at": "2026-11-06T10:30:00+08:00"}],
             "members": [
                 {"name": "Lin", "handle": "@lin", "note": "President"},
                 {"name": "Zhou", "handle": "@zhou", "note": "Events head"}],
         }}]
    return task


def officer_task():
    """DSB-01 plus an officer whose single workflow step extracts fields."""
    task = deepcopy(load(1))
    task["actors"].append({
        **deepcopy(next(a for a in task["actors"] if a["id"] == "sales")),
        "id": "officer", "name": "Club Officer - Lin", "role": "Interview scheduling",
        "contact_details": {"email": "officer@bench.example"},
        "description": "Answers interview rescheduling requests.",
        "knowledge": [],
        "tools": {
            "officer.main.1.extract": {
                "kind": "extract",
                "extract": {"wednesday_unavailable": {"type": "boolean"},
                            "keep_original": {"type": "boolean"}},
                "branches": [
                    {"when": {"wednesday_unavailable": True, "keep_original": True},
                     "text": "Understood, we will keep your original Tuesday slot."},
                    {"when": {"wednesday_unavailable": False},
                     "text": "Then the Wednesday 20:00 slot works for you."},
                ],
                "fallback": {"text": "Could you restate your availability in full?"},
            }},
        "workflows": [{
            "id": "main", "label": "Interview scheduling", "aliases": ["interview"],
            "required_fields": [],
            "steps": [{"id": "main_1", "label": "Read the request and answer",
                       "tool": "officer.main.1.extract",
                       "delay": {"mode": "elapsed", "minutes": 0}}],
            "evidence_fields": {},
        }],
    })
    task["public"]["initial_contacts"] = task["public"]["initial_contacts"] + ["officer"]
    return task


class GroupToolTests(unittest.TestCase):
    def setUp(self):
        self.task = group_task()
        self.assertEqual(validate_task(self.task), [])
        self.env = Environment(self.task)
        self.api = self.env.tools()
        self.api.discover_tools("club_group")

    def test_preview_shows_count_before_growth(self):
        preview = self.api.club_group()
        self.assertEqual(preview["member_count"], 198)
        self.assertFalse(preview["joined"])

    def test_join_blocked_inside_full_window(self):
        outcome = self.api.club_group(reason="I want to join the club")
        self.assertEqual(outcome["status"], "full")
        self.assertFalse(self.env.group_states["club_group"]["joined"])

    def test_review_join_approves_at_authored_time(self):
        self.env.advance("2026-11-06T12:30:00+08:00")
        outcome = self.api.club_group(reason="Freshman wanting to join")
        self.assertEqual(outcome["status"], "pending")
        # Growth schedule applied once the step time passes.
        self.assertEqual(outcome["member_count"], 201)
        # Reading before approval is not allowed.
        with self.assertRaises(PermissionError):
            self.api.club_group(query="interview")
        self.env.advance("2026-11-06T14:00:00+08:00")
        self.assertTrue(self.env.group_states["club_group"]["joined"])
        self.assertTrue(any("approved" in (m.get("text") or "").lower()
                            for m in self.env.messages))

    def test_query_returns_timeline_and_members(self):
        self.env.advance("2026-11-06T12:30:00+08:00")
        self.api.club_group()  # materialize the state entry, then join it
        self.env.group_states["club_group"]["joined"] = True
        result = self.api.club_group(query="members")
        speakers = [m["speaker"] for m in result["messages"]]
        self.assertIn("Lin (President)", speakers)
        self.assertEqual(result["announcements"][0]["title"], "Recruitment open")
        self.assertEqual([m["handle"] for m in result["members"]], ["@lin", "@zhou"])


class FormWindowTests(unittest.TestCase):
    def setUp(self):
        self.task = group_task()
        # A form service with an open window 12:00-15:00 on Nov 6.
        self.task["hidden_tools"].append({
            "name": "club_survey", "usage":
                'Submit the survey. Argument: {"fields": {...}}.',
            "kind": "form", "params": {
                "form": next(p["form"]["id"] for p in self.task["public"]["pages"] if p.get("form")),
                "available_from": "2026-11-06T12:00:00+08:00",
                "available_until": "2026-11-06T15:00:00+08:00",
                "expect": {}}})
        self.assertEqual(validate_task(self.task), [])
        self.env = Environment(self.task)
        self.api = self.env.tools()
        self.api.discover_tools("club_survey")

    def _fields(self):
        form = next(p["form"] for p in self.task["public"]["pages"] if p.get("form"))
        return {f["name"]: "x" for f in form["fields"]}

    def test_rejected_before_opening(self):
        with self.assertRaises(ValueError):
            self.api.club_survey(fields=self._fields())

    def test_accepted_inside_window(self):
        self.env.advance("2026-11-06T13:00:00+08:00")
        outcome = self.api.club_survey(fields=self._fields())
        self.assertEqual(outcome["status"], "submitted")

    def test_rejected_after_closing(self):
        self.env.advance("2026-11-06T15:00:00+08:00")
        with self.assertRaises(ValueError):
            self.api.club_survey(fields=self._fields())


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.task = officer_task()
        self.assertEqual(validate_task(self.task), [])

    def _drive(self, env, text, fields=None):
        api = env.tools()
        case = api.send_email("officer@bench.example", text, fields or {})
        while env.cases[case["case_id"]]["state"] != "replied":
            api.wait_until(self.task["deadline_at"])
        reply = next(m for m in env.messages if m["case_id"] == case["case_id"]
                     and m["status"] == "reply")
        return reply["text"], env.cases[case["case_id"]]

    def test_structured_fields_take_precedence(self):
        env = Environment(self.task)
        text, _ = self._drive(env, "About the interview",
                              {"wednesday_unavailable": True, "keep_original": True})
        self.assertIn("keep your original Tuesday slot", text)

    def test_llm_extraction_matches_branch(self):
        result = {"wednesday_unavailable": True, "keep_original": True}
        env = Environment(self.task, recipient={"officer": ClientRecipient(_client(result))})
        text, case = self._drive(env, "I have a rehearsal on Wednesday, so please "
                                      "keep my interview at the original time.")
        self.assertIn("keep your original Tuesday slot", text)
        self.assertTrue(any(e["kind"] == "agent_extract" for e in env.audit))

    def test_no_branch_matches_uses_fallback(self):
        result = {"wednesday_unavailable": True, "keep_original": False}
        env = Environment(self.task, recipient={"officer": ClientRecipient(_client(result))})
        text, _ = self._drive(env, "About the interview: Wednesday does not work; not sure about the rest.")
        self.assertIn("restate your availability", text)

    def test_llm_failure_falls_back_to_neutral_defaults(self):
        # No dialogue client at all: booleans default to False, matching the
        # deterministic neutral branch rather than erroring.
        env = Environment(self.task)
        text, _ = self._drive(env, "About the interview: any time next week is fine with me.")
        self.assertIn("Wednesday 20:00 slot works", text)


if __name__ == "__main__":
    unittest.main()
