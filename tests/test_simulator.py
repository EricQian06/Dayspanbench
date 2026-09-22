from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from dayspanbench.calendar import parse
from dayspanbench.engine import Environment
from dayspanbench.llm import LLMConfig, StructuredClient, SimulatorError
from dayspanbench.recipient import RuleRecipient
from dayspanbench.reference import run_reference
from dayspanbench.simulator import LLMSimulator
from scripts.serve import main as serve

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / f"tasks/private/DSB-{n:02}.json").read_text(encoding="utf-8"))


def mailbox(task, actor_id):
    return next(a["contact_details"]["email"] for a in task["actors"] if a["id"] == actor_id)


class FixtureClient:
    def __init__(self, route=None, reply=None):
        self.route_override, self.reply_override = route, reply
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        view = kwargs["view"]
        if kwargs["purpose"] == "route":
            if self.route_override:
                return self.route_override(view)
            return {"workflow_id": view.get("existing_workflow_id") or RuleRecipient().choose(view), "fields": []}
        if self.reply_override:
            return self.reply_override(view)
        return {"tone": "polite", "evidence_order": [e["id"] for e in reversed(view["evidence"])]}


def recipients(task, client):
    return {a["id"]: LLMSimulator(client, a["id"]) for a in task["actors"]}


class CharacterSimulatorTests(unittest.TestCase):
    def test_validation_retry_repairs_without_admitting_unsupported_fields(self):
        task = load(3)
        attempts = []
        def route(view):
            attempts.append(deepcopy(view))
            if len(attempts) == 1:
                return {"workflow_id": "main", "fields": [{"key": "syllabus_version", "value_json": "null", "source_quote": ""}]}
            return {"workflow_id": "main", "fields": []}
        client = FixtureClient(route=route)
        mapping = {a["id"]: LLMSimulator(client, a["id"], validation_retries=2) for a in task["actors"]}
        env = Environment(task, mapping)
        env.tools().visit_page("faculty")
        result = env.tools().send_email(mailbox(task, "records"), "请咨询学分转换。", {"course_code": "CS204"})
        self.assertEqual(env.agent_sends, 1)
        env.advance(parse("2026-11-05T18:00:00+08:00"))
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        self.assertEqual(len(attempts), 2)
        self.assertIn("validation_feedback", attempts[1])
        self.assertNotIn("validation_feedback", attempts[0])
        self.assertFalse(env.simulator_failure)

    def test_validation_retries_are_bounded_and_do_not_retry_transport_errors(self):
        view = {"actor_id": "test", "message": "test", "fields": {}, "history": [],
                "workflows": [{"id": "main", "required_fields": []}], "existing_workflow_id": None}
        client = FixtureClient(route=lambda _: {"workflow_id": "invented", "fields": []})
        with self.assertRaises(SimulatorError):
            LLMSimulator(client, "test", validation_retries=2).route(view)
        self.assertEqual(len(client.calls), 3)
        class Broken:
            calls = []
            def complete(self, **kwargs):
                self.calls.append(kwargs)
                raise SimulatorError("Simulator HTTP failure (401)")
        broken = Broken()
        with self.assertRaises(SimulatorError):
            LLMSimulator(broken, "test", validation_retries=2).route(view)
        self.assertEqual(len(broken.calls), 1)

    def test_exact_explicit_field_echo_is_not_a_new_extraction(self):
        for number, actor, fields in ((1, "reception", {"event_date": "2026-11-13", "headcount": 80}),
                                     (2, "landlord", {"pet_weight": "8kg", "move_date": "2026-11-12"})):
            with self.subTest(task=number):
                task = load(number)
                echoed = [{"key": key, "value_json": json.dumps(value), "source_quote": str(value)} for key, value in fields.items()]
                client = FixtureClient(route=lambda _: {"workflow_id": "main", "fields": echoed})
                env = Environment(task, recipients(task, client))
                api = env.tools()
                if number == 1:
                    api.visit_page("venue")
                result = api.send_email(mailbox(task, actor), "请提供办理信息。", fields)
                self.assertEqual(result["status"], "received")
                self.assertFalse(env.simulator_failure)

    def test_conflicting_explicit_field_echo_still_invalidates_simulator(self):
        task = load(2)
        client = FixtureClient(route=lambda _: {"workflow_id": "main", "fields": [
            {"key": "pet_weight", "value_json": '"6kg"', "source_quote": "6kg"}]})
        env = Environment(task, recipients(task, client))
        with self.assertRaises(SimulatorError):
            env.tools().send_email(mailbox(task, "landlord"), "6kg", {"pet_weight": "8kg", "move_date": "2026-11-12"})

    def test_all_twelve_references_with_model_shaped_outputs(self):
        for n in range(1, 13):
            task, client = load(n), FixtureClient()
            with self.subTest(task=n):
                env, _, result = run_reference(task, recipient=recipients(task, client))
                self.assertTrue(result["complete"])
                window = (parse(task["deadline_at"]) - parse(task["start_at"])).total_seconds() / 3600
                self.assertLessEqual(result["calendar_hours"], window)
                self.assertTrue(any(c["purpose"] == "reply" for c in client.calls))
                self.assertEqual(len({id(a.recipient) for a in env.actors.values()}), len(task["actors"]))
                for call in client.calls:
                    view = call["view"]
                    self.assertFalse({"facts", "goals", "expected_conclusion", "reference_actions", "calendars"} & set(view))
                    self.assertEqual(view["actor_id"], call["actor_id"])

    def test_natural_language_field_extraction_and_missing_material_followup(self):
        task = load(6)
        def route(view):
            fields = []
            for key, value in (("serial", "SN-A731"), ("receipt", "R-731")):
                if value in view["message"]:
                    fields.append({"key": key, "value_json": json.dumps(value), "source_quote": value})
            return {"workflow_id": "main", "fields": fields}
        client = FixtureClient(route=route)
        env = Environment(task, recipients(task, client))
        api = env.tools()
        api.visit_page("service")
        first = api.send_email(mailbox(task, "support"), "请咨询保修")
        env.advance(parse("2026-11-04T17:00:00+08:00"))
        self.assertEqual(env.cases[first["case_id"]]["state"], "needs_information")
        api.send_email(mailbox(task, "support"), "序列号SN-A731，收据R-731。", case_id=first["case_id"])
        # Advance past the deferred admission but before the first step completes.
        env.advance(parse("2026-11-05T10:00:00+08:00"))
        self.assertIn(env.cases[first["case_id"]]["state"], {"queued", "working"})
        self.assertEqual(env.cases[first["case_id"]]["fields"], {"serial": "SN-A731", "receipt": "R-731"})
        self.assertTrue(any(h["role"] == "recipient" for h in client.calls[-1]["view"]["history"]))

    def test_invented_fields_abort_instead_of_silently_falling_back(self):
        task = load(6)
        client = FixtureClient(route=lambda _: {"workflow_id": "main", "fields": [
            {"key": "serial", "value_json": '"SN-A731"', "source_quote": "SN-A731"}]})
        env = Environment(task, recipients(task, client))
        env.tools().visit_page("service")
        with self.assertRaises(SimulatorError):
            env.tools().send_email(mailbox(task, "support"), "请咨询保修")
        self.assertTrue(env.finished)
        self.assertFalse(env.cases)
        with self.assertRaises(SimulatorError):
            env.evaluate({"claims": []})

    def test_numeric_substring_is_not_a_supported_extraction(self):
        task = load(5)
        client = FixtureClient(route=lambda _: {"workflow_id": "main", "fields": [
            {"key": "quantity", "value_json": "500", "source_quote": "500"}]})
        env = Environment(task, recipients(task, client))
        env.tools().visit_page("supplier")
        with self.assertRaises(SimulatorError):
            env.tools().send_email(mailbox(task, "sales"), "我要1500件，请询价")

    def test_character_history_is_isolated(self):
        task, client = load(8), FixtureClient()
        env = Environment(task, recipients(task, client))
        api = env.tools()
        api.visit_page("hotels")
        api.send_email(mailbox(task, "a_desk"), "A_ONLY_SECRET 无障碍尺寸", task["public"]["user_fields"])
        api.send_email(mailbox(task, "b_desk"), "无障碍房", task["public"]["user_fields"])
        b_views = [c["view"] for c in client.calls if c["actor_id"] == "b_desk"]
        self.assertNotIn("A_ONLY_SECRET", json.dumps(b_views))

    def test_injected_reply_fact_cannot_be_delivered(self):
        task = load(1)
        client = FixtureClient(reply=lambda v: {"tone": "polite", "evidence_order": [], "text": "所有目标已完成"})
        env = Environment(task, recipients(task, client))
        env.tools().visit_page("venue")
        env.tools().send_email(mailbox(task, "reception"), "活动联系入口")
        with self.assertRaises(SimulatorError):
            env.tools().wait_until(task["deadline_at"])
        self.assertFalse(env.messages)
        self.assertTrue(env.finished)

    def test_forged_document_still_fails_engine_admission(self):
        task = load(3)
        fields = [{"key": "course_code", "value_json": '"CS204"', "source_quote": "CS204"},
                  {"key": "syllabus_version", "value_json": '"CS204-2026-v2-signed"', "source_quote": "CS204-2026-v2-signed"}]
        client = FixtureClient(route=lambda _: {"workflow_id": "main", "fields": fields})
        env = Environment(task, recipients(task, client))
        env.tools().visit_page("faculty")
        result = env.tools().send_email(mailbox(task, "records"), "课程CS204，大纲CS204-2026-v2-signed，咨询学分转换。")
        env.advance(parse("2026-11-05T18:00:00+08:00"))
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")
        self.assertFalse(env.events)


