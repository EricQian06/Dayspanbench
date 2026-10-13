"""DSB-13..DSB-42: the 30 tasks ported from the LATCH_BENCH case corpus.

Source of truth: LATCH_BENCH/cases/current/*.json (schema "case-v2"; see that
repo's cases/README.md). Each LATCH case becomes one DSB task authored in one
module under scripts/latch_cases/ (auto-discovered, sorted by filename):

  participants           -> person() actors with rule-based recipient workflows
  fact_store + visibility-> facts() with scoped actor knowledge
  events (timestamped)   -> page_update() rewrites and catalog inventory updates
  user.dialogue          -> a hidden kind="dialogue" tool (canned Q&A; facts
                            never surface in any page, only by asking)
  flight/hotel/dining/...
  booking-style tools    -> hidden kind="catalog" + kind="select" tools, whose
                            names are discoverable through web_search keyword
                            clues (params.keywords) and unlocked via
                            discover_tools
  rubric code_judge_first-> goals + evidence requirements (deterministic)
  rubric llm_judge_...   -> judge_criteria() (post-episode LLM review; separate
                            from resolved_success)

Ported tasks are English: the corpus is US/EU scenarios (cities, providers,
amounts) and translation would silently bend authored facts. Engine messages
mix languages by design -- every tool contract is language-neutral.

Case modules never import author_tasks (it runs both as a module and as a
script); build() receives author_tasks' globals, so helper functions and the
global email/phone allocation state stay single. Each module appends exactly
one task and registers its PAGE_SITES / HORIZON_DESIGN / CONCLUSION_OPTIONS
entries.
"""

import importlib
from pathlib import Path
import sys


# Filled by build(): the four artifacts author_tasks.merge_latch() consumes.
LATCH_TASKS = []
LATCH_PAGE_SITES = {}
LATCH_HORIZON_DESIGN = {}
LATCH_CONCLUSION_OPTIONS = {}


# Calendars for the ported cases' locales, registered into author_tasks'
# CALENDARS before any person() call (task() snapshots the whole dict).
_LATCH_CALENDARS = {
    "us_eastern_office": {"timezone": "America/New_York", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "17:00"]]},
    "us_eastern_daily": {"timezone": "America/New_York", "weekdays": list(range(7)), "hours": [["08:00", "20:00"]]},
    "us_central_office": {"timezone": "America/Chicago", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "17:00"]]},
    "us_central_daily": {"timezone": "America/Chicago", "weekdays": list(range(7)), "hours": [["08:00", "20:00"]]},
    "us_mountain_office": {"timezone": "America/Denver", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "17:00"]]},
    "us_pacific_office": {"timezone": "America/Los_Angeles", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "17:00"]]},
    "halifax_daily": {"timezone": "America/Halifax", "weekdays": list(range(7)), "hours": [["09:00", "21:00"]]},
    "paris_daily": {"timezone": "Europe/Paris", "weekdays": list(range(7)), "hours": [["08:00", "20:00"]]},
    "london_daily": {"timezone": "Europe/London", "weekdays": list(range(7)), "hours": [["07:00", "21:00"]]},
    "kolkata_office": {"timezone": "Asia/Kolkata", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:30", "18:00"]]},
}


def case_modules():
    """The ported-case modules, sorted by filename. DSB numbering lives inside
    each module, so discovery order only affects export order, not ids."""
    directory = Path(__file__).resolve().parent / "latch_cases"
    if not directory.is_dir():
        return []
    here = str(directory)
    if here not in sys.path:
        sys.path.insert(0, here)
    return [importlib.import_module(p.stem) for p in sorted(directory.glob("*.py"))
            if p.stem != "__init__" and not p.name.startswith("_")]


def build(A):
    """Author the ported tasks. A is author_tasks' globals: helpers (task,
    person, fact, ...) plus shared allocation state (_EMAILS, _PHONE_SEQ)."""
    A["CALENDARS"].update(_LATCH_CALENDARS)
    for module in case_modules():
        module.build(A, LATCH_TASKS, LATCH_PAGE_SITES, LATCH_HORIZON_DESIGN,
                     LATCH_CONCLUSION_OPTIONS)
