"""Merge valid episodes from an interrupted run into its rerun dir and
regenerate summary.json + report.md. Usage:
    python scripts/merge_runs.py <old_run> <rerun_dir> [--keep DSB-01 DSB-02 ...]

Without --keep, every task dir present in old_run but absent in rerun_dir is
copied over (only completed episodes with result.json)."""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dayspanbench.evaluation import render_report, summarize, write_json  # noqa: E402


def load_result(path):
    import json
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_run")
    parser.add_argument("rerun_dir")
    parser.add_argument("--keep", nargs="*", default=None,
                        help="task ids to copy from old_run (default: all absent, completed ones)")
    args = parser.parse_args()
    old, new = Path(args.old_run), Path(args.rerun_dir)
    task_ids = sorted(p.name for p in new.iterdir()
                      if p.is_dir() and p.name.startswith("DSB-"))
    for cand in sorted(old.iterdir()):
        if not cand.is_dir() or not cand.name.startswith("DSB-"):
            continue
        if cand.name in task_ids:
            continue
        if args.keep is not None and cand.name not in args.keep:
            continue
        if not (cand / "result.json").exists():
            continue
        shutil.copytree(cand, new / cand.name)
        task_ids.append(cand.name)
        print("merged", cand.name)
    task_ids.sort()
    results = [load_result(new / tid / "result.json") for tid in task_ids]
    summary = summarize(results, task_ids)
    write_json(new / "summary.json", summary)
    import json
    with open(new / "manifest.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
    (new / "report.md").write_text(
        render_report(summary, manifest["agent_model"], manifest["simulator_model"]),
        encoding="utf-8")
    print("merged run:", new, "tasks:", len(task_ids))


if __name__ == "__main__":
    main()
