"""Tool declarations and the registry shared by the agent-facing tool surface.

Tools live in three categories with identical dispatch mechanics:

- common: every task starts from these (PUBLIC_TOOLS);
- optional: a task's public["tools"] may add any of these (EXTRA_TOOLS),
  sometimes useful, sometimes pure decoys;
- hidden: per-task authored tools, unlocked through discover_tools — these are
  NOT registered here (their names and behavior are task data), but their
  handlers live in tools/hidden.py and dispatch on the authored kind.

Each tool is a module-level function ``handler(ctx, **kwargs)`` where ``ctx`` is
the AgentTools instance owning the environment reference. Registering one is
``@tool_register(name, category)``; the registry rejects duplicates so a name
can never silently shadow another. AgentTools delegates every RPC to the
registry, keeping engine.py free of tool implementations.
"""

from dataclasses import dataclass
from typing import Any, Callable


# The agent-facing tool surface every task starts from; serve.py allowlists
# per-task tool lists built from this plus EXTRA_TOOLS below. discover_tools
# is always available: per-task hidden tools are unlocked through it.
PUBLIC_TOOLS = ("observe", "recall_task", "web_search", "visit_page",
                "send_email", "call", "read_inbox", "wait_until",
                "discover_tools", "submit_answer")

# Optional task-specific tools. A task's public["tools"] may add any of these;
# they are sometimes useful and sometimes pure decoys, and the agent must decide
# from the tool descriptions and its own probing which ones carry information.
EXTRA_TOOLS = ("query_case_status", "fetch_document", "check_schedule",
               "lookup_directory", "request_callback", "leave_note", "consult_user")

# Per-task hidden tools (task["hidden_tools"]) are NOT part of public["tools"]:
# their names surface only inside authored NPC replies or page text, and the
# agent must call discover_tools(name) to learn their usage and unlock them.
# An unlocked tool's behavior is fully parameterized by its authored params.
HIDDEN_TOOL_KINDS = ("form", "status", "record", "catalog", "select", "dialogue", "group")


@dataclass(frozen=True)
class ToolSpec:
    """One registered capability: a name, its category, and its handler."""
    name: str
    category: str
    handler: Callable[..., Any]


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def tool_register(name: str, category: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a tool handler under a unique name within its category."""
    def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
        if category not in {"common", "optional"}:
            raise ValueError(f"Unknown tool category: {category}")
        if name in TOOL_REGISTRY:
            raise ValueError(f"Duplicate tool: {name}")
        TOOL_REGISTRY[name] = ToolSpec(name=name, category=category, handler=handler)
        return handler
    return decorator


def category_names(category: str) -> tuple[str, ...]:
    """Registered tool names of one category, sorted for stable listings."""
    return tuple(sorted(s.name for s in TOOL_REGISTRY.values() if s.category == category))
