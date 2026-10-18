"""Hidden tools (discover_tools), staged web forms, and guess-chain deny replies."""

from copy import deepcopy
import json
import unittest

from dayspanbench.calendar import parse
from dayspanbench.engine import Environment, PUBLIC_TOOLS
from dayspanbench.validation import validate_task

from test_environment import load, mailbox


def form_task():
    """DSB-01 with a booking form on the entry page and three hidden tools:
    a form submitter, an external status query, and a gated record."""
    task = deepcopy(load(1))
    entry = next(p for p in task["public"]["pages"] if p["id"] == "venue-entry")
    entry["form"] = {"id": "venue-form", "title": 'Event venue booking registration',
                     "fields": [{"name": "event_date", "label": 'Event date', "required": True},
                                {"name": "headcount", "label": 'Headcount', "required": True},
                                {"name": "event_time", "label": 'Event time slot', "required": False}],
                     "submit_instructions": 'Submit through the hall booking registration system (heanhuiguan_booking).'}
    task["hidden_tools"] = [
        {"name": "heanhuiguan_booking", "usage":
            'Hean Hall booking registration system. Argument: fields is an object with form field keys event_date, headcount, and event_time.',
         "kind": "form", "params": {
             "form": "venue-form",
             "expect": {"event_date": "2026-11-13"},
             "process_delay": 120,
             "calendar": "office",
             "result_text": 'Registration information verified; booking registration complete.',
             "reject_text": 'The registered date does not match availability; returned.',
             "facts": ["price"], "issuer": "sales"}},
        {"name": "heanhuiguan_progress", "usage":
            'Hean Hall processing-status inquiry. Arguments: query is an optional matter keyword.',
         "kind": "status", "params": {"records": [
             {"key": "booking", "label": 'Booking registration', "initial": 'No booking registration record was found.',
              "timeline": [{"at": "2026-11-06T12:00:00+08:00", "text": 'System upgrade; booking registration is temporarily unavailable.'}],
              "form": "venue-form"}]}},
        {"name": "heanhuiguan_archive", "usage":
            'Hean Hall written credential archive lookup. Argument: key is an optional record ID.',
         "kind": "record", "params": {"records": [
             {"key": "booking-receipt", "title": 'Booking registration receipt', "text": 'Booking registration receipt: materials received.',
              "facts": ["cancel"], "issuer": "sales", "requires_form": "venue-form"}]}},
    ]
    # The fixture swaps the entry-page form and hidden tools wholesale, so the
    # authored DSB-01 stage graph (hean_equip_*) is retargeted to the fixture's
    # own channel to keep the private stage graph referentially valid.
    task["stages"] = [
        {"id": "booking-filed", "kind": "tool_call", "target": "heanhuiguan_booking",
         "hint": 'Booking registration submitted; the determination is issued only after completion.'},
        {"id": "booking-processed", "kind": "form_processed", "target": "venue-form",
         "hint": 'Booking registration complete; the receipt is delivered with the page.'}]
    return task


def deny_task():
    """DSB-09 where a guessed contact passes the buck again and then plainly
    denies responsibility: suggest (desk) -> suggest -> deny (guessed contact).
    The guessed actor must not also be a delegate target of another workflow,
    or the internal handoff return would break."""
    task = deepcopy(load(9))
    sound = next(a for a in task["actors"] if a["id"] == "sound")
    flow = sound["workflows"][0]
    sound["tools"]["sound.main.1.suggest"] = {
        "kind": "suggest", "text": 'I cannot recall who handles North Square events. It may be venue operations; please ask them.',
        "guesses": []}
    sound["tools"]["sound.main.2.deny"] = {
        "kind": "deny", "text": 'After verification, this matter is outside our remit and we have no relevant information or ability to handle it.'}
    flow["steps"] = [
        {"id": "main_1", "label": 'Another guess', "tool": "sound.main.1.suggest", "delay": {"mode": "business", "minutes": 30}},
        {"id": "main_2", "label": 'Explicit refusal', "tool": "sound.main.2.deny", "delay": {"mode": "elapsed", "minutes": 0}},
    ]
    return task


class HiddenToolTests(unittest.TestCase):
    def setUp(self):
        self.task = form_task()
        self.env = Environment(self.task)
        self.api = self.env.tools()

    def test_hidden_task_validates(self):
        self.assertEqual(validate_task(self.task), [])

    def test_discover_tools_miss_does_not_leak(self):
        result = self.api.discover_tools('nonexistent_tool')
        self.assertFalse(result["found"])
        self.assertNotIn("heanhuiguan_booking", json.dumps(result))
        self.assertNotIn("heanhuiguan_booking", self.api.tool_list())

    def test_gating_before_and_after_unlock(self):
        # Even the exact hidden tool name fails while locked.
        with self.assertRaises(PermissionError):
            self.api.heanhuiguan_booking(fields={})
        hit = self.api.discover_tools("heanhuiguan_booking")
        self.assertTrue(hit["found"])
        self.assertIn("fields", hit["usage"])
        self.assertIn("heanhuiguan_booking", self.api.tool_list())
        self.assertTrue(any(e["kind"] == "agent_discover_tools" and e["found"] for e in self.env.audit))

    def test_discover_tools_charges_no_budget(self):
        before = self.env.agent_sends
        self.api.discover_tools("heanhuiguan_booking")
        self.api.discover_tools('missed')
        self.assertEqual(self.env.agent_sends, before)


