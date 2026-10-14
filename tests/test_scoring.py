from copy import deepcopy
import json
from pathlib import Path
import unittest

from dayspanbench.llm import key_tokens
from dayspanbench.reference import run_reference
from dayspanbench.scoring import equivalent, score_with_judge, token_present
from dayspanbench.validation import validate_task

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / f"tasks/private/DSB-{n:02}.json").read_text(encoding="utf-8"))


def other_label(task):
    options = task["public"]["conclusion_options"]
    return next(label for label in options if label != task["expected_conclusion"])


def judged_task():
    """DSB-01 with two injected judge criteria (mock judge results drive the
    subpart score; no LLM is involved here)."""
    task = load(1)
    task["judge_criteria"] = [
        {"id": "R1", "statement": "The summary states the total cost.", "pass_if": "Correct figure.", "source": "final_answer"},
        {"id": "R2", "statement": "The summary is honest about unconfirmed items.", "pass_if": "No invention.", "source": "final_answer"},
    ]
    return task


def review(passed_values):
    return {"status": "graded", "criteria": [
        {"id": "R1", "passed": passed_values[0], "evidence": [], "reason": "r1"},
        {"id": "R2", "passed": passed_values[1], "evidence": [], "reason": "r2"}]}


class TokenAnchorTests(unittest.TestCase):
    def test_literal_and_lightly_normalized_presence(self):
        self.assertTrue(token_present("总价18600元", "18600"))
        self.assertTrue(token_present("总价 18,600 元", "18600"))
        self.assertTrue(token_present("total USD 247.80", "247.80"))
        self.assertFalse(token_present("总价1500元", "18600"))
        self.assertFalse(token_present("JOB4410", "JOB441"))
        self.assertFalse(token_present(None, "18600"))
        self.assertFalse(token_present("1501 U Street", "15"))
        # Re-tokenization symmetry: "15" inside a time range was itself
        # extracted from one, so it counts as present.
        self.assertTrue(token_present("June 12 09:00-15:00 shutdown", "15", frozenset(key_tokens("June 12 09:00-15:00 shutdown"))))

    def test_numeric_equivalence_for_trailing_zeros_and_units(self):
        # 236.0 / 236.00 / 236 are the same number; formatting must not fail
        # the anchor (scoring 0.5.1).
        self.assertTrue(token_present("总费用236.00 USD", "236.0"))
        self.assertTrue(token_present("total 236 USD", "236.0"))
        self.assertTrue(token_present("236.0", "236.00"))
        self.assertTrue(token_present("1,236.00 元", "1236.0"))
        self.assertFalse(token_present("total 230.00 USD", "236.0"))
        self.assertFalse(token_present("约二百三十六美元", "236.0"))


