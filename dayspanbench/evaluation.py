"""Trusted evaluation harness. The remote agent only receives public tool results."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError

from .engine import Environment
from .llm import StructuredClient, SimulatorError
from .scoring import score_with_judge
from .simulator import LLMSimulator
from .judge import LLMJudge


AGENT_PROMPT = """你正在完成DaySpanBench的一项信息获取任务。你的目标是在任务截止时间（deadline）之前完成信息收集，并亲自提交submit_answer完成最终作答。

【交互协议】
每轮仅输出一个JSON对象：{"tool":"工具名","arguments":{...}}。不要输出解释、思维过程或Markdown。

【任务背景】
- 初始任务信息（任务简介、截止时间、用户字段、答案字段、结论标签及已直接提供的联系人）由系统消息给出；忘记时用recall_task重新获取，内容与初始完全一致。
- 场景中的机构、人物、网页和资料都是合成的；你只能以环境工具返回的场景证据为依据，不能使用真实世界知识代替场景证据。

【行为规范】
- 只联系已发现的联系人，不凭空猜测联系方式或网址；需要新联系人时先搜索并访问公开页面。
- 每个任务可用的工具集不同（以下工具定义即本任务可用工具，observe()也会返回同一列表）；其中可能有对本任务无用的工具，请按需选用。
- 部分任务存在初始工具列表之外的隐藏工具：其名称只会出现在对接方回复或网页正文中。用discover_tools(名称)查询：命中会返回该工具的用法说明并解锁（此后出现在observe()的工具列表中，可按说明调用）；未命中不消耗消息预算。
- 网页内容可能在任务期间更新：对时间敏感的信息（价格、批次、时间窗口等）应在提交前重访相关页面核对最新版本。
- 对接方的回复可能只是凭记忆的猜测（可能同时提到若干"可能的地方"），猜测可能错误，需逐一去函验证；收到"我先去问一下同事"这类中间回执时，正式答复尚未到达，应继续等待，催办不会加速。
- 向对接方发邮件时，日期一律按委托信息原文的规范格式（YYYY-MM-DD）书写，不要改用其他写法。
- 同一事项补件或催问时使用其case_id；不同的办理事项发起新消息。
- 字段取值和凭证必须来自任务材料或已收到的信息，不得编造。
- 时间一律带UTC偏移；时钟不能倒退。
- 注意message_budget（发送预算）、受理窗口和材料有效期，规划联系顺序时一并考虑。
- 若结论取决于截止时刻（deadline）的状态（如"截止时尚未确认"类结论），须等到deadline时点之后再提交作答；时钟推进不会超过deadline，等待到该时点即可。
- 邮件回复有随机延迟，需要主动等待并跟进；不要因为一时没有回复就认定失败。
- wait_until等待途中若有新邮件送达，时钟会在该邮件送达时刻提前返回；规划长等待时以返回的当前时间为准重新安排后续动作。

【最终作答】
- submit_answer的answer为{"conclusion":"<结论标签>","summary":"<自然语言总结>"}：conclusion从公开conclusion_options中选择标签或其公开中文名称；summary用自己的话完整总结本次任务结果。
- summary必须涵盖已取得的全部关键信息：编号（受理号、票号、单号、预约号等）、数量、金额、日期、时间、单位；以实际收到的回执和书面答复为依据陈述，不要引用"证据编号"之类的内部编号。
- 未能确认或尚未办结的事项，在summary中如实说明"尚未确认"，不要编造；权威方明确回复否定性结论（"没有X""尚无X"）时，如实转述该否定结论，"没拿到肯定答复"不等于编造。
- 不要提交场景证据之外的猜想或真实世界知识。
- 主进程不会代你判断事实或生成最终答案；submit_answer只允许一次，不提供试错评分。

【效率要求】
- 在确保100%完成信息收集的前提下，尽量减少操作步数与token开销：避免重复读取已读消息、避免无效搜索、无效等待和重复催问；一个动作能并行的信息不要拆成多轮。
- 每完成一个阶段的收集，即推进到下一步；全部信息确认或到达deadline后立即提交submit_answer。

