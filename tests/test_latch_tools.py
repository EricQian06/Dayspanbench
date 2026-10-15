"""LATCH-port mechanisms: catalog/select/dialogue hidden tools, web-search
service mentions, and the post-episode LLM judge."""

from copy import deepcopy
import json
import unittest

from dayspanbench.engine import Environment
from dayspanbench.llm import LLMConfig, SimulatorError, StructuredClient
from dayspanbench.validation import validate_task
from dayspanbench.judge import LLMJudge

from test_environment import load, mailbox


def catalog_task():
    """DSB-01 plus a searchable menu catalog, a table-selection commit tool
    with a hold that can lapse, and a user-dialogue tool."""
    task = deepcopy(load(1))
    task["hidden_tools"] = [
        {"name": "garden_menu_search", "usage":
            "Garden Ramp Bistro menu search. Argument: query (optional string).",
         "kind": "catalog", "params": {
             "keywords": ["menu", "lunch", "bistro", "table"],
             "clue": "Garden Ramp Bistro publishes its live menu through the garden_menu_search service.",
             "entries": [
                 {"id": "lunch-1300", "title": "Six-top Sunday lunch 13:00",
                  "text": "Six-person Sunday lunch table at 13:00.", "fields": {"total_usd": 247.8},
                  "facts": ["price"], "issuer": "sales"},
                 {"id": "lunch-1330", "title": "Sunday lunch table 13:30",
                  "text": "The remaining table, after the 13:00 slot sells out.",
                  "fields": {"total_usd": 262.0, "available_at_note": "v2 offer"}},
             ],
             "updates": [
                 {"at": "2026-11-07T10:00:00+08:00", "remove": ["lunch-1300"]},
             ]}},
        {"name": "garden_reserve_table", "usage":
            "Reserve a table from the garden_menu_search results. Argument: entry "
            "(option id) to select, or query to check the current reservation status.",
         "kind": "select", "params": {
             "catalog": "garden_menu_search",
             "expect_entry": "lunch-1330",
             "process_delay": 60, "calendar": "office",
             "hold_minutes": 240,
             "result_text": "The table has been reserved.",
             "reject_text": "That option is no longer available.",
             "facts": ["slot"], "issuer": "operations"}},
        {"name": "ask_user", "usage":
            "Ask the family member you are assisting a question. Argument: question (string).",
         "kind": "dialogue", "params": {
             "persona": "the user",
             "rules": [
                 {"keywords": ["budget", "spend"], "answer": "Our budget for lunch is 280 dollars in total."},
                 {"keywords": ["allerg", "sesame"], "answer": "One child has a sesame allergy; it must be controlled."},
             ],
             "default": "I have nothing to add."}},
    ]
    return task


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.task = catalog_task()
        self.assertEqual(validate_task(self.task), [])
        self.env = Environment(self.task)
        self.api = self.env.tools()
        for name in ("garden_menu_search", "garden_reserve_table", "ask_user"):
            self.api.discover_tools(name)

    def test_search_mention_surfaces_then_hides(self):
        task = catalog_task()
        env = Environment(task)
        api = env.tools()
        mentions = api.web_search("bistro menu")["service_mentions"]
        self.assertEqual([m["service"] for m in mentions], ["garden_menu_search"])
        api.discover_tools("garden_menu_search")
        self.assertEqual(api.web_search("bistro menu")["service_mentions"], [])
        # Unrelated queries never see the clue.
        self.assertEqual(api.web_search("venue")["service_mentions"], [])

    def test_catalog_lists_and_filters_with_receipt(self):
        result = self.api.garden_menu_search(query="six-person")
        self.assertEqual([r["id"] for r in result["results"]], ["lunch-1300"])
        receipt = result["results"][0]["receipts"][0]
        self.assertEqual(receipt["fields"], {"price": 10500})
        self.assertIn("10500", receipt["text"])
        self.assertTrue(self.env.director.facts["price"]["agent_visible"])

    def test_catalog_update_removes_stale_offer(self):
        self.env.advance("2026-11-07T10:01:00+08:00")
        result = self.api.garden_menu_search(query="lunch")
        self.assertEqual([r["id"] for r in result["results"]], ["lunch-1330"])

    def test_select_processes_and_reads_back(self):
        receipt = self.api.garden_reserve_table(entry="lunch-1330")
        self.assertEqual(receipt["status"], "submitted")
        with self.assertRaises(ValueError):  # active selection blocks re-selection
            self.api.garden_reserve_table(entry="lunch-1330")
        pending = self.api.garden_reserve_table(query="status")
        self.assertEqual(pending["status"], "pending")
        self.env.advance("2026-11-06T17:30:00+08:00")
        outcome = self.api.garden_reserve_table(query="status")
        self.assertEqual(outcome["status"], "processed")
        self.assertEqual(outcome["state"], "The table has been reserved.")
        self.assertEqual(outcome["receipts"][0]["fields"], {"slot": True})  # the slot fact

    def test_select_rejects_wrong_option(self):
        self.api.garden_reserve_table(entry="lunch-1300")
        self.env.advance("2026-11-06T17:30:00+08:00")
        outcome = self.api.garden_reserve_table(query="status")
        self.assertEqual(outcome["status"], "rejected")

    def test_hold_expiry_cancels_pending_selection(self):
        # Submitted at Friday 17:30: the hold lapses 240 elapsed minutes later,
        # before the office-calendar processing completes on Monday morning.
        self.env.advance("2026-11-06T17:30:00+08:00")
        self.api.garden_reserve_table(entry="lunch-1330")
        self.env.advance("2026-11-06T21:31:00+08:00")
        outcome = self.api.garden_reserve_table(query="status")
        self.assertEqual(outcome["status"], "expired")

    def test_dialogue_matches_rules_and_default(self):
        answer = self.api.ask_user(question="What is your budget for the meal?")
        self.assertIn("280", answer["answer"])
        answer = self.api.ask_user(question="Any allergies I should know about?")
        self.assertIn("sesame", answer["answer"])
        answer = self.api.ask_user(question="What color tablecloth?")
        self.assertEqual(answer["answer"], "I have nothing to add.")