class DeterministicEvaluateTests(unittest.TestCase):
    def test_reference_on_criterionless_task_scores_deterministic_only(self):
        # Since the v0.5 full migration every authored task carries
        # judge_criteria; strip them to pin the no-criteria degradation path.
        task = load(5)
        task["judge_criteria"] = []
        env, answer, result = run_reference(task)
        self.assertTrue(result["deterministic_anchors_ok"], result["deterministic_checks"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["scored_by"], "deterministic_only")
        self.assertEqual(result["subparts_total"], 0)

    def test_reference_on_judged_task_awaits_judge_but_passes_anchors(self):
        # DSB-01 carries authored judge_criteria since v0.5 M4: the reference
        # still passes every deterministic anchor, but the deterministic score
        # alone stays "awaiting_judge" until score_with_judge composes it.
        task = load(1)
        self.assertTrue(task["judge_criteria"])
        env, answer, result = run_reference(task)
        self.assertTrue(result["deterministic_anchors_ok"], result["deterministic_checks"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["scored_by"], "awaiting_judge")
        self.assertEqual(result["subparts_total"], len(task["judge_criteria"]))

    def test_dsb12_bounded_semantics_come_from_the_same_anchors(self):
        env, answer, result = run_reference(load(12))
        self.assertEqual(result["completion_class"], "bounded_unresolved")
        self.assertTrue(result["bounded_handling_success"])
        self.assertFalse(result["resolved_success"])
        self.assertFalse(result["information_sufficient"])
        self.assertTrue(result["deterministic_checks"]["pending_process_satisfied"])

    def test_wrong_conclusion_label_fails(self):
        task = load(1)
        env, answer, _ = run_reference(task)
        answer["conclusion"] = other_label(task)
        result = env.evaluate(answer)
        self.assertFalse(result["deterministic_anchors_ok"])
        self.assertFalse(result["conclusion_correct"])
        self.assertTrue(result["deterministic_checks"]["conclusion_label_legal"])

    def test_summary_missing_an_anchor_element_fails(self):
        env, answer, _ = run_reference(load(1))
        # Drop anchor elements one by one until one is genuinely missed.
        token, result = None, None
        for candidate in sorted(key_tokens(answer["summary"])):
            stripped = answer["summary"].replace(candidate, "X")
            attempt = env.evaluate({**answer, "summary": stripped})
            if candidate in attempt["deterministic_checks"]["summary_anchor_missing"]:
                token, result = candidate, attempt
                break
        self.assertIsNotNone(token, "no anchor token could be dropped")
        self.assertFalse(result["deterministic_anchors_ok"])
        self.assertFalse(result["complete"])

    def test_malformed_answers_are_failures_not_crashes(self):
        env, _, _ = run_reference(load(1))
        for answer in (None, [], {}, {"conclusion": "suitable"}, {"conclusion": 1, "summary": []},
                       {"conclusion": "suitable", "summary": "ok", "claims": []}):
            with self.subTest(answer=answer):
                result = env.evaluate(answer)
                self.assertFalse(result["complete"])
                self.assertFalse(result["answer_schema_valid"])

    def test_anchors_exclude_expired_facts(self):
        env, answer, _ = run_reference(load(5))
        # The superseded quote is agent-visible but no longer valid at scoring
        # time; its figure must not be demanded from the summary.
        old = next(f for f in env.director.facts.values() if f["fact_id"] == "quote_old")
        result = env.evaluate(answer)
        for token in key_tokens(str(old["value"])):
            self.assertNotIn(token, result["deterministic_checks"]["summary_anchor_missing"])

    def test_pending_deadline_must_be_reached_before_filing(self):
        env, answer, result = run_reference(load(12))
        self.assertTrue(result["complete"])
        env.now = env.task["start_at"] and __import__("dayspanbench.calendar", fromlist=["parse"]).parse(env.task["start_at"])
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_typed_normalizers_still_exported(self):
        self.assertTrue(equivalent("2,360", 2360, {"type": "number"}))
        self.assertTrue(equivalent({"value": 23.6, "unit": "m"}, 2360, {"type": "number", "units": {"m": 100}}))
        self.assertTrue(equivalent("2026-11-18T02:00:00Z", "2026-11-18T10:00:00+08:00", {"type": "datetime"}))
        self.assertFalse(equivalent(True, 1, {"type": "number"}))
        self.assertFalse(equivalent("1,2", 12, {"type": "number"}))


class ScoreWithJudgeTests(unittest.TestCase):
    def setUp(self):
        self.task = judged_task()
        self.env, self.answer, self.base = run_reference(self.task)

    def test_all_subparts_pass_composes_complete(self):
        result = score_with_judge(self.env, review([True, True]))
        self.assertEqual(result["scored_by"], "judge")
        self.assertEqual(result["subparts_passed"], 2)
        self.assertEqual(result["subparts_total"], 2)
        self.assertEqual(result["pending_criteria"], 0)
        self.assertTrue(result["complete"])
        self.assertTrue(result["resolved_success"])
        self.assertEqual(result["required_fact_coverage"], 1.0)

    def test_one_failed_subpart_blocks_success(self):
        result = score_with_judge(self.env, review([True, False]))
        self.assertEqual(result["subparts_passed"], 1)
        self.assertFalse(result["complete"])
        self.assertFalse(result["resolved_success"])
        self.assertEqual(result["required_fact_coverage"], 0.5)

    def test_failed_anchor_blocks_judged_pass(self):
        self.answer["conclusion"] = other_label(self.task)
        self.env.evaluate(self.answer)  # records the mutated final answer
        result = score_with_judge(self.env, review([True, True]))
        self.assertEqual(result["scored_by"], "judge")
        self.assertFalse(result["complete"])

    def test_pending_review_never_scores_as_failure_or_pass(self):
        pending = {"status": "pending", "criteria": [
            {"id": "R1", "passed": None, "reason": "judge call failed; pending"},
            {"id": "R2", "passed": None, "reason": "judge call failed; pending"}]}
        result = score_with_judge(self.env, pending)
        self.assertEqual(result["scored_by"], "judge_pending")
        self.assertEqual(result["pending_criteria"], 2)
        self.assertFalse(result["complete"])
        self.assertFalse(result["resolved_success"])
        self.assertFalse(result["bounded_handling_success"])

    def test_skipped_review_falls_back_to_deterministic_only(self):
        for skipped in (None, {"status": "skipped", "criteria": []}):
            with self.subTest(review=skipped):
                result = score_with_judge(self.env, skipped)
                self.assertEqual(result["scored_by"], "deterministic_only")
                self.assertEqual(result["pending_criteria"], 0)

    def test_task_without_criteria_uses_deterministic_view(self):
        task = load(1)
        env, answer, result = run_reference(task)
        composed = score_with_judge(env, {"status": "skipped", "criteria": []})
        self.assertEqual(composed["scored_by"], "deterministic_only")
        self.assertEqual(composed["complete"], result["complete"])

    def test_bounded_class_with_judge(self):
        task = load(12)
        task["judge_criteria"] = deepcopy(self.task["judge_criteria"])
        env, answer, _ = run_reference(task)
        result = score_with_judge(env, review([True, True]))
        self.assertFalse(result["resolved_success"])
        self.assertTrue(result["bounded_handling_success"])

    def test_anchor_review_confirmation_lifts_missing_anchor(self):
        # Simulate a format-level anchor miss (judge subparts all pass), then
        # a graded anchor-review confirmation lifts summary_anchors_ok.
        answer = deepcopy(self.answer)
        base = self.env.evaluate(answer)
        self.assertTrue(base["deterministic_anchors_ok"])  # reference passes first
        checks = base["deterministic_checks"]
        # Force a miss the way a "236.00 vs 236.0" episode would look.
        checks["summary_anchor_missing"] = ["9999"]
        checks["summary_anchors_ok"] = False
        base["deterministic_anchors_ok"] = False
        result = score_with_judge(self.env, review([True, True]), base=base,
                                  anchor_review={"status": "graded", "confirmed": True, "tokens": []})
        self.assertEqual(result["deterministic_checks"]["anchor_review_verdict"],
                         "judge_confirmed_equivalent")
        self.assertEqual(result["deterministic_checks"]["summary_anchor_missing"], [])
        self.assertTrue(result["deterministic_anchors_ok"])
        self.assertTrue(result["complete"])

    def test_anchor_review_denial_keeps_deterministic_failure(self):
        base = self.env.evaluate(deepcopy(self.answer))
        checks = base["deterministic_checks"]
        checks["summary_anchor_missing"] = ["9999"]
        checks["summary_anchors_ok"] = False
        base["deterministic_anchors_ok"] = False
        result = score_with_judge(self.env, review([True, True]), base=base,
                                  anchor_review={"status": "graded", "confirmed": False, "tokens": []})
        self.assertEqual(result["deterministic_checks"]["anchor_review_verdict"], "judge_denied")
        self.assertFalse(result["deterministic_anchors_ok"])
        self.assertFalse(result["complete"])

    def test_pending_anchor_review_keeps_deterministic_verdict(self):
        base = self.env.evaluate(deepcopy(self.answer))
        checks = base["deterministic_checks"]
        checks["summary_anchor_missing"] = ["9999"]
        checks["summary_anchors_ok"] = False
        base["deterministic_anchors_ok"] = False
        result = score_with_judge(self.env, review([True, True]), base=base,
                                  anchor_review={"status": "pending", "confirmed": False, "tokens": []})
        self.assertFalse(result["deterministic_anchors_ok"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["anchor_review"]["status"], "pending")


class ValidationSmokeTests(unittest.TestCase):
    def test_injected_criteria_do_not_break_task_validation_shape(self):
        # Scoring never mutates the task; validation stays a task-level guard.
        task = judged_task()
        self.assertEqual(validate_task(task), [])


if __name__ == "__main__":
    unittest.main()
