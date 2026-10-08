from copy import deepcopy
from datetime import timedelta
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
    return json.loads((ROOT / "tasks/private" / f"DSB-{n:02d}.json").read_text(encoding="utf-8"))


def mailbox(task, actor_id):
    """The agent addresses people by their published mailbox."""
    return next(a["contact_details"]["email"] for a in task["actors"] if a["id"] == actor_id)


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
                # Randomized handling latency shifts the witness past the designed
                # horizon; it must still finish inside the deadline window.
                window = (parse(task["deadline_at"]) - parse(task["start_at"])).total_seconds() / 3600
                self.assertLessEqual(result["calendar_hours"], window)
                self.assertEqual({c["actor"] for c in env.cases.values()}, {a["id"] for a in task["actors"]})
                actors += len(task["actors"])
        self.assertEqual(actors, 42)

    def test_golden_calendar_completion_times(self):
        # Deterministic under the default latency seed; guards against unintended
        # drift in admission/jitter behavior.
        expected = {1: "2026-11-09T07:14:00+00:00", 2: "2026-11-11T11:44:00+00:00",
                    3: "2027-02-02T07:04:00+00:00", 4: "2026-11-25T02:50:00+00:00",
                    5: "2026-12-07T08:25:00+00:00", 6: "2026-11-17T08:52:00+00:00",
                    7: "2027-06-07T02:00:00+00:00", 8: "2026-11-11T06:48:00+00:00",
                    9: "2026-12-28T07:49:00+00:00", 10: "2026-11-09T02:56:00+00:00",
                    11: "2027-02-24T12:46:00+00:00", 12: "2027-09-02T07:00:00+00:00"}
        for n, time in expected.items():
            with self.subTest(task=n):
                env, _, _ = run_reference(load(n))
                self.assertEqual(env.now, parse(time))

    def test_in_flight_followup_with_unchanged_fields_only_acknowledges(self):
        # A progress ping on a case that is already delegated internally must
        # not spawn a duplicate internal case that competes for the recipient
        # office's weekly slot and pushes the original past the deadline.
        task = load(3)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://chengchuan.bench/contact")
        # Legitimate material: the syllabus version must come from the
        # lecturer's attested reply, not out of thin air.
        api.send_email(mailbox(task, "lecturer"), "请补发正式签章大纲", {"course_code": "CS204"})
        api.wait_until("2026-11-10T15:00:00+08:00")  # lecturer has replied after the trip
        syllabus = next(m for m in env.messages if m["status"] == "reply")["evidence"][0]["value"]
        first = api.send_email(mailbox(task, "records"), "咨询CS204学分转换",
                               {"course_code": "CS204", "syllabus_version": syllabus})
        # A mid-workflow acceptance receipt reaches the inbox before the
        # internal handoff, without closing the case. Drain the event queue
        # until the handoff happens rather than guessing jittered timestamps.
        while env.cases[first["case_id"]]["state"] != "waiting_internal" and env.events:
            env.advance(env.events[0][0])
        case = env.cases[first["case_id"]]
        self.assertEqual(case["state"], "waiting_internal")
        self.assertTrue(any(m["case_id"] == first["case_id"] and m["status"] == "acknowledgement"
                            for m in env.messages))
        before = len(env.cases)
        ack = api.send_email(mailbox(task, "records"), "请问办理进度如何",
                             {"course_code": "CS204", "syllabus_version": syllabus},
                             case_id=first["case_id"])
        self.assertEqual(ack["case_id"], first["case_id"])
        self.assertEqual(len(env.cases), before)
        self.assertFalse(any(e["kind"] == "followup_reopened" for e in env.audit))
        # The delegate's weekly slot reservation is untouched: the board case
        # still starts at the spring session, not a week later.
        board = next(c for c in env.cases.values() if c["actor"] == "board")
        self.assertEqual(board["state"], "queued")
        # A follow-up that actually changes the material does re-open.
        reopened = api.send_email(mailbox(task, "records"), "大纲版本有更新，请按新版本办理",
                                  {"course_code": "CS204", "syllabus_version": "CS204-2026-v3"},
                                  case_id=first["case_id"])
        self.assertNotEqual(reopened["case_id"], first["case_id"])
        # A progress ping with no fields at all also only acknowledges: it
        # must not be treated as a new request and re-routed into a duplicate
        # parallel case.
        before = len(env.cases)
        ping = api.send_email(mailbox(task, "records"), "请问办理进度如何", {}, case_id=first["case_id"])
        self.assertEqual(ping["case_id"], first["case_id"])
        self.assertEqual(len(env.cases), before)

    def test_missing_material_and_forged_material_are_not_accepted(self):
        task = load(3)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://chengchuan.bench/contact")
        result = api.send_email(mailbox(task, "records"), "咨询学分转换", {"course_code": "CS204"})
        # Admission is deferred to the recipient's work hours after the task's
        # reply delay; drain the event queue rather than guessing a timestamp.
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        api.send_email(mailbox(task, "records"), "补充大纲", {"syllabus_version": "CS204-2026-v2-signed"}, case_id=result["case_id"])
        while env.events:
            env.advance(env.events[0][0])
        # A claimed-but-unverified syllabus still fails the evidence gate.
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        self.assertEqual(env.events, [])

    def test_wrong_case_identifiers_are_rejected(self):
        task = load(6)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://jiguang.bench/contact")
        result = api.send_email(mailbox(task, "support"), "保修咨询", {"serial": "OTHER", "receipt": "R-731"})
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")

    def test_internal_contacts_and_fact_tools_are_not_agent_tools(self):
        task = load(1)
        api = Environment(task).tools()
        with self.assertRaises(PermissionError):
            api.send_email(mailbox(task, "technician"), "维修", {"event_date": "2026-11-13"})
        self.assertFalse(hasattr(api, "execute_tool"))
        visible = json.dumps(api.recall_task(), ensure_ascii=False)
        self.assertNotIn('"expected_conclusion"', visible)
        self.assertNotIn('"facts"', visible)
        self.assertNotIn("全天维修", visible)

    def test_unit_variant_field_still_admits(self):
        # A quantity quoted with a synonym unit ("8公斤") describes the same case
        # as the canonical user_fields spelling ("8kg") and must not bounce to
        # needs_information; a genuinely different quantity still must.
        task = load(2)
        env = Environment(task)
        api = env.tools()
        variant = {**task["public"]["user_fields"], "pet_weight": "8公斤"}
        result = api.send_email(mailbox(task, "landlord"), "咨询宠物入住", variant)
        while env.events:
            env.advance(env.events[0][0])
        case = env.cases[result["case_id"]]
        self.assertEqual(case["fields"]["pet_weight"], "8kg")
        self.assertNotEqual(case["state"], "needs_information")

    def test_followup_does_not_change_completion(self):
        task = load(2)
        env = Environment(task)
        api = env.tools()
        case = api.send_email(mailbox(task, "landlord"), "咨询宠物入住", task["public"]["user_fields"])
        api.send_email(mailbox(task, "landlord"), "跟进一下", case_id=case["case_id"])
        env.advance(env.deadline)
        replies = [m for m in env.messages if m["status"] == "reply"]
        reference, _, _ = run_reference(load(2))
        self.assertEqual(replies[-1]["at"], reference.messages[-1]["at"])

    def test_resource_queue_prevents_parallel_work_by_one_person(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), "联系活动场地")
        api.send_email(mailbox(task, "reception"), "联系活动场地")
        api.wait_until("2026-11-06T17:00:00+08:00", wake_on_message=False)
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        # The second case can never start before the single worker finishes the first.
        self.assertGreaterEqual(parse(scheduled[1]["start_at"]), parse(scheduled[0]["due_at"]))

    def test_simultaneous_events_and_independent_people(self):
        task = load(8)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://wuzhangzhusu.bench/contact")
        fields = task["public"]["user_fields"]
        a = api.send_email(mailbox(task, "a_desk"), "无障碍尺寸", fields)
        b = api.send_email(mailbox(task, "b_desk"), "无障碍尺寸", fields)
        self.assertNotEqual(a["case_id"], b["case_id"])
        api.wait_until("2026-11-06T17:00:00+08:00", wake_on_message=False)
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        # Independent people are admitted and scheduled without waiting for each other.
        self.assertEqual({s["actor"] for s in scheduled[:2]}, {"a_desk", "b_desk"})
        started = [parse(s["start_at"]) for s in scheduled[:2]]
        self.assertTrue(all(parse(load(8)["start_at"]) <= s <= parse(load(8)["start_at"]) + timedelta(days=1) for s in started))

    def test_wait_wakes_for_agent_delivery_not_private_transition(self):
        task = load(2)
        env = Environment(task)
        api = env.tools()
        api.send_email(mailbox(task, "landlord"), "咨询宠物入住", task["public"]["user_fields"])
        reply = api.wait_until(load(2)["deadline_at"])
        self.assertTrue(reply["messages"])
        # The wake happens exactly at the reply's delivery, whenever the
        # seeded reply delay places it.
        self.assertEqual(env.now, parse(reply["messages"][-1]["at"]))

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
        self.assertEqual(days, [2, 3, 5, 8, 13, 21, 34, 55, 89, 109, 210, 300])
        bins = [(2, 7), (8, 30), (31, 100), (101, 300)]
        self.assertEqual([sum(lo <= day <= hi for day in days) for lo, hi in bins], [3, 3, 3, 3])

    def test_expired_material_cannot_open_new_processing_case(self):
        task = load(12)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://yuancheng.bench/contact")
        front = api.send_email(mailbox(task, "forwarder"), "查询货件状态", task["public"]["user_fields"])
        while env.cases[front["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        doc = api.send_email(mailbox(task, "exporter"), "取得首轮更正申报资料", {"tracking": "PK-608"})
        while env.cases[doc["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        self.assertTrue(any(e["agent_visible"] and e["fact_id"] == "declaration" for e in env.evidence.values()))
        api.wait_until("2027-04-01T09:00:00+08:00", wake_on_message=False)
        case = api.send_email(mailbox(task, "customsdesk"), "申请初审登记", {"tracking": "PK-608", "declaration_version": "DEC-608-v2"})
        while env.cases[case["case_id"]]["state"] == "new" and env.events:
            env.advance(env.events[0][0])
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
        task = load(7)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://beiting.bench/contact")
        reply = api.send_email(mailbox(task, "archive"), "申请数字化交付", {"archive_id": "ARC-71", "exhibition_permission": True})
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[reply["case_id"]]["state"], "needs_information")
        self.assertFalse(env.events)

    def test_intermediate_patch_does_not_finish_quarterly_release_task(self):
        task = load(11)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://xingzhou.bench/contact")
        case = api.send_email(mailbox(task, "maintainer"), "确认兼容问题与补丁", task["public"]["user_fields"])
        while env.cases[case["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        self.assertTrue(any(ev["agent_visible"] and ev["fact_id"] == "workaround" for ev in env.evidence.values()))
        self.assertFalse(any(ev["agent_visible"] and ev["fact_id"] == "candidate" for ev in env.evidence.values()))
        self.assertFalse(env.evaluate({"conclusion": "workaround_available_stable_uncommitted", "claims": []})["information_sufficient"])

    def test_llm_router_is_scoped_and_validated(self):
        views = []
        def callback(view):
            views.append(view)
            return {"workflow_id": "main"}
        env = Environment(load(1), LLMRecipient(callback))
        env.tools().visit_page("https://heanhuiguan.bench/contact")
        env.tools().send_email(mailbox(load(1), "reception"), "请帮我找到合适的人")
        self.assertNotIn("facts", views[0])
        self.assertNotIn("actors", views[0])
        bad = Environment(load(1), LLMRecipient(lambda _: {"workflow_id": "secret"}))
        bad.tools().visit_page("https://heanhuiguan.bench/contact")
        with self.assertRaises(ValueError):
            bad.tools().send_email(mailbox(load(1), "reception"), "查询")

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
            {"id": 2, "tool": "recall_task", "arguments": {}},
            {"id": 3, "tool": "visit_page", "arguments": {"url": "https://heanhuiguan.bench/contact"}},
            {"id": 4, "tool": "send_email", "arguments": {"recipient": mailbox(load(1), "reception"), "text": "活动联系入口"}},
            {"id": 5, "tool": "wait_until", "arguments": {"until": "2026-11-10T18:00:00+08:00"}},
            {"id": 6, "tool": "execute_tool", "arguments": {}},
        ]
        completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-01"],
                    input="\n".join(json.dumps(r) for r in requests) + "\n", capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=True)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 6)
        # observe carries no task data; only recall_task re-issues the brief.
        self.assertEqual(set(responses[0]["result"]), {"now", "tools", "unread_messages"})
        self.assertIn("conclusion_options", responses[1]["result"]["task"])
        self.assertEqual(responses[3]["result"]["status"], "received")
        self.assertEqual(responses[4]["result"]["messages"][0]["status"], "reply")
        self.assertEqual(responses[5]["error"]["type"], "PermissionError")
        self.assertNotIn('"private_audit"', completed.stdout)

    def test_duplicate_claims_and_multiple_submissions_rejected(self):
        env, answer, _ = run_reference(load(1))
        answer["claims"].append(deepcopy(answer["claims"][0]))
        self.assertFalse(env.evaluate(answer)["complete"])
        with self.assertRaises(ValueError):
            env.tools().submit_answer(answer)

    def test_clock_backwards_and_after_deadline_send_rejected(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        with self.assertRaises(ValueError):
            api.wait_until("2026-11-01T00:00:00+08:00")
        api.wait_until(task["deadline_at"], wake_on_message=False)
        with self.assertRaises(ValueError):
            api.send_email(mailbox(task, "reception"), "活动")

    def test_browser_search_and_visit_are_two_levels(self):
        env = Environment(load(1))
        api = env.tools()
        # The task brief carries no pages and no contacts: discovery is the
        # agent's job through web_search and visit_page.
        brief = json.dumps(api.recall_task(), ensure_ascii=False)
        self.assertNotIn("旧版简介", brief)
        self.assertNotIn("reception", brief)
        self.assertEqual(api.recall_task(), api.recall_task())
        self.assertEqual(set(api.observe()), {"now", "tools", "unread_messages"})
        self.assertEqual(api.observe()["unread_messages"], 0)
        links = api.web_search("禾岸会馆")["results"]
        self.assertTrue(links)
        # Search results are URLs, never internal ids or page bodies.
        self.assertTrue(all(set(l) == {"url", "title", "snippet"} for l in links))
        self.assertTrue(all(l["url"].startswith("https://") and ".bench/" in l["url"] for l in links))
        self.assertNotIn("reception", json.dumps(api.web_search("联系方式"), ensure_ascii=False))
        # Empty queries and terms that match nothing return no links at all,
        # but the hint still reports how many pages remain undiscovered.
        total = len(load(1)["public"]["pages"])
        empty = api.web_search("")
        self.assertEqual(empty["results"], [])
        self.assertEqual(empty["hint"]["undiscovered_pages"], total - len({l["url"] for l in links}))
        self.assertEqual(api.web_search("   ")["results"], [])
        self.assertEqual(api.web_search("完全不相关的查询词")["results"], [])
        # Only proper page addresses are accepted; ids and foreign URLs are not.
        with self.assertRaises(ValueError):
            api.visit_page("venue")
        with self.assertRaises(ValueError):
            api.visit_page("https://example.com/contact")
        with self.assertRaises(ValueError):
            api.visit_page("https://heanhuiguan.bench/nowhere")
        venue = api.visit_page("https://heanhuiguan.bench/contact")
        self.assertNotIn("id", venue)
        self.assertIn("旧版简介", api.visit_page("https://heanhuiguan.bench/intro")["text"])
        self.assertEqual({c["id"] for c in venue["contact_details"]}, {"reception"})
        card = venue["contact_details"][0]
        self.assertTrue(card["contact_details"]["email"].endswith("@bench.example"))
        self.assertIn("phone", card["contact_details"])
        # Discovered contacts and later progress never leak back into the brief.
        self.assertNotIn("reception", json.dumps(api.recall_task(), ensure_ascii=False))

    def test_recipient_must_be_a_mailbox_address(self):
        task = load(1)
        api = Environment(task).tools()
        with self.assertRaises(ValueError):
            api.send_email("reception", "咨询")
        with self.assertRaises(ValueError):
            api.send_email("not-an-address", "咨询")
        with self.assertRaises(ValueError):
            api.send_email("@bench.example", "咨询")

    def test_unknown_mailbox_acknowledges_but_never_replies(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        result = api.send_email("nobody@bench.example", "联系活动场地")
        # The receipt is indistinguishable from a delivered mail and consumes
        # budget, but no case exists and nothing ever arrives.
        self.assertEqual(result["status"], "received")
        self.assertEqual(env.agent_sends, 1)
        self.assertNotIn(result["case_id"], env.cases)
        inbox = api.wait_until(task["deadline_at"])
        self.assertEqual(inbox["messages"], [])
        self.assertTrue(any(e["kind"] == "dead_letter" for e in env.audit))

    def test_misrouted_mail_gets_an_async_referral_email(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        # reception only routes venue contact inquiries, not price questions.
        result = api.send_email(mailbox(task, "reception"), "请提供报价和取消条款")
        self.assertEqual(result["status"], "received")
        # Nothing is answered at send time; the referral lands during work hours.
        self.assertEqual(env.cases[result["case_id"]]["state"], "new")
        inbox = api.wait_until(task["deadline_at"])
        referral = next(m for m in inbox["messages"] if m["case_id"] == result["case_id"])
        self.assertEqual(referral["status"], "referral")
        self.assertIn("不属于我负责的范围", referral["text"])
        self.assertNotIn("\n", referral["text"])
        self.assertEqual(env.cases[result["case_id"]]["state"], "replied")

    def test_followup_on_replied_case_reopens_when_it_routes(self):
        task = load(5)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://lengchuan.bench/contact")
        first = api.send_email(mailbox(task, "sales"), "初次报价", {"quantity": 500, "spec": "M26-Q7"})
        # First quote has been replied; drain the queue instead of guessing
        # the exact (jittered) reply time.
        while env.cases[first["case_id"]]["state"] != "replied" and env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[first["case_id"]]["state"], "replied")
        # A follow-up on the replied case that names a new request is re-routed
        # as a fresh case: it cannot restart or skip the original one.
        reopened = api.send_email(mailbox(task, "sales"), "旧报价已过期，请重新确认报价",
                                  {"quantity": 500, "spec": "M26-Q7"}, case_id=first["case_id"])
        self.assertNotEqual(reopened["case_id"], first["case_id"])
        self.assertEqual(env.cases[reopened["case_id"]]["workflow"]["id"], "refresh")
        self.assertEqual(env.cases[first["case_id"]]["state"], "replied")
        self.assertTrue(any(e["kind"] == "followup_reopened" and e["case_id"] == reopened["case_id"]
                            for e in env.audit))
        # An unmatched follow-up stays an acknowledgement and opens nothing.
        before = len(env.cases)
        ack = api.send_email(mailbox(task, "sales"), "谢谢，辛苦了", case_id=first["case_id"])
        self.assertEqual(ack["case_id"], first["case_id"])
        self.assertEqual(len(env.cases), before)
        api.wait_until(task["deadline_at"])
        reply = next(m for m in env.messages if m["case_id"] == reopened["case_id"] and m["status"] == "reply")
        self.assertTrue(any(e["value"] == 18600 for e in reply["evidence"]))

    def test_agent_email_gets_no_instant_reply(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        result = api.send_email(mailbox(task, "reception"), "联系活动场地")
        # Admission is deferred: nothing is routed at send time, and the reply
        # lands inside work hours after at least the task's minimum reply delay.
        self.assertEqual(env.cases[result["case_id"]]["state"], "new")
        self.assertTrue(env.events)
        inbox = api.wait_until(task["deadline_at"])
        reply = inbox["messages"][-1]
        self.assertGreaterEqual(parse(reply["at"]) - parse(task["start_at"]),
                                timedelta(minutes=task["reply_delay"][0]))

    def test_replies_are_single_paragraph_natural_language(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), "联系活动场地")
        inbox = api.wait_until(task["deadline_at"])
        for message in inbox["messages"]:
            self.assertNotIn("\n", message["text"])
            self.assertTrue(message["text"].startswith("您好，我是"))

    def test_messages_carry_no_structured_contacts(self):
        # Referrals speak names and mailboxes in prose only: no contact cards
        # ride along, and the sender surface is a mailbox address, never an
        # internal id. The referral itself registers the contacts so the
        # agent may follow up.
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), "联系活动场地")
        inbox = api.wait_until(task["deadline_at"])
        reply = inbox["messages"][-1]
        self.assertEqual(reply["from"], mailbox(task, "reception"))
        self.assertNotIn("contacts", reply)
        self.assertIn("姚岚（" + mailbox(task, "sales") + "）", reply["text"])
        self.assertIn("赵航（" + mailbox(task, "operations") + "）", reply["text"])
        # The contact page only knows the reception desk; the two specialists
        # become addressable through the referral, not through the directory.
        self.assertEqual(env.known_contacts, set(["reception", "sales", "operations"]))
        followup = api.send_email(mailbox(task, "sales"), "请发报价和取消条款",
                                  {"event_date": "2026-11-13", "headcount": 80})
        self.assertEqual(followup["status"], "received")


    def test_phone_call_semantics(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), "联系活动场地")
        # The two specialists are only discoverable through the reception
        # desk's referral, which arrives after the task's reply delay.
        while "sales" not in env.known_contacts:
            api.wait_until(task["deadline_at"])
        # sales is email-only: there is no number to dial.
        with self.assertRaises(ValueError):
            api.call("sales", "请报价格")
        # Outside the reception desk's work hours nobody picks up.
        api.wait_until("2026-11-07T10:00:00+08:00", wake_on_message=False)
        self.assertEqual(api.call("reception", "请转接销售")["status"], "no_answer")
        # Within work hours a quick referral completes during the call, but a
        # spoken answer attaches no evidence.
        api.wait_until("2026-11-09T09:30:00+08:00", wake_on_message=False)
        result = api.call("reception", "联系活动场地")
        self.assertEqual(result["status"], "answered")
        message = next(m for m in env.messages if m["case_id"] == result["case_id"])
        self.assertEqual(message["channel"], "phone")
        self.assertEqual(message["evidence"], [])


if __name__ == "__main__":
    unittest.main()
