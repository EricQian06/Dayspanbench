# -*- coding: utf-8 -*-
"""Behavior probes for DSB-09/10/11 (skill checklist section 6)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.reference import run_reference
from dayspanbench.engine import Environment

def load(tid):
    return json.loads((ROOT / "tasks/private" / f"{tid}.json").read_text(encoding="utf-8"))

def mailbox(task, who):
    return next(a["contact_details"]["email"] for a in task["actors"] if a["id"] == who)

def drain(env, api, deadline):
    """wait_until loop until clock hits deadline (wake on messages, keep going)."""
    while env.now < env.deadline:
        api.wait_until(env.deadline, wake_on_message=True)

def discover(api, task, page_id):
    page = next(p for p in task["public"]["pages"] if p["id"] == page_id)
    api.visit_page(page["url"])


def discover_sound(api, task, env):
    """service desk round-trip to obtain sound's contact."""
    discover(api, task, "service")
    api.send_email(mailbox(task, "service"), "请核实活动办理管辖", dict(task["public"]["user_fields"]))
    while "sound" not in api._env.known_contacts and api._env.now < api._env.deadline:
        api.wait_until(api._env.deadline, wake_on_message=True)

def probe09():
    task = load("DSB-09")
    # A. day-1 premature mail to the FINAL workflow (no receipt yet)
    env = Environment(task); api = env.tools()
    discover_sound(api, task, env)
    api.send_email(mailbox(task, "sound"), "请按回执进行联合复核和最终分类", dict(task["public"]["user_fields"]))
    drain(env, api, None)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    print("09A premature-final:", c["state"], "| msgs:", [str(m)[:90] for m in env.messages])
    assert c["state"] == "needs_information", "premature final should ask for receipt"
    assert not any(ev["agent_visible"] and ev["fact_id"] == "consultation_receipt" for ev in env.evidence.values())
    # B. day-1 consultation mail -> ack with ETA, receipt issued only at 12-03
    env = Environment(task); api = env.tools()
    r = discover_sound(api, task, env)
    api.send_email(mailbox(task, "sound"), "请确认本轮扩声意见征集及回执", dict(task["public"]["user_fields"]))
    api.wait_until("2026-12-02T23:00:00+08:00", wake_on_message=True)
    visible = [ev for ev in env.evidence.values() if ev["agent_visible"]]
    print("09B visible evidence before 12-03:", [(e["fact_id"], e["id"]) for e in visible])
    assert not any(e["fact_id"] == "consultation_receipt" for e in visible), "receipt must not appear before 12-03"
    drain(env, api, None)
    visible = [ev for ev in env.evidence.values() if ev["agent_visible"]]
    print("09B visible evidence after 12-03:", [(e["fact_id"], e["id"]) for e in visible])
    assert any(e["fact_id"] == "consultation_receipt" for e in visible), "receipt should be issued at 12-03"
    # C. late final filing at deadline day 16:00 -> cannot finish
    env = Environment(task); api = env.tools()
    discover_sound(api, task, env)
    api.wait_until("2026-12-29T16:00:00+08:00", wake_on_message=False)
    api.send_email(mailbox(task, "sound"), "请按回执进行联合复核和最终分类",
                   {**task["public"]["user_fields"], "consultation_receipt": "CONSULT-DEC03-19"})
    drain(env, api, None)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    print("09C late-final state:", c["state"], "now:", env.now)
    assert c["state"] != "replied", "filing at deadline-day 16:00 must not complete"

def probe10():
    task = load("DSB-10")
    # A. missing serial -> needs_information listing serial
    env = Environment(task); api = env.tools()
    discover(api, task, "camera"); api.send_email(mailbox(task, "seller"), "请核实相机快门热靴及实测条件", {"serial": ""})
    drain(env, api, None)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    print("10A missing-serial:", c["state"])
    assert c["state"] == "needs_information"
    # B. Saturday-morning first contact (seller evening-only) -> does it still finish?
    env = Environment(task); api = env.tools()
    api.wait_until("2026-11-07T09:00:00+08:00", wake_on_message=False)
    discover(api, task, "camera"); api.send_email(mailbox(task, "seller"), "请核实相机快门热靴及实测条件", dict(task["public"]["user_fields"]))
    drain(env, api, None)
    done = [c for c in env.cases.values() if c["state"] == "replied" and not c.get("parent")]
    got_actual = any(ev["agent_visible"] and ev["fact_id"] == "actual" for ev in env.evidence.values())
    print("10B Sat-morning filing: replied-root:", len(done), "actual-visible:", got_actual, "now:", env.now)
    # C. Monday morning first contact -> friend weekend-only: must miss
    env = Environment(task); api = env.tools()
    api.wait_until("2026-11-09T08:00:00+08:00", wake_on_message=False)
    discover(api, task, "camera"); api.send_email(mailbox(task, "seller"), "请核实相机快门热靴及实测条件", dict(task["public"]["user_fields"]))
    drain(env, api, None)
    got_actual = any(ev["agent_visible"] and ev["fact_id"] == "actual" for ev in env.evidence.values())
    print("10C Mon-morning filing: actual-visible:", got_actual, "now:", env.now)
    assert not got_actual, "Monday-morning filing must miss the friend's weekend window"

def probe11():
    task = load("DSB-11")
    # A. premature release_check before accept_after -> early_reply registration, no case queue
    env = Environment(task); api = env.tools()
    discover(api, task, "repo"); api.send_email(mailbox(task, "maintainer"), "请转交核实季度发布的候选版与稳定版状态",
                   {"version": "1.4.1", "verified_commit": "commit-7bc2"})
    api.wait_until("2026-11-09T21:00:00+08:00", wake_on_message=True)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    kinds = [a["kind"] for a in env.audit]
    print("11A premature state:", c["state"], "early_reply audited:", "early_reply" in kinds,
          "| queue-empty:", c["state"] == "replied")
    assert "early_reply" in kinds and c["state"] == "replied"
    # B. inside window, fabricated commit (no evidence) -> needs_information credential bucket
    env = Environment(task); api = env.tools()
    api.wait_until("2027-01-27T20:30:00+08:00", wake_on_message=False)
    discover(api, task, "repo"); api.send_email(mailbox(task, "maintainer"), "请转交核实季度发布的候选版与稳定版状态",
                   {"version": "1.4.1", "verified_commit": "commit-7bc2"})
    drain(env, api, None)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    print("11B fabricated-credential state:", c["state"], "|", [str(m)[:90] for m in env.messages][:1])
    assert c["state"] == "needs_information"
    # C. after accept_before -> failed
    env = Environment(task); api = env.tools()
    api.wait_until("2027-02-24T20:30:00+08:00", wake_on_message=False)
    discover(api, task, "repo"); api.send_email(mailbox(task, "maintainer"), "请转交核实季度发布的候选版与稳定版状态",
                   {"version": "1.4.1", "verified_commit": "commit-7bc2"})
    drain(env, api, None)
    c = sorted(env.cases.values(), key=lambda c: c["id"])[-1]
    print("11C late filing state:", c["state"])
    assert c["state"] == "failed"

if __name__ == "__main__":
    probe09(); print("---"); probe10(); print("---"); probe11(); print("ALL BEHAVIOR PROBES PASSED")
