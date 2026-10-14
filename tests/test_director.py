"""DirectorState: authored stage advancement, fact registration, receipts."""

import unittest

from dayspanbench.director import DirectorState


def stage(stage_id, kind, target, hint=""):
    return {"id": stage_id, "kind": kind, "target": target, "hint": hint}


class StageAdvancementTests(unittest.TestCase):
    def test_stages_advance_in_order_on_matching_events(self):
        director = DirectorState({"stages": [
            stage("s1", "tool_call", "verify_form"),
            stage("s2", "form_processed", "booking_form"),
            stage("s3", "fact_registered", "declaration"),
        ]})
        self.assertEqual(director.snapshot()["current_stage"]["id"], "s1")
        self.assertEqual(director.advance({"kind": "tool_call", "tool": "other"}), None)
        self.assertEqual(director.advance({"kind": "tool_call", "tool": "verify_form"}), "s1")
        # A later stage's event never satisfies an earlier pending stage.
        self.assertEqual(director.advance({"kind": "fact_registered", "fact": "declaration"}), None)
        self.assertEqual(director.advance({"kind": "form_processed", "form": "booking_form"}), "s2")
        self.assertEqual(director.advance({"kind": "fact_registered", "fact": "declaration"}), "s3")
        # All stages done: further events are no-ops.
        self.assertEqual(director.advance({"kind": "tool_call", "tool": "verify_form"}), None)
        snapshot = director.snapshot()
        self.assertIsNone(snapshot["current_stage"])
        self.assertEqual(snapshot["achieved_stages"], ["s1", "s2", "s3"])
        self.assertTrue(all(s["done"] for s in snapshot["stages"]))

    def test_stage_mismatch_target_never_advances(self):
        director = DirectorState({"stages": [stage("s1", "form_processed", "f1")]})
        self.assertEqual(director.advance({"kind": "form_processed", "form": "f2"}), None)
        self.assertEqual(director.snapshot()["achieved_stages"], [])

    def test_snapshot_carries_current_hint(self):
        director = DirectorState({"stages": [
            stage("s1", "tool_call", "t", hint="ask about the deadline")]})
        self.assertEqual(director.snapshot()["hint"], "ask about the deadline")

    def test_no_stages_is_inert(self):
        director = DirectorState({})
        self.assertEqual(director.advance({"kind": "tool_call", "tool": "x"}), None)
        self.assertEqual(director.snapshot()["achieved_stages"], [])

    def test_tool_call_matches_agent_hidden_tool_events(self):
        """tool_call covers the agent's own hidden-tool invocations too."""
        director = DirectorState({"stages": [
            stage("s1", "tool_call", "crew_board"),
            stage("s2", "selection_processed", "dispatch_desk")]})
        self.assertEqual(director.advance({"kind": "agent_hidden_catalog", "tool": "crew_board",
                                           "query": "valve list"}), "s1")
        self.assertEqual(director.advance({"kind": "agent_dialogue", "tool": "crew_board",
                                           "question": "again"}), None)
        self.assertEqual(director.advance({"kind": "selection_processed", "tool": "dispatch_desk",
                                           "accepted": True}), "s2")

    def test_keyword_stage_only_fires_on_matching_question(self):
        director = DirectorState({"stages": [
            {"id": "s1", "kind": "tool_call", "target": "user_dialogue",
             "keywords": ["approve", "批准"], "hint": ""}]})
        self.assertEqual(director.advance({"kind": "agent_dialogue", "tool": "user_dialogue",
                                           "question": "What are the rules?"}), None)
        self.assertEqual(director.advance({"kind": "agent_dialogue", "tool": "user_dialogue",
                                           "question": "Do you approve this exact plan?"}), "s1")


class FactRegistrationTests(unittest.TestCase):
    def test_register_fact_records_established_fact(self):
        director = DirectorState()
        record = director.register_fact("total", 18600, "总价为18600元。", "sales", "2026-11-02T09:00:00+08:00")
        self.assertEqual(record["id"], "total")
        self.assertEqual(record["fact_id"], "total")
        self.assertEqual(record["value"], 18600)
        self.assertTrue(record["agent_visible"])
        self.assertIn("total", director.snapshot()["achieved_facts"])

    def test_reregistration_keeps_visibility_and_unions_authorities(self):
        director = DirectorState()
        director.register_fact("f", 1, "text", "a", "t0", agent_visible=True,
                               authorities=["attest:x"])
        record = director.register_fact("f", 1, "text", "b", "t1", agent_visible=False,
                                        authorities=["attest:y"])
        self.assertTrue(record["agent_visible"], "an already visible fact never hides")
        self.assertEqual(record["authorities"], ["attest:x", "attest:y"])


class ReceiptTests(unittest.TestCase):
    def test_receipt_numbering_and_shape(self):
        director = DirectorState()
        first = director.issue_receipt("预约办结回执", "登记完成。", {"price": 10500}, "venue_desk",
                                       "2026-11-06T17:30:00+08:00")
        second = director.issue_receipt("确认回执", "The table has been reserved.", {"slot": True},
                                        "trip_desk", "2026-11-06T18:00:00+08:00")
        self.assertEqual(first["receipt_no"], "R-0001")
        self.assertEqual(second["receipt_no"], "R-0002")
        for receipt in (first, second):
            self.assertEqual(set(receipt), {"receipt_no", "title", "text", "fields",
                                            "issuer", "issued_at"})
        self.assertEqual(director.snapshot()["receipts"], [first, second])


if __name__ == "__main__":
    unittest.main()
