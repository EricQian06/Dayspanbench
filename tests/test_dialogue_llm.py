"""v0.5 milestone 2: dialogue-mode LLM hidden tools and the LLM letter render.

The engine injects canonical facts; the model only contributes wording.
Key tokens (numbers, letter+digit ids, quoted names) must survive verbatim,
with one repair retry and then SimulatorError (invalid episode, not a
failed one). Keyword dialogue and the rule recipient stay untouched.
"""

from copy import deepcopy
import unittest

from dayspanbench.engine import Environment
from dayspanbench.llm import SimulatorError, key_tokens, missing_key_tokens
from dayspanbench.simulator import LLMSimulator

from test_environment import load, mailbox
from test_simulator import FixtureClient


def dialogue_task(mode="llm"):
    task = deepcopy(load(1))
    task["hidden_tools"] = [{
        "name": "ask_user",
        "usage": "Ask the comms lead a question. Argument: {\"question\": text}.",
        "kind": "dialogue",
        "params": {
            "persona": "Keisha Brown (communications lead)",
            "dialogue_mode": mode,
            "rules": [
                {"keywords": ["budget", "spend"],
                 "answer": "The budget cap is 247.80 USD for print run JOB441."},
                {"keywords": ["deadline", "truck"],
                 "answer": "The corrected hangers leave the yard with the 06:00 truck."},
            ],
            "default": "Nothing to add; ask me about the budget or the deadline."}}]
    return task


def llm_env(task, client):
    recipients = {a["id"]: LLMSimulator(client, a["id"]) for a in task["actors"]}
    return Environment(task, recipients)


class KeyTokenTests(unittest.TestCase):
    def test_numbers_ids_and_quoted_names_are_anchors(self):
        text = 'The cap is 247.80 USD for run JOB441 at "1501 U Street", 06:00.'
        self.assertIn("247.80", key_tokens(text))
        self.assertIn("JOB441", key_tokens(text))
        self.assertIn("1501", key_tokens(text))
        self.assertIn("06", key_tokens(text))
        self.assertIn("1501 U Street", key_tokens(text))
        # Pure words are wording, not facts.
        self.assertNotIn("cap", key_tokens(text))

    def test_missing_tokens_respect_boundaries(self):
        tokens = ["247.80", "JOB441"]
        self.assertEqual(missing_key_tokens("The cap is 247.80 for JOB441.", tokens), [])
        # A nearby but different number/id does not satisfy the anchor.
        self.assertEqual(missing_key_tokens("The cap is 247.8 for JOB442.", tokens),
                         ["247.80", "JOB441"])
        # 441 hiding inside JOB4410 is not JOB441's own presence.
        self.assertIn("JOB441", missing_key_tokens("see JOB4410", ["JOB441"]))
        self.assertEqual(missing_key_tokens(None, tokens), tokens)


class DialogueLLMTests(unittest.TestCase):
    def test_llm_mode_rephrases_with_injected_canonical_fact_and_history(self):
        task, client = dialogue_task(), FixtureClient()
        env = llm_env(task, client)
        api = env.tools()
        api.discover_tools("ask_user")
        first = api.ask_user(question="What is the budget?")
        # The FixtureClient echoes the canonical fact; the engine injected it.
        self.assertEqual(first["answer"], "The budget cap is 247.80 USD for print run JOB441.")
        self.assertEqual(first["speaker"], "Keisha Brown (communications lead)")
        view = client.calls[0]["view"]
        self.assertEqual(view["persona"], "Keisha Brown (communications lead)")
        self.assertEqual(view["canonical_fact"], first["answer"])
        self.assertTrue(view["matched_topic"])
        self.assertEqual(view["prior_dialogue"], [])
        self.assertIn("stage_hint", view)  # no authored stages -> None hint
        # Second question sees the first exchange as prior dialogue.
        second = api.ask_user(question="And the deadline?")
        self.assertEqual(second["answer"], "The corrected hangers leave the yard with the 06:00 truck.")
        view2 = client.calls[1]["view"]
        self.assertEqual(len(view2["prior_dialogue"]), 1)
        self.assertEqual(view2["prior_dialogue"][0]["question"], "What is the budget?")
        # The audit records the delivered answer.
        self.assertTrue(any(r["kind"] == "agent_dialogue" and r["answer"] == second["answer"]
                            for r in env.audit))

    def test_token_loss_retries_once_then_succeeds(self):
        answers = [{"answer": "Sure, the budget is about 250 dollars."},
                   {"answer": "As I said, the budget cap is 247.80 USD for print run JOB441."}]
        client = FixtureClient(dialogue=lambda view: answers.pop(0))
        env = llm_env(dialogue_task(), client)
        api = env.tools()
        api.discover_tools("ask_user")
        result = api.ask_user(question="budget?")
        self.assertIn("247.80", result["answer"])
        dialogue_calls = [c for c in client.calls if c["purpose"] == "dialogue"]
        self.assertEqual(len(dialogue_calls), 2)
        self.assertIn("validation_feedback", dialogue_calls[1]["view"])
        self.assertIn("247.80", dialogue_calls[1]["view"]["validation_feedback"]["error"])
        self.assertFalse(env.simulator_failure)

    def test_persistent_token_loss_invalidates_the_episode(self):
        client = FixtureClient(dialogue=lambda view: {"answer": "No idea, sorry."})
        env = llm_env(dialogue_task(), client)
        api = env.tools()
        api.discover_tools("ask_user")
        with self.assertRaises(SimulatorError):
            api.ask_user(question="budget?")
        self.assertTrue(env.simulator_failure)
        self.assertTrue(env.finished)
        self.assertTrue(any(r["kind"] == "simulator_failure" for r in env.audit))
        self.assertEqual(len([c for c in client.calls if c["purpose"] == "dialogue"]), 2)

    def test_keyword_mode_without_llm_simulator_stays_deterministic(self):
        env = Environment(dialogue_task())  # rule recipients: no client
        api = env.tools()
        api.discover_tools("ask_user")
        result = api.ask_user(question="What is the budget cap?")
        self.assertEqual(result["answer"], "The budget cap is 247.80 USD for print run JOB441.")
        result = api.ask_user(question="What color tablecloth?")
        self.assertEqual(result["answer"], "Nothing to add; ask me about the budget or the deadline.")

    def test_authored_llm_mode_falls_back_to_keywords_without_a_client(self):
        # dialogue_mode="llm" but the episode runs rule-based (replay/validate):
        # the authored keyword answer is used verbatim, no LLM is contacted.
        env = Environment(dialogue_task(mode="llm"))
        api = env.tools()
        api.discover_tools("ask_user")
        result = api.ask_user(question="budget?")
        self.assertEqual(result["answer"], "The budget cap is 247.80 USD for print run JOB441.")


