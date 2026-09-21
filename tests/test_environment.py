from copy import deepcopy
import json
from pathlib import Path
import unittest
import subprocess
import sys

from dayspanbench.calendar import Calendar, parse
from dayspanbench.engine import Environment
from dayspanbench.recipient import LLMRecipient
from dayspanbench.reference import run_reference
from dayspanbench.validation import validate_task

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / "tasks/private" / f"DSB-{n:02d}.json").read_text())


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.cal = Calendar(load(1)["calendars"]["office"])

    def test_weekend_and_lunch_pause(self):
        self.assertEqual(self.cal.add_business(parse("2026-11-06T16:30:00+08:00"), 180), parse("2026-11-09T11:30:00+08:00"))
        self.assertEqual(self.cal.add_business(parse("2026-11-09T11:30:00+08:00"), 60), parse("2026-11-09T13:30:00+08:00"))

    def test_exact_closing_boundary(self):
        self.assertEqual(self.cal.add_business(parse("2026-11-06T16:00:00+08:00"), 60), parse("2026-11-06T17:00:00+08:00"))
        self.assertEqual(self.cal.next_open(parse("2026-11-06T17:00:00+08:00")), parse("2026-11-09T09:00:00+08:00"))

    def test_weekly_cutoff(self):
        self.assertEqual(self.cal.next_slot(parse("2026-11-10T10:00:01+08:00"), 1, "10:00"), parse("2026-11-17T10:00:00+08:00"))

    def test_holiday_and_override(self):
        spec = deepcopy(self.cal.spec)
        spec["closed_dates"] = ["2026-11-09"]
        spec["overrides"] = {"2026-11-10": [["14:00", "16:00"]]}
        self.assertEqual(Calendar(spec).next_open(parse("2026-11-06T18:00:00+08:00")), parse("2026-11-10T14:00:00+08:00"))

    def test_elapsed_time_does_not_pause_at_weekend(self):
        start = parse("2026-11-06T22:00:00+08:00")
        _, due, free = self.cal.schedule(start, {"mode": "elapsed", "minutes": 2880}, start)
        self.assertEqual(due, parse("2026-11-08T22:00:00+08:00"))
        self.assertEqual(free, start)

    def test_cross_timezone_and_dst(self):
        ny = Calendar(load(7)["calendars"]["new_york"])
        self.assertEqual(ny.next_open(parse("2026-11-06T10:00:00+08:00")), parse("2026-11-06T22:00:00+08:00"))
        self.assertEqual(ny.add_business(parse("2026-10-30T16:00:00-04:00"), 120), parse("2026-11-02T10:00:00-05:00"))


