"""Small HTTP client for structured simulator calls; no SDK or implicit credentials."""

from dataclasses import dataclass, field
import json
import re
import time
import unicodedata
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class SimulatorError(RuntimeError):
    """An environment failure, never an evaluated-agent failure."""


def key_tokens(text):
    """Verbatim anchors a model rephrase must preserve: every number (with
    decimals), every letter+digit id-like token (JOB441, CS204-2026-v2), and
    every quoted proper name, and every email address (contact channels only
    travel in prose). Digits inside an id token are not separate anchors (441
    within JOB441), and pure words carry no anchor: wording is the model's
    job, facts are the engine's."""
    if not isinstance(text, str) or not text:
        return []
    tokens = set()
    covered = []
    for email in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", text):
        tokens.add(email)
    for match in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_-]*", text):
        token = match.group(0)
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            tokens.add(token)
            covered.append(match.span())
    for match in re.finditer(r"\d+(?:\.\d+)?", text):
        if any(start <= match.start() and match.end() <= end for start, end in covered):
            continue
        tokens.add(match.group(0))
    for quoted in re.findall(r"\"([^\"]+)\"|“([^”]+)”", text):
        name = (quoted[0] or quoted[1]).strip()
        if name:
            tokens.add(name)
    return sorted(tokens)


def missing_key_tokens(answer, tokens):
    """Which required anchors are absent from an answer string (case-folded,
    word-boundary matching so JOB442 cannot satisfy JOB441's inner 441).
    The boundary only counts alphanumerics as continuation: a hyphen must not,
    or the date 2027-07-11 could never satisfy its own extracted tokens
    2027/07/11 — any reply keeping the date verbatim would still fail."""
    if not isinstance(answer, str):
        return list(tokens)
    haystack = unicodedata.normalize("NFKC", answer).casefold()
    missing = []
    for token in tokens:
        needle = unicodedata.normalize("NFKC", token).casefold()
        if re.search(r"(?<![0-9a-z])" + re.escape(needle) + r"(?![0-9a-z])", haystack):
            continue
        missing.append(token)
    return missing


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class LLMConfig:
    model: str
    api_key: str = field(default="", repr=False)
    base_url: str = "https://api.openai.com/v1"
    api: str = "chat"
    output_format: str = "json_schema"
    timeout: float = 30
    max_retries: int = 2
    max_tokens: int = 2048
    # Extra request fields merged into the provider payload (e.g. thinking
    # suppression for reasoning models: {"thinking": {"type": "disabled"}}).
    extra_body: Mapping = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.extra_body, Mapping):
            raise ValueError("extra_body must be a JSON object mapping")
        url = urlsplit(self.base_url)
        if not self.model or url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("A model and a valid credential-free base URL are required")
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Use HTTPS except for a local simulator service")
        if self.api not in {"chat", "responses"} or self.output_format not in {"json_schema", "json_object"}:
            raise ValueError("Unsupported simulator API/format")
        if not 0 < self.timeout <= 300 or not 0 <= self.max_retries <= 8 or self.max_tokens <= 0:
            raise ValueError("Invalid timeout, retry count or token budget")

    def public_dict(self):
        return {key: getattr(self, key) for key in ("model", "base_url", "api", "output_format", "timeout", "max_retries", "max_tokens", "extra_body")}


class StructuredClient:
    def __init__(self, config, *, transport=None, sleep=time.sleep):
        self.config, self.sleep = config, sleep
        self.transport = transport or self._post
        self.calls = []

    def _post(self, url, payload):
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = "Bearer " + self.config.api_key
        request = Request(url, data=json.dumps(payload, ensure_ascii=False).encode(), headers=headers, method="POST")
        with build_opener(NoRedirect()).open(request, timeout=self.config.timeout) as response:
            return json.loads(response.read())

    def complete(self, *, purpose, actor_id, system, view, schema):
        config = self.config
        if config.output_format == "json_object":
            # JSON mode does not transmit or enforce a schema through response_format.
            system += "\nReturn only a JSON object matching this JSON Schema:\n" + json.dumps(schema, ensure_ascii=False)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(view, ensure_ascii=False)}]
        fmt = {"type": "json_object"} if config.output_format == "json_object" else {
            "type": "json_schema", "name": "simulator_" + purpose, "schema": schema, "strict": True}
        if config.api == "chat":
            response_format = fmt if config.output_format == "json_object" else {"type": "json_schema", "json_schema": {k: v for k, v in fmt.items() if k != "type"}}
            payload = {"model": config.model, "messages": messages, "response_format": response_format,
                       "max_completion_tokens": config.max_tokens, "stream": False}
            endpoint = "/chat/completions"
        else:
            payload = {"model": config.model, "input": messages, "text": {"format": fmt},
                       "max_output_tokens": config.max_tokens, "store": False}
            endpoint = "/responses"
        payload.update(config.extra_body)
        record = {"purpose": purpose, "actor_id": actor_id, "model": config.model, "request": payload, "attempts": 0}
        self.calls.append(record)
        started = time.monotonic()
        try:
            for attempt in range(config.max_retries + 1):
                record["attempts"] += 1
                try:
                    response = self.transport(config.base_url.rstrip("/") + endpoint, payload)
                    break
                except HTTPError as exc:
                    code = exc.code
                    exc.close()
                    # 400 is retried too: some gateways report transient
                    # "no healthy deployments" states as 400; a genuine bad
                    # request still fails after the bounded retries.
                    if attempt == config.max_retries or (code not in (400, 429) and not 500 <= code < 600):
                        raise SimulatorError(f"Simulator HTTP failure ({code})") from None
                except (URLError, TimeoutError, OSError):
                    if attempt == config.max_retries:
                        raise SimulatorError("Simulator transport failure or timeout") from None
                self.sleep(min(2 ** attempt, 4))
            record["usage"] = response.get("usage", {})
            record["response_id"] = response.get("id")
            if config.api == "chat":
                choice = response["choices"][0]
                message = choice["message"]
                if message.get("refusal") or choice.get("finish_reason") != "stop":
                    raise SimulatorError("Simulator refused or returned an incomplete response")
                content = message["content"]
            else:
                if response.get("status") != "completed":
                    raise SimulatorError("Simulator response is incomplete")
                parts = [c for item in response.get("output", []) if item.get("type") == "message" for c in item.get("content", [])]
                if any(c.get("type") == "refusal" for c in parts):
                    raise SimulatorError("Simulator refused the request")
                content = "".join(c["text"] for c in parts if c.get("type") == "output_text")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise SimulatorError("Simulator must return a JSON object")
            record["response"] = result
            return result
        except SimulatorError as exc:
            record["error"] = str(exc)
            raise
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            record["error"] = "Invalid simulator response envelope or JSON"
            raise SimulatorError(record["error"]) from None
        finally:
            record["wall_seconds"] = round(time.monotonic() - started, 4)
