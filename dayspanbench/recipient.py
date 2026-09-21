"""Recipient decisions see only the current actor's routing manifest and message.

Both adapters must select a declared workflow. They cannot add facts, tools, or
modify state. Grounded responses are rendered by the engine from tool results.
"""

from typing import Callable, Protocol


class Recipient(Protocol):
    def choose(self, view: dict) -> str | None: ...


class RuleRecipient:
    def choose(self, view: dict) -> str | None:
        text = view["message"].casefold()
        candidates = []
        for workflow in view["workflows"]:
            matches = [len(word) for word in workflow["aliases"] if word.casefold() in text]
            if matches:
                candidates.append((max(matches), workflow["id"]))
        if not candidates:
            return None
        return sorted(candidates, key=lambda pair: (-pair[0], pair[1]))[0][1]


class LLMRecipient:
    """Inject a model client: callback(view) -> {'workflow_id': str | None}.

    No provider is contacted by this package. The host must configure its client.
    Every response is allowlist-validated; model output never executes a tool.
    """
    def __init__(self, callback: Callable[[dict], dict]):
        self.callback = callback

    def choose(self, view: dict) -> str | None:
        result = self.callback(view)
        workflow_id = result.get("workflow_id")
        allowed = {workflow["id"] for workflow in view["workflows"]}
        if workflow_id is not None and workflow_id not in allowed:
            raise ValueError("Recipient attempted an undeclared workflow")
        return workflow_id
