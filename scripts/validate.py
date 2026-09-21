import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.validation import validate_task

failures = []
paths = sorted((ROOT / "tasks/private").glob("*.json"))
for path in paths:
    task = json.loads(path.read_text())
    errors = validate_task(task)
    expected_public = {**task["public"], "start_at": task["start_at"], "deadline_at": task["deadline_at"]}
    actual_public = json.loads((ROOT / "tasks/public" / path.name).read_text())
    if actual_public != expected_public:
        errors.append("Public export drift or private-field leak")
    for actor in task["actors"]:
        bundle = json.loads((ROOT / "tasks/actors" / task["id"] / f"{actor['id']}.json").read_text())
        if bundle["actor"] != actor or bundle["calendar"] != task["calendars"][actor["calendar"]]:
            errors.append(f"Actor export drift: {actor['id']}")
        if bundle["local_facts"] != {fid: task["facts"][fid] for fid in actor["knowledge"]}:
            errors.append(f"Actor knowledge leak/drift: {actor['id']}")
    failures.extend(f"{path.stem}: {error}" for error in errors)
if len(paths) != 12:
    failures.append("Expected exactly 12 handwritten tasks")
if failures:
    print("\n".join(failures))
    raise SystemExit(1)
print("Validated 12 tasks: actor engines, receiver manifests, scoped tools, handoffs, goals and public/private exports.")