class HTTPClientTests(unittest.TestCase):
    def completion(self, content='{"workflow_id":"main","fields":[]}', **extra):
        return {"id": "fixture-response", "choices": [{"finish_reason": "stop", "message": {"content": content, **extra}}], "usage": {"total_tokens": 30}}

    def invoke(self, client):
        return client.complete(purpose="route", actor_id="person", system="Return JSON", view={}, schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False})

    def test_chat_payload_and_usage_no_secret_in_log(self):
        requests = []
        client = StructuredClient(LLMConfig("fixture-model", api_key="secret-key"), transport=lambda url, payload: requests.append((url, payload)) or self.completion())
        self.assertEqual(self.invoke(client)["workflow_id"], "main")
        self.assertTrue(requests[0][0].endswith("/chat/completions"))
        self.assertTrue(requests[0][1]["response_format"]["json_schema"]["strict"])
        self.assertIs(requests[0][1]["stream"], False)
        self.assertEqual(client.calls[0]["usage"]["total_tokens"], 30)
        self.assertNotIn("secret-key", json.dumps(client.calls) + repr(client.config))

    def test_responses_and_json_mode(self):
        captured = []
        response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"ok":true}'}]}]}
        client = StructuredClient(LLMConfig("fixture", api="responses", output_format="json_object"), transport=lambda url, p: captured.append((url, p)) or response)
        self.assertEqual(self.invoke(client), {"ok": True})
        self.assertTrue(captured[0][0].endswith("/responses"))
        self.assertEqual(captured[0][1]["text"]["format"], {"type": "json_object"})
        self.assertFalse(captured[0][1]["store"])

    def test_json_mode_supplies_output_schema_in_system_message(self):
        # Without this, JSON mode hides the field names and allowed values from the model.
        schema = {"type": "object", "properties": {"tone": {"type": "string", "enum": ["polite"]}},
                  "required": ["tone"], "additionalProperties": False}
        for api in ("chat", "responses"):
            with self.subTest(api=api):
                captured = []
                content = '{"tone":"polite"}'
                response = self.completion(content) if api == "chat" else {
                    "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": content}]}]}
                client = StructuredClient(LLMConfig("fixture", api=api, output_format="json_object"),
                    transport=lambda url, payload: captured.append(payload) or response)
                result = client.complete(purpose="reply", actor_id="person", system="Choose a tone.", view={}, schema=schema)
                self.assertEqual(result, {"tone": "polite"})
                messages = captured[0]["messages" if api == "chat" else "input"]
                self.assertEqual(messages[0]["role"], "system")
                self.assertIn("Choose a tone.", messages[0]["content"])
                self.assertIn(json.dumps(schema), messages[0]["content"])
                self.assertEqual(messages[1], {"role": "user", "content": "{}"})

    def test_full_episode_through_http_protocol_adapter(self):
        fixture = FixtureClient()
        def transport(url, payload):
            name = payload["response_format"]["json_schema"]["name"]
            view = json.loads(payload["messages"][1]["content"])
            response = fixture.complete(purpose=name.removeprefix("simulator_"), actor_id=view["actor_id"], view=view)
            return self.completion(json.dumps(response, ensure_ascii=False))
        client = StructuredClient(LLMConfig("fixture-model"), transport=transport)
        task = load(12)
        env, _, result = run_reference(task, recipient=recipients(task, client))
        self.assertTrue(result["bounded_handling_success"])
        self.assertEqual(result["calendar_days"], 300)
        self.assertGreater(len(client.calls), 5)
        self.assertFalse(env.simulator_failure)

    def test_actual_http_request_construction(self):
        body = json.dumps(self.completion()).encode()
        class Response(io.BytesIO):
            pass
        with patch("dayspanbench.llm.build_opener") as opener:
            opener.return_value.open.return_value = Response(body)
            client = StructuredClient(LLMConfig("fixture", api_key="private-key"))
            self.invoke(client)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer private-key")
            self.assertEqual(request.method, "POST")
            self.assertEqual(json.loads(request.data)["model"], "fixture")

    def test_retryable_failure_and_auth_error(self):
        attempts, sleeps = [], []
        def transient(*_):
            attempts.append(1)
            if len(attempts) == 1:
                raise HTTPError("https://fixture", 429, "rate limited", {}, None)
            return self.completion()
        client = StructuredClient(LLMConfig("fixture"), transport=transient, sleep=sleeps.append)
        self.invoke(client)
        self.assertEqual(client.calls[0]["attempts"], 2)
        self.assertEqual(sleeps, [1])
        def unauthorized(*_):
            raise HTTPError("https://fixture", 401, "private provider detail", {}, None)
        client = StructuredClient(LLMConfig("fixture"), transport=unauthorized)
        with self.assertRaisesRegex(SimulatorError, "401"):
            self.invoke(client)
        self.assertEqual(client.calls[0]["attempts"], 1)

    def test_refusal_truncation_and_bad_json_fail(self):
        examples = [self.completion(refusal="No"), self.completion("not JSON"), {"choices": []}]
        truncated = self.completion()
        truncated["choices"][0]["finish_reason"] = "length"
        examples.append(truncated)
        for response in examples:
            with self.subTest(response=response):
                client = StructuredClient(LLMConfig("fixture"), transport=lambda *_: response)
                with self.assertRaises(SimulatorError):
                    self.invoke(client)

    def test_transport_failure_is_bounded(self):
        def down(*_):
            raise URLError("do not expose transport secrets")
        client = StructuredClient(LLMConfig("fixture", max_retries=1), transport=down, sleep=lambda _: None)
        with self.assertRaises(SimulatorError):
            self.invoke(client)
        self.assertEqual(client.calls[0]["attempts"], 2)
        self.assertNotIn("transport secrets", client.calls[0]["error"])


