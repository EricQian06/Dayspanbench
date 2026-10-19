"""DSB-43+: v0.5 club cases — the assisted-user benchmark family.

Each club case is authored in one module under scripts/club_cases/
(auto-discovered, sorted by filename) with the same author_tasks helpers the
handwritten and LATCH tasks use:

  the assisted user        -> task["interactor"]: an authored spec consumed by
                             dayspanbench.interactor.UserInteractor (persona
                             answers over consult_user, policy-table consent
                             gating send_email/call/hidden tools)
  chat groups in the app   -> hidden kind="group" tools (preview, join with
                             capacity windows and admin review, timeline
                             reading); never joinable from the browser
  web questionnaires       -> pages carrying web forms + hidden kind="form"
                             tools whose names surface in group announcements
  trap conversations      -> recipient tool kind "extract": an LLM pass
                             extracts authored fields from the agent's prose,
                             branch matching runs over the structured result
                             only — never keywords

Case modules never import author_tasks (it runs both as a module and as a
script); build() receives author_tasks' globals so helper functions and the
global email/phone allocation state stay single. Each module appends exactly
one task and registers its PAGE_SITES / HORIZON_DESIGN / CONCLUSION_OPTIONS
entries.
"""

import importlib
from pathlib import Path
import sys


# Filled by build(): the four artifacts author_tasks.merge_club() consumes.
CLUB_TASKS = []
CLUB_PAGE_SITES = {}
CLUB_HORIZON_DESIGN = {}
CLUB_CONCLUSION_OPTIONS = {}


# Club officers and members are active in the evenings, every day.
CLUB_CALENDARS = {
    "campus_evening": {"timezone": "Asia/Shanghai", "weekdays": list(range(7)),
                       "hours": [["18:00", "23:00"]]},
}


def case_modules():
    """The club-case modules, sorted by filename."""
    directory = Path(__file__).resolve().parent / "club_cases"
    if not directory.is_dir():
        return []
    here = str(directory)
    if here not in sys.path:
        sys.path.insert(0, here)
    return [importlib.import_module(p.stem) for p in sorted(directory.glob("*.py"))
            if p.stem != "__init__" and not p.name.startswith("_")]


def build(A):
    """Author the club cases. A is author_tasks' globals: helpers (task,
    person, fact, ...) plus shared allocation state (_EMAILS, _PHONE_SEQ)."""
    A["CALENDARS"].update(CLUB_CALENDARS)
    for module in case_modules():
        module.build(A, CLUB_TASKS, CLUB_PAGE_SITES, CLUB_HORIZON_DESIGN,
                     CLUB_CONCLUSION_OPTIONS)
