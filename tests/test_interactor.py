"""Interactor: reply delays, consent gate, persona answers, ask_user tool."""

from copy import deepcopy
import json
import unittest
from pathlib import Path

from dayspanbench.calendar import parse, stamp
from dayspanbench.engine import Environment
from dayspanbench.interactor import UserInteractor
from dayspanbench.llm import SimulatorError

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / f"tasks/private/DSB-{n:02}.json").read_text(encoding="utf-8"))


class FixtureClient:
    def __init__(self, behavior=None):
        self.behavior = behavior or {}
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        handler = self.behavior.get(kwargs["purpose"])
        if handler is None:
            raise SimulatorError("Simulator transport failure or timeout")
        return handler(kwargs["view"])


SPEC = {
    "persona": "Alex Chen, a first-year undergraduate; friendly, a bit scatterbrained.",
    "speaker": "Alex Chen",
    "timezone": "Asia/Shanghai",
    "reply_delay": {"min_minutes": 10, "max_minutes": 180,
                    "quiet_start": "02:00", "quiet_end": "08:00"},
    "consent_policy": [
        {"action": "send_email", "when": "always", "approve": False,
         "say": "Please don't send that without asking me what to write."},
        {"approve": True, "say": "Go ahead."},
    ],
    "rules": [
        {"keywords": ["available", "evening", "wednesday"],
         "answer": "Except Wednesday evening I am free all week: 9.21, 9.24 and 9.25."},
    ],
    "default": "I don't have anything to add about that.",
    "profile": ["Wednesday evening has a standing rehearsal."],
}


class ReplyDelayTests(unittest.TestCase):
    def test_delay_is_seeded_and_bounded(self):
        base = parse("2026-09-11T12:00:00+08:00")
        one, two = UserInteractor(SPEC, seed=7), UserInteractor(SPEC, seed=7)
        first = one.reply_at(base)
        self.assertEqual(first, two.reply_at(base))
        self.assertGreaterEqual(first, base)
        self.assertLessEqual(first, base.replace(hour=15, minute=0))

    def test_quiet_window_shifts_past_8am(self):
        it = UserInteractor(SPEC, seed=0)
        base = parse("2026-09-12T01:50:00+08:00")
        at = it.reply_at(base)
        local = at.astimezone(it.zone)
        # Anything drawn into 02:00-08:00 lands after 08:00 with remainder kept.
        self.assertGreaterEqual(local.hour, 8)
        self.assertLessEqual(local.hour, 9)


class ConsentTests(unittest.TestCase):
    def test_policy_consent_without_client(self):
        it = UserInteractor(SPEC)
        outcome = it.consent("send_email", {"recipient": "x"}, parse("2026-09-11T12:00:00+08:00"))
        self.assertFalse(outcome["approve"])
        self.assertIn("asking me", outcome["say"])
        outcome = it.consent("hidden_form", {"tool": "join"}, parse("2026-09-11T12:00:00+08:00"))
        self.assertTrue(outcome["approve"])

    def test_llm_consent_and_fallback(self):
        client = FixtureClient({"consent": lambda view: {"approve": True, "say": "Sure."}})
        it = UserInteractor(SPEC, client=client)
        outcome = it.consent("send_email", {}, parse("2026-09-11T12:00:00+08:00"))
        self.assertTrue(outcome["approve"])
        self.assertEqual(outcome["say"], "Sure.")
        # An invalid or failing LLM consent never silently approves.
        broken = FixtureClient()  # every purpose raises
        it2 = UserInteractor(SPEC, client=broken)
        outcome = it2.consent("send_email", {}, parse("2026-09-11T12:00:00+08:00"))
        self.assertFalse(outcome["approve"])

    def test_gate_blocks_send_email(self):
        task = load(1)
        env = Environment(task)
        env.attach_interactor(UserInteractor(SPEC))
        api = env.tools()
        outcome = api.send_email("someone@bench", "hello")
        self.assertEqual(outcome["status"], "refused")
        kinds = {entry["kind"] for entry in env.audit}
        self.assertIn("agent_action_consent", kinds)


class AnswerTests(unittest.TestCase):
    def test_keyword_rule_grounds_answer(self):
        it = UserInteractor(SPEC)
        outcome = it.answer("Which evenings are you available?", parse("2026-09-11T12:00:00+08:00"))
        self.assertIn("9.21", outcome["answer"])
        self.assertIn("Wednesday", outcome["answer"])

    def test_llm_rephrase_keeps_key_tokens(self):
        def answer(view):
            if "validation_feedback" in view:
                return {"answer": view["canonical_fact"]}
            return {"answer": "Basically I'm free most weeknights except the one with rehearsal."}
        client = FixtureClient({"interactor": answer})
        it = UserInteractor(SPEC, client=client)
        outcome = it.answer("Which evenings are you available?", parse("2026-09-11T12:00:00+08:00"))
        # Key tokens lost on the first pass, repaired on the second.
        self.assertIn("9.21", outcome["answer"])

    def test_llm_failure_falls_back_to_canonical(self):
        client = FixtureClient()
        it = UserInteractor(SPEC, client=client)
        outcome = it.answer("Which evenings are you available?", parse("2026-09-11T12:00:00+08:00"))
        self.assertIn("9.21", outcome["answer"])


class AskUserToolTests(unittest.TestCase):
    def test_ask_user_advances_clock_and_logs_reply(self):
        task = load(1)
        task["public"]["tools"] = list(task["public"].get("tools") or []) + ["consult_user"]
        env = Environment(task)
        env.attach_interactor(UserInteractor(SPEC, seed=3))
        api = env.tools()
        self.assertIn("consult_user", api.tool_list())
        outcome = api.consult_user("Which evenings are you available?")
        self.assertLessEqual(parse(outcome["at"]), env.now)
        self.assertTrue(any(m["from"] == "user" for m in env.messages))
        kinds = [entry["kind"] for entry in env.audit]
        self.assertIn("agent_ask_user", kinds)
        self.assertIn("user_reply", kinds)

    def test_ask_user_undeclared_is_permission_error(self):
        task = load(1)
        env = Environment(task)
        env.attach_interactor(UserInteractor(SPEC))
        with self.assertRaises(PermissionError):
            env.tools().consult_user("anything")

    def test_no_interactor_is_permission_error(self):
        task = load(1)
        task["public"]["tools"] = list(task["public"].get("tools") or []) + ["consult_user"]
        env = Environment(task)
        with self.assertRaises(PermissionError):
            env.tools().consult_user("anything")


if __name__ == "__main__":
    unittest.main()
