"""Graph-mode engine integration: the DSB-43 world graph driven end to end.

The unit semantics live in test_graph.py; this file locks in the engine-side
plumbing: transport-only send, activation batching, environment backfill via
processed forms and scheduled announcements, mutex branch firing with
receipts, and the reference witness's graph-mode wait.
"""

import json
from pathlib import Path
import unittest

from dayspanbench.engine import Environment
from dayspanbench.reference import run_reference
from dayspanbench.simulator import LLMSimulator
from dayspanbench.validation import validate_task

ROOT = Path(__file__).resolve().parents[1]


class GraphInterpretStub:
    """A dialogue_client stand-in: one canned interpret response (in whatever
    shape the model actually produced) plus a passthrough reply render."""

    def __init__(self, interpret_response):
        self.interpret_response = interpret_response
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["purpose"] == "interpret":
            return self.interpret_response
        if kwargs["purpose"] == "reply":
            return {"tone": "polite", "text": kwargs["view"]["canonical_text"]}
        raise AssertionError(f"unexpected purpose {kwargs['purpose']}")


def load():
    return json.loads((ROOT / "tasks/private/DSB-43.json").read_text(encoding="utf-8"))


class GraphEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = load()
        cls.env, cls.answer, cls.result = run_reference(cls.task)

    def test_task_validates(self):
        self.assertEqual(validate_task(self.task), [])

    def test_witness_completes(self):
        self.assertTrue(self.result["complete"])
        self.assertTrue(self.result["deterministic_anchors_ok"])
        self.assertEqual(self.answer["conclusion"], "resolved")

    def test_unestablished_goal_fact_fails_anchors(self):
        # ep-007 regression: an agent that never contacted the piano club
        # cannot be complete just because its summary (or a hallucinating
        # judge) claims the confirmation — the missing accepted fact must
        # fail the deterministic anchors on graph tasks.
        from dayspanbench import scoring
        answer = {"conclusion": "resolved", "summary": "everything confirmed"}
        env, _, _ = run_reference(self.task)
        env.director.facts.pop("pnc_confirmed_original")
        result = scoring.evaluate(env, answer)
        self.assertFalse(result["deterministic_checks"]["goal_facts_established"])
        self.assertFalse(result["deterministic_anchors_ok"])
        self.assertFalse(result["complete"])

    def test_rescheduling_branches_fired(self):
        # The two conversations landed on their authored branches: badminton
        # moved off Wednesday, piano kept the original slot.
        facts = self.env.director.facts
        self.assertIn("bwc_rescheduled_monday", facts)
        self.assertIn("pnc_confirmed_original", facts)
        self.assertNotIn("bwc_wednesday_booked", facts)
        self.assertNotIn("pnc_wednesday_booked", facts)

    def test_survey_environment_nodes_backfilled(self):
        # The processed forms completed the environment nodes, which is what
        # let the rescheduling service nodes pass their prerequisites later.
        nodes = self.env.graph.nodes
        self.assertEqual(nodes["bwc_survey_processed"].state, "completed")
        self.assertEqual(nodes["pnc_survey_processed"].state, "completed")
        self.assertEqual(nodes["bwc_assignment_posted"].state, "completed")
        self.assertEqual(nodes["pnc_assignment_posted"].state, "completed")

    def test_receipts_issued_for_service_fires(self):
        # The two rescheduling conversations produce written verification;
        # the environment nodes (surveys, announcements) never do.
        receipt_nodes = set().union(*(set(r.get("fields") or {}) for r in self.env.director.receipts))
        self.assertEqual(receipt_nodes,
                         {"bwc_rescheduled_monday", "pnc_confirmed_original"})

    def test_repeated_request_answers_from_completion(self):
        # One-shot semantics: after completion a fresh letter is answered from
        # on_completed_reply, without a second processing or new facts.
        env = Environment(self.task)
        env.graph.env_backfill("bwc_assignment_posted", at=env.now)
        env.graph.fired("bwc_assignment_posted", at=env.now)
        env.graph.mark("bwc_move_slot",
                       {"slot_change_requested": True, "wednesday_unavailable": True},
                       source="test", at=env.now)
        env.graph.fire("bwc_move_slot", at=env.now, source="test")
        env.graph.fired("bwc_move_slot", at=env.now)
        mailboxes = env.graph_letters  # transport-only send never parses
        self.assertEqual(mailboxes, {})
        reply = env.graph.completed_reply("bwc_move_slot")
        self.assertIn("already been moved", reply)