class EnvironmentTests(unittest.TestCase):
    def test_all_tasks_and_actor_configs(self):
        actors = 0
        for n in range(1, 13):
            task = load(n)
            with self.subTest(task=task["id"]):
                self.assertEqual(validate_task(task), [])
                env, _, result = run_reference(task)
                self.assertTrue(result["complete"], result)
                self.assertGreaterEqual(result["calendar_hours"], 48)
                self.assertLessEqual(result["calendar_hours"], 7200)
                self.assertEqual(result["calendar_days"], task["horizon_design"]["reference_days"])
                self.assertEqual({c["actor"] for c in env.cases.values()}, {a["id"] for a in task["actors"]})
                actors += len(task["actors"])
        self.assertEqual(actors, 41)

    def test_golden_calendar_completion_times(self):
        expected = {1: "2026-11-09T10:00:00+08:00", 2: "2026-11-11T19:30:00+08:00",
                    3: "2027-02-02T14:00:00+08:00", 4: "2026-11-25T09:30:00+08:00",
                    5: "2026-12-07T14:00:00+08:00", 6: "2026-11-17T16:00:00+08:00",
                    7: "2027-06-03T15:00:00+08:00", 8: "2026-11-11T13:30:00+08:00",
                    9: "2026-12-28T15:00:00+08:00", 10: "2026-11-08T10:00:00+08:00",
                    11: "2027-03-31T20:30:00+08:00", 12: "2027-09-02T15:00:00+08:00"}
        for n, time in expected.items():
            with self.subTest(task=n):
                env, _, _ = run_reference(load(n))
                self.assertEqual(env.now, parse(time))

    def test_missing_material_and_forged_material_are_not_accepted(self):
        env = Environment(load(3))
        api = env.tools()
        result = api.send_message("records", "咨询学分转换", {"course_code": "CS204"})
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        api.send_message("records", "补充大纲", {"syllabus_version": "CS204-2026-v2-signed"}, case_id=result["case_id"])
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        self.assertEqual(env.events, [])

    def test_wrong_case_identifiers_are_rejected(self):
        env = Environment(load(6))
        result = env.tools().send_message("support", "保修咨询", {"serial": "OTHER", "receipt": "R-731"})
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")

    def test_internal_contacts_and_fact_tools_are_not_agent_tools(self):
        api = Environment(load(1)).tools()
        with self.assertRaises(PermissionError):
            api.send_message("technician", "维修", {"event_date": "2026-11-13"})
        self.assertFalse(hasattr(api, "execute_tool"))
        visible = json.dumps(api.observe(), ensure_ascii=False)
        self.assertNotIn('"expected_conclusion"', visible)
        self.assertNotIn('"facts"', visible)
        self.assertNotIn("全天维修", visible)

    def test_followup_does_not_change_completion(self):
        env = Environment(load(2))
        api = env.tools()
        case = api.send_message("landlord", "咨询宠物入住", load(2)["public"]["user_fields"])
        api.send_message("landlord", "跟进一下", case_id=case["case_id"])
        env.advance(env.deadline)
        replies = [m for m in env.messages if m["status"] == "reply"]
        reference, _, _ = run_reference(load(2))
        self.assertEqual(replies[-1]["at"], reference.messages[-1]["at"])

    def test_resource_queue_prevents_parallel_work_by_one_person(self):
        env = Environment(load(1))
        api = env.tools()
        api.send_message("reception", "联系活动场地")
        api.send_message("reception", "联系活动场地")
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        self.assertEqual(scheduled[0]["due_at"], scheduled[1]["start_at"])

    def test_simultaneous_events_and_independent_people(self):
        env = Environment(load(8))
        api = env.tools()
        api.read_page("hotels")
        fields = load(8)["public"]["user_fields"]
        a = api.send_message("a_desk", "无障碍尺寸", fields)
        b = api.send_message("b_desk", "无障碍尺寸", fields)
        self.assertNotEqual(a["case_id"], b["case_id"])
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        self.assertEqual(scheduled[0]["start_at"], scheduled[1]["start_at"])

    def test_wait_wakes_for_agent_delivery_not_private_transition(self):
        env = Environment(load(2))
        api = env.tools()
        api.send_message("landlord", "咨询宠物入住", load(2)["public"]["user_fields"])
        reply = api.wait_until(load(2)["deadline_at"])
        self.assertTrue(reply["messages"])
        self.assertEqual(env.now, parse("2026-11-11T19:30:00+08:00"))

    def test_expired_or_unreceived_evidence_does_not_score(self):
        env, answer, _ = run_reference(load(5))
        old = next(e for e in env.evidence.values() if e["fact_id"] == "quote_old")
        bad = deepcopy(answer)
        bad["claims"][0]["evidence_ids"] = [old["id"]]
        self.assertFalse(env.evaluate(bad)["complete"])
        bad["claims"][0]["evidence_ids"] = ["EV-NOT-ISSUED"]
        self.assertFalse(env.evaluate(bad)["complete"])

    def test_unknown_claim_cannot_replace_available_answer(self):
        env, answer, _ = run_reference(load(1))
        answer["claims"][0] = {"key": "total_cost", "status": "unconfirmed"}
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_unresolved_requires_real_query_and_deadline_wait(self):
        env, answer, result = run_reference(load(12))
        self.assertTrue(result["complete"])
        self.assertEqual(result["completion_class"], "bounded_unresolved")
        self.assertFalse(any(ev["fact_id"] == "release" and ev["agent_visible"] for ev in env.evidence.values()))
        env.now = parse(load(12)["start_at"])
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_log_scale_horizon_distribution(self):
        days = sorted(load(n)["horizon_design"]["reference_days"] for n in range(1, 13))
        self.assertEqual(days, [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 210, 300])
        bins = [(2, 7), (8, 30), (31, 100), (101, 300)]
        self.assertEqual([sum(lo <= day <= hi for day in days) for lo, hi in bins], [3, 3, 3, 3])

    def test_expired_material_cannot_open_new_processing_case(self):
        env = Environment(load(12))
        api = env.tools()
        front = api.send_message("forwarder", "查询货件状态", load(12)["public"]["user_fields"])
        while env.cases[front["case_id"]]["state"] != "replied":
            api.wait_until(load(12)["deadline_at"])
        doc = api.send_message("exporter", "取得首轮更正申报资料", {"tracking": "PK-608"})
        while env.cases[doc["case_id"]]["state"] != "replied":
            api.wait_until(load(12)["deadline_at"])
        self.assertTrue(any(e["agent_visible"] and e["fact_id"] == "declaration" for e in env.evidence.values()))
        api.wait_until("2027-04-01T09:00:00+08:00", wake_on_message=False)
        case = api.send_message("customsdesk", "申请初审登记", {"tracking": "PK-608", "declaration_version": "DEC-608-v2"})
        self.assertEqual(env.cases[case["case_id"]]["state"], "needs_information")
        self.assertFalse(any(c["actor"] == "broker" for c in env.cases.values()))

    def test_long_horizon_contains_active_multimonth_handoffs(self):
        env, _, result = run_reference(load(12))
        sends = [e for e in env.audit if e["kind"] == "agent_send"]
        self.assertGreaterEqual(len({parse(e["at"]).strftime("%Y-%m") for e in sends}), 4)
        self.assertTrue(any(c["actor"] == "customsdesk" and c["workflow"]["id"] == "main" and c["state"] == "replied" for c in env.cases.values()))
        self.assertTrue(any(c["actor"] == "customsdesk" and c["workflow"]["id"] == "final" and c["state"] == "waiting_internal" for c in env.cases.values()))
        self.assertEqual(result["calendar_days"], 300)
        self.assertFalse(result["resolved_success"])
        self.assertTrue(result["bounded_handling_success"])

    def test_wrong_pending_stage_does_not_count_as_completed_followthrough(self):
        env, answer, _ = run_reference(load(12))
        final_case = next(c for c in env.cases.values() if c["actor"] == "customsdesk" and c["workflow"]["id"] == "final")
        child = next(c for c in env.cases.values() if c["parent"] == final_case["id"])
        child["workflow"]["capabilities"] = ["preliminary_registration"]
        self.assertFalse(env.evaluate(answer)["bounded_handling_success"])

    def test_archive_cannot_skip_permission_before_digitization(self):
        env = Environment(load(7))
        reply = env.tools().send_message("archive", "申请数字化交付", {"archive_id": "ARC-71", "exhibition_permission": True})
        self.assertEqual(env.cases[reply["case_id"]]["state"], "needs_information")
        self.assertFalse(env.events)

    def test_intermediate_patch_does_not_finish_quarterly_release_task(self):
        env = Environment(load(11))
        api = env.tools()
        case = api.send_message("maintainer", "确认兼容问题与补丁", load(11)["public"]["user_fields"], channel="ticket")
        while env.cases[case["case_id"]]["state"] != "replied":
            api.wait_until(load(11)["deadline_at"])
        self.assertTrue(any(ev["agent_visible"] and ev["fact_id"] == "workaround" for ev in env.evidence.values()))
        self.assertFalse(any(ev["agent_visible"] and ev["fact_id"] == "candidate" for ev in env.evidence.values()))
        self.assertFalse(env.evaluate({"conclusion": "workaround_available_stable_uncommitted", "claims": []})["information_sufficient"])

    def test_llm_router_is_scoped_and_validated(self):
        views = []
        def callback(view):
            views.append(view)
            return {"workflow_id": "main"}
        env = Environment(load(1), LLMRecipient(callback))
        env.tools().send_message("reception", "请帮我找到合适的人")
        self.assertNotIn("facts", views[0])
        self.assertNotIn("actors", views[0])
        bad = Environment(load(1), LLMRecipient(lambda _: {"workflow_id": "secret"}))
        with self.assertRaises(ValueError):
            bad.tools().send_message("reception", "查询")

    def test_each_actor_has_an_independent_default_recipient(self):
        env = Environment(load(1))
        self.assertEqual(len({id(a.recipient) for a in env.actors.values()}), 4)
        self.assertEqual(len({id(a.inbox) for a in env.actors.values()}), 4)
        self.assertEqual(len({id(a.calendar) for a in env.actors.values()}), 4)

    def test_information_sufficiency_separate_from_bad_answer(self):
        env, answer, _ = run_reference(load(1))
        answer["conclusion"] = "suitable"
        result = env.evaluate(answer)
        self.assertTrue(result["information_sufficient"])
        self.assertFalse(result["resolved_success"])
        _, _, bounded = run_reference(load(12))
        self.assertFalse(bounded["information_sufficient"])
        self.assertFalse(bounded["resolved_success"])
        self.assertTrue(bounded["bounded_handling_success"])

    def test_jsonl_server_rpc_boundary(self):
        requests = [
            {"id": 1, "tool": "observe", "arguments": {}},
            {"id": 2, "tool": "send_message", "arguments": {"recipient": "reception", "text": "活动联系入口"}},
            {"id": 3, "tool": "wait_until", "arguments": {"until": "2026-11-10T18:00:00+08:00"}},
            {"id": 4, "tool": "execute_tool", "arguments": {}},
        ]
        completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-01"],
                    input="\n".join(json.dumps(r) for r in requests) + "\n", capture_output=True, text=True, cwd=ROOT, check=True)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 4)
        self.assertIn("conclusion_options", responses[0]["result"]["task"])
        self.assertEqual(responses[1]["result"]["status"], "received")
        self.assertEqual(responses[2]["result"]["messages"][0]["status"], "reply")
        self.assertEqual(responses[3]["error"]["type"], "PermissionError")
        self.assertNotIn('"private_audit"', completed.stdout)

    def test_duplicate_claims_and_multiple_submissions_rejected(self):
        env, answer, _ = run_reference(load(1))
        answer["claims"].append(deepcopy(answer["claims"][0]))
        self.assertFalse(env.evaluate(answer)["complete"])
        with self.assertRaises(ValueError):
            env.tools().submit_answer(answer)

    def test_clock_backwards_and_after_deadline_send_rejected(self):
        env = Environment(load(1))
        api = env.tools()
        with self.assertRaises(ValueError):
            api.wait_until("2026-11-01T00:00:00+08:00")
        api.wait_until(load(1)["deadline_at"], wake_on_message=False)
        with self.assertRaises(ValueError):
            api.send_message("reception", "活动")


if __name__ == "__main__":
    unittest.main()