工具定义如下：
"""


class AgentAPIError(RuntimeError):
    """Provider/transport failure, reported separately from evaluated behavior."""


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_env_file(path, environ):
    """Read simple KEY=value entries without executing shell code or printing values."""
    path = Path(path)
    if not path.exists():
        return
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Invalid environment-file assignment on line {number}")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Unclosed environment-file quote on line {number}")
            value = value[1:-1]
        if not environ.get(key):
            environ[key] = value


class ChatAgent:
    """One ordinary non-streaming Chat Completions request per agent action."""

    def __init__(self, config, *, token_parameter="max_tokens", transport=None, sleep=time.sleep):
        if token_parameter not in {"max_tokens", "max_completion_tokens", "omit"}:
            raise ValueError("Invalid agent token parameter")
        self.config, self.token_parameter, self.sleep = config, token_parameter, sleep
        self.transport = transport or StructuredClient(config)._post
        self.calls = []

    def next_action(self, messages):
        payload = {"model": self.config.model, "messages": deepcopy(messages), "stream": False}
        if self.token_parameter != "omit":
            payload[self.token_parameter] = self.config.max_tokens
        record = {"request": payload, "attempts": 0}
        self.calls.append(record)
        started = time.monotonic()
        try:
            for attempt in range(self.config.max_retries + 1):
                record["attempts"] += 1
                try:
                    response = self.transport(self.config.base_url.rstrip("/") + "/chat/completions", payload)
                    break
                except HTTPError as error:
                    code = error.code
                    error.close()
                    # 400 is retried too: the shared gateway (az.gptplus5.com)
                    # returns transient 400s during blips even for payloads that
                    # replay successfully verbatim; a genuine bad request still
                    # fails after the bounded retries.
                    if attempt == self.config.max_retries or (code not in (400, 429) and not 500 <= code < 600):
                        raise AgentAPIError(f"Agent HTTP failure ({code})") from None
                except (URLError, TimeoutError, OSError):
                    if attempt == self.config.max_retries:
                        raise AgentAPIError("Agent transport failure or timeout") from None
                self.sleep(min(2 ** attempt, 4))
            choice = response["choices"][0]
            message = choice["message"]
            record.update(usage=response.get("usage", {}), response_id=response.get("id"),
                          returned_model=response.get("model"), finish_reason=choice.get("finish_reason"),
                          response=message)
            content = message.get("content")
            if content is None and message.get("refusal"):
                content = message["refusal"]
            if not isinstance(content, str):
                raise AgentAPIError("Agent response has no text content")
            # Truncation, refusal and malformed action text remain agent behavior.
            return content
        except AgentAPIError as error:
            record["error"] = str(error)
            raise
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            record["error"] = "Invalid agent API response envelope"
            raise AgentAPIError(record["error"]) from None
        finally:
            record["wall_seconds"] = round(time.monotonic() - started, 4)


def validate_value(value, schema, path="arguments"):
    """Validate the public tools' small JSON Schema subset before Python dispatch."""
    kind = schema.get("type")
    checks = {"object": lambda: isinstance(value, dict), "array": lambda: isinstance(value, list),
              "string": lambda: isinstance(value, str), "integer": lambda: type(value) is int,
              "boolean": lambda: type(value) is bool}
    if kind in checks and not checks[kind]():
        raise ValueError(f"{path} must be {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} has an unsupported value")
    if "minimum" in schema and value < schema["minimum"]:
        raise ValueError(f"{path} is below minimum")
    if kind == "object":
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - set(value):
            raise ValueError(f"{path} is missing required fields")
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ValueError(f"{path} contains unknown fields")
        for key, sub in properties.items():
            if key in value:
                validate_value(value[key], sub, path + "." + key)
    if kind == "array":
        for item in value:
            validate_value(item, schema.get("items", {}), path + "[]")


def parse_action(content, definitions):
    content = content.strip()
    if content.startswith("```json\n") and content.endswith("```"):
        content = content[8:-3].strip()
    def reject_constant(_):
        raise ValueError("Non-finite JSON numbers are not allowed")
    try:
        action = json.loads(content, parse_constant=reject_constant)
    except json.JSONDecodeError:
        raise ValueError('Return one JSON object: {"tool":"name","arguments":{...}}') from None
    if not isinstance(action, dict) or set(action) != {"tool", "arguments"}:
        raise ValueError("An action must contain exactly tool and arguments")
    name = action["tool"]
    if not isinstance(name, str) or name not in definitions:
        raise ValueError("Tool is not exposed to the evaluated agent")
    validate_value(action["arguments"], definitions[name]["parameters"])
    return action


