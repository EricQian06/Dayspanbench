"""Replay every handwritten task's authoring witness and export audit artifacts."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.calendar import parse
from dayspanbench.reference import run_reference


def main():
    output = ROOT / "artifacts/reference_runs"
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    paths = sorted((ROOT / "tasks/private").glob("*.json"))
    for path in paths:
        task = json.loads(path.read_text(encoding="utf-8"))
        env, answer, result = run_reference(task)
        # Agent-side email handling carries seeded random latency, so the witness
        # no longer lands on the designed horizon exactly; it must merely finish
        # inside the deadline window.
        window_hours = (parse(task["deadline_at"]) - parse(task["start_at"])).total_seconds() / 3600
        if result["calendar_hours"] > window_hours + 1/60:
            raise AssertionError(f"{task['id']}: witness missed the deadline ({result['calendar_hours']}h > {window_hours:g}h)")
        bundle = {"notice": "Privileged authoring witness; not an LLM benchmark result.",
                  "task_id": task["id"], "answer": answer, "result": result,
                  "agent_messages": env.messages, "private_audit": env.audit,
                  "pending_cases": [{"id": c["id"], "actor": c["actor"], "state": c["state"]} for c in env.cases.values() if c["state"] not in {"failed", "replied"}]}
        (output / f"{task['id']}.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.append({**result, "title": task["title"], "actors": len(task["actors"]), "deadline": task["deadline_at"], "horizon_design": task["horizon_design"]})
        print(f"{task['id']}: {'PASS' if result['complete'] else 'FAIL'} | {result['calendar_days']:g} days / {result['calendar_hours']} hours (designed {task['horizon_design']['reference_days']*24}h) | {len(task['actors'])} actors")
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if len(summary) != len(paths) or not all(row["complete"] for row in summary):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