class ServerIntegrationTests(unittest.TestCase):
    def test_llm_startup_announces_readiness_without_calling_provider(self):
        with patch.dict(os.environ, {"DSB_SIMULATOR_API_KEY": "test-secret"}), patch("scripts.serve.StructuredClient") as factory, patch("sys.stdin", io.StringIO("")), patch("sys.stdout", new_callable=io.StringIO) as output, patch("sys.stderr", new_callable=io.StringIO) as diagnostic:
            client = factory.return_value
            client.config.public_dict.return_value = {"model": "fixture"}
            client.calls = []
            self.assertEqual(serve(["--task", "DSB-12", "--simulator", "llm", "--simulator-model", "fixture"]), 0)
            client.complete.assert_not_called()
            self.assertEqual(output.getvalue(), "")
            self.assertIn("环境已就绪", diagnostic.getvalue())
            self.assertIn("等待stdin", diagnostic.getvalue())
            self.assertNotIn("test-secret", diagnostic.getvalue())

    def test_quiet_mode_preserves_clean_jsonl(self):
        request = json.dumps({"id": 1, "tool": "recall_task", "arguments": {}})
        completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-12", "--quiet"],
            input=request + "\n", text=True, encoding="utf-8", capture_output=True, cwd=ROOT, check=True)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout)["result"]["task"]["id"], "DSB-12")

    def test_blank_lines_are_ignored_without_rpc_or_audit_errors(self):
        request = json.dumps({"id": 1, "tool": "recall_task", "arguments": {}})
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-12", "--run-dir", folder],
                input="\n \t\r\n" + request + "\n\n", text=True, encoding="utf-8", capture_output=True, cwd=ROOT, check=True)
            responses = [json.loads(line) for line in completed.stdout.splitlines()]
            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0]["id"], 1)
            self.assertEqual(responses[0]["result"]["task"]["id"], "DSB-12")
            self.assertEqual(len((Path(folder) / "rpc_trace.jsonl").read_text(encoding="utf-8").splitlines()), 1)
            self.assertEqual((Path(folder) / "private_audit.jsonl").read_text(encoding="utf-8"), "")

    def test_bad_json_has_input_hint_and_next_request_still_works(self):
        request = json.dumps({"id": 2, "tool": "observe", "arguments": {}})
        completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-12"],
            input="\nnot-json\n" + request + "\n", text=True, encoding="utf-8", capture_output=True, cwd=ROOT, check=True)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 2)
        error = responses[0]["error"]
        self.assertEqual(error["type"], "JSONDecodeError")
        self.assertEqual(error["line"], 2)
        self.assertIn("JSONL", error["hint"])
        self.assertIn('"tool":"observe"', error["hint"])
        self.assertEqual(responses[1]["id"], 2)
        self.assertIn("result", responses[1])

    def test_cli_logs_real_rpc_and_score_separately_from_reference(self):
        _, answer, _ = run_reference(load(1))
        # Replay its public requests to the persistent rule server.
        task = load(1)
        requests = []
        for action in task["reference_actions"]:
            if action["op"] == "visit_page":
                requests.append({"tool": "visit_page", "arguments": {"page_id": action["page"]}})
            elif action["op"] == "send":
                requests.append({"tool": "send_email", "arguments": {"recipient": mailbox(task, action["to"]), "text": action["text"], "fields": task["public"]["user_fields"]}})
            elif action["op"] == "wait_for":
                requests.append({"tool": "wait_until", "arguments": {"until": task["deadline_at"]}})
        requests.append({"tool": "submit_answer", "arguments": {"answer": answer}})
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run([sys.executable, "scripts/serve.py", "--task", "DSB-01", "--run-dir", folder],
                input="\n".join(json.dumps({"id": i, **r}) for i, r in enumerate(requests)), text=True, encoding="utf-8", capture_output=True, cwd=ROOT)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((Path(folder) / "result.json").read_text(encoding="utf-8"))
            self.assertTrue(result["valid_episode"])
            self.assertTrue(result["complete"])
            self.assertTrue((Path(folder) / "rpc_trace.jsonl").is_file())
            self.assertTrue((Path(folder) / "private_audit.jsonl").is_file())

    def test_llm_cli_environment_error_is_not_a_model_score(self):
        request = (json.dumps({"id": 1, "tool": "visit_page", "arguments": {"page_id": "venue"}}) + "\n"
                   + json.dumps({"id": 2, "tool": "send_email", "arguments": {"recipient": mailbox(load(1), "reception"), "text": "活动"}}) + "\n")
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"DSB_SIMULATOR_API_KEY": "test-secret"}), patch("scripts.serve.StructuredClient") as factory, patch("sys.stdin", io.StringIO(request)), patch("sys.stdout", new_callable=io.StringIO) as output:
            client = factory.return_value
            client.config.public_dict.return_value = {"model": "fixture"}
            client.calls = []
            client.complete.side_effect = SimulatorError("Simulator refused")
            code = serve(["--task", "DSB-01", "--simulator", "llm", "--simulator-model", "fixture", "--run-dir", folder])
            self.assertEqual(code, 2)
            response = json.loads(output.getvalue().splitlines()[-1])
            self.assertTrue(response["error"]["terminal"])
            result = json.loads((Path(folder) / "result.json").read_text(encoding="utf-8"))
            self.assertFalse(result["valid_episode"])
            self.assertNotIn("complete", result)
            self.assertNotIn("test-secret", (Path(folder) / "manifest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
