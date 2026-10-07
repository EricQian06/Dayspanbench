"""The recipient-side comprehension layer for credential-backed fields.

An applicant conveys a credential in human ways: quoting the confirmation
letter, citing its evidence id, or restating its substance in prose. Admission
must understand all of these while still refusing fabrication — prose without
an issued, agent-visible attestation behind it never admits.
"""

import unittest

from dayspanbench.comprehension import understood_evidence
from dayspanbench.engine import Environment

from tests.test_environment import load, mailbox


def drain(env):
    """Advance the event queue to exhaustion (bounded by the deadline)."""
    while env.events:
        env.advance(env.events[0][0])


def obtain_rights_confirmation(task, env, api):
    """Walk the DSB-07 front desk -> rights holder path until the
    physical/online permission attestations are in the agent's inbox."""
    api.visit_page("https://beiting.bench/contact")
    api.send_email(mailbox(task, "archive"), "咨询档案费用与权利联系人",
                   {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"})
    drain(env)
    api.send_email(mailbox(task, "rights"), "请确认ARC-71两种用途的权利授权",
                   {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"})
    drain(env)
    visible = [ev for m in env.messages for ev in m["evidence"]
               if ev["id"].startswith("EV-")]
    return {ev["id"]: ev for ev in visible}


class ComprehensionUnitTests(unittest.TestCase):
    def setUp(self):
        self.task = load(7)
        self.env = Environment(self.task)
        self.api = self.env.tools()
        self.evidence = obtain_rights_confirmation(self.task, self.env, self.api)
        self.requirement = next(
            w["evidence_fields"]["exhibition_permission"]
            for a in self.task["actors"] if a["id"] == "archive"
            for w in a["workflows"] if w["id"] == "digitize")
        self.exhibit_ids = [eid for eid, ev in self.evidence.items()
                            if ev["value"] is True]
        self.assertTrue(self.exhibit_ids)

    def check(self, field_value, correspondence=()):
        return understood_evidence(field_value, list(correspondence),
                                   self.requirement, self.env.evidence, self.env.now)

    def test_strict_boolean_still_admits(self):
        self.assertTrue(self.check(True))

    def test_quoted_confirmation_text_admits(self):
        # The exact failure of the recorded gpt-5.4 episode: the rights
        # holder's written confirmation restated as prose.
        self.assertTrue(self.check(
            "图像ARC-71获准用于本次非商业实体展览，并授权展览网站、社交媒体公开发布"))

    def test_evidence_id_citation_admits(self):
        self.assertTrue(self.check("已获权利方书面确认", ["随信附上确认结论：" + self.exhibit_ids[0]]))

    def test_prose_restatement_admits(self):
        self.assertTrue(self.check("权利方已确认：实体展览用途获准"))

    def test_opposite_polarity_does_not_admit(self):
        self.assertFalse(self.check("实体展览用途未获准"))

    def test_claim_without_evidence_anchor_does_not_admit(self):
        # Same prose, but no issued evidence exists at all (fresh environment).
        fresh = Environment(load(7))
        requirement = self.requirement
        self.assertEqual(understood_evidence("权利方已确认：实体展览用途获准", [],
                                             requirement, fresh.evidence, fresh.now), [])


class ComprehensionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.task = load(7)
        self.env = Environment(self.task)
        self.api = self.env.tools()
        obtain_rights_confirmation(self.task, self.env, self.api)

    def test_digitize_admits_on_quoted_confirmation(self):
        # Replay the recorded gpt-5.4 field value: the digitize workflow must
        # be admitted and eventually deliver the scan specification.
        result = self.api.send_email(
            mailbox(self.task, "archive"),
            "权利方已确认ARC-71用于本次非商业实体展览，现申请数字化交付并确认扫描规格。",
            {"archive_id": "ARC-71",
             "exhibition_permission": "图像ARC-71获准用于本次非商业实体展览，并授权展览网站、社交媒体公开发布"})
        drain(self.env)
        case = self.env.cases[result["case_id"]]
        self.assertNotEqual(case["state"], "needs_information")
        self.assertTrue(any(e["kind"] == "material_understood" for e in self.env.audit))
        drain(self.env)
        reply = next(m for m in self.env.messages if m["case_id"] == result["case_id"]
                     and m["status"] == "reply")
        self.assertTrue(any(ev["value"] == 600 for ev in reply["evidence"]))

    def test_digitize_bounces_without_confirmation(self):
        # No rights confirmation has been obtained: the prose claim has no
        # issued attestation behind it and must still bounce.
        task = load(7)
        env = Environment(task)
        api = env.tools()
        api.visit_page("https://beiting.bench/contact")
        result = api.send_email(
            mailbox(task, "archive"), "申请数字化交付并确认扫描规格",
            {"archive_id": "ARC-71", "exhibition_permission": "实体展览用途获准"})
        drain(env)
        self.assertEqual(env.cases[result["case_id"]]["state"], "needs_information")


if __name__ == "__main__":
    unittest.main()