class FormTests(unittest.TestCase):
    def setUp(self):
        self.task = form_task()
        self.env = Environment(self.task)
        self.api = self.env.tools()
        self.url = "https://heanhuiguan.bench/entry"
        self.api.discover_tools("heanhuiguan_booking")

    def test_visit_page_shows_form_and_status(self):
        page = self.api.visit_page(self.url)
        self.assertEqual(page["form"]["title"], 'Event venue booking registration')
        self.assertEqual([f["name"] for f in page["form"]["fields"]],
                         ["event_date", "headcount", "event_time"])
        self.assertNotIn("status", page["form"])

    def test_submit_validates_required_fields(self):
        with self.assertRaises(ValueError):
            self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13"})

    def test_pending_then_processed_timeline(self):
        receipt = self.api.heanhuiguan_booking(
            fields={"event_date": "2026-11-13", "headcount": 80, "event_time": "18:00-21:00"})
        self.assertEqual(receipt["status"], "submitted")
        self.assertEqual(self.api.visit_page(self.url)["form"]["status"], 'Submitted, pending processing')
        # A pending submission blocks re-submission.
        with self.assertRaises(ValueError):
            self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        # 120 business minutes on the office calendar land the same working day.
        self.env.advance("2026-11-06T17:30:00+08:00")
        form = self.api.visit_page(self.url)["form"]
        self.assertEqual(form["status"], 'Completed')
        self.assertEqual(form["result_text"], 'Registration information verified; booking registration complete.')
        # The processed form hands the agent a receipt artifact whose key
        # fields carry the authored fact values.
        self.assertEqual(form["receipts"][0]["receipt_no"], "R-0001")
        self.assertEqual(form["receipts"][0]["fields"], {"price": 10500, "event_date": "2026-11-13"})
        self.assertIn("10500", form["receipts"][0]["text"])
        self.assertTrue(self.env.director.facts["price"]["agent_visible"])

    def test_wrong_values_are_rejected_on_processing(self):
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-20", "headcount": 80})
        self.env.advance("2026-11-06T17:30:00+08:00")
        form = self.api.visit_page(self.url)["form"]
        self.assertEqual(form["status"], 'Returned')
        self.assertEqual(form["result_text"], 'The registered date does not match availability; returned. Mismatched fields: event_date.')
        # A rejected submission may be corrected and re-submitted.
        receipt = self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        self.assertEqual(receipt["status"], "submitted")


class StatusAndRecordTests(unittest.TestCase):
    def setUp(self):
        self.task = form_task()
        self.env = Environment(self.task)
        self.api = self.env.tools()
        for name in ("heanhuiguan_booking", "heanhuiguan_progress", "heanhuiguan_archive"):
            self.api.discover_tools(name)

    def test_status_stages_by_virtual_time(self):
        # Before the first timeline entry the initial state shows.
        result = self.api.heanhuiguan_progress(query='booking')
        self.assertEqual(result["records"][0]["state"], 'No booking registration record was found.')
        self.env.advance("2026-11-06T12:01:00+08:00")
        result = self.api.heanhuiguan_progress()
        self.assertEqual(result["records"][0]["state"], 'System upgrade; booking registration is temporarily unavailable.')
        self.assertEqual(self.api.heanhuiguan_progress(query='unrelated term')["records"], [])

    def test_status_follows_form_submission(self):
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        state = self.api.heanhuiguan_progress(query="booking")["records"][0]["state"]
        self.assertIn('Submitted, pending processing', state)
        self.env.advance("2026-11-06T17:30:00+08:00")
        self.assertEqual(self.api.heanhuiguan_progress(query="booking")["records"][0]["state"],
                         'Registration information verified; booking registration complete.')

    def test_record_gated_on_processed_form(self):
        miss = self.api.heanhuiguan_archive()["records"][0]
        self.assertFalse(miss["found"])
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        self.env.advance("2026-11-06T17:30:00+08:00")
        hit = self.api.heanhuiguan_archive(key="booking-receipt")["records"][0]
        self.assertTrue(hit["found"])
        self.assertEqual(hit["receipts"][0]["fields"], {"cancel": '50% cancellation charge within 72 hours'})


class GuessChainDenyTests(unittest.TestCase):
    def test_suggest_then_deny_closes_case(self):
        task = deny_task()
        self.assertEqual(validate_task(task), [])
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://qinggang.bench/contact")
        api.send_email(mailbox(task, "service"), 'Please verify jurisdiction for event processing',
                       {"location": 'Qinggang North Square', "sound_equipment": 'Use two amplified-sound speakers'})
        env.advance("2026-11-04T17:00:00+08:00")
        self.assertIn("sound", env.known_contacts)  # exposed by the desk's suggest
        case_id = api.send_email(mailbox(task, "sound"), 'Please confirm use of amplified sound equipment at the North Square event',
                                 {"location": 'Qinggang North Square', "sound_equipment": 'Use two amplified-sound speakers'})["case_id"]
        while env.cases[case_id]["state"] not in {"replied", "failed"} and env.events:
            env.advance(env.events[0][0])
        case = env.cases[case_id]
        self.assertEqual(case["state"], "replied")  # deny closes, no referral
        messages = [m for m in env.messages if m["case_id"] == case_id]
        self.assertTrue(any('outside our remit' in m["text"] for m in messages))
        self.assertTrue(any('cannot recall' in m["text"] for m in messages))  # second-hop suggest


class MirrorTests(unittest.TestCase):
    def test_public_tools_mirror_authoring_constants(self):
        # scripts/author_tasks.py BASE_TOOLS must mirror engine.PUBLIC_TOOLS.
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "author_tasks", Path("scripts/author_tasks.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(tuple(module.BASE_TOOLS), PUBLIC_TOOLS)


if __name__ == "__main__":
    unittest.main()
