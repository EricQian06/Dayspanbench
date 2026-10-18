"""An allowlisted JSON-lines tool server for a single task (no shell tool).

Example: python3 scripts/serve.py --task DSB-01
Input: {"id": 1, "tool": "observe", "arguments": {}}
Output: {"id": 1, "result": ...}

Private fixtures are read by this trusted process, never returned via RPC.
Do not give a evaluated agent filesystem access to this repository.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.engine import Environment, PUBLIC_TOOLS, EXTRA_TOOLS
from dayspanbench.llm import LLMConfig, StructuredClient, SimulatorError
from dayspanbench.simulator import LLMSimulator

# Task fixtures and JSONL frames are always UTF-8, regardless of platform locale
# (Windows defaults to the ANSI codepage otherwise).
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ALLOWED = set(PUBLIC_TOOLS) | set(EXTRA_TOOLS)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=[f"DSB-{n:02d}" for n in range(1, 43)])
    parser.add_argument("--simulator", choices=["rule", "llm"], default="rule")
    parser.add_argument("--simulator-model", default=os.getenv("DSB_SIMULATOR_MODEL"))
    parser.add_argument("--simulator-base-url", default=os.getenv("DSB_SIMULATOR_BASE_URL", "https://az.gptplus5.com/v1"))
    parser.add_argument("--simulator-api", choices=["chat", "responses"], default="chat")
    parser.add_argument("--simulator-format", choices=["json_schema", "json_object"], default="json_schema")
    parser.add_argument("--api-key-env", default="DSB_SIMULATOR_API_KEY")
    parser.add_argument("--simulator-timeout", type=float, default=30)
    parser.add_argument("--simulator-retries", type=int, default=2)
    parser.add_argument("--simulator-max-tokens", type=int, default=2048)
    parser.add_argument("--history-limit", type=int, default=24)
    parser.add_argument("--run-dir", type=Path, help="Private per-episode logs; must be a new or empty directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress human-readable readiness/progress messages on stderr")
    args = parser.parse_args(argv)
    task_path = ROOT / "tasks/private" / f"{args.task}.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    # The per-task tool surface declared by the task itself (common tools plus
    # whichever optional tools it enables); the static registry is just a cap.
    ALLOWED = set(task["public"].get("tools") or PUBLIC_TOOLS)
    assert ALLOWED <= set(PUBLIC_TOOLS) | set(EXTRA_TOOLS)
    # Hidden per-task tools pass the allowlist by name; the engine still gates
    # them on discover_tools unlock (a locked name fails with "not available").
    HIDDEN = {tool["name"] for tool in task.get("hidden_tools", [])}
    client, recipients = None, None
    if args.simulator == "llm":
        try:
            config = LLMConfig(model=args.simulator_model, api_key=os.getenv(args.api_key_env, ""),
                               base_url=args.simulator_base_url, api=args.simulator_api,
                               output_format=args.simulator_format, timeout=args.simulator_timeout,
                               max_retries=args.simulator_retries, max_tokens=args.simulator_max_tokens)
            if not config.api_key and not config.base_url.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")):
                parser.error(f"Set the {args.api_key_env} environment variable")
            client = StructuredClient(config)
            recipients = {a["id"]: LLMSimulator(client, a["id"], history_limit=args.history_limit) for a in task["actors"]}
        except ValueError as error:
            parser.error(str(error))
    env = Environment(task, recipients)
    api = env.tools()
    manifest = {"task_id": args.task, "task_set_version": task["task_set_version"], "scoring_version": "0.5.0",
                "task_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
                "simulator": args.simulator, "history_limit": args.history_limit,
                "simulator_config": client.config.public_dict() if client else None,
                "reply_mode": "grounded_plan" if client else "template", "time_mode": "virtual_calendar",
                "notice": "Environment episode log; not an automatic evaluated-model runner."}
    if args.run_dir:
        if args.run_dir.exists() and any(args.run_dir.iterdir()):
            parser.error("run-dir must be new or empty; existing experiment data will not be overwritten")
        args.run_dir.mkdir(parents=True, exist_ok=True)
        (args.run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final_result, final_answer, exit_code = None, None, 0
    def save():
        if not args.run_dir:
            return
        for name, rows in (("private_audit.jsonl", env.audit), ("simulator_calls.jsonl", client.calls if client else [])):
            (args.run_dir / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        if final_result is not None:
            (args.run_dir / "result.json").write_text(json.dumps(final_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if final_answer is not None:
            (args.run_dir / "final_answer.json").write_text(json.dumps(final_answer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        print(f"[DaySpanBench] {args.task} Environment ready; character simulator: {args.simulator}.\n"
              "Waiting for stdin requests as single-line JSON. The server does not run tasks automatically; no character model has been called.\n"
              'Try: {"id":1,"tool":"observe","arguments":{}}', file=sys.stderr, flush=True)
    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        request = {}
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                request = {}
                raise ValueError("Request must be a JSON object")
            tool = request["tool"]
            if tool not in ALLOWED and tool not in HIDDEN:
                raise PermissionError("Tool not exposed to evaluated agents")
            if not args.quiet and args.simulator == "llm" and tool in {"send_email", "call", "wait_until"}:
                print(f"[DaySpanBench] Processing {tool}; character interactions wait for the simulator API response.", file=sys.stderr, flush=True)
            result = getattr(api, tool)(**request.get("arguments", {}))
            response = {"id": request.get("id"), "result": result}
            if tool == "submit_answer":
                final_answer = request["arguments"]["answer"]
                final_result = {"valid_episode": True, **result}
        except json.JSONDecodeError as error:
            response = {"id": None, "error": {
                "type": "JSONDecodeError",
                "message": f"Invalid JSON request on stdin line {line_number}: {error.msg}",
                "line": line_number, "column": error.colno,
                "hint": 'Enter one complete JSON object per line (JSONL), without line breaks or Markdown fences. Example: {"id":1,"tool":"observe","arguments":{}}',
            }}
        except SimulatorError as error:
            response = {"id": request.get("id"), "error": {"type": "SimulatorError", "message": str(error), "terminal": True}}
            final_result = {"task_id": args.task, "valid_episode": False, "termination": "simulator_error", "error": str(error)}
            exit_code = 2
        except (ValueError, KeyError, TypeError, PermissionError, StopIteration) as error:
            response = {"id": request.get("id"), "error": {"type": type(error).__name__, "message": str(error)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)
        if args.run_dir:
            with (args.run_dir / "rpc_trace.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"request": request, "response": response}, ensure_ascii=False) + "\n")
        save()
        if exit_code:
            break
    if final_result is None:
        final_result = {"task_id": args.task, "valid_episode": False, "termination": "no_final_submission"}
    save()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
