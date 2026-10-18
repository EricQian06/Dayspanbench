"""The active case exports and their reference conversations use English."""

import json
from pathlib import Path
import re
import unittest

from dayspanbench.engine import DIALOGUE_PROMPT
from dayspanbench.evaluation import AGENT_PROMPT
from dayspanbench.reference import run_reference
from dayspanbench.simulator import REPLY_PROMPT, ROUTE_PROMPT

ROOT = Path(__file__).resolve().parents[1]
HAN = re.compile(r"[\u3400-\u9fff]")


class EnglishExportTests(unittest.TestCase):
    def test_all_active_exports_and_tool_descriptions_are_english(self):
        paths = [*sorted((ROOT / "tasks").rglob("*.json")), ROOT / "docs/agent-tools.json"]
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsNone(HAN.search(json.dumps(data, ensure_ascii=False)))

    def test_shared_model_prompts_are_english(self):
        for prompt in (DIALOGUE_PROMPT, AGENT_PROMPT, REPLY_PROMPT, ROUTE_PROMPT):
            self.assertIsNone(HAN.search(prompt))

    def test_reference_conversations_and_receipts_are_english(self):
        for path in sorted((ROOT / "tasks/private").glob("*.json")):
            with self.subTest(task=path.stem):
                env, answer, result = run_reference(json.loads(path.read_text(encoding="utf-8")))
                self.assertTrue(result["complete"], result)
                self.assertIsNone(HAN.search(json.dumps([env.messages, answer], ensure_ascii=False)))


if __name__ == "__main__":
    unittest.main()
