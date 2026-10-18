"""Regressions for audited dialogue, publication and resource scheduling faults.

These tests use authored tasks and local simulator fixtures, never model APIs.
Reference runs establish deterministic solvability, not LLM benchmark scores.
"""
from copy import deepcopy
from datetime import timedelta
import unittest
from unittest.mock import patch

from dayspanbench.calendar import Calendar, parse
from dayspanbench.dialogue import matches
from dayspanbench.engine import Environment
from dayspanbench.llm import SimulatorError
from dayspanbench.reference import run_reference
from dayspanbench.validation import validate_task
from test_environment import load
from test_dialogue_llm import llm_env
from test_simulator import FixtureClient


def ask(env, name, question):
    api = env.tools()
    api.discover_tools(name)
    return getattr(api, name)(question=question)["answer"]


class DialogueRegressionTests(unittest.TestCase):
    def test_phone_survives_when_and_case_in_rule_and_llm_modes(self):
        for client in (None, FixtureClient()):
            env = llm_env(load(31), client) if client else Environment(load(31))
            for question in (
                "What phone number did you provide when you applied for relief?",
                "What is the phone number on your case file?",
            ):
                with self.subTest(question=question, llm=bool(client)):
                    self.assertIn("555-0182", ask(env, "rosa_dialogue", question))
            if client:
                views = [c["view"] for c in client.calls if c["purpose"] == "dialogue"]
                self.assertTrue(all(any("555-0182" in f["text"] for f in v["role_facts"]) for v in views))

    def test_word_boundaries_do_not_read_id_inside_did_or_provide(self):
        self.assertFalse(matches("What did you provide?", ["id"]))
        self.assertTrue(matches("What ID document?", ["id"]))
        self.assertTrue(matches("accessibility needs", ["access"]))

    def test_multi_topic_question_includes_access_food_budget_and_approval(self):
        env = Environment(load(13))
        answer = ask(env, "family_dialogue",
                     "For our party, what are the access, food, budget and approval requirements?")
        for expected in ("Four adults", "wheelchair", "sesame", "280", "11:00"):
            self.assertIn(expected, answer)

    def test_semantic_selection_supports_question_without_authored_keywords(self):
        class SynonymClient(FixtureClient):
            def complete(self, **kwargs):
                if kwargs["purpose"] == "dialogue_topics":
                    self.calls.append(deepcopy(kwargs))
                    return {"topic_ids": ["3"]}
                return super().complete(**kwargs)
        env = llm_env(load(31), SynonymClient())
        self.assertIn("555-0182", ask(env, "rosa_dialogue", "Which digits should I dial?"))

    def test_invalid_selector_falls_back_without_losing_explicit_topic(self):
        class InvalidSelector(FixtureClient):
            def complete(self, **kwargs):
                if kwargs["purpose"] == "dialogue_topics":
                    return {"topic_ids": ["invented"]}
                return super().complete(**kwargs)
        env = llm_env(load(31), InvalidSelector())
        self.assertIn("555-0182", ask(env, "rosa_dialogue", "phone when applied?"))
        self.assertTrue(any(r["kind"] == "dialogue_topic_fallback" for r in env.audit))

    def test_completed_course_replaces_stale_history_without_revealing_future_packet(self):
        client = FixtureClient()
        env, _, _ = run_reference(load(16), recipient=None)
        # Preserve an earlier false memory; current facts must override it.
        env.dialogue_history["career_dialogue"] = [{"question": "course?", "answer": "Not complete."}]
        env.dialogue_client = client
        answer = ask(env, "career_dialogue", "Is the course complete, may I apply with the projects?")
        self.assertIn("course is complete", answer)
        self.assertNotIn("have not completed", answer)
        view = [c["view"] for c in client.calls if c["purpose"] == "dialogue"][-1]
        self.assertEqual(view["current_state"]["enroll_desk"]["status"], "processed")
        self.assertIsNone(view["stage_hint"])
        fresh = Environment(load(16))
        self.assertIn("have not completed", ask(fresh, "career_dialogue", "course?"))
        # Time alone must not give a non-enrolled learner completed artifacts.
        fresh.advance("2027-02-10T16:00:00-06:00")
        self.assertIn("have not completed", ask(fresh, "career_dialogue", "course?"))
        api = fresh.tools()
        api.discover_tools("learning_records")
        self.assertNotIn("portfolio-packet", str(api.learning_records(query="portfolio-packet")))

    def test_role_state_cannot_invent_a_booking_or_see_unrelated_services(self):
        client = FixtureClient()
        env = llm_env(load(13), client)
        env.selections["unrelated_private_service"] = {"status": "processed", "entry": "secret"}
        ask(env, "family_dialogue", "Can you confirm our party booking?")
        view = [c["view"] for c in client.calls if c["purpose"] == "dialogue"][-1]
        self.assertEqual(view["current_state"], {"reserve_table": {"status": "no_selection", "entry": None}})


