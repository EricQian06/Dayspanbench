import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.validation import validate_task

failures = []
paths = sorted((ROOT / "tasks/private").glob("*.json"))
for path in paths:
    task = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_task(task)
    expected_public = {**task["public"], "start_at": task["start_at"], "deadline_at": task["deadline_at"]}
    actual_public = json.loads((ROOT / "tasks/public" / path.name).read_text(encoding="utf-8"))
    if actual_public != expected_public:
        errors.append("Public export drift or private-field leak")
    # Hidden tool definitions (names as keys + usage text) must never be
    # exported publicly; tool names may only appear inside authored prose.
    if "hidden_tools" in actual_public:
        errors.append("Hidden tool definitions leaked into the public export")
    for actor in task["actors"]:
        bundle = json.loads((ROOT / "tasks/actors" / task["id"] / f"{actor['id']}.json").read_text(encoding="utf-8"))
        if bundle["actor"] != actor or bundle["calendar"] != task["calendars"][actor["calendar"]]:
            errors.append(f"Actor export drift: {actor['id']}")
        if bundle["local_facts"] != {fid: task["facts"][fid] for fid in actor["knowledge"]}:
            errors.append(f"Actor knowledge leak/drift: {actor['id']}")
    failures.extend(f"{path.stem}: {error}" for error in errors)
# 12 handwritten DSB tasks + one module per ported LATCH case; the count grows
# automatically as case modules land in scripts/latch_cases/.
EXPECTED_TASKS = 12 + len(list((ROOT / "scripts" / "latch_cases").glob("*.py"))) \
    + len(list((ROOT / "scripts" / "club_cases").glob("*.py")))
if len(paths) != EXPECTED_TASKS:
    failures.append(f"Expected exactly {EXPECTED_TASKS} handwritten tasks")
if failures:
    print("\n".join(failures))
    raise SystemExit(1)
print(f"Validated {EXPECTED_TASKS} tasks: actor engines, receiver manifests, scoped tools, handoffs, goals and public/private exports.")
