"""Replay every handwritten task's authoring witness and export audit artifacts."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.reference import run_reference


def main():
    output = ROOT / "artifacts/reference_runs"
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    for path in sorted((ROOT / "tasks/private").glob("*.json")):
        task = json.loads(path.read_text())
        env, answer, result = run_reference(task)
        expected_hours = task["horizon_design"]["reference_days"] * 24
        if abs(result["calendar_hours"] - expected_hours) > 1/60:
            raise AssertionError(f"{task['id']}: calendar replay {result['calendar_hours']}h != designed {expected_hours}h")
        bundle = {"notice": "Privileged authoring witness; not an LLM benchmark result.",
                  "task_id": task["id"], "answer": answer, "result": result,
                  "agent_messages": env.messages, "private_audit": env.audit,
                  "pending_cases": [{"id": c["id"], "actor": c["actor"], "state": c["state"]} for c in env.cases.values() if c["state"] not in {"failed", "replied"}]}
        (output / f"{task['id']}.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
        summary.append({**result, "title": task["title"], "actors": len(task["actors"]), "deadline": task["deadline_at"], "horizon_design": task["horizon_design"]})
        print(f"{task['id']}: {'PASS' if result['complete'] else 'FAIL'} | {result['calendar_days']:g} days / {result['calendar_hours']} hours | {len(task['actors'])} actors")
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if len(summary) != 12 or not all(row["complete"] for row in summary):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
