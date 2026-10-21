"""The world-graph runtime (dayspanbench/graph.py): evidence-driven nodes.

Covers the design pillars of docs/graph-workflow-redesign.md: multi-letter
evidence accumulation, three-state slots (unfilled / filled true / filled
false), deterministic mutex branches covering every reachable direction (no
default branch), self-loop inquiry nodes, one-shot completed nodes,
environment backfill and prerequisite gating, evidence expiry, and
amend-by-overwrite.
"""

from copy import deepcopy
import unittest

from dayspanbench.calendar import parse
from dayspanbench.graph import GraphRuntime, GraphSpecError


def posted(runtime):
    """The environment assignment event: backfill + engine confirms effects."""
    fire = runtime.env_backfill("bwc_assignment_posted")
    if fire is not None:
        runtime.fired("bwc_assignment_posted")
    return fire


def badminton_graph():
    """A DSB-43-shaped excerpt: referral inquiry, posted-assignment environment
    node, and the move-slot service with mutex branches."""
    return {
        "nodes": [
            {"id": "bwc_referral", "owner": "bwc_president", "kind": "inquiry",
             "title": "Badminton recruitment referral",
             "requires": [{"key": "user_inquired", "type": "boolean", "volatile": True,
                           "require": True}],
             "branches": [{"label": "refer",
                           "when": {"user_inquired": True},
                           "reply": "Interview matters go to our Events head, Zhou Yanan."}],
             "on_completed_reply": "I already referred you; write to Zhou Yanan."},
            {"id": "bwc_assignment_posted", "owner": "environment", "kind": "environment",
             "title": "Badminton interview assignment posted",
             "effects": [{"kind": "register_facts", "facts": ["bwc_assignment_out"]}]},
            {"id": "bwc_move_slot", "owner": "bwc_events_head", "kind": "service",
             "title": "Move the badminton interview slot",
             "requires": ["bwc_assignment_posted",
                          {"key": "slot_change_requested", "type": "boolean",
                           "volatile": True},
                          {"key": "wednesday_unavailable", "type": "boolean",
                           "volatile": True, "require": "filled"}],
             "branches": [
                 {"label": "move_off_wednesday",
                  "when": {"slot_change_requested": True, "wednesday_unavailable": True},
                  "reply": "Moved to Monday, 2026-09-21, 19:30-20:30, Gym Court 2.",
                  "effects": [{"kind": "register_facts", "facts": ["bwc_rescheduled_monday"]}]},
                 {"label": "book_wednesday",
                  "when": {"slot_change_requested": True, "wednesday_unavailable": False},
                  "reply": "Moved to Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2.",
                  "effects": [{"kind": "register_facts", "facts": ["bwc_wednesday_booked"]}]},
                 {"label": "no_change",
                  "when": {"slot_change_requested": False},
                  "reply": "Your interview stays as assigned."}],
             "on_completed_reply": "Your interview has already been moved."},
        ]
    }


