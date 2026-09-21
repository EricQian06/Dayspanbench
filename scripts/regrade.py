"""Offline scoring errata: verify original traces before applying declared aliases.

No model/API calls, no author reference policy, no new evidence or agent answers.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.engine import Environment
from dayspanbench.evaluation import summarize, render_report, write_json
from dayspanbench.simulator import LLMSimulator


class RecordedSimulator:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def complete(self, *, purpose, actor_id, system, view, schema):
        row = deepcopy(self.rows[len(self.calls)])
        if row.get("error"):
            raise ValueError("A valid replay cannot contain a failed simulator API call")
        assert row["purpose"] == purpose and row["actor_id"] == actor_id, "Simulator call order drift"
        key = "messages" if "messages" in row["request"] else "input"
        assert json.loads(row["request"][key][1]["content"]) == view, "Simulator context drift"
        self.calls.append(row)
        return deepcopy(row["response"])


def regrade_episode(directory, erratum):
    original = json.loads((directory / "result.json").read_text())
    if not original["valid_episode"]:
        return original, False
    manifest = json.loads((directory / "manifest.json").read_text())
    task = json.loads((directory.parent / "task_snapshot" / (original["task_id"] + ".json")).read_text())
    assert hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest() == manifest["task_sha256"]
    recorded = RecordedSimulator([json.loads(x) for x in (directory / "simulator_calls.jsonl").read_text().splitlines()])
    recipients = None if manifest["simulator"] == "rule" else {
        a["id"]: LLMSimulator(recorded, a["id"], history_limit=manifest["history_limit"],
            validation_retries=manifest.get("simulator_validation_retries", 0)) for a in task["actors"]}
    env = Environment(task, recipients)
    api = env.tools()
    final_grade = None
    for line in (directory / "rpc_trace.jsonl").read_text().splitlines():
        row = json.loads(line)
        action = row["request"]
        if action is None:
            assert "error" in row["response"]
            continue
        try:
            value = getattr(api, action["tool"])(**action["arguments"])
            response = {"result": value}
        except (ValueError, KeyError, TypeError, PermissionError, StopIteration) as error:
            response = {"error": {"type": type(error).__name__, "message": str(error)}}
        assert response == row["response"], f"Tool replay drift at step {row['step']}"
        if action["tool"] == "submit_answer":
            final_grade = value
    assert len(recorded.calls) == len(recorded.rows), "Unconsumed simulator calls"
    answer_path = directory / "final_answer.json"
    answer = json.loads(answer_path.read_text()) if answer_path.exists() else {}
    final_grade = final_grade or env.evaluate(answer)
    assert all(original[k] == v for k, v in final_grade.items()), "Original grade could not be reproduced"
    changed = task["id"] == erratum["task_id"]
    if changed:
        goal = next(g for g in env.task["goals"] if g["key"] == erratum["goal_key"])
        for normalization in (goal["normalization"], goal["evidence_requirement"]["normalization"]):
            aliases = normalization.setdefault("aliases", {}).setdefault(erratum["canonical"], [])
            aliases.extend(a for a in erratum["additional_aliases"] if a not in aliases)
    corrected = {**original, **env.evaluate(answer), "replay_verified": True,
                 "scoring_errata": [erratum["id"]] if changed else []}
    return corrected, corrected.get("complete") != original.get("complete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--erratum", type=Path, default=ROOT / "docs/scoring-errata/DSB11-alias-20260921.json")
    parser.add_argument("--output-dir", type=Path, help="New output directory; defaults to RUN_DIR/regraded")
    args = parser.parse_args()
    raw = json.loads((args.run_dir / "summary.json").read_text())
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    erratum = json.loads(args.erratum.read_text())
    output = args.output_dir or args.run_dir / "regraded"
    output.mkdir(exist_ok=False)
    results, changed, verified = [], [], []
    for row in raw["results"]:
        corrected, change = regrade_episode(args.run_dir / row["task_id"], erratum)
        results.append(corrected)
        if corrected.get("replay_verified"):
            verified.append(row["task_id"])
        if change:
            changed.append(row["task_id"])
        write_json(output / (row["task_id"] + ".json"), corrected)
    summary = summarize(results, raw["requested_tasks"])
    summary.update(post_hoc_rule_correction=erratum, original_resolved=raw["resolved"],
                   replay_verified_tasks=verified, changed_tasks=changed)
    write_json(output / "summary.json", summary)
    write_json(output / "erratum.json", erratum)
    write_json(output / "replay_manifest.json", {
        "original_summary_sha256": hashlib.sha256((args.run_dir / "summary.json").read_bytes()).hexdigest(),
        "erratum_sha256": hashlib.sha256(args.erratum.read_bytes()).hexdigest(),
        "regrade_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "network_calls": 0, "replay_verified_tasks": verified, "changed_tasks": changed})
    report = render_report(summary, manifest["agent_model"], manifest["simulator_model"])
    note = ("**本报告包含实测后声明的规则修正。** DSB-11的‘暂无承诺日期’与证据‘尚无承诺日期’等价。"
            "已用保存的工具动作和人物输出重放全部有效题目，先复现原始评分，再应用同义表达规则。"
            "没有新API调用，没有替换模型答案，没有增加证据，也没有采用作者参考策略。\n\n"
            f"原始可解决题成绩：{raw['resolved']['successes']}/{raw['resolved']['valid_episodes']}；"
            f"规则修正后：{summary['resolved']['successes']}/{summary['resolved']['valid_episodes']}。"
            "原始结果保留在上级目录的report.md和summary.json。\n\n")
    (output / "report.md").write_text(report.replace("# DaySpanBench 实测报告\n\n", "# DaySpanBench 实测报告（规则修正复评分）\n\n" + note))
    print(json.dumps({"verified_replays": verified, "changed_tasks": changed, "resolved": summary["resolved"],
                      "invalid_episodes": summary["invalid_episodes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
