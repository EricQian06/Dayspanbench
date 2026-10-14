"""Regression tests for the v0.5 deterministic summary anchors.

Pinned by the DeepSeek pilot run (v05-deepseek-pilot-run1): the anchor set
must not contain internal identifiers (fact ids, form field names) or decoy
content (a distractor quote the agent may omit), and a form channel the agent
corrected after one rejection must count as accepted.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dayspanbench.scoring import anchor_tokens

UTC = ZoneInfo("UTC")


class _FakeDirector:
    def __init__(self, facts):
        self.facts = facts


class _FakeEnv:
    def __init__(self, facts, now):
        self.task = {"goals": [{"key": "audience", "accepted_facts": ["affected_list", "decoy"]}]}
        self.director = _FakeDirector(facts)
        self.now = now


class AnchorSourceTest(unittest.TestCase):
    def setUp(self):
        self.facts = {
            # graded fact: its value is an anchor source
            "affected_list": {"fact_id": "affected_list", "value": "1400, 1408, 1410, 1418 14th Street",
                              "agent_visible": True, "text": "prose mentioning 2019 stale GIS and 1501 U Street"},
            # decoy fact outside the graded goals: never anchored
            "price_ref": {"fact_id": "price_ref", "value": 9600, "agent_visible": True,
                          "text": "breakdown 8200 plus 1400"},
            # graded but expired: skipped
            "decoy": {"fact_id": "decoy", "value": 999, "agent_visible": True, "valid_until": "2027-01-01T00:00:00+00:00"},
        }
        self.env = _FakeEnv(self.facts, datetime(2027, 6, 11, 10, 0, tzinfo=UTC))

    def test_anchor_set_uses_graded_fact_values_only(self):
        tokens = set(anchor_tokens(self.env))
        self.assertEqual(tokens, {"1400", "1408", "1410", "1418", "14th"})

    def test_internal_identifiers_and_decoys_are_absent(self):
        tokens = set(anchor_tokens(self.env))
        for banned in ("affected_list", "price_ref", "9600", "8200", "1400元", "2019", "1501", "999"):
            self.assertNotIn(banned, tokens)

    def test_invisible_facts_are_skipped(self):
        self.facts["affected_list"]["agent_visible"] = False
        self.assertEqual(anchor_tokens(self.env), {})


if __name__ == "__main__":
    unittest.main()