class MarkingTests(unittest.TestCase):
    def test_partial_evidence_across_letters_accumulates(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        # First letter only states the wish to move.
        report = runtime.mark("bwc_move_slot", {"slot_change_requested": True}, source="MSG-1")
        self.assertEqual(report.changed, ["slot_change_requested"])
        self.assertFalse(runtime.is_ready(runtime.nodes["bwc_move_slot"]))
        # Second letter supplies the Wednesday constraint; still no false from absence.
        runtime.mark("bwc_move_slot", {"wednesday_unavailable": True}, source="MSG-2")
        self.assertTrue(runtime.is_ready(runtime.nodes["bwc_move_slot"]))

    def test_absence_is_never_false(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        runtime.mark("bwc_move_slot", {"slot_change_requested": True}, source="MSG-1")
        slot = runtime.nodes["bwc_move_slot"].slots["wednesday_unavailable"]
        self.assertFalse(slot.filled)  # unaddressed, not filled false
        runtime.mark("bwc_move_slot", {}, source="MSG-2")
        self.assertFalse(slot.filled)

    def test_filled_false_is_valid_evidence_and_selects_the_other_branch(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        runtime.mark("bwc_move_slot", {"slot_change_requested": True,
                                       "wednesday_unavailable": False}, source="MSG-1")
        fire = runtime.fire("bwc_move_slot")
        self.assertEqual(fire["status"], "fired")
        self.assertEqual(fire["branch"], "book_wednesday")
        self.assertEqual(fire["effects"][0]["facts"], ["bwc_wednesday_booked"])

    def test_later_letter_overwrites_amends_unlit_evidence(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        runtime.mark("bwc_move_slot", {"slot_change_requested": True,
                                       "wednesday_unavailable": False}, source="MSG-1")
        # The agent corrects itself before the node fires.
        runtime.mark("bwc_move_slot", {"wednesday_unavailable": True}, source="MSG-2")
        fire = runtime.fire("bwc_move_slot")
        self.assertEqual(fire["branch"], "move_off_wednesday")

    def test_repeated_identical_value_is_not_new_evidence(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        first = runtime.mark("bwc_move_slot", {"slot_change_requested": True}, source="MSG-1")
        second = runtime.mark("bwc_move_slot", {"slot_change_requested": True}, source="MSG-2")
        self.assertEqual(first.changed, ["slot_change_requested"])
        self.assertEqual(second.changed, [])

    def test_invalid_values_rejected(self):
        runtime = GraphRuntime(badminton_graph())
        with self.assertRaises(ValueError):
            runtime.mark("bwc_move_slot", {"slot_change_requested": "yes"})
        with self.assertRaises(ValueError):
            runtime.mark("bwc_move_slot", {"nonexistent_key": True})


class BranchTests(unittest.TestCase):
    def test_explicitly_false_direction_has_its_own_branch(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        # slot_change_requested explicitly false: a real direction with an
        # authored branch, not a fallback question.
        runtime.mark("bwc_move_slot", {"slot_change_requested": False,
                                       "wednesday_unavailable": True}, source="MSG-1")
        node = runtime.nodes["bwc_move_slot"]
        self.assertTrue(runtime.is_ready(node))
        fire = runtime.fire("bwc_move_slot")
        self.assertEqual(fire["status"], "fired")
        self.assertEqual(fire["branch"], "no_change")
        self.assertEqual(fire["effects"], [])
        runtime.fired("bwc_move_slot")
        self.assertEqual(node.state, "completed")

    def test_require_true_slot_blocks_on_explicit_false(self):
        # An inquiry's user_inquired slot requires True: a letter conveying
        # False fills the slot but never completes the node.
        runtime = GraphRuntime(badminton_graph())
        runtime.mark("bwc_referral", {"user_inquired": False}, source="MSG-1")
        node = runtime.nodes["bwc_referral"]
        self.assertTrue(node.slots["user_inquired"].filled)
        self.assertFalse(node.satisfied)

    def test_node_level_effects_run_on_every_branch(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        runtime.mark("bwc_move_slot", {"slot_change_requested": True,
                                       "wednesday_unavailable": True}, source="MSG-1")
        fire = runtime.fire("bwc_move_slot")
        kinds = [e["kind"] for e in fire["effects"]]
        self.assertEqual(kinds.count("register_facts"), 1)


class InquiryTests(unittest.TestCase):
    def test_self_loop_clears_volatile_and_refires(self):
        runtime = GraphRuntime(badminton_graph())
        runtime.mark("bwc_referral", {"user_inquired": True}, source="MSG-1")
        node = runtime.nodes["bwc_referral"]
        self.assertTrue(runtime.is_ready(node))
        fire = runtime.fire("bwc_referral")
        self.assertEqual(fire["status"], "fired")
        runtime.fired("bwc_referral")
        # Back to collecting with the volatile slot cleared: askable again.
        self.assertEqual(node.state, "collecting")
        self.assertFalse(node.slots["user_inquired"].filled)
        self.assertEqual(node.fire_count, 1)
        runtime.mark("bwc_referral", {"user_inquired": True}, source="MSG-3")
        self.assertTrue(runtime.is_ready(node))

    def test_inquiry_counts_as_satisfied_prerequisite_after_firing(self):
        graph = badminton_graph()
        graph["nodes"].append(
            {"id": "followup_help", "owner": "bwc_president", "kind": "service",
             "title": "Follow-up help",
             "requires": ["bwc_referral", {"key": "asked", "type": "boolean"}],
             "on_completed_reply": "Helped."})
        runtime = GraphRuntime(graph)
        node = runtime.nodes["followup_help"]
        runtime.mark("followup_help", {"asked": True}, source="MSG-1")
        self.assertFalse(runtime.prerequisites_met(node))
        runtime.mark("bwc_referral", {"user_inquired": True}, source="MSG-2")
        runtime.fire("bwc_referral")
        runtime.fired("bwc_referral")
        self.assertTrue(runtime.prerequisites_met(node))


class OneShotTests(unittest.TestCase):
    def test_completed_node_answers_repeats_and_never_refires(self):
        runtime = GraphRuntime(badminton_graph())
        posted(runtime)
        runtime.mark("bwc_move_slot", {"slot_change_requested": True,
                                       "wednesday_unavailable": True}, source="MSG-1")
        fire = runtime.fire("bwc_move_slot")
        self.assertEqual(fire["status"], "fired")
        runtime.fired("bwc_move_slot")
        # The agent asks again after completion.
        repeat = runtime.fire("bwc_move_slot")
        self.assertEqual(repeat["status"], "already_completed")
        self.assertEqual(repeat["reply"], "Your interview has already been moved.")
        self.assertEqual(runtime.completed_reply("bwc_move_slot"),
                         "Your interview has already been moved.")


class EnvironmentTests(unittest.TestCase):
    def test_prerequisite_gates_service_until_event_fires(self):
        runtime = GraphRuntime(badminton_graph())
        runtime.mark("bwc_move_slot", {"slot_change_requested": True,
                                       "wednesday_unavailable": True}, source="MSG-1")
        node = runtime.nodes["bwc_move_slot"]
        self.assertTrue(node.satisfied)
        self.assertFalse(runtime.is_ready(node))  # assignment not posted yet
        status = runtime.requirements_status(node)
        self.assertEqual(status["waiting_for_nodes"], ["bwc_assignment_posted"])
        backfill = posted(runtime)
        self.assertEqual(backfill["status"], "fired")
        self.assertTrue(runtime.is_ready(node))

    def test_environment_backfill_is_idempotent(self):
        runtime = GraphRuntime(badminton_graph())
        self.assertIsNotNone(posted(runtime))
        self.assertIsNone(runtime.env_backfill("bwc_assignment_posted"))


class ExpiryTests(unittest.TestCase):
    def test_expired_slot_blocks_readiness_and_is_reported(self):
        graph = badminton_graph()
        graph["nodes"].append(
            {"id": "quote_hold", "owner": "landlord", "kind": "service",
             "title": "Hold the quoted price",
             "requires": [{"key": "accept_quote", "type": "boolean",
                           "valid_until": "2026-09-15T12:00:00+08:00"}],
             "on_completed_reply": "Held."})
        runtime = GraphRuntime(graph)
        node = runtime.nodes["quote_hold"]
        runtime.mark("quote_hold", {"accept_quote": True}, source="MSG-1",
                     at=parse("2026-09-14T10:00:00+08:00"))
        self.assertTrue(runtime.is_ready(node, parse("2026-09-14T11:00:00+08:00")))
        self.assertFalse(runtime.is_ready(node, parse("2026-09-16T10:00:00+08:00")))
        status = runtime.requirements_status(node, parse("2026-09-16T10:00:00+08:00"))
        self.assertEqual(status["expired_evidence"], ["accept_quote"])
        self.assertFalse(status["satisfied"])


class SpecValidationTests(unittest.TestCase):
    def test_unknown_prerequisite_rejected(self):
        graph = badminton_graph()
        graph["nodes"][1]["requires"] = ["no_such_node"]
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_branch_condition_on_unknown_slot_rejected(self):
        graph = badminton_graph()
        graph["nodes"][2]["branches"][0]["when"] = {"mystery": True}
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_branch_gap_rejected(self):
        # Branches must cover every reachable evidence combination.
        graph = badminton_graph()
        del graph["nodes"][2]["branches"][2]  # drop the no_change direction
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_default_branch_rejected(self):
        graph = badminton_graph()
        graph["nodes"][2]["default_branch"] = {"reply": "fallback"}
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_string_slot_cannot_steer_branches(self):
        graph = badminton_graph()
        graph["nodes"][2]["branches"][0]["when"] = {"slot_change_requested": True}
        graph["nodes"][2]["requires"] = ["bwc_assignment_posted",
                                         {"key": "slot_change_requested", "type": "string"}]
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_prerequisite_cycle_rejected(self):
        graph = badminton_graph()
        graph["nodes"][2]["requires"] = ["bwc_move_slot",
                                         {"key": "slot_change_requested", "type": "boolean"}]
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)

    def test_duplicate_node_ids_rejected(self):
        graph = badminton_graph()
        graph["nodes"].append(deepcopy(graph["nodes"][0]))
        with self.assertRaises(GraphSpecError):
            GraphRuntime(graph)


if __name__ == "__main__":
    unittest.main()