class TemporalRegressionTests(unittest.TestCase):
    def test_future_weekly_reservation_does_not_block_earlier_work(self):
        cal = Calendar({"timezone": "UTC", "weekdays": [1, 3], "hours": [["10:00", "17:00"]]})
        booked = []
        cal.reserve(parse("2026-11-06T10:00:00Z"),
                    {"mode": "weekly", "weekday": 3, "time": "14:00", "minutes": 120}, booked)
        start, end = cal.reserve(parse("2026-11-06T10:00:00Z"),
                                 {"mode": "business", "minutes": 83}, booked)
        self.assertEqual(start, parse("2026-11-10T10:00:00Z"))
        self.assertEqual(end, parse("2026-11-10T11:23:00Z"))
        self.assertTrue(all(b <= c for (_, b), (c, _) in zip(booked, booked[1:])))

    def test_business_work_splits_around_booking_and_elapsed_wait_reserves_nothing(self):
        cal = Calendar({"timezone": "UTC", "weekdays": list(range(7)), "hours": [["09:00", "17:00"]]})
        booked = [(parse("2026-11-06T10:00:00Z"), parse("2026-11-06T11:00:00Z"))]
        start, end = cal.reserve(parse("2026-11-06T09:00:00Z"), {"minutes": 120}, booked)
        self.assertEqual(end, parse("2026-11-06T12:00:00Z"))
        self.assertTrue(all(b <= c for (_, b), (c, _) in zip(booked, booked[1:])))
        before = list(booked)
        cal.reserve(start, {"mode": "elapsed", "minutes": 1440}, booked)
        self.assertEqual(booked, before)

    def test_early_companion_request_waits_for_publication_then_finishes(self):
        env = Environment(load(23))
        case = env.new_case("companion_lea", "main", {}, origin="agent")
        release = parse(env.task["facts"]["companion_ack"]["available_at"])
        env.advance(release - timedelta(seconds=1))
        self.assertNotIn("companion_ack", env.director.facts)
        env.advance("2027-04-16T23:59:00+02:00")
        self.assertEqual(case["state"], "replied")
        self.assertTrue(env.director.facts["companion_ack"]["agent_visible"])
        self.assertFalse(env.simulator_failure)

    def test_background_failure_preserves_event_and_invalidates_episode(self):
        env = Environment(load(23))
        first = env.events[0]
        with patch.object(env, "process_event", side_effect=ValueError("broken fixture")):
            with self.assertRaises(SimulatorError):
                env.advance(first[0])
        self.assertIn(first, env.events)
        self.assertEqual(env.simulator_failure["type"], "ValueError")
        with self.assertRaises(SimulatorError):
            env.advance(env.deadline)
        with self.assertRaises(SimulatorError):
            env.evaluate({"conclusion": "unconfirmed", "summary": ""})

    def test_repair_direct_requests_share_internal_work_and_deliver_to_all(self):
        task = load(6)
        env = Environment(task)
        cases = [env.new_case(actor, "main", task["public"]["user_fields"], origin="agent")
                 for actor in ("support", "engineer", "parts")]
        env.advance(env.deadline)
        self.assertTrue(any(c.get("linked_to") for c in env.cases.values()))
        for case in cases:
            self.assertEqual(case["state"], "replied")
            self.assertTrue(any(m.get("case_id") == case["id"] and m.get("receipts") for m in env.messages))
        lookups = [r for r in env.audit if r["kind"] == "tool_call" and r.get("tool") == "engineer.main.1.lookup"]
        self.assertEqual(len(lookups), 1)
        for actor in env.actors.values():
            self.assertTrue(all(b <= c for (_, b), (c, _) in zip(actor.reservations, actor.reservations[1:])))

    def test_dedup_does_not_merge_conflicting_requests(self):
        env = Environment(load(6))
        first = env.new_case("parts", "main", {"serial": "SN-A731", "note": "one"})
        second = env.new_case("parts", "main", {"serial": "SN-A731", "note": "two"})
        self.assertNotIn("linked_to", first)
        self.assertNotIn("linked_to", second)

    def test_instrument_date_follows_actual_review_and_personal_query_returns_receipt(self):
        task = load(4)
        env, answer, _ = run_reference(task)
        actual = env.director.facts["window"]["value"]
        review = next(r for r in env.audit if r["kind"] == "tool_call" and r.get("tool") == "instrument.main.4.lookup")
        self.assertEqual(actual, review["at"])
        self.assertEqual(answer["conclusion"], "available_now")
        env.tools().discover_tools("nanyu_training_status")
        result = env.tools().nanyu_training_status(query="training")
        self.assertIn("SAFE-NOV06-482", str(result))
        self.assertTrue(result["records"][0]["receipts"])
        delayed = deepcopy(task)
        delayed["deadline_at"] = "2026-12-15T17:00:00+08:00"
        index = next(i for i, a in enumerate(delayed["reference_actions"]) if a.get("label") == "measure")
        delayed["reference_actions"].insert(index, {"op": "advance", "at": "2026-11-20T09:00:00+08:00"})
        late_env, late_answer, _ = run_reference(delayed)
        self.assertGreater(parse(late_env.director.facts["window"]["value"]), parse(actual))
        self.assertEqual(late_answer["conclusion"], "available_now")

    def test_hotel_finishes_before_arrival_and_rejects_late_booking(self):
        task = load(23)
        env, _, result = run_reference(task)
        self.assertEqual(env.selections["stay_book"]["status"], "processed")
        self.assertLess(env.now, parse("2027-04-17T00:05:00+02:00"))
        self.assertTrue(result["complete"])
        late = Environment(task)
        late.advance("2027-04-17T00:06:00+02:00")
        late.tools().discover_tools("stay_book")
        with self.assertRaisesRegex(ValueError, "service deadline"):
            late.tools().stay_book(entry="villa-extended")
        self.assertNotIn("stay_book", late.selections)

    def test_author_validation_rejects_publication_after_booking_deadline(self):
        task = load(23)
        task["facts"]["late_extension"]["available_at"] = "2027-04-17T08:30:00+02:00"
        self.assertTrue(any("published after service deadline" in e for e in validate_task(task)))

    def test_hotel_random_and_maximum_latencies_fit_before_arrival(self):
        task = load(23)
        for seed in list(range(50)) + ["maximum"]:
            with self.subTest(seed=seed):
                env = Environment(task, seed=0 if seed == "maximum" else seed)
                if seed == "maximum":
                    env.rng.randint = lambda low, high: high
                with patch("dayspanbench.reference.Environment", return_value=env):
                    _, _, result = run_reference(task)
                self.assertTrue(result["complete"])
                booking = next(r for r in env.audit if r["kind"] == "selection_processed"
                               and r.get("tool") == "stay_book")
                self.assertLess(parse(booking["at"]), parse("2027-04-17T00:05:00+02:00"))

    def test_all_42_reference_paths_and_deterministic_checks(self):
        for n in range(1, 43):
            with self.subTest(case=n):
                task = load(n)
                self.assertEqual(validate_task(task), [])
                env, _, result = run_reference(task)
                self.assertFalse(env.simulator_failure)
                self.assertTrue(result["complete"])
                self.assertTrue(result["conclusion_correct"])
                self.assertTrue(all(v is not False for v in result["deterministic_checks"].values()))


if __name__ == "__main__":
    unittest.main()