def _client(result_object, fail=False):
    """A StructuredClient whose transport returns one canned verdict."""
    def transport(url, payload):
        if fail:
            raise SimulatorError("gateway down")
        content = json.dumps(result_object)
        return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}
    return StructuredClient(LLMConfig("judge-model", base_url="http://localhost:9", api_key="k"),
                            transport=transport)


CRITERIA = [{"id": "R6", "statement": "The final response states the reservation plainly.",
             "pass_if": "No invented details.", "source": "final_answer"}]


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.task = deepcopy(load(1))
        self.task["judge_criteria"] = CRITERIA
        self.env = Environment(self.task)

    def test_graded_verdict_round_trip(self):
        verdict = {"criteria": [{"criterion_id": "R6", "passed": True,
                                 "evidence": [{"source": "final_answer", "pointer": "goals",
                                               "quote_or_value": "reserved"}],
                                 "reason": "Matches the record."}]}
        judge = LLMJudge(_client(verdict))
        review = judge.judge(self.task, self.env, {"conclusion": "ok"})
        self.assertEqual(review["status"], "graded")
        self.assertTrue(review["criteria"][0]["passed"])

    def test_malformed_verdict_retries_then_pending(self):
        verdict = {"criteria": [{"criterion_id": "OTHER", "passed": True, "evidence": [], "reason": "x"}]}
        judge = LLMJudge(_client(verdict), validation_retries=1)
        review = judge.judge(self.task, self.env, {})
        self.assertEqual(review["status"], "pending")
        self.assertIsNone(review["criteria"][0]["passed"])
        self.assertEqual(judge.client.calls[-1]["validation_error"] is not None, True)

    def test_infrastructure_failure_is_pending_not_raise(self):
        judge = LLMJudge(_client(None, fail=True))
        review = judge.judge(self.task, self.env, {})
        self.assertEqual(review["status"], "pending")

    def test_provider_quirk_keys_are_normalized_not_pending(self):
        # deepseek-v4-flash style output: "verdicts"/"pass", no evidence array
        # but inline citations in "reason". Key spelling must not turn a
        # gradeable episode into a pending one.
        verdict = {"verdicts": [{"criterion_id": "R6", "pass": True,
                                 "reason": "final_answer.summary states the reservation; receipt R-0001 confirms."}]}
        judge = LLMJudge(_client(verdict))
        review = judge.judge(self.task, self.env, {"conclusion": "ok"})
        self.assertEqual(review["status"], "graded")
        self.assertTrue(review["criteria"][0]["passed"])
        self.assertTrue(review["criteria"][0]["evidence_synthesized"])
        self.assertEqual(review["criteria"][0]["evidence"][0]["pointer"], "judge.reason")

    def test_evidence_source_aliases_are_normalized_not_pending(self):
        # Models on lenient gateways invent source names ("receipts",
        # "established_facts"); aliases must coerce them instead of failing
        # strict validation and marking the episode judge_pending.
        verdict = {"criteria": [{"criterion_id": "R6", "passed": True,
                                 "evidence": [
                                     {"source": "receipts", "pointer": "R-0001",
                                      "quote_or_value": "reservation confirmed"},
                                     {"source": "Established_Facts", "pointer": "goals",
                                      "quote_or_value": "reserved"}],
                                 "reason": "Cited from receipt and facts."}]}
        judge = LLMJudge(_client(verdict))
        review = judge.judge(self.task, self.env, {"conclusion": "ok"})
        self.assertEqual(review["status"], "graded")
        sources = [e["source"] for e in review["criteria"][0]["evidence"]]
        self.assertEqual(sources, ["receipt", "trace"])


if __name__ == "__main__":
    unittest.main()
