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
    entry["form"] = {"id": "venue-form", "title": "活动场地预约登记",
                     "fields": [{"name": "event_date", "label": "活动日期", "required": True},
                                {"name": "headcount", "label": "人数", "required": True},
                                {"name": "event_time", "label": "活动时段", "required": False}],
                     "submit_instructions": "请通过会馆预约登记系统（heanhuiguan_booking）提交。"}
    task["hidden_tools"] = [
        {"name": "heanhuiguan_booking", "usage":
            "禾岸会馆预约登记系统。调用参数：fields为对象，键为表单字段名（event_date、headcount、event_time）。",
         "kind": "form", "params": {
             "form": "venue-form",
             "expect": {"event_date": "2026-11-13"},
             "process_delay": 120,
             "calendar": "office",
             "result_text": "登记信息已核对无误，预约登记完成。",
             "reject_text": "登记日期与档期安排不符，已退回。",
             "facts": ["price"], "issuer": "sales"}},
        {"name": "heanhuiguan_progress", "usage":
            "禾岸会馆办理进度查询。调用参数：query为事项关键词（可省略）。",
         "kind": "status", "params": {"records": [
             {"key": "booking", "label": "预约登记", "initial": "尚未查询到预约登记记录。",
              "timeline": [{"at": "2026-11-06T12:00:00+08:00", "text": "系统升级，预约登记暂时不可用。"}],
              "form": "venue-form"}]}},
        {"name": "heanhuiguan_archive", "usage":
            "禾岸会馆书面凭证档案查询。调用参数：key为记录编号（可省略）。",
         "kind": "record", "params": {"records": [
             {"key": "booking-receipt", "title": "预约登记回执", "text": "预约登记回执：材料已核收。",
              "facts": ["cancel"], "issuer": "sales", "requires_form": "venue-form"}]}},
    ]
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
        "kind": "suggest", "text": "北广场的活动我记不清归谁管，可能是场馆运营那边，您再问问。",
        "guesses": []}
    sound["tools"]["sound.main.2.deny"] = {
        "kind": "deny", "text": "经核实，该事项不归我处管理，我处也没有相关信息，无法为您办理。"}
    flow["steps"] = [
        {"id": "main_1", "label": "再次猜测", "tool": "sound.main.1.suggest", "delay": {"mode": "business", "minutes": 30}},
        {"id": "main_2", "label": "明确回绝", "tool": "sound.main.2.deny", "delay": {"mode": "elapsed", "minutes": 0}},
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
        result = self.api.discover_tools("不存在的工具")
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
        self.api.discover_tools("错过")
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
        self.assertEqual(page["form"]["title"], "活动场地预约登记")
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
        self.assertEqual(self.api.visit_page(self.url)["form"]["status"], "已提交，待处理")
        # A pending submission blocks re-submission.
        with self.assertRaises(ValueError):
            self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        # 120 business minutes on the office calendar land the same working day.
        self.api.wait_until("2026-11-06T17:30:00+08:00", wake_on_message=False)
        form = self.api.visit_page(self.url)["form"]
        self.assertEqual(form["status"], "已办结")
        self.assertEqual(form["result_text"], "登记信息已核对无误，预约登记完成。")
        self.assertEqual(form["evidence"][0]["value"], 10500)
        self.assertTrue(self.env.evidence[form["evidence"][0]["id"]]["agent_visible"])

    def test_wrong_values_are_rejected_on_processing(self):
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-20", "headcount": 80})
        self.api.wait_until("2026-11-06T17:30:00+08:00", wake_on_message=False)
        form = self.api.visit_page(self.url)["form"]
        self.assertEqual(form["status"], "已退回")
        self.assertEqual(form["result_text"], "登记日期与档期安排不符，已退回。 不符合的字段：event_date。")
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
        result = self.api.heanhuiguan_progress(query="预约")
        self.assertEqual(result["records"][0]["state"], "尚未查询到预约登记记录。")
        self.api.wait_until("2026-11-06T12:01:00+08:00", wake_on_message=False)
        result = self.api.heanhuiguan_progress()
        self.assertEqual(result["records"][0]["state"], "系统升级，预约登记暂时不可用。")
        self.assertEqual(self.api.heanhuiguan_progress(query="无关词")["records"], [])

    def test_status_follows_form_submission(self):
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        state = self.api.heanhuiguan_progress(query="booking")["records"][0]["state"]
        self.assertIn("已提交，待处理", state)
        self.api.wait_until("2026-11-06T17:30:00+08:00", wake_on_message=False)
        self.assertEqual(self.api.heanhuiguan_progress(query="booking")["records"][0]["state"],
                         "登记信息已核对无误，预约登记完成。")

    def test_record_gated_on_processed_form(self):
        miss = self.api.heanhuiguan_archive()["records"][0]
        self.assertFalse(miss["found"])
        self.api.heanhuiguan_booking(fields={"event_date": "2026-11-13", "headcount": 80})
        self.api.wait_until("2026-11-06T17:30:00+08:00", wake_on_message=False)
        hit = self.api.heanhuiguan_archive(key="booking-receipt")["records"][0]
        self.assertTrue(hit["found"])
        self.assertEqual(hit["evidence"][0]["value"], "72小时内取消收取50%")


class GuessChainDenyTests(unittest.TestCase):
    def test_suggest_then_deny_closes_case(self):
        task = deny_task()
        self.assertEqual(validate_task(task), [])
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://qinggang.bench/contact")
        api.send_email(mailbox(task, "service"), "请核实活动办理管辖",
                       {"location": "晴港北广场", "sound_equipment": "使用两只扩声音箱"})
        api.wait_until("2026-11-04T17:00:00+08:00", wake_on_message=False)
        self.assertIn("sound", env.known_contacts)  # exposed by the desk's suggest
        case_id = api.send_email(mailbox(task, "sound"), "请确认北广场活动扩声设备的使用",
                                 {"location": "晴港北广场", "sound_equipment": "使用两只扩声音箱"})["case_id"]
        while env.cases[case_id]["state"] not in {"replied", "failed"} and env.events:
            env.advance(env.events[0][0])
        case = env.cases[case_id]
        self.assertEqual(case["state"], "replied")  # deny closes, no referral
        messages = [m for m in env.messages if m["case_id"] == case_id]
        self.assertTrue(any("不归我处管理" in m["text"] for m in messages))
        self.assertTrue(any("记不清" in m["text"] for m in messages))  # second-hop suggest


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
