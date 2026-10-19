"""Offline re-judge for judge_pending episodes: replay the recorded judge
responses through the CURRENT validation code (alias normalization etc.).
If a recorded response still fails validation, optionally re-call the API.

Usage: python scripts/rejudge_pending.py <run_dir> [--live]
Only touches episodes whose result.json has scored_by == "judge_pending".
"""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dayspanbench.engine import Environment  # noqa: E402
from dayspanbench.evaluation import summarize, render_report, write_json  # noqa: E402
from dayspanbench.llm import LLMConfig, StructuredClient  # noqa: E402
from dayspanbench.judge import LLMJudge  # noqa: E402
from dayspanbench.scoring import score_with_judge  # noqa: E402
from dayspanbench.simulator import LLMSimulator  # noqa: E402


class RecordedJudgeClient:
    """Feeds recorded judge responses, in order, through the judge interface."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self._sc = None

    # StructuredClient-compatible surface used by LLMJudge
    @property
    def _rows_iter(self):
        return iter(self.rows)

    def complete(self, *, purpose, actor_id, system, view, schema):
        row = self.rows[len(self.calls)]
        self.calls.append(row)
        if row.get("error"):
            raise ValueError(row["error"])
        return deepcopy(row["response"])


class LiveFallbackClient(RecordedJudgeClient):
    """Replays recorded responses; on error (or exhaustion), calls the API."""

    def __init__(self, rows, live):
        super().__init__(rows)
        self.live = live

    def complete(self, *, purpose, actor_id, system, view, schema):
        try:
            if len(self.calls) >= len(self.rows) or self.rows[len(self.calls)].get("error"):
                raise ValueError("recorded response unusable")
            return super().complete(purpose=purpose, actor_id=actor_id,
                                    system=system, view=view, schema=schema)
        except Exception:  # noqa: BLE001
            if self.live is None:
                raise
            return self.live.complete(purpose=purpose, actor_id=actor_id,
                                      system=system, view=view, schema=schema)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--live", action="store_true",
                        help="fall back to a live API call when replayed responses fail validation")
    args = parser.parse_args()
    live_client = None
    if args.live:
        import os
        env_file = args.run_dir.parent.parent.parent / ".env.paratera"
        for line in (ROOT / ".env.paratera").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                os.environ.setdefault(*line.split("=", 1))
        from dayspanbench.evaluation import load_env_file
        load_env_file(ROOT / ".env.paratera", os.environ)
        cfg = LLMConfig(os.environ.get("DSB_SIMULATOR_MODEL", "DeepSeek-V4-Flash"),
                        api_key=os.environ.get("DSB_SIMULATOR_API_KEY", ""),
                        base_url=os.environ.get("DSB_SIMULATOR_BASE_URL", ""),
                        output_format="json_schema", max_tokens=8192,
                        max_retries=5,
                        extra_body={"thinking": {"type": "disabled"}})
        live_client = StructuredClient(cfg)
    summary = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((args.run_dir / "manifest.json").read_text(encoding="utf-8"))
    results = {row["task_id"]: row for row in summary["results"]}
    task_ids = [row["task_id"] for row in summary["results"]]

    env_keys = {}
    for tid, row in list(results.items()):
        d = args.run_dir / tid
        if not (d / "result.json").exists():
            continue
        result = json.loads((d / "result.json").read_text(encoding="utf-8"))
        # Judge on the episode's own result file, not the (possibly stale)
        # summary row: a previous rejudge pass may have updated it.
        if result.get("scored_by") != "judge_pending":
            continue
        snap = d / "task_snapshot" / (tid + ".json")
        if not snap.exists():
            snap = ROOT / "tasks" / "private" / (tid + ".json")
        task = json.loads(snap.read_text(encoding="utf-8"))
        answer = json.loads((d / "final_answer.json").read_text(encoding="utf-8")) \
            if (d / "final_answer.json").exists() else {}
        rows = [json.loads(x) for x in (d / "judge_calls.jsonl").read_text(encoding="utf-8").splitlines()]
        judge_rows = [r for r in rows if r.get("purpose") == "judge"]
        if not judge_rows:
            print(tid, "no recorded judge calls; skipped")
            continue
        client = LiveFallbackClient(judge_rows, live_client) if live_client else RecordedJudgeClient(judge_rows)
        judge = LLMJudge(client, validation_retries=manifest.get("judge_validation_retries", 1))
        env = Environment(task)
        try:
            review = judge.judge(task, env, answer)
        except Exception as exc:  # noqa: BLE001
            print(tid, "replay failed:", exc)
            continue
        if review["status"] != "graded":
            print(tid, "still pending after replay (validation)")
            continue
        base = {k: v for k, v in result.items()
                if k not in ("llm_judge", "scored_by", "score", "subparts_passed",
                             "subparts_total", "pending_criteria", "complete",
                             "resolved_success", "bounded_handling_success",
                             "information_sufficient", "required_fact_coverage",
                             "anchor_review", "anchor_review_detail")}
        graded = score_with_judge(env, review, base=base)
        graded["llm_judge"] = review
        graded["judge_pending"] = review["status"] == "pending"
        graded["rejudged"] = True
        merged = {**result, **graded}
        write_json(d / "result.json", merged)
        results[tid] = merged
        print(tid, "->", merged.get("scored_by"),
              f"{merged.get('subparts_passed')}/{merged.get('subparts_total')}",
              "complete:", merged.get("complete"))

    new_summary = summarize(list(results.values()), task_ids)
    new_summary["rejudged"] = True
    write_json(args.run_dir / "summary.json", new_summary)
    (args.run_dir / "report.md").write_text(
        render_report(new_summary, manifest["agent_model"], manifest["simulator_model"]),
        encoding="utf-8")
    print("summary regenerated")


if __name__ == "__main__":
    main()