def usage_total(calls):
    total = {"requests": len(calls), "http_attempts": sum(c.get("attempts", 0) for c in calls),
             "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "usage_reported_requests": 0}
    for call in calls:
        usage = call.get("usage") or {}
        if isinstance(usage, dict) and any(k in usage for k in ("total_tokens", "input_tokens", "prompt_tokens")):
            total["usage_reported_requests"] += 1
        for target, keys in (("prompt_tokens", ("prompt_tokens", "input_tokens")),
                             ("completion_tokens", ("completion_tokens", "output_tokens")),
                             ("total_tokens", ("total_tokens",))):
            for key in keys:
                if isinstance(usage, dict) and type(usage.get(key)) is int:
                    total[target] += usage[key]
                    break
    return total


def run_episode(task, agent, tool_specs, run_dir, *, simulator_client=None, judge_client=None,
                max_steps=80, history_limit=24, simulator_validation_retries=0,
                judge_validation_retries=1, seed=0, progress=lambda _: None):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    recipients = {a["id"]: LLMSimulator(simulator_client, a["id"], history_limit=history_limit,
                                      validation_retries=simulator_validation_retries)
                  for a in task["actors"]} if simulator_client else None
    env = Environment(task, recipients, seed=seed)
    api, trace = env.tools(), []
    # The tool surface differs per task: only specs this task declares are
    # shown to the evaluated model (observe() reports the same list at runtime).
    allowed = set(api.tool_list())
    tool_specs = [t for t in tool_specs if t["name"] in allowed]
    definitions = {t["name"]: t for t in tool_specs}

    def sync_hidden_definitions():
        # Hidden per-task tools unlock mid-episode via discover_tools and so
        # have no static schema here; the harness only enforces a permissive
        # object schema (calling convention = the usage text discover_tools
        # returned) and the engine validates the actual arguments.
        for name in sorted(env.unlocked_tools):
            if name not in definitions:
                definitions[name] = {"name": name, "description": env.hidden_tools[name]["usage"],
                                     "parameters": {"type": "object", "properties": {}, "additionalProperties": True}}
    system_content = (AGENT_PROMPT + json.dumps(tool_specs, ensure_ascii=False)
                      + "\n初始任务信息如下（可随时用recall_task重新获取，内容保持不变）：\n"
                      + json.dumps(api.recall_task(), ensure_ascii=False))
    messages = [{"role": "system", "content": system_content},
                {"role": "user", "content": json.dumps({"max_steps": max_steps, "note": "请开始执行任务"}, ensure_ascii=False)}]
    started, submitted, result, answer = time.monotonic(), False, None, None
    steps, action_errors = 0, 0
    def save():
        write_jsonl(run_dir / "agent_calls.jsonl", agent.calls)
        write_jsonl(run_dir / "rpc_trace.jsonl", trace)
        write_jsonl(run_dir / "private_audit.jsonl", env.audit)
        write_jsonl(run_dir / "simulator_calls.jsonl", simulator_client.calls if simulator_client else [])
    write_json(run_dir / "manifest.json", {
        "task_id": task["id"], "task_set_version": task["task_set_version"], "completion_class": task["completion_class"],
        "agent": agent.config.public_dict(), "agent_protocol": "json_action_chat", "agent_token_parameter": agent.token_parameter,
        "simulator": simulator_client.config.public_dict() if simulator_client else "rule",
        "max_steps": max_steps, "history_limit": history_limit, "simulator_validation_retries": simulator_validation_retries,
        "latency_seed": seed,
        "task_sha256": hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest(),
        "agent_prompt_sha256": hashlib.sha256(messages[0]["content"].encode()).hexdigest(),
        "started_at": datetime.now(timezone.utc).isoformat(), "time_mode": "virtual_calendar"})
    try:
        for steps in range(1, max_steps + 1):
            progress(f"{task['id']} agent step {steps}/{max_steps}")
            sync_hidden_definitions()
            content = agent.next_action(messages)
            messages.append({"role": "assistant", "content": content})
            action = None
            try:
                action = parse_action(content, definitions)
                progress(f"{task['id']} {action['tool']}")
                value = getattr(api, action["tool"])(**action["arguments"])
                response = {"result": value}
                if action["tool"] == "submit_answer":
                    submitted, answer = True, action["arguments"]["answer"]
                    result = {"valid_episode": True, "termination": "submitted", **value}
            except (ValueError, KeyError, TypeError, PermissionError, StopIteration) as error:
                action_errors += 1
                response = {"error": {"type": type(error).__name__, "message": str(error)}}
            trace.append({"step": steps, "request": action, "response": response})
            save()
            if submitted:
                break  # The evaluated model never sees its score.
            messages.append({"role": "user", "content": json.dumps({"tool_response": response,
                             "steps_remaining": max_steps - steps}, ensure_ascii=False)})
        if result is None:
            result = {"valid_episode": True, "termination": "step_limit", **env.evaluate({})}
    except (SimulatorError, AgentAPIError) as error:
        result = {"task_id": task["id"], "valid_episode": False,
                  "termination": "simulator_error" if isinstance(error, SimulatorError) else "agent_api_error",
                  "error": str(error)}
    except Exception as error:
        result = {"task_id": task["id"], "valid_episode": False, "termination": "harness_error", "error_type": type(error).__name__}
    finally:
        save()
    result.update(completion_class=task["completion_class"], submitted=submitted, agent_steps=steps,
                  action_errors=action_errors, wall_seconds=round(time.monotonic() - started, 3),
                  agent_usage=usage_total(agent.calls), simulator_usage=usage_total(simulator_client.calls if simulator_client else []))
    if answer is not None:
        write_json(run_dir / "final_answer.json", answer)
    # Post-episode LLM review is the PRIMARY score for tasks with authored
    # judge_criteria: the deterministic anchors from evaluate() are recomposed
    # with the per-criterion verdicts by score_with_judge. A pending judge
    # (infrastructure failure) keeps the episode valid but records
    # pending_criteria so the summary excludes it from pass-rate denominators.
    if result.get("valid_episode") and task.get("judge_criteria") and judge_client:
        progress(f"{task['id']} llm judge")
        judge = LLMJudge(judge_client, validation_retries=judge_validation_retries)
        review = judge.judge(task, env, answer)
        result["llm_judge"] = review
        # Anchor review (scoring 0.5.1): anchor tokens the literal check could
        # not find go to a second judge pass for value-level equivalence; a
        # graded confirmation lifts summary_anchors_ok, a denial or a pending
        # (infrastructure) review keeps the deterministic verdict.
        anchor_review = None
        missing = (result.get("deterministic_checks") or {}).get("summary_anchor_missing")
        if missing:
            anchor_review = judge.review_anchors(task, env, answer, missing)
            result["anchor_review_detail"] = anchor_review
        result.update(score_with_judge(env, review, anchor_review=anchor_review))
        result["judge_pending"] = review["status"] == "pending"
        write_jsonl(run_dir / "judge_calls.jsonl", judge_client.calls)
        if review["status"] == "graded":
            result["judge_passed"] = sum(1 for c in review["criteria"] if c["passed"])
            result["judge_total"] = len(review["criteria"])
    write_json(run_dir / "result.json", result)
    return result


def summarize(results, requested_tasks):
    valid = [r for r in results if r["valid_episode"]]
    scored = [r for r in valid if not r.get("judge_pending")]
    def group(kind, key):
        # Judge-pending episodes stay valid but leave the pass-rate denominator:
        # an infrastructure failure is never an agent failure.
        selected = [r for r in scored if r["completion_class"] == kind]
        successes = sum(bool(r.get(key)) for r in selected)
        return {"successes": successes, "valid_episodes": len(selected),
                "rate": successes / len(selected) if selected else None}
    return {"requested_tasks": requested_tasks, "finished_episodes": len(results), "valid_episodes": len(valid),
            "invalid_episodes": len(results) - len(valid),
            "judge_pending_episodes": sum(bool(r.get("judge_pending")) for r in valid),
            "resolved": group("resolved", "resolved_success"),
            "bounded_unresolved": group("bounded_unresolved", "bounded_handling_success"),
            "mean_required_fact_coverage": sum(r.get("required_fact_coverage") or 0 for r in valid) / len(valid) if valid else None,
            "results": sorted(results, key=lambda r: r["task_id"])}


def render_report(summary, agent_model, simulator_model):
    lines = ["# DaySpanBench 实测报告", "", f"被测模型：`{agent_model}`；人物模拟器：`{simulator_model}`。",
             "每题独立一次运行；虚拟日历，LLM终审（judge子部分）为主指标，确定性锚点仅作过程核对。该小样本不代表模型稳定成功率。", "",
             f"已结束 {summary['finished_episodes']}/{len(summary['requested_tasks'])} 题；有效 {summary['valid_episodes']}；基础设施/模拟器故障 {summary['invalid_episodes']}；judge挂起 {summary.get('judge_pending_episodes', 0)}。"]
    for label, key in (("可解决题成功率", "resolved"), ("截止受阻题处理成功率", "bounded_unresolved")):
        item = summary[key]
        value = f"{item['rate']:.1%}" if item["rate"] is not None else "N/A"
        lines.append(f"- {label}：{item['successes']}/{item['valid_episodes']}（{value}；仅有效且非judge挂起运行）。")
    lines += ["", "| 任务 | 结果 | 评分方式 | 子部分/事实覆盖 | 虚拟天数 | Agent步数 | 对外消息 |", "|---|---|---|---:|---:|---:|---:|"]
    for row in summary["results"]:
        state = ("通过" if row.get("complete") else "未通过") if row["valid_episode"] else "无效：" + row["termination"]
        if row.get("judge_pending"):
            state = "judge挂起"
        coverage = f"{row.get('required_fact_coverage', 0):.0%}" if row["valid_episode"] else "—"
        lines.append(f"| {row['task_id']} | {state} | {row.get('scored_by', '—')} | {coverage} | {row.get('calendar_days', '—')} | {row['agent_steps']} | {row.get('agent_messages', '—')} |")
    lines += ["", "覆盖率列：judge题为子部分通过率（pending不计分母），无judge_criteria的题暂为确定性事实覆盖率。故障与judge挂起不计作Agent失败；步数耗尽而未提交计有效失败。",
              "", "## 未通过与故障原因", ""]
    for row in summary["results"]:
        if not row["valid_episode"]:
            lines.append(f"- {row['task_id']}：{row.get('error', row.get('error_type', row['termination']))}")
        elif row.get("judge_pending"):
            lines.append(f"- {row['task_id']}：judge调用失败，{row.get('pending_criteria', 'N/A')}条子部分挂起（pending）。")
        elif not row.get("complete"):
            reasons = []
            checks = row.get("deterministic_checks") or {}
            if row.get("conclusion_correct") is False:
                reasons.append("结论标签不正确")
            missing = checks.get("summary_anchor_missing") or []
            if missing:
                reasons.append("总结缺失关键要素：" + "、".join(missing[:10]) + (f"（等{len(missing)}项）" if len(missing) > 10 else ""))
            if checks.get("forms_all_accepted") is False:
                reasons.append("表单/选择未全部按expect办结")
            if checks.get("pending_process_satisfied") is False:
                reasons.append("截止受理流程未完成")
            if checks.get("pending_deadline_reached") is False:
                reasons.append("未等到截止时点即作答")
            for criterion in (row.get("llm_judge") or {}).get("criteria", []):
                if criterion.get("passed") is False:
                    reasons.append(f"子部分{criterion['id']}未通过：{criterion.get('reason', '')}")
            reasons.extend(row.get("schema_errors") or [])
            lines.append(f"- {row['task_id']}（{row['termination']}）：" + "；".join(reasons))
    lines += ["", "每题的final_answer.json、rpc_trace.jsonl与result.json提供答案、交互和逐项目标判定；agent_calls.jsonl与simulator_calls.jsonl记录实际API调用与服务端usage。",
              "日志不含认证头，但包含任务轨迹与环境私有信息，不应再作为被测Agent的输入。", ""]
    return "\n".join(lines)
