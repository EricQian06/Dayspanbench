"""The assisted user as an environment role: consent gate and question answers.

The interactor is authored per task (task["interactor"], private): a persona,
the user's profile facts, reply-delay rules, and a consent policy. It is the
voice behind the ask_user tool and the consent gate in front of agent actions
that have external effects (sending mail, submitting forms, joining groups).

Like the rest of the v0.5 simulator surface, understanding is delegated to an
LLM (StructuredClient) and judgment runs on schema-validated structured
output. Two implementations exist:

- ``UserInteractor``: the authored spec plus an optional StructuredClient.
  Without a client it degrades to the deterministic authored rules (canned
  answers, policy-table consent), so replay/validate never need an API key.
- ``FixtureInteractor`` (tests): canned responses.

Reply delays are seeded: replay/validate are deterministic while evaluation
episodes still vary per seed. The overnight rule mirrors the case design: a
reply drawn into the 02:00-08:00 window lands after 08:00 with its overnight
remainder preserved (projected - 02:00 + 08:00).
"""

from copy import deepcopy
from datetime import datetime, time, timedelta
import random
from zoneinfo import ZoneInfo

from .calendar import stamp
from .llm import SimulatorError, key_tokens, missing_key_tokens


INTERACTOR_PROMPT = """You are the user being assisted by an Agent in a benchmark environment. Answer one Agent question in your own natural English.
profile contains the facts you know about yourself and your situation; consent_policy and reply conventions apply when relevant. Answer from profile and prior_dialogue only: never invent commitments, availability, preferences, or facts you were not given.
answer the question actually asked. If the question depends on information not in profile, say you do not know or need to check rather than guessing.
Keep every date, time, number, and proper name exactly as authored. Output only schema-compliant JSON, without explanation or reasoning."""

CONSENT_PROMPT = """You are the user being assisted by an Agent in a benchmark environment. Decide whether to approve one Agent action.
action describes what the Agent wants to do; consent_policy lists your standing rules (what you approve, what you refuse, and what you want asked first). Approve an action only when it is consistent with consent_policy; otherwise refuse with a short natural reason in say.
Do not invent new rules. Keep every name and identifier exactly as given. Output only schema-compliant JSON, without explanation or reasoning."""


def _local_clock(value, zone):
    return value.astimezone(zone)


