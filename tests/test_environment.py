from copy import deepcopy
from datetime import timedelta
import json
import re
from pathlib import Path
import unittest
import subprocess
import sys

from dayspanbench.calendar import Calendar, parse
from dayspanbench.engine import Environment
from dayspanbench.llm import key_tokens
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
        self.assertEqual(actors, 43)

    def test_golden_calendar_completion_times(self):
        # Deterministic under the default latency seed; guards against unintended
        # drift in admission/jitter behavior.
        expected = {1: "2026-11-10T09:30:00+00:00", 2: "2026-11-12T02:30:00+00:00",
                    3: "2027-02-03T01:30:00+00:00", 4: "2026-11-25T02:50:00+00:00",
                    5: "2026-12-08T02:30:00+00:00", 6: "2026-11-18T00:30:00+00:00",
                    7: "2027-06-08T02:30:00+00:00", 8: "2026-11-12T05:41:00+00:00",
                    9: "2026-12-28T08:00:00+00:00", 10: "2026-11-09T03:03:00+00:00",
                    11: "2027-02-26T12:30:00+00:00", 12: "2027-09-02T07:00:00+00:00"}
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
        # The contact page only vaguely guesses where the signed syllabus
        # lives; the dean's office first suggests (making the lecturer
        # discoverable), then plainly denies, closing the archive request.
        dean = api.send_email(mailbox(task, "dean_office"), 'Please check the signed CS204 syllabus archive', {})
        while env.cases[dean["case_id"]]["state"] != "replied" and env.events:
            env.advance(env.events[0][0])
        # Legitimate material: the syllabus version must come from the
        # lecturer's attested reply, not out of thin air.
        api.send_email(mailbox(task, "lecturer"), 'Please reissue the official signed syllabus', {"course_code": "CS204"})
        api.wait_until("2026-11-10T15:00:00+08:00")  # lecturer has replied after the trip
        syllabus = next(r["fields"]["syllabus"] for m in env.messages
                        if m["status"] == "reply" and m["from"] == mailbox(task, "lecturer")
                        for r in m["receipts"])
        first = api.send_email(mailbox(task, "records"), 'Inquire about CS204 credit transfer',
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
        ack = api.send_email(mailbox(task, "records"), 'How is processing progressing',
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
        reopened = api.send_email(mailbox(task, "records"), 'The syllabus version has changed; please process the new version',
                                  {"course_code": "CS204", "syllabus_version": "CS204-2026-v3"},
                                  case_id=first["case_id"])
        self.assertNotEqual(reopened["case_id"], first["case_id"])
        # A progress ping with no fields at all also only acknowledges: it
        # must not be treated as a new request and re-routed into a duplicate
        # parallel case.
        before = len(env.cases)
        ping = api.send_email(mailbox(task, "records"), 'How is processing progressing', {}, case_id=first["case_id"])
        self.assertEqual(ping["case_id"], first["case_id"])
        self.assertEqual(len(env.cases), before)

    def test_missing_material_and_forged_material_are_not_accepted(self):
        task = load(3)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://chengchuan.bench/contact")
        result = api.send_email(mailbox(task, "records"), 'Inquire about credit transfer', {"course_code": "CS204"})
        # Admission is deferred to the recipient's work hours after the task's
        # reply delay; drain the event queue rather than guessing a timestamp.
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        api.send_email(mailbox(task, "records"), 'Supplement syllabus', {"syllabus_version": "CS204-2026-v2-signed"}, case_id=result["case_id"])
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
        result = api.send_email(mailbox(task, "support"), 'Warranty inquiry', {"serial": "OTHER", "receipt": "R-731"})
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")

    def test_internal_contacts_and_fact_tools_are_not_agent_tools(self):
        task = load(1)
        api = Environment(task).tools()
        with self.assertRaises(PermissionError):
            api.send_email(mailbox(task, "technician"), 'maintenance', {"event_date": "2026-11-13"})
        self.assertFalse(hasattr(api, "execute_tool"))
        visible = json.dumps(api.recall_task(), ensure_ascii=False)
        self.assertNotIn('"expected_conclusion"', visible)
        self.assertNotIn('"facts"', visible)
        self.assertNotIn('all-day maintenance', visible)

    def test_unit_variant_field_still_admits(self):
        # A quantity quoted with a synonym unit ("8公斤") describes the same case
        # as the canonical user_fields spelling ("8kg") and must not bounce to
        # needs_information; a genuinely different quantity still must.
        task = load(2)
        env = Environment(task)
        api = env.tools()
        variant = {**task["public"]["user_fields"], "pet_weight": "8公斤"}
        result = api.send_email(mailbox(task, "landlord"), 'Inquire about pet move-in', variant)
        while env.events:
            env.advance(env.events[0][0])
        case = env.cases[result["case_id"]]
        self.assertEqual(case["fields"]["pet_weight"], "8kg")
        self.assertNotEqual(case["state"], "needs_information")

    def test_bare_number_and_date_variant_fields_still_admit(self):
        # "8" and "11月12日" (no unit / Chinese date spelling) describe the same
        # case as "8kg" / "2026-11-12"; a different number or date still bounces.
        task = load(2)
        for variant in ({"pet_weight": "8", "move_date": "11月12日"},
                        {"pet_weight": "8", "move_date": "2026年11月12日"}):
            env = Environment(task)
            api = env.tools()
            case = env.cases[api.send_email(mailbox(task, "landlord"), 'Inquire about pet move-in', variant)["case_id"]]
            while env.events:
                env.advance(env.events[0][0])
            self.assertEqual(case["fields"]["pet_weight"], "8kg")
            self.assertEqual(case["fields"]["move_date"], "2026-11-12")
            self.assertNotEqual(case["state"], "needs_information")
        for variant in ({"pet_weight": "9", "move_date": "2026-11-12"},
                        {"pet_weight": "8", "move_date": "11月13日"}):
            env = Environment(task)
            api = env.tools()
            case = env.cases[api.send_email(mailbox(task, "landlord"), 'Inquire about pet move-in', variant)["case_id"]]
            while env.events:
                env.advance(env.events[0][0])
            self.assertEqual(case["state"], "needs_information")

    def test_followup_does_not_change_completion(self):
        task = load(2)
        env = Environment(task)
        api = env.tools()
        case = api.send_email(mailbox(task, "landlord"), 'Inquire about pet move-in', task["public"]["user_fields"])
        api.send_email(mailbox(task, "landlord"), 'Following up', case_id=case["case_id"])
        env.advance(env.deadline)
        replies = [m for m in env.messages if m["status"] == "reply"]
        reference, _, _ = run_reference(load(2))
        self.assertEqual(replies[-1]["at"], reference.messages[-1]["at"])

    def test_resource_queue_prevents_parallel_work_by_one_person(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), 'Contact event venue')
        api.send_email(mailbox(task, "reception"), 'Contact event venue')
        env.advance("2026-11-06T17:00:00+08:00")
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        # The second case can never start before the single worker finishes the first.
        self.assertGreaterEqual(parse(scheduled[1]["start_at"]), parse(scheduled[0]["due_at"]))

    def test_simultaneous_events_and_independent_people(self):
        task = load(8)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://wuzhangzhusu.bench/contact")
        fields = task["public"]["user_fields"]
        a = api.send_email(mailbox(task, "a_desk"), 'Accessibility dimensions', fields)
        # Before B's measurement window opens the desk only registers the
        # request; file after the window opens to get it admitted.
        early = api.send_email(mailbox(task, "b_desk"), 'Accessibility remeasurement', fields)
        env.advance("2026-11-09T09:30:00+08:00")
        self.assertTrue(any(e["kind"] == "early_reply" and e["case_id"] == early["case_id"] for e in env.audit))
        self.assertFalse(any(e["kind"] == "scheduled" and e.get("actor") == "b_desk" and e["case_id"] == early["case_id"]
                              for e in env.audit))
        b = api.send_email(mailbox(task, "b_desk"), 'Accessibility remeasurement', fields)
        self.assertNotEqual(a["case_id"], b["case_id"])
        self.assertNotEqual(early["case_id"], b["case_id"])
        env.advance("2026-11-09T17:00:00+08:00")
        scheduled = [e for e in env.audit if e["kind"] == "scheduled"]
        # Independent people are admitted and scheduled without waiting for each
        # other: each desk's first step runs on its own filing timeline.
        first_by_actor = {}
        for s in scheduled:
            first_by_actor.setdefault(s["actor"], parse(s["start_at"]))
        self.assertEqual(set(first_by_actor), {"a_desk", "b_desk", "a_tech", "b_tech"})
        self.assertLess(first_by_actor["a_desk"], parse(load(8)["start_at"]) + timedelta(days=1))
        self.assertGreaterEqual(first_by_actor["b_desk"], parse("2026-11-09T09:00:00+08:00"))
        self.assertLess(first_by_actor["b_desk"], parse("2026-11-09T17:00:00+08:00"))

    def test_dsb08_measurement_window_and_atomic_field(self):
        # Before 11-09 09:00 B's measurement desk only registers the request;
        # the price workflow stays open, and a semantically correct "78cm"
        # (unit synonym of the canonical value) still admits after the window.
        task = load(8)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://wuzhangzhusu.bench/contact")
        fields = dict(task["public"]["user_fields"])
        # Price/availability is answered immediately, window or not.
        price = api.send_email(mailbox(task, "b_desk"), 'Room availability and total price inquiry', {"stay_dates": fields["stay_dates"]})
        env.advance("2026-11-06T18:00:00+08:00")
        self.assertTrue(any(m["case_id"] == price["case_id"] and m["status"] == "reply" for m in env.messages))
        # Early measurement request: registration only, no evidence, no queue.
        early = api.send_email(mailbox(task, "b_desk"), 'Accessibility remeasurement', fields)
        env.advance("2026-11-09T09:00:00+08:00")
        self.assertTrue(any(e["kind"] == "early_reply" and e["case_id"] == early["case_id"] for e in env.audit))
        early_case = env.cases[early["case_id"]]
        self.assertEqual(early_case["state"], "replied")
        self.assertFalse(any(m["case_id"] == early["case_id"] and m["receipts"] for m in env.messages))
        # In-window filing with a synonym unit spelling of the width admits.
        filed = api.send_email(mailbox(task, "b_desk"), 'Accessibility remeasurement',
                               {**fields, "wheelchair_width": "78厘米"})
        while env.cases[filed["case_id"]]["state"] != "waiting_internal" and env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[filed["case_id"]]["state"], "waiting_internal")
        self.assertTrue(any(m["case_id"] == filed["case_id"] and m["status"] == "acknowledgement"
                            for m in env.messages))
        # Mismatched width gets a distinguishable needs_information sentence.
        env2 = Environment(task)
        api2 = env2.tools()
        api2.visit_page("https://wuzhangzhusu.bench/contact")
        env2.advance("2026-11-09T09:30:00+08:00")
        bad = api2.send_email(mailbox(task, "b_desk"), 'Accessibility remeasurement', {**fields, "wheelchair_width": "90cm"})
        env2.advance("2026-11-09T17:00:00+08:00")
        text = next(m["text"] for m in env2.messages if m["case_id"] == bad["case_id"])
        self.assertIn('does not match the registered information', text)
        self.assertNotIn('valid evidence', text)

    def test_wait_wakes_for_agent_delivery_not_private_transition(self):
        task = load(2)
        env = Environment(task)
        api = env.tools()
        api.send_email(mailbox(task, "landlord"), 'Inquire about pet move-in', task["public"]["user_fields"])
        reply = api.wait_until(load(2)["deadline_at"])
        self.assertTrue(reply["messages"])
        # The wake happens exactly at the reply's delivery, whenever the
        # seeded reply delay places it.
        self.assertEqual(env.now, parse(reply["messages"][-1]["at"]))

    def test_expired_quote_is_no_anchor_but_current_quote_is(self):
        env, answer, _ = run_reference(load(5))
        result = env.evaluate(answer)
        self.assertTrue(result["complete"])
        # The superseded quote expired at scoring time; its figure must not be
        # demanded from the final summary.
        old = next(e for e in env.evidence.values() if e["fact_id"] == "quote_old")
        for token in key_tokens(str(old["value"])):
            self.assertNotIn(token, result["deterministic_checks"]["summary_anchor_missing"])
        # Dropping a current anchor element from the summary fails the anchors.
        token, failed = None, None
        for candidate in sorted(key_tokens(answer["summary"])):
            stripped = answer["summary"].replace(candidate, "X")
            attempt = env.evaluate({**answer, "summary": stripped})
            if candidate in attempt["deterministic_checks"]["summary_anchor_missing"]:
                token, failed = candidate, attempt
                break
        self.assertIsNotNone(token, "no anchor token could be dropped")
        self.assertFalse(failed["complete"])

    def test_missing_summary_is_a_schema_failure(self):
        env, answer, _ = run_reference(load(1))
        answer.pop("summary")
        result = env.evaluate(answer)
        self.assertFalse(result["answer_schema_valid"])
        self.assertFalse(result["complete"])

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
        front = api.send_email(mailbox(task, "forwarder"), 'Query shipment status', task["public"]["user_fields"])
        while env.cases[front["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        env.advance("2026-11-25T10:00:00+08:00")
        doc = api.send_email(mailbox(task, "exporter"), 'Obtain first round corrected declaration materials', {"tracking": "PK-608"})
        while env.cases[doc["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        self.assertTrue(any(e["agent_visible"] and e["fact_id"] == "declaration" for e in env.evidence.values()))
        env.advance("2027-04-01T09:00:00+08:00")
        case = api.send_email(mailbox(task, "customsdesk"), 'Request preliminary review registration', {"tracking": "PK-608", "declaration_version": "DEC-608-v2"})
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

    def test_premature_dsb12_mail_gets_registration_reply_only(self):
        # Before an accept_after window opens, a complete request earns only a
        # registration reply: no case is queued, no evidence is issued.
        task = load(12)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://yuancheng.bench/contact")
        front = api.send_email(mailbox(task, "forwarder"), 'Query shipment status', task["public"]["user_fields"])
        while env.cases[front["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        early = api.send_email(mailbox(task, "exporter"), 'Please reissue first-round corrected declaration materials', {"tracking": "PK-608"})
        env.advance("2026-12-01T10:00:00+08:00")
        case = env.cases[early["case_id"]]
        self.assertEqual(case["state"], "replied")
        self.assertEqual(case["workflow"]["id"], "main")
        self.assertFalse(case["facts"])
        self.assertFalse(any(e["fact_id"] == "declaration" for e in env.evidence.values()))
        self.assertTrue(any(e["kind"] == "early_reply" for e in env.audit))
        # Filing again inside the window opens a normal case with an ETA receipt.
        again = api.send_email(mailbox(task, "exporter"), 'Please reissue first-round corrected declaration materials', {"tracking": "PK-608"})
        while env.cases[again["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        self.assertTrue(any(e["agent_visible"] and e["fact_id"] == "declaration" for e in env.evidence.values()))

    def test_followup_on_unrouted_case_acknowledges_without_error(self):
        # A follow-up quoting the case_id of an unrouted (referral-replied) case
        # must acknowledge instead of crashing on the missing workflow.
        task = load(12)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://yuancheng.bench/contact")
        misrouted = api.send_email(mailbox(task, "forwarder"), 'What is the flight timetable', {"tracking": "PK-608"})
        while env.cases[misrouted["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        result = api.send_email(mailbox(task, "forwarder"), 'Who should handle this?', case_id=misrouted["case_id"])
        self.assertEqual(result["status"], "received")

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
        reply = api.send_email(mailbox(task, "archive"), 'Request digitized delivery', {"archive_id": "ARC-71", "exhibition_permission": True})
        while env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[reply["case_id"]]["state"], "needs_information")
        self.assertFalse(env.events)

    def test_intermediate_patch_does_not_finish_quarterly_release_task(self):
        task = load(11)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://xingzhou.bench/contact")
        case = api.send_email(mailbox(task, "maintainer"), 'Confirm compatibility issue and patch', task["public"]["user_fields"])
        while env.cases[case["case_id"]]["state"] != "replied":
            api.wait_until(task["deadline_at"])
        self.assertTrue(any(ev["agent_visible"] and ev["fact_id"] == "workaround" for ev in env.evidence.values()))
        self.assertFalse(any(ev["agent_visible"] and ev["fact_id"] == "candidate" for ev in env.evidence.values()))
        self.assertFalse(env.evaluate({"conclusion": "workaround_available_stable_uncommitted", "summary": ""})["information_sufficient"])

    def test_llm_router_is_scoped_and_validated(self):
        views = []
        def callback(view):
            views.append(view)
            return {"workflow_id": "main"}
        env = Environment(load(1), LLMRecipient(callback))
        env.tools().visit_page("https://heanhuiguan.bench/contact")
        env.tools().send_email(mailbox(load(1), "reception"), 'Please help me find the right person')
        self.assertNotIn("facts", views[0])
        self.assertNotIn("actors", views[0])
        bad = Environment(load(1), LLMRecipient(lambda _: {"workflow_id": "secret"}))
        bad.tools().visit_page("https://heanhuiguan.bench/contact")
        with self.assertRaises(ValueError):
            bad.tools().send_email(mailbox(load(1), "reception"), 'inquiry')

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
            {"id": 4, "tool": "send_email", "arguments": {"recipient": mailbox(load(1), "reception"), "text": 'Event contact channel'}},
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

    def test_multiple_submissions_rejected(self):
        env, answer, _ = run_reference(load(1))
        with self.assertRaises(ValueError):
            env.tools().submit_answer(answer)

    def test_clock_backwards_and_after_deadline_send_rejected(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        with self.assertRaises(ValueError):
            api.wait_until("2026-11-01T00:00:00+08:00")
        env.advance(task["deadline_at"])
        with self.assertRaises(ValueError):
            api.send_email(mailbox(task, "reception"), 'event')

    def test_browser_search_and_visit_are_two_levels(self):
        env = Environment(load(1))
        api = env.tools()
        # The task brief carries no pages and no contacts: discovery is the
        # agent's job through web_search and visit_page.
        brief = json.dumps(api.recall_task(), ensure_ascii=False)
        self.assertNotIn('Old introduction', brief)
        self.assertNotIn("reception", brief)
        self.assertEqual(api.recall_task(), api.recall_task())
        self.assertEqual(set(api.observe()), {"now", "tools", "unread_messages"})
        self.assertEqual(api.observe()["unread_messages"], 0)
        links = api.web_search('Hean Hall')["results"]
        self.assertTrue(links)
        # Search results are URLs, never internal ids or page bodies.
        self.assertTrue(all(set(l) == {"url", "title", "snippet"} for l in links))
        self.assertTrue(all(l["url"].startswith("https://") and ".bench/" in l["url"] for l in links))
        self.assertNotIn("reception", json.dumps(api.web_search('contacts'), ensure_ascii=False))
        # Empty queries and terms that match nothing return no links at all,
        # but the hint still reports how many pages remain undiscovered.
        total = len(load(1)["public"]["pages"])
        empty = api.web_search("")
        self.assertEqual(empty["results"], [])
        self.assertEqual(empty["hint"]["undiscovered_pages"], total - len({l["url"] for l in links}))
        self.assertEqual(api.web_search("   ")["results"], [])
        self.assertEqual(api.web_search('completely unrelated query words')["results"], [])
        # Only proper page addresses are accepted; ids and foreign URLs are not.
        with self.assertRaises(ValueError):
            api.visit_page("venue")
        with self.assertRaises(ValueError):
            api.visit_page("https://example.com/contact")
        with self.assertRaises(ValueError):
            api.visit_page("https://heanhuiguan.bench/nowhere")
        venue = api.visit_page("https://heanhuiguan.bench/contact")
        self.assertNotIn("id", venue)
        self.assertIn('Old introduction', api.visit_page("https://heanhuiguan.bench/intro")["text"])
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
            api.send_email("reception", 'inquiry')
        with self.assertRaises(ValueError):
            api.send_email("not-an-address", 'inquiry')
        with self.assertRaises(ValueError):
            api.send_email("@bench.example", 'inquiry')

    def test_unknown_mailbox_acknowledges_but_never_replies(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        result = api.send_email("nobody@bench.example", 'Contact event venue')
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
        result = api.send_email(mailbox(task, "reception"), 'Please provide quote and cancellation terms')
        self.assertEqual(result["status"], "received")
        # Nothing is answered at send time; the referral lands during work hours.
        self.assertEqual(env.cases[result["case_id"]]["state"], "new")
        inbox = api.wait_until(task["deadline_at"])
        referral = next(m for m in inbox["messages"] if m["case_id"] == result["case_id"])
        self.assertEqual(referral["status"], "referral")
        self.assertIn('outside my remit', referral["text"])
        self.assertNotIn("\n", referral["text"])
        self.assertEqual(env.cases[result["case_id"]]["state"], "replied")

    def test_followup_on_replied_case_reopens_when_it_routes(self):
        task = load(5)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://lengchuan.bench/contact")
        first = api.send_email(mailbox(task, "sales"), 'Initial quote', {"quantity": 500, "spec": "M26-Q7"})
        # First quote has been replied; drain the queue instead of guessing
        # the exact (jittered) reply time.
        while env.cases[first["case_id"]]["state"] != "replied" and env.events:
            env.advance(env.events[0][0])
        self.assertEqual(env.cases[first["case_id"]]["state"], "replied")
        # A follow-up on the replied case that names a new request is re-routed
        # as a fresh case: it cannot restart or skip the original one.
        reopened = api.send_email(mailbox(task, "sales"), 'The old quote has expired; please reconfirm quote',
                                  {"quantity": 500, "spec": "M26-Q7"}, case_id=first["case_id"])
        self.assertNotEqual(reopened["case_id"], first["case_id"])
        self.assertEqual(env.cases[reopened["case_id"]]["workflow"]["id"], "refresh")
        self.assertEqual(env.cases[first["case_id"]]["state"], "replied")
        self.assertTrue(any(e["kind"] == "followup_reopened" and e["case_id"] == reopened["case_id"]
                            for e in env.audit))
        # An unmatched follow-up stays an acknowledgement and opens nothing.
        before = len(env.cases)
        ack = api.send_email(mailbox(task, "sales"), 'Thank you for your help', case_id=first["case_id"])
        self.assertEqual(ack["case_id"], first["case_id"])
        self.assertEqual(len(env.cases), before)
        api.wait_until(task["deadline_at"])
        # The refresh workflow's acknowledgement receipt wakes the wait early;
        # drain to the terminal state before looking for the final reply.
        while env.cases[reopened["case_id"]]["state"] != "replied" and env.events:
            env.advance(env.events[0][0])
        reply = next(m for m in env.messages if m["case_id"] == reopened["case_id"] and m["status"] == "reply")
        self.assertTrue(any(18600 in r["fields"].values() for r in reply["receipts"]))

    def test_agent_email_gets_no_instant_reply(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        result = api.send_email(mailbox(task, "reception"), 'Contact event venue')
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
        api.send_email(mailbox(task, "reception"), 'Contact event venue')
        inbox = api.wait_until(task["deadline_at"])
        for message in inbox["messages"]:
            self.assertNotIn("\n", message["text"])
            self.assertTrue(message["text"].startswith('Hello, I am '))

    def test_messages_carry_no_structured_contacts(self):
        # Referrals speak names and mailboxes in prose only: no contact cards
        # ride along, and the sender surface is a mailbox address, never an
        # internal id. The referral itself registers the contacts so the
        # agent may follow up.
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), 'Contact event venue')
        inbox = api.wait_until(task["deadline_at"])
        reply = inbox["messages"][-1]
        self.assertEqual(reply["from"], mailbox(task, "reception"))
        self.assertNotIn("contacts", reply)
        self.assertIn('Yao Lan (' + mailbox(task, "sales") + ")", reply["text"])
        self.assertIn('Zhao Hang (' + mailbox(task, "operations") + ")", reply["text"])
        # The contact page only knows the reception desk; the two specialists
        # become addressable through the referral, not through the directory.
        self.assertEqual(env.known_contacts, set(["reception", "sales", "operations"]))
        followup = api.send_email(mailbox(task, "sales"), 'Please provide a quotation and cancellation terms',
                                  {"event_date": "2026-11-13", "headcount": 80})
        self.assertEqual(followup["status"], "received")

    def test_ping_without_case_reference_joins_the_open_case(self):
        # A progress ping that carries no case_id must neither spawn a rival
        # case (it would compete with the original queue) nor draw a referral
        # from a person actively serving the sender: it acknowledges the open
        # case and restates its ETA (DSB-02 lesson).
        task = load(2)
        env = Environment(task)
        api = env.tools()
        filed = api.send_email(mailbox(task, "landlord"), 'Inquire about rental, pets, and move-in',
                                task["public"]["user_fields"])
        env.advance("2026-11-06T21:00:00+08:00")
        self.assertEqual(env.cases[filed["case_id"]]["state"], "waiting_internal")
        agent_cases_before = [c for c in env.cases.values()
                              if c.get("origin") == "agent" and not c.get("parent")]
        # Alias-less ping and alias-matched ping both land on the open case.
        for text in ('How is progress?', 'How is the rental matter progressing?'):
            ping = api.send_email(mailbox(task, "landlord"), text)
            self.assertEqual(ping["case_id"], filed["case_id"])
        agent_cases_after = [c for c in env.cases.values()
                             if c.get("origin") == "agent" and not c.get("parent")]
        self.assertEqual(len(agent_cases_after), len(agent_cases_before))
        env.advance(task["deadline_at"])
        pings = [m for m in env.messages if m["case_id"] == filed["case_id"]
                 and m["status"] == "acknowledgement"]
        self.assertGreaterEqual(len(pings), 2)
        self.assertFalse(any(m["status"] == "referral" and m["case_id"] == filed["case_id"]
                             for m in env.messages))

    def test_restated_eta_follows_child_progress_and_never_shrinks_trust(self):
        # Re-asserting the ETA of a waiting_internal case must follow the
        # delegate child's real progress: after the Friday reviewer batch has
        # run, a ping may not promise the next weekly batch (DSB-02 once
        # re-promised 11-13 for a case finishing 11-11).
        task = load(2)
        env = Environment(task)
        api = env.tools()
        filed = api.send_email(mailbox(task, "landlord"), 'Inquire about rental, pets, and move-in',
                                task["public"]["user_fields"])
        env.advance("2026-11-09T21:00:00+08:00")
        api.send_email(mailbox(task, "landlord"), 'How is progress?')
        env.advance(task["deadline_at"])
        acks = [m for m in env.messages if m["case_id"] == filed["case_id"]
                and m["status"] == "acknowledgement"]
        import re
        promised = [re.search('The earliest expected completion is (.+?) local time, followed', m["text"]).group(1) for m in acks]
        final = next(m for m in env.messages if m["case_id"] == filed["case_id"] and m["status"] == "reply")
        # Every promise is conservative: the reply never lands after the
        # promised minute (an agent may safely wait until it), and never more
        # than a day before it (the promise stays informative). The promise is
        # in the recipient's timezone (Asia/Shanghai, +08:00).
        for text in promised:
            self.assertGreaterEqual(parse(text + "+08:00"), parse(final["at"]))
            self.assertLess(parse(text + "+08:00"), parse(final["at"]) + timedelta(days=1))

    def test_promise_eta_is_conservative_across_seeds(self):
        # The acknowledgement's "earliest completion" must never be beaten by
        # the real run: the projection includes the worst-case agent jitter
        # (DSB-04 once promised 09:30 and delivered 10:50, and the agent gave
        # up exactly at the promised minute).
        import re
        task = load(4)
        for seed in range(4):
            env = Environment(task, seed=seed)
            api = env.tools()
            api.visit_page("https://nanyu.bench/contact")
            api.send_email(mailbox(task, "labdesk"), 'Measurement instrument contact')
            # The labdesk referral names the safety officer and the instrument
            # keeper; only then are they addressable. File before the Friday
            # 14:00 training batch so the certificate is in hand.
            env.advance("2026-11-05T17:00:00+08:00")
            api.send_email(mailbox(task, "safety"), 'Safety training record', {"person_name": 'Gu Xiao'})
            while not any(m["status"] == "reply" and m["from"] == mailbox(task, "safety")
                          for m in env.messages):
                env.advance(env.events[0][0] if env.events else parse(task["deadline_at"]))
            # The safety officer no longer mails the record: the deny reply names
            # the training-record system, which issues the certificate only after
            # the batch has been processed.
            api.discover_tools("nanyu_training_record")
            api.nanyu_training_record(fields={"person_name": 'Gu Xiao', "training_date": "2026-11-13"})
            env.advance("2026-11-13T16:30:00+08:00")
            api.send_email(mailbox(task, "instrument"), 'Verify measurement calibration and fees',
                           {"sample_id": "S-482", "safety_certificate": "SAFE-NOV06-482"})
            env.advance(task["deadline_at"])
            ack = next(m for m in env.messages if m["status"] == "acknowledgement"
                       and 'Du He' in m["text"])
            reply = next(m for m in env.messages if m["status"] == "reply" and 'Du He' in m["text"])
            promised = re.search('The earliest expected completion is (.+?) local time, followed', ack["text"]).group(1)
            self.assertGreaterEqual(parse(promised + "+08:00"), parse(reply["at"]),
                                    f"seed {seed}: promise {promised} beaten by {reply['at']}")

    def test_queue_contention_retracts_a_stale_eta_promise(self):
        # A promised earliest completion can be outgrown by later queue
        # contention: the agent's duplicate phone inquiry delegated a second
        # case onto the weekend-only tester, pushing the written-record step
        # past the Sunday close and the whole chain to the next Saturday. The
        # requester must get a revision email instead of planning around a
        # broken promise. DSB-10's authored friend now reports the read-out
        # verbally and routes the written record through the hidden inspection
        # form (a short chain that contention cannot push a week out), so this
        # engine-level check restores the old long document step on a local
        # copy; the authored task itself is untouched.
        task = deepcopy(load(10))
        friend = next(a for a in task["actors"] if a["id"] == "friend")
        friend["tools"].pop("friend.main.2.deny")
        friend["tools"]["friend.main.2.document"] = {
            "kind": "document", "facts": ["actual", "hotshoe"],
            "delay": {"mode": "business", "minutes": 30}}
        friend["workflows"][0]["steps"][1] = {
            "id": "main_2", "label": 'Issue written inspection record',
            "tool": "friend.main.2.document", "delay": {"mode": "business", "minutes": 30}}
        env = Environment(task, seed=0)
        api = env.tools()
        filed = api.send_email(mailbox(task, "seller"), 'Inquire about CAM-402: measured shutter count, hot shoe, price, returns, and pickup.',
                               {"serial": "CAM-402", "pickup_area": 'Qiaoxi East District'})
        env.advance("2026-11-06T21:00:00+08:00")
        api.call("seller", 'Ask again about CAM-402: measured shutter count, hot shoe, price, and returns.',
                 {"serial": "CAM-402", "pickup_area": 'Qiaoxi East District'})
        env.advance(task["deadline_at"])
        revisions = [m for m in env.messages if m["case_id"] == filed["case_id"]
                     and 'Progress update' in m["text"]]
        self.assertEqual(len(revisions), 1)
        promised = next(m for m in env.messages if m["case_id"] == filed["case_id"]
                        and 'The earliest expected completion is ' in m["text"])
        promised_at = parse(re.search('The earliest expected completion is (.+?) local time, followed', promised["text"]).group(1) + "+08:00")
        revised_at = parse(re.search('earliest expected completion is now (.+?) local time', revisions[0]["text"]).group(1) + "+08:00")
        self.assertGreater(revised_at, promised_at + timedelta(days=1))
        # The revision stays conservative versus the raw engine projection:
        # directly past the deadline, the document step already sits a week
        # past the original promise.
        env.advance("2026-11-14T23:00:00+08:00")
        document = next(e for e in env.audit if e["kind"] == "scheduled"
                        and e["case_id"] in {"CASE-0003", "CASE-0004"} and e["step"] == "main_2")
        self.assertGreater(parse(document["due_at"]), promised_at + timedelta(days=5))

    def test_phone_call_semantics(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        api.send_email(mailbox(task, "reception"), 'Contact event venue')
        # The two specialists are only discoverable through the reception
        # desk's referral, which arrives after the task's reply delay.
        while "sales" not in env.known_contacts:
            api.wait_until(task["deadline_at"])
        # sales is email-only: there is no number to dial.
        with self.assertRaises(ValueError):
            api.call("sales", 'Please quote the price')
        # Outside the reception desk's work hours nobody picks up.
        env.advance("2026-11-07T10:00:00+08:00")
        self.assertEqual(api.call("reception", 'Please connect me to sales')["status"], "no_answer")
        # Within work hours a quick referral completes during the call, but a
        # spoken answer attaches no receipts.
        env.advance("2026-11-09T09:30:00+08:00")
        result = api.call("reception", 'Contact event venue')
        self.assertEqual(result["status"], "answered")
        message = next(m for m in env.messages if m["case_id"] == result["case_id"])
        self.assertEqual(message["channel"], "phone")
        self.assertEqual(message["receipts"], [])


class ComplexityMechanismTests(unittest.TestCase):
    """Page updates, vague suggestions, visible consults, optional tools."""

    def test_page_updates_rewrite_content_over_time(self):
        task = load(1)
        env = Environment(task)
        api = env.tools()
        url = "https://heanhuiguan.bench/intro"
        before = api.visit_page(url)
        self.assertIn('Old introduction', before["text"])
        # The update lands at its authored virtual time; nothing changes before.
        env.advance("2026-11-07T09:59:00+08:00")
        self.assertIn('Old introduction', api.visit_page(url)["text"])
        env.advance("2026-11-07T10:01:00+08:00")
        after = api.visit_page(url)
        self.assertNotIn('Old introduction', after["text"])
        self.assertIn('invalid', after["text"])
        self.assertGreaterEqual(parse(after["last_updated"]), parse("2026-11-07T10:00:00+08:00"))
        self.assertTrue(any(e["kind"] == "page_updated" for e in env.audit))
        # The stale snippet also stops matching the way it used to.
        self.assertIn('latest pricing', api.web_search('pricing')["results"][0]["snippet"])

    def test_suggest_emits_vague_reply_and_exposes_guesses(self):
        task = load(9)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://qinggang.bench/contact")
        api.send_email(mailbox(task, "service"), 'Please verify jurisdiction for event processing',
                       {"location": 'Qinggang North Square', "sound_equipment": 'Use two amplified-sound speakers'})
        env.advance("2026-11-04T17:00:00+08:00")
        vague = next((m for m in env.messages if 'cannot clearly recall' in m["text"]), None)
        self.assertIsNotNone(vague, "expected the service desk's vague guess reply")
        # The guessed colleagues become addressable even though the reply is vague.
        self.assertIn("land", env.known_contacts)
        self.assertIn("sound", env.known_contacts)

    def test_consult_sends_interim_letter_then_real_reply(self):
        task = load(2)
        env = Environment(task)
        api = env.tools()
        api.send_email(mailbox(task, "landlord"), 'Inquire about rent, pets, and move-in conditions',
                       task["public"]["user_fields"])
        # The evening window is short; the transfer letter may land the next
        # evening. Drain events until the case is waiting on the manager.
        while env.cases and not any(c.get("state") == "waiting_internal" for c in env.cases.values()) and env.events:
            env.advance(env.events[0][0])
        interim = [m for m in env.messages if 'management' in m["text"] and m["status"] == "acknowledgement"]
        self.assertTrue(interim, "expected the landlord's interim consult letter")
        env.advance(task["deadline_at"])
        final = [m for m in env.messages if m["status"] == "reply"]
        self.assertTrue(final)

    def test_per_task_optional_tools_and_fetch_document_receipt(self):
        task = load(5)
        env = Environment(task)
        api = env.tools()
        tools = api.observe()["tools"]
        self.assertIn("fetch_document", tools)
        self.assertNotIn("lookup_directory", tools)
        # A batch price file hangs on the intro page from the start (an
        # early unauthorized-issuer decoy), while the December quote
        # document only exists after the page update publishes it.
        url = "https://lengchuan.bench/intro"
        initial = api.visit_page(url).get("documents", [])
        self.assertEqual([d["title"] for d in initial], ['500-unit M26 batch price list.pdf'])
        with self.assertRaises(ValueError):
            api.fetch_document("https://lengchuan.bench/files/supplier-quote-2026-12.pdf")
        env.advance("2026-12-07T10:01:00+08:00")
        documents = api.visit_page(url)["documents"]
        self.assertEqual(documents[0]["title"], 'December batch price list.pdf')
        fetched = api.fetch_document(documents[0]["url"])
        self.assertIn(18600, fetched["receipts"][0]["fields"].values())
        # The fetched price file's fact is agent-visible on the director.
        self.assertTrue(env.director.facts["quote_new"]["agent_visible"])
        # A task that does not declare the tool rejects it (every task now
        # ships fetch_document for its published files, so strip it manually).
        stripped = load(3)
        stripped["tools"] = [t for t in stripped["tools"] if t != "fetch_document"]
        stripped["public"]["tools"] = list(stripped["tools"])
        other = Environment(stripped).tools()
        with self.assertRaises(PermissionError):
            other.fetch_document(documents[0]["url"])

    def test_decoy_tools_answer_but_do_nothing(self):
        task = load(1)
        api = Environment(task).tools()
        api.visit_page("https://heanhuiguan.bench/contact")
        result = api.request_callback("reception", 'quotation')
        self.assertEqual(result["status"], "registered")
        with self.assertRaises(PermissionError):
            api.request_callback("technician", 'Undiscovered contact')
        # DSB-03 offers no leave_note (DSB-01 gained it as an added decoy).
        other = Environment(load(3)).tools()
        other.visit_page("https://chengchuan.bench/contact")
        with self.assertRaises(PermissionError):
            other.leave_note("records", 'Notes are unavailable in this task')


if __name__ == "__main__":
    unittest.main()
