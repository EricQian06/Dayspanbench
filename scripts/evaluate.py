"""Run real model episodes, or check both providers before spending an episode budget."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.evaluation import (ChatAgent, AgentAPIError, load_env_file, parse_action,
    run_episode, summarize, render_report, write_json, write_jsonl)
from dayspanbench.llm import LLMConfig, StructuredClient, SimulatorError
from dayspanbench.simulator import LLMSimulator


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--agent-model", required=True)
    parser.add_argument("--agent-base-url")
    parser.add_argument("--agent-api-key-env", default="DSB_AGENT_API_KEY")
    parser.add_argument("--agent-token-parameter", choices=["max_tokens", "max_completion_tokens", "omit"], default="max_tokens")
    parser.add_argument("--agent-max-tokens", type=int, default=4096)
    parser.add_argument("--simulator", choices=["llm", "rule"], default="llm")
    parser.add_argument("--simulator-model")
    parser.add_argument("--simulator-base-url")
    parser.add_argument("--simulator-api-key-env", default="DSB_SIMULATOR_API_KEY")
    parser.add_argument("--simulator-format", choices=["json_schema", "json_object"], default="json_schema")
    parser.add_argument("--simulator-max-tokens", type=int, default=8192)
    parser.add_argument("--simulator-validation-retries", type=int, choices=range(4), default=2)
    parser.add_argument("--simulator-extra-body", default='{"thinking": {"type": "disabled"}}',
                        help="JSON object merged into simulator request payloads; pass '{}' to keep provider defaults")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--seed", type=int, default=0, help="Seed for agent-side email handling-latency jitter; recorded in the manifest")
    parser.add_argument("--history-limit", type=int, default=24)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--tasks", nargs="+", choices=[f"DSB-{n:02}" for n in range(1, 13)])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true", help="Check agent chat, simulator routing, missing fields and reply planning; no scored episode")
    args = parser.parse_args(argv)
    try:
        load_env_file(args.env_file, os.environ)
    except ValueError as error:
        parser.error(str(error))
    sim_base = args.simulator_base_url or os.getenv("DSB_SIMULATOR_BASE_URL") or "https://az.gptplus5.com/v1"
    agent_base = args.agent_base_url or os.getenv("DSB_AGENT_BASE_URL") or sim_base
    sim_model = args.simulator_model or os.getenv("DSB_SIMULATOR_MODEL") or "deepseek-v4-flash"
    sim_key = os.getenv(args.simulator_api_key_env, "")
    agent_key = os.getenv(args.agent_api_key_env, "")
    if not agent_key and args.agent_api_key_env == "DSB_AGENT_API_KEY" and agent_base.rstrip("/") == sim_base.rstrip("/"):
        agent_key = sim_key
    if not agent_key:
        parser.error(f"Set {args.agent_api_key_env} (or the simulator key for the same base URL)")
    if args.simulator == "llm" and not sim_key:
        parser.error(f"Set {args.simulator_api_key_env}")
    if not 1 <= args.workers <= 12 or args.max_steps < 1 or args.history_limit < 1:
        parser.error("workers must be 1..12; max-steps and history-limit must be positive")
    try:
        simulator_extra = json.loads(args.simulator_extra_body)
        if not isinstance(simulator_extra, dict):
            raise ValueError("--simulator-extra-body must be a JSON object")
        agent_config = LLMConfig(args.agent_model, api_key=agent_key, base_url=agent_base,
            timeout=args.timeout, max_retries=args.retries, max_tokens=args.agent_max_tokens)
        sim_config = LLMConfig(sim_model, api_key=sim_key, base_url=sim_base, output_format=args.simulator_format,
            timeout=args.timeout, max_retries=args.retries, max_tokens=args.simulator_max_tokens, extra_body=simulator_extra)
    except ValueError as error:
        parser.error(str(error))
    if args.run_dir.exists() and any(args.run_dir.iterdir()):
        parser.error("run-dir must be new or empty")
    args.run_dir.mkdir(parents=True, exist_ok=True)
    tool_specs = json.loads((ROOT / "docs/agent-tools.json").read_text(encoding="utf-8"))
    if args.check_only:
        agent = ChatAgent(agent_config, token_parameter=args.agent_token_parameter)
        sim = StructuredClient(sim_config) if args.simulator == "llm" else None
        checks = []
        try:
            print("Checking evaluated-model Chat Completions...", flush=True)
            content = agent.next_action([{"role": "system", "content": 'Return only {"tool":"observe","arguments":{}} as JSON.'},
                                         {"role": "user", "content": "Start."}])
            parse_action(content, {t["name"]: t for t in tool_specs})
            checks.append("agent_chat")
            if sim:
                print("Checking simulator routing and reply planning...", flush=True)
                actor = LLMSimulator(sim, "fixture", validation_retries=args.simulator_validation_retries)
                view = {"actor_id": "fixture", "name": "测试联系人", "role": "信息查询", "instructions": "提供记录查询。",
                        "message": "请查询记录", "fields": {}, "history": [], "existing_workflow_id": None,
                        "workflows": [{"id": "main", "label": "记录查询", "aliases": ["查询"], "required_fields": []}], "local_cases": []}
                if actor.route(view) != {"workflow_id": "main", "fields": {}}:
                    raise SimulatorError("Preflight route was not understood")
                missing_view = {**view, "message": "请为ITEM42查询记录，需要什么文件？",
                                "workflows": [{"id": "main", "label": "记录查询", "aliases": ["查询"],
                                               "required_fields": ["item_id", "document_id"]}]}
                extracted = actor.route(missing_view)["fields"]
                if "document_id" in extracted or ("item_id" in extracted and extracted["item_id"] != "ITEM42"):
                    raise SimulatorError("Preflight invented a missing field")
                actor.render({"actor_id": "fixture", "name": "测试联系人", "role": "信息查询", "history": [],
                              "status": "reply", "canonical_text": "查询完成", "contacts": [], "evidence": []})
                checks.extend(["simulator_route", "simulator_missing_fields", "simulator_reply"])
            result = {"ok": True, "checks": checks}
        except (AgentAPIError, SimulatorError, ValueError) as error:
            result = {"ok": False, "checks": checks, "error": str(error)}
        write_jsonl(args.run_dir / "agent_calls.jsonl", agent.calls)
        write_jsonl(args.run_dir / "simulator_calls.jsonl", sim.calls if sim else [])
        write_json(args.run_dir / "preflight.json", result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if result["ok"] else 2
    task_ids = args.tasks or [f"DSB-{n:02}" for n in range(1, 13)]
    if len(task_ids) != len(set(task_ids)):
        parser.error("Duplicate task IDs are not permitted; use another run for repeats")
    source_files = [*sorted((ROOT / "dayspanbench").glob("*.py")), ROOT / "scripts/evaluate.py", ROOT / "docs/agent-tools.json"]
    manifest = {"agent_model": args.agent_model, "simulator_mode": args.simulator, "simulator_model": sim_model if args.simulator == "llm" else None,
                "agent_config": agent_config.public_dict(), "simulator_config": sim_config.public_dict() if args.simulator == "llm" else None,
                "agent_protocol": "json_action_chat", "agent_token_parameter": args.agent_token_parameter,
                "tasks": task_ids, "repeats": 1, "max_steps": args.max_steps, "history_limit": args.history_limit,
                "workers": args.workers, "simulator_validation_retries": args.simulator_validation_retries, "seed": args.seed,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "code_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}}
    write_json(args.run_dir / "manifest.json", manifest)
    for path in source_files:
        snapshot = args.run_dir / "source_snapshot" / path.relative_to(ROOT)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(path.read_bytes())
    lock = threading.Lock()
    def progress(message):
        with lock:
            print(message, flush=True)
    def worker(task_id):
        task = json.loads((ROOT / "tasks/private" / (task_id + ".json")).read_text(encoding="utf-8"))
        agent = ChatAgent(agent_config, token_parameter=args.agent_token_parameter)
        sim = StructuredClient(sim_config) if args.simulator == "llm" else None
        return run_episode(task, agent, tool_specs, args.run_dir / task_id, simulator_client=sim,
                           max_steps=args.max_steps, history_limit=args.history_limit,
                           simulator_validation_retries=args.simulator_validation_retries, seed=args.seed, progress=progress)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, task_id): task_id for task_id in task_ids}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            summary = summarize(results, task_ids)
            write_json(args.run_dir / "summary.json", summary)
            (args.run_dir / "report.md").write_text(render_report(summary, args.agent_model, sim_model if args.simulator == "llm" else "rule"), encoding="utf-8")
            progress(f"{result['task_id']} finished: {result['termination']}, valid={result['valid_episode']}, complete={result.get('complete', 'N/A')}")
    print((args.run_dir / "report.md").read_text(encoding="utf-8"), flush=True)
    return 2 if summary["invalid_episodes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
