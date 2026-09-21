from copy import deepcopy
import json
from pathlib import Path
import unittest

from dayspanbench.reference import run_reference
from dayspanbench.scoring import equivalent
from dayspanbench.validation import validate_task

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / f"tasks/private/DSB-{n:02}.json").read_text())


class OutcomeScoringTests(unittest.TestCase):
    def test_semantic_alias_and_false_promise(self):
        env, answer, _ = run_reference(load(11))
        claim = next(c for c in answer["claims"] if c["key"] == "stable_release_date")
        for phrase in ("尚未承诺正式稳定版发布日期", "暂无承诺日期"):
            claim["value"] = phrase
            self.assertTrue(env.evaluate(answer)["complete"])
        claim["value"] = "下周一定发布稳定版"
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_quantities_units_and_wrong_dimensions(self):
        env, answer, _ = run_reference(load(8))
        for claim in answer["claims"]:
            if type(claim["value"]) is int:
                claim["value"] = {"value": claim["value"] / 100, "unit": "m"} if claim["value"] < 100 else "2,360 CNY"
        self.assertTrue(env.evaluate(answer)["complete"])
        answer["claims"][0]["value"] = {"value": 72, "unit": "kg"}
        self.assertFalse(env.evaluate(answer)["complete"])
        self.assertFalse(equivalent(True, 1, {"type": "number"}))
        self.assertFalse(equivalent("NaN", 0, {"type": "number"}))
        self.assertFalse(equivalent("1,2", 12, {"type": "number"}))

    def test_calendar_dates_timezones_and_ambiguous_time(self):
        env, answer, _ = run_reference(load(5))
        next(c for c in answer["claims"] if c["key"] == "earliest_dispatch")["value"] = "2026年12月9日"
        self.assertTrue(env.evaluate(answer)["complete"])
        self.assertTrue(equivalent("2026-11-18T02:00:00Z", "2026-11-18T10:00:00+08:00", {"type": "datetime"}))
        self.assertFalse(equivalent("2026-11-18T10:00:00", "2026-11-18T10:00:00+08:00", {"type": "datetime"}))

    def test_materials_are_sets_but_omissions_fail(self):
        env, answer, _ = run_reference(load(9))
        claim = next(c for c in answer["claims"] if isinstance(c.get("value"), list))
        claim["value"].reverse()
        self.assertTrue(env.evaluate(answer)["complete"])
        claim["value"].pop()
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_order_and_channel_do_not_define_success(self):
        task = load(8)
        actions = task["reference_actions"]
        actions[1], actions[2] = actions[2], actions[1]
        for action in actions:
            if action["op"] == "send":
                action["channel"] = "chat"
        env, answer, result = run_reference(task)
        self.assertTrue(result["complete"])
        answer["claims"].reverse()
        self.assertTrue(env.evaluate(answer)["complete"])

    def test_new_fact_identifier_from_authorized_source(self):
        task = load(7)
        task["facts"]["alternate_permission"] = deepcopy(task["facts"]["exhibit"])
        rights = next(a for a in task["actors"] if a["id"] == "rights")
        rights["knowledge"].append("alternate_permission")
        for tool in rights["tools"].values():
            if "facts" in tool:
                tool["facts"] = ["alternate_permission" if f == "exhibit" else f for f in tool["facts"]]
        for action in task["reference_actions"]:
            if isinstance(action.get("fields"), dict):
                for key, value in action["fields"].items():
                    if value == "$fact:exhibit":
                        action["fields"][key] = "$fact:alternate_permission"
        self.assertEqual(validate_task(task), [])
        env, answer, _ = run_reference(task)
        claim = next(c for c in answer["claims"] if c["key"] == "physical_exhibit_allowed")
        claim["evidence_ids"] = [e["id"] for e in env.evidence.values() if e["fact_id"] == "alternate_permission" and e["agent_visible"]]
        self.assertTrue(env.evaluate(answer)["complete"])
        for ev_id in claim["evidence_ids"]:
            env.evidence[ev_id]["authorities"] = []
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_wrong_subject_and_unobserved_proof_fail(self):
        env, answer, _ = run_reference(load(1))
        evs = [env.evidence[e] for e in answer["claims"][0]["evidence_ids"]]
        for ev in evs:
            ev["attributes"]["subject"] = {"task": "different_event"}
        self.assertFalse(env.evaluate(answer)["complete"])
        env, answer, _ = run_reference(load(1))
        for e in answer["claims"][0]["evidence_ids"]:
            env.evidence[e]["agent_visible"] = False
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_dsb12_real_direct_contact_path(self):
        task = load(12)
        last = deepcopy(task["reference_actions"][-2])
        referral = {**last, "text": "请核验材料并转介境外代理直联", "label": "direct_referral"}
        direct = {**last, "to": "broker", "text": "请按完整材料进行长期复核", "label": "direct_review"}
        task["reference_actions"][-2:] = [referral, {"op": "wait_for", "label": "direct_referral"}, direct, {"op": "wait_for", "label": "direct_review"}]
        env, _, result = run_reference(task)
        self.assertTrue(result["bounded_handling_success"])
        self.assertTrue(any(c["actor"] == "broker" and c["parent"] is None and "technical_review" in c["workflow"].get("capabilities", []) for c in env.cases.values()))
        self.assertFalse(any(c["actor"] == "customsdesk" and c["workflow"]["id"] == "final" for c in env.cases.values()))

    def test_renamed_internal_actor_and_additional_relay(self):
        task = load(12)
        desk = next(a for a in task["actors"] if a["id"] == "customsdesk")
        final = next(w for w in desk["workflows"] if w["id"] == "final")
        relay = deepcopy(final)
        relay["id"] = "relay"
        relay["steps"] = deepcopy(final["steps"])
        # Different tools keep the new workflow graph acyclic.
        tool_id = "relay.delegate"
        desk["tools"][tool_id] = deepcopy(desk["tools"][final["steps"][0]["tool"]])
        relay["steps"][0]["tool"] = tool_id
        desk["workflows"].append(relay)
        desk["tools"][final["steps"][0]["tool"]].update(target="customsdesk", workflow="relay")
        broker = next(a for a in task["actors"] if a["id"] == "broker")
        broker["id"] = "technical_team"
        for actor in task["actors"]:
            for tool in actor["tools"].values():
                if tool.get("target") == "broker":
                    tool["target"] = "technical_team"
                if "contacts" in tool:
                    tool["contacts"] = ["technical_team" if c == "broker" else c for c in tool["contacts"]]
        self.assertEqual(validate_task(task), [])
        env, _, result = run_reference(task)
        self.assertTrue(result["complete"])
        self.assertTrue(any(c["actor"] == "technical_team" for c in env.cases.values()))

    def test_renewed_document_identifier_is_grounded_in_actual_evidence(self):
        task = load(12)
        task["facts"]["declaration_latest"]["value"] = "DEC-608-v4"
        task["facts"]["declaration_latest"]["text"] = "实际签发的有效新版单证为DEC-608-v4。"
        env, answer, _ = run_reference(task)
        claim = next(c for c in answer["claims"] if c["key"] == "declaration_version")
        self.assertFalse(env.evaluate(answer)["complete"])
        claim["value"] = "DEC-608-v4"
        self.assertTrue(env.evaluate(answer)["complete"])
        claim["value"] = "DEC-608-v999"
        self.assertFalse(env.evaluate(answer)["complete"])

    def test_public_normalizers_do_not_disclose_private_alias_answers(self):
        public = load(11)["public"]["value_normalization"]
        self.assertNotIn("尚无承诺日期", json.dumps(public, ensure_ascii=False))
        self.assertNotIn("aliases", public["stable_release_date"])

    def test_unconfirmed_status_cannot_hide_a_contradictory_assertion(self):
        env, answer, _ = run_reference(load(12))
        claim = next(c for c in answer["claims"] if c["key"] == "release_status")
        claim["value"] = "已经放行"
        result = env.evaluate(answer)
        self.assertFalse(result["complete"])
        self.assertFalse(result["answer_schema_valid"])

    def test_malformed_answers_are_failures_not_crashes(self):
        env, _, _ = run_reference(load(1))
        for answer in (None, [], {"claims": None}, {"claims": [{"key": []}]}, {"claims": [{"key": "total_cost", "status": {}, "evidence_ids": {}}]}):
            with self.subTest(answer=answer):
                self.assertFalse(env.evaluate(answer)["complete"])


if __name__ == "__main__":
    unittest.main()