class LiveChatTests(unittest.TestCase):
    """Real-time customer service replaces the phone channel in graph mode:
    queue-wait reply inside work hours, idle-cancel after 10 minutes."""

    @classmethod
    def setUpClass(cls):
        cls.task = load()

    def env_with_president(self):
        env = Environment(self.task)
        env.known_contacts.add("bwc_president")
        return env, env.tools()

    def activations(self, env, actor):
        return [e for e in env.events if e[2] == "graph_activate" and e[3] == actor]

    def test_chat_outside_work_hours_is_closed(self):
        env, api = self.env_with_president()
        # Advance to 12:00 local: the campus_evening calendar (18:00-23:00)
        # is closed, so the service queue does not accept the session.
        env.advance("2026-09-12T04:00:00+00:00")
        result = api.call("bwc_president", "How do I join?", fields={"user_inquired": True})
        self.assertEqual(result["status"], "no_answer")

    def test_chat_letter_queued_and_read_within_the_wait(self):
        env, api = self.env_with_president()
        # 22:30 local: inside work hours, outside the 19:00-21:00 peak, so the
        # wait is 0-3 minutes.
        env.advance("2026-09-12T14:30:00+00:00")
        result = api.call("bwc_president", "How do I join?", fields={"user_inquired": True})
        self.assertEqual(result["status"], "queued")
        self.assertTrue(env.graph_letters["bwc_president"])
        env.advance("2026-09-12T14:35:00+00:00")
        # The activation read the batch: no letters remain parked.
        self.assertFalse(env.graph_letters.get("bwc_president"))

    def test_idle_timeout_cancels_session_and_requeues(self):
        env, api = self.env_with_president()
        env.advance("2026-09-11T12:00:00+00:00")  # 20:00 local: peak window
        api.call("bwc_president", "How do I join?", fields={"user_inquired": True})
        epoch = env.graph_chat_epochs["bwc_president"]
        self.assertEqual(len(self.activations(env, "bwc_president")), 1)
        # A stale timeout (a newer interaction already opened a new session)
        # must not touch the queue.
        env.graph_session_timeout(("bwc_president", epoch + 1))
        self.assertEqual(len(self.activations(env, "bwc_president")), 1)
        # The live timeout cancels: the unread letter is re-queued with a
        # fresh wait (still exactly one pending activation), never dropped.
        env.graph_session_timeout(("bwc_president", epoch))
        self.assertEqual(len(self.activations(env, "bwc_president")), 1)
        self.assertTrue(env.graph_letters["bwc_president"])
        kinds = [r["kind"] for r in env.audit]
        self.assertIn("chat_session_cancelled", kinds)


class InterpretShapeTests(unittest.TestCase):
    """The ep-001 failure: models sometimes flatten the marks object to the
    top level ({node: {slot: value}} instead of {marks: {node: {slot: ...}}}),
    and a loose schema gave them room to. The enumerated schema and the
    unwrap fallback must both hold."""

    @classmethod
    def setUpClass(cls):
        cls.task = load()

    def env_with(self, response):
        stub = GraphInterpretStub(response)
        recipients = {a["id"]: LLMSimulator(stub, a["id"]) for a in self.task["actors"]}
        return Environment(self.task, recipient=recipients), stub

    def run_move_slot(self, response):
        env, stub = self.env_with(response)
        env.graph.env_backfill("bwc_assignment_posted", at=env.now)
        env.graph.fired("bwc_assignment_posted", at=env.now)
        env.graph_deliver("bwc_events_head", "Please move my interview; I cannot do Wednesday.", {})
        env.advance("2026-09-11T21:00:00+08:00")   # activation reads the batch
        env.advance("2026-09-11T23:30:00+08:00")   # node fires after its delay
        return env, stub

    def test_schema_enumerates_every_node_and_slot(self):
        env, stub = self.run_move_slot({"marks": {"bwc_move_slot": {
            "slot_change_requested": True, "wednesday_unavailable": True}}})
        interpret = next(c for c in stub.calls if c["purpose"] == "interpret")
        marks = interpret["schema"]["properties"]["marks"]
        self.assertEqual(set(marks["properties"]), {n.id for n in env.graph.nodes.values()
                                                    if n.owner == "bwc_events_head"})
        slots = marks["properties"]["bwc_move_slot"]["properties"]
        self.assertEqual(set(slots), {"slot_change_requested", "wednesday_unavailable"})
        self.assertEqual(slots["slot_change_requested"], {"type": "boolean"})

    def test_wellformed_nested_marks_fire_the_node(self):
        env, _ = self.run_move_slot({"marks": {"bwc_move_slot": {
            "slot_change_requested": True, "wednesday_unavailable": True}}})
        self.assertEqual(env.graph.nodes["bwc_move_slot"].state, "completed")
        self.assertIn("bwc_rescheduled_monday", env.director.facts)

    def test_flattened_marks_are_unwrapped(self):
        # The exact failure shape from ep-001: no "marks" wrapper.
        env, _ = self.run_move_slot({"bwc_move_slot": {
            "slot_change_requested": True, "wednesday_unavailable": True}})
        self.assertEqual(env.graph.nodes["bwc_move_slot"].state, "completed")
        self.assertIn("bwc_rescheduled_monday", env.director.facts)

    def test_empty_marks_are_a_legal_no_op(self):
        # The ep-005 failure shape: the letter restates an already-marked
        # request, so the interpretation is an empty marks object for a real
        # node. That is "no new evidence", never an environment error.
        env, _ = self.run_move_slot({"marks": {"bwc_move_slot": {}}})
        node = env.graph.nodes["bwc_move_slot"]
        self.assertEqual(node.state, "collecting")
        self.assertFalse(node.slots["slot_change_requested"].filled)

    def test_incomplete_node_gets_a_proactive_question(self):
        # Design point 3: the agent writes to a node whose evidence is
        # incomplete - the NPC asks about the missing slot instead of
        # staying silent (the ep-005 dead end).
        env, _ = self.run_move_slot({"marks": {"bwc_move_slot": {
            "slot_change_requested": True}}})
        node = env.graph.nodes["bwc_move_slot"]
        self.assertEqual(node.state, "collecting")
        replies = [m for m in env.messages
                   if m["from"] == "zhouyanan@bench.example"]
        self.assertTrue(replies)
        self.assertIn("Wednesday, 2026-09-23", replies[-1]["text"])


if __name__ == "__main__":
    unittest.main()