class RenderLLMTests(unittest.TestCase):
    def reply_view(self):
        return {"actor_id": "test", "name": "测试联系人", "role": "信息查询",
                "persona": "耐心且正式的窗口职员",
                "status": "reply",
                "canonical_text": "您咨询的事项已经核实，具体情况如下：回执号R-0001已登记。",
                "case_id": "CASE-0001", "case_state": "replied", "now": "2026-11-06T09:00:00+08:00",
                "history": [{"role": "agent", "text": "请核实回执", "fields": {}, "case_id": None,
                             "at": "2026-11-06T08:00:00+08:00"}],
                "stage_hint": None,
                "contacts": [{"id": "ops", "name": "运营部",
                              "contact_details": {"email": "ops@heanhuiguan.bench"}}],
                "facts": [{"id": "f1", "text": "活动总价10500元，须在11月13日前付清。",
                           "value": 10500, "issuer": "reception", "valid_until": None}],
                "receipts": [{"receipt_no": "R-0001", "title": "核实回执",
                              "text": "回执号R-0001，总额247.80 USD。",
                              "fields": {}, "issuer": "reception",
                              "issued_at": "2026-11-06T09:00:00+08:00"}]}

    def test_reply_letter_is_model_written_and_tokens_survive(self):
        def letter(view):
            return {"tone": "polite",
                    "text": "您好，我是测试联系人。核实结果：活动总价10500元，"
                            "须在11月13日前付清；回执号R-0001，总额247.80 USD。"
                            "另请联系运营部（ops@heanhuiguan.bench）。"}
        client = FixtureClient(reply=letter)
        text = LLMSimulator(client, "test").render(self.reply_view())
        self.assertIn("10500", text)
        self.assertIn("247.80", text)
        self.assertIn("ops@heanhuiguan.bench", text)
        self.assertEqual(len(client.calls), 1)
        view = client.calls[0]["view"]
        self.assertEqual(view["persona"], "耐心且正式的窗口职员")

    def test_render_retries_once_on_token_loss_then_fails_invalid(self):
        answers = [{"tone": "polite", "text": "全部办好了，请查收。"},
                   {"tone": "polite", "text": "活动总价10500元，须在11月13日前付清；"
                                              "回执号R-0001，总额247.80 USD；"
                                              "请联系运营部（ops@heanhuiguan.bench）。"}]
        client = FixtureClient(reply=lambda view: answers.pop(0))
        text = LLMSimulator(client, "test").render(self.reply_view())
        self.assertIn("247.80", text)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("validation_feedback", client.calls[1]["view"])
        # Persistently losing the anchors is a SimulatorError, never a score.
        stubborn = FixtureClient(reply=lambda view: {"tone": "polite", "text": "办好了。"})
        with self.assertRaises(SimulatorError):
            LLMSimulator(stubborn, "test").render(self.reply_view())
        self.assertEqual(len([c for c in stubborn.calls]), 2)

    def test_non_reply_status_is_deterministic_passthrough(self):
        client = FixtureClient()
        view = self.reply_view()
        view["status"] = "needs_information"
        view["canonical_text"] = "您提交的材料尚不完整，请补充以下信息：编号。"
        text = LLMSimulator(client, "test").render(view)
        self.assertEqual(text, view["canonical_text"])
        self.assertEqual(client.calls, [])  # no model call for acceptance semantics


if __name__ == "__main__":
    unittest.main()
