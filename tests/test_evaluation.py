from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from dayspanbench.evaluation import (ChatAgent, AgentAPIError, load_env_file, parse_action,
    run_episode, summarize, render_report)
from dayspanbench.llm import LLMConfig, SimulatorError
from dayspanbench.reference import run_reference

ROOT = Path(__file__).resolve().parents[1]
TOOLS = json.loads((ROOT / "docs/agent-tools.json").read_text(encoding="utf-8"))
DEFINITIONS = {t["name"]: t for t in TOOLS}


def task():
    return json.loads((ROOT / "tasks/private/DSB-01.json").read_text(encoding="utf-8"))


def mailbox(spec, actor_id):
    return next(a["contact_details"]["email"] for a in spec["actors"] if a["id"] == actor_id)


class ScriptedAgent(ChatAgent):
    """Author-generated test actions, never used in real evaluation."""
    def __init__(self, actions):
        self.actions = iter(actions)
        super().__init__(LLMConfig("test-only", api_key="secret-never-log"), transport=self.respond)

    def respond(self, url, payload):
        content = next(self.actions)
        if not isinstance(content, str):
            content = json.dumps(content)
        return {"model": "test-only", "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class EvaluationTests(unittest.TestCase):
    def test_complete_episode_submits_once_without_score_feedback_or_private_input(self):
        spec = task()
        _, answer, _ = run_reference(spec)
        spec["private_test_sentinel"] = "HIDDEN_SENTINEL"
        actions = []
        for action in spec["reference_actions"]:
            if action["op"] == "visit_page":
                url = next(p["url"] for p in spec["public"]["pages"] if p["id"] == action["page"])
                actions.append({"tool": "visit_page", "arguments": {"url": url}})
            elif action["op"] == "send":
                actions.append({"tool": "send_email", "arguments": {"recipient": mailbox(spec, action["to"]), "text": action["text"], "fields": spec["public"]["user_fields"]}})
            elif action["op"] == "wait_for":
                actions.append({"tool": "wait_until", "arguments": {"until": spec["deadline_at"]}})
            elif action["op"] == "advance":
                actions.append({"tool": "wait_until", "arguments": {"until": action["at"]}})
            elif action["op"] == "discover":
                actions.append({"tool": "discover_tools", "arguments": {"name": action["name"]}})
            elif action["op"] == "tool":
                # $fact placeholders quote material the privileged witness
                # already holds; the scripted agent substitutes the fact value.
                def resolve(value):
                    if isinstance(value, str) and value.startswith("$fact:"):
                        return spec["facts"][value.split(":", 1)[1]]["value"]
                    if isinstance(value, dict):
                        return {key: resolve(item) for key, item in value.items()}
                    return value
                actions.append({"tool": action["name"], "arguments": resolve(action.get("args", {}))})
        # Mid-workflow acknowledgement receipts now add extra inbox messages;
        # extra waits absorb them so submission happens after the final reply
        # (each wait_until wakes on the next message or on the deadline).
        for _ in range(4):
            actions.append({"tool": "wait_until", "arguments": {"until": spec["deadline_at"]}})
        actions.append({"tool": "submit_answer", "arguments": {"answer": answer}})
        agent = ScriptedAgent(actions)
        with tempfile.TemporaryDirectory() as folder:
            result = run_episode(spec, agent, TOOLS, Path(folder) / "DSB-01")
            self.assertTrue(result["complete"])
            self.assertTrue(result["submitted"])
            self.assertEqual(result["agent_steps"], len(actions))
            text = json.dumps([c["request"] for c in agent.calls])
            for forbidden in ("HIDDEN_SENTINEL", '"expected_conclusion"', '"reference_actions"', '"goal_results"', "secret-never-log"):
                self.assertNotIn(forbidden, text)
            self.assertNotIn("secret-never-log", (Path(folder) / "DSB-01/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["agent_usage"]["total_tokens"], len(actions) * 15)

    def test_invalid_action_can_recover_but_budget_exhaustion_is_valid_failure(self):
        agent = ScriptedAgent(["not JSON", {"tool": "observe", "arguments": {}}])
        with tempfile.TemporaryDirectory() as folder:
            result = run_episode(task(), agent, TOOLS, Path(folder) / "run", max_steps=2)
        self.assertTrue(result["valid_episode"])
        self.assertFalse(result["complete"])
        self.assertFalse(result["submitted"])
        self.assertEqual(result["termination"], "step_limit")
        self.assertEqual(result["action_errors"], 1)
        self.assertIn("Return one JSON object", agent.calls[1]["request"]["messages"][-1]["content"])

    def test_provider_error_is_invalid_and_not_zero_score(self):
        agent = ScriptedAgent([])
        def failure(_):
            raise AgentAPIError("Agent HTTP failure (401)")
        agent.next_action = failure
        with tempfile.TemporaryDirectory() as folder:
            result = run_episode(task(), agent, TOOLS, Path(folder) / "run")
        self.assertFalse(result["valid_episode"])
        self.assertEqual(result["termination"], "agent_api_error")
        self.assertNotIn("complete", result)

    def test_simulator_error_is_invalid(self):
        class BrokenSimulator:
            calls = []
            config = LLMConfig("broken")
            def complete(self, **kwargs):
                raise SimulatorError("Simulator HTTP failure (400)")
        agent = ScriptedAgent([{"tool": "visit_page", "arguments": {"url": "https://heanhuiguan.bench/contact"}},
                               {"tool": "send_email", "arguments": {"recipient": mailbox(task(), "reception"), "text": "活动"}}])
        with tempfile.TemporaryDirectory() as folder:
            result = run_episode(task(), agent, TOOLS, Path(folder) / "run", simulator_client=BrokenSimulator())
        self.assertFalse(result["valid_episode"])
        self.assertEqual(result["termination"], "simulator_error")

    def test_public_tool_schema_rejects_invalid_types_and_unexposed_access(self):
        cases = [("__getattribute__", {"name": "_env"}), ("read_inbox", {"after": -1}),
                 ("wait_until", {"until": 42}), ("send_email", {"recipient": [], "text": "x"}),
                 ("observe", {"private": True}), ("read_inbox", {"after": True})]
        for name, arguments in cases:
            with self.subTest(name=name, arguments=arguments), self.assertRaises(ValueError):
                parse_action(json.dumps({"tool": name, "arguments": arguments}), DEFINITIONS)

    def test_environment_file_is_data_and_existing_values_win(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("# config\nDSB_SIMULATOR_API_KEY='local-secret'\nDSB_AGENT_API_KEY=$(not-executed)\n")
            environ = {"DSB_SIMULATOR_API_KEY": "existing-secret"}
            load_env_file(path, environ)
        self.assertEqual(environ["DSB_SIMULATOR_API_KEY"], "existing-secret")
        self.assertEqual(environ["DSB_AGENT_API_KEY"], "$(not-executed)")

    def test_invalid_episodes_excluded_and_completion_classes_separate(self):
        base = {"valid_episode": True, "completion_class": "resolved", "resolved_success": True,
                "bounded_handling_success": False, "required_fact_coverage": 1}
        rows = [{**base, "task_id": "DSB-01"}, {"task_id": "DSB-02", "valid_episode": False},
                {**base, "task_id": "DSB-12", "completion_class": "bounded_unresolved", "resolved_success": False, "bounded_handling_success": False}]
        summary = summarize(rows, ["DSB-01", "DSB-02", "DSB-12"])
        self.assertEqual(summary["valid_episodes"], 2)
        self.assertEqual(summary["invalid_episodes"], 1)
        self.assertEqual(summary["resolved"]["rate"], 1)
        self.assertEqual(summary["bounded_unresolved"]["rate"], 0)

    def test_ordinary_chat_and_token_parameter_are_explicit(self):
        captured = []
        for parameter in ("max_tokens", "max_completion_tokens", "omit"):
            agent = ChatAgent(LLMConfig("exact-user-model", max_tokens=123), token_parameter=parameter,
                transport=lambda url, payload: captured.append((url, payload)) or {
                    "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
            agent.next_action([{"role": "user", "content": "test"}])
            url, payload = captured[-1]
            self.assertEqual(payload["model"], "exact-user-model")
            self.assertFalse(payload["stream"])
            self.assertNotIn("response_format", payload)
            self.assertTrue(url.endswith("/chat/completions"))
            if parameter != "omit":
                self.assertEqual(payload[parameter], 123)
            else:
                self.assertNotIn("max_tokens", payload)
                self.assertNotIn("max_completion_tokens", payload)


if __name__ == "__main__":
    unittest.main()