class UserInteractor:
    """One assisted user: consent gate + question answering + reply delays."""

    def __init__(self, spec, client=None, seed=0):
        if not isinstance(spec.get("persona"), str) or not spec["persona"]:
            raise ValueError("interactor spec requires a persona")
        self.spec = deepcopy(spec)
        self.client = client
        self.zone = ZoneInfo(spec.get("timezone", "UTC"))
        self.rng = random.Random((seed ^ 0x1A2B) & 0xFFFFFFFF)
        self.history = []
        self.consents = []

    # -- delays -----------------------------------------------------------

    def reply_at(self, now):
        """When a message sent to the user at ``now`` gets its reply.

        A random delay is drawn in [min, max] minutes. A reply that would land
        inside the quiet window (02:00-08:00 by default) is shifted past its
        end keeping the overnight remainder; a reply past the active window's
        end waits for the next active start."""
        rule = self.spec.get("reply_delay", {})
        low = int(rule.get("min_minutes", 10))
        high = int(rule.get("max_minutes", 180))
        if low < 0 or high < low:
            raise ValueError("Invalid reply delay bounds")
        zone = self.zone
        at = now + timedelta(minutes=self.rng.randint(low, high))
        quiet_start = time.fromisoformat(rule.get("quiet_start", "02:00"))
        quiet_end = time.fromisoformat(rule.get("quiet_end", "08:00"))
        local = _local_clock(at, zone)
        if quiet_start <= local.time() < quiet_end:
            shift = (datetime.combine(local.date(), local.time())
                     - datetime.combine(local.date(), quiet_start))
            at = local.replace(hour=quiet_end.hour, minute=quiet_end.minute,
                               second=0, microsecond=0) + shift
        active_end = rule.get("active_end")
        if active_end is not None:
            close = time.fromisoformat(active_end)
            local = _local_clock(at, zone)
            if local.time() > close:
                at = (local + timedelta(days=1)).replace(
                    hour=quiet_end.hour, minute=quiet_end.minute,
                    second=0, microsecond=0)
        return at

    # -- consent gate -----------------------------------------------------

    def consent(self, action, detail, at):
        """Approve or refuse one agent action. Understanding is the model's
        job; the verdict travels as a validated {approve, say} pair. Without
        a client the authored policy table decides, so rule-based replay
        stays deterministic."""
        view = {"persona": self.spec["persona"],
                "action": action, "detail": deepcopy(detail), "now": stamp(at),
                "consent_policy": deepcopy(self.spec.get("consent_policy", [])),
                "prior_dialogue": deepcopy(self.history[-12:])}
        schema = {"type": "object",
                  "properties": {"approve": {"type": "boolean"},
                                 "say": {"type": "string"}},
                  "required": ["approve", "say"], "additionalProperties": False}
        if self.client is None:
            outcome = self._policy_consent(action, detail)
        else:
            try:
                result = self.client.complete(purpose="consent", actor_id="user",
                                              system=CONSENT_PROMPT, view=view,
                                              schema=schema)
                approve, say = result.get("approve"), result.get("say")
                if not isinstance(approve, bool) or not isinstance(say, str) or not say.strip():
                    raise SimulatorError("Invalid interactor consent")
                outcome = {"approve": approve, "say": say}
            except SimulatorError:
                # A failed consent call is an environment failure, never a
                # silent approval; the deterministic policy decides instead.
                outcome = self._policy_consent(action, detail)
        self.consents.append({"action": action, "detail": detail,
                              "approve": outcome["approve"], "say": outcome["say"]})
        return outcome

    def _policy_consent(self, action, detail):
        for rule in self.spec.get("consent_policy", []):
            if rule.get("action") in (None, action) and rule.get("when") in (None, "always"):
                return {"approve": bool(rule.get("approve")),
                        "say": rule.get("say") or ""}
        return {"approve": False, "say": self.spec.get("default_refusal")
                or "I would rather you did not do that without checking with me first."}

    # -- answering --------------------------------------------------------

    def answer(self, question, at):
        """Answer one agent question in persona. Keyword rules supply the
        canonical answer when the question matches (facts stay grounded);
        otherwise the persona answers from the profile, and a model failure
        falls back to the authored default rather than inventing."""
        matched = None
        for rule in self.spec.get("rules", []):
            if any(keyword.casefold() in question.casefold()
                   for keyword in rule.get("keywords", [])):
                matched = rule
                break
        if matched is not None:
            canonical = matched["answer"]
        else:
            canonical = self.spec.get("default") or \
                "I don't have anything to add about that; please work from what you already know."
        answer = canonical
        if self.client is not None:
            try:
                answer = self._persona_answer(question, canonical, bool(matched))
            except SimulatorError:
                # A failed persona call never invents an answer: the grounded
                # canonical text is delivered verbatim and the fallback is
                # audited by the caller via the recorded history.
                answer = canonical
        self.history.append({"question": question, "answer": answer, "at": stamp(at)})
        return {"speaker": self.spec.get("speaker", "the user"),
                "answer": answer, "at": stamp(at)}

    def _persona_answer(self, question, canonical, matched):
        view = {"persona": self.spec["persona"], "question": question,
                "profile": deepcopy(self.spec.get("profile", [])),
                "matched_topic": matched, "canonical_fact": canonical,
                "prior_dialogue": deepcopy(self.history[-12:]),
                "reply_conventions": deepcopy(self.spec.get("reply_conventions", []))}
        schema = {"type": "object", "properties": {"answer": {"type": "string"}},
                  "required": ["answer"], "additionalProperties": False}
        tokens = key_tokens(canonical)
        for attempt in range(2):
            result = self.client.complete(purpose="interactor", actor_id="user",
                                          system=INTERACTOR_PROMPT, view=view,
                                          schema=schema)
            text = result.get("answer") if isinstance(result, dict) else None
            missing = missing_key_tokens(text, tokens)
            if isinstance(text, str) and text.strip() and not missing:
                return text
            if attempt == 0:
                view = deepcopy(view)
                view["validation_feedback"] = {
                    "previous_answer": text,
                    "error": "answer is empty or not a string"
                             if not isinstance(text, str) or not text.strip()
                             else "answer lost required key tokens: " + ", ".join(missing),
                    "requirements": ("answer must rephrase canonical_fact while preserving every number, "
                                     "date, identifier, and quoted proper name exactly; add no new facts.")}
        return canonical
