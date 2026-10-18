"""Agent-facing tool surface: registry, common/optional handlers, hidden kinds."""

from .base import (HIDDEN_TOOL_KINDS, EXTRA_TOOLS, PUBLIC_TOOLS, TOOL_REGISTRY,
                  ToolSpec, category_names, tool_register)
from . import common, hidden, optional  # noqa: F401  (imports register the tools)

__all__ = ["HIDDEN_TOOL_KINDS", "EXTRA_TOOLS", "PUBLIC_TOOLS", "TOOL_REGISTRY",
           "ToolSpec", "category_names", "tool_register", "common", "hidden", "optional"]
