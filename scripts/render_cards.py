"""Render reviewer-facing task cards, actor dossiers and verified time traces."""

import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dayspanbench.calendar import parse


def local(time):
    return parse(time).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %a %H:%M")


def delay_text(delay):
    if delay["mode"] == "weekly":
        text = f"下一次周{'一二三四五六日'[delay['weekday']]} {delay['time']}批次，随后{delay['minutes']}工作分钟"
    elif delay["mode"] == "elapsed":
        text = f"连续{delay['minutes']}分钟（不停夜间/周末）"
    else:
        text = f"{delay['minutes']}工作分钟"
    if delay.get("not_before"):
        text += f"；不早于{local(delay['not_before'])}（北京时间）"
    return text


def render():
    out = ROOT / "docs/tasks"
    out.mkdir(parents=True, exist_ok=True)
    summary = ["# DaySpanBench 手写任务集 v0.3", "", "12个合成场景、41个独立角色。所有时间线由事件引擎回放验证。", "",
               "参考历时采用近似对数间隔：**2、3、5、8、13、21、34、55、89、144、210、300天**。2–7天、8–30天、31–100天、101–300天四档各3题；这是测评采样设计，不代表现实办事时间的频率分布。详见[跨度设计](horizon-design.md)。", "",
               "这些是作者参考轨迹的历时，不是任务的最短时间，也不是任何LLM的成绩。DSB-12评价截止前的受阻处理，不能并入已获取全部信息的成功率。", "",
               "| 任务 | 场景 | 人物 | 参考历时 | 时间档 | 参考结束（北京时间） | 结果类型 |", "|---|---|---:|---:|---|---|---|"]
    for path in sorted((ROOT / "tasks/private").glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        run = json.loads((ROOT / "artifacts/reference_runs" / path.name).read_text(encoding="utf-8"))
        result = run["result"]
        horizon = task["horizon_design"]
        summary.append(f"| [{task['id']}](tasks/{task['id']}.md) | {task['title']} | {len(task['actors'])} | {result['calendar_days']:g}天 / {result['calendar_hours']:g}小时 | {horizon['stratum']} | {local(result['as_of'])} | {task['completion_class']} |")
        lines = [f"# {task['id']} · {task['title']}", "", "> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。", "",
                 f"领域：{task['domain']}。开始：{local(task['start_at'])}；截止：{local(task['deadline_at'])}（北京时间）。", "",
                 f"参考轨迹历时：**{result['calendar_days']:g}天（{result['calendar_hours']:g}小时）**。结果类别：`{task['completion_class']}`。", "",
                 f"跨度设计：{horizon['stratum']}；{horizon['mechanism']}。这是作者参考路径的历时，非最短可行耗时。", "",
                 "## 用户任务", "", task["public"]["brief"], "", task["public"]["authorization"], "",
                 "已给信息：", "", "```json", json.dumps(task["public"]["user_fields"], ensure_ascii=False, indent=2), "```", "",
                 "初始联系人：" + ("、".join(task["public"]["initial_contacts"]) or "无（须由Agent搜索公开页面发现）"), "", "## 时间机制", ""]
        lines += ["- " + mechanism for mechanism in task["temporal_mechanisms"]]
        lines += ["", "## 人物、流程、接收者与工具", "",
                  "每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。", ""]
        for actor in task["actors"]:
            cal = task["calendars"][actor["calendar"]]
            lines += [f"### {actor['name']} (`{actor['id']}`)", "", f"角色：{actor['role']}。{actor['description']}", "",
                      f"[独立角色配置](../../tasks/actors/{task['id']}/{actor['id']}.json) · 日历 `{actor['calendar']}` · 时区 `{cal['timezone']}` · 工作日：" + "、".join("周" + "一二三四五六日"[d] for d in cal["weekdays"]) + " · 时段：" + " / ".join("—".join(h) for h in cal["hours"]), "",
                      "接收者约束：" + actor["recipient"]["instructions"], "",
                      "本地知识：" + ("、".join(actor["knowledge"]) or "没有直接持有的目标事实；按声明工具进行转介、核验或内部查询"), ""]
            for workflow in actor["workflows"]:
                lines += [f"**流程：{workflow['label']}** (`{workflow['id']}`)", "", "必须提供：" + ("、".join(workflow["required_fields"]) or "无额外字段"), ""]
                if workflow.get("evidence_fields"):
                    lines += ["证据门槛：" + json.dumps(workflow["evidence_fields"], ensure_ascii=False) + "；仅猜对值不算取得凭证。", ""]
                lines += ["| 步骤/工具 | 等待规则 | 可见结果或内部动作 |", "|---|---|---|"]
                for step in workflow["steps"]:
                    tool = actor["tools"][step["tool"]]
                    action = {"lookup": "读取本地事实", "document": "签发文本证据", "refer": "公开转介联系人", "delegate": "内部转交并等待返回", "reply": "向父事项/Agent回复"}[tool["kind"]]
                    details = tool.get("facts", tool.get("contacts", []))
                    if tool["kind"] == "delegate":
                        details = [tool["target"] + "/" + tool["workflow"], "仅传递字段：" + ", ".join(tool["forward_fields"])]
                    lines.append(f"| {step['label']}<br>`{step['tool']}` | {delay_text(step['delay'])} | {action}：{'、'.join(details)} |")
                lines.append("")
        lines += ["## 隐藏事实与标准条件", "", "| 事实 | 值 | 说明 |", "|---|---|---|"]
        for fid, fact in task["facts"].items():
            text = fact["text"]
            if fact.get("valid_until"):
                text += f" 有效至{local(fact['valid_until'])}。"
            lines.append(f"| `{fid}` | `{json.dumps(fact['value'], ensure_ascii=False)}` | {text} |")
        lines += ["", "目标结论：`" + task["expected_conclusion"] + "`。", "",
                  "```json", json.dumps(task["goals"], ensure_ascii=False, indent=2), "```", "",
                  "## 已验证参考时间线", "", "时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。", "",
                  "| 开始 | 完成/预计完成 | 人物 | 阶段 |", "|---|---|---|---|"]
        actor_map = {a["id"]: a for a in task["actors"]}
        # Messages are addressed by sender mailbox; resolve back to the actor.
        by_email = {a["contact_details"]["email"]: a for a in task["actors"]}
        for event in run["private_audit"]:
            if event["kind"] == "scheduled":
                name = actor_map[event["actor"]]["name"]
                phase = next(s["label"] for w in actor_map[event["actor"]]["workflows"] for s in w["steps"] if s["tool"] == event["tool"])
                lines.append(f"| {local(event['start_at'])} | {local(event['due_at'])} | {name} | {phase} |")
        lines += ["", "Agent收到的实质回复：", ""]
        for message in run["agent_messages"]:
            lines.append(f"- {local(message['at'])}：{by_email[message['from']]['name']}，`{message['status']}`，{len(message['evidence'])}条文本证据。")
        if run["pending_cases"]:
            lines += ["", "截止时仍在等待：", ""]
            lines += [f"- {c['actor']} / {c['id']}：`{c['state']}`。" for c in run["pending_cases"]]
        lines += ["", "## 易错点", ""] + ["- " + failure for failure in task["failure_modes"]]
        lines += ["", "## 机器可读文件", "", f"- [Agent公开任务](../../tasks/public/{task['id']}.json)",
                  f"- [环境私有定义](../../tasks/private/{task['id']}.json)",
                  f"- [完整参考回放](../../artifacts/reference_runs/{task['id']}.json)", "", task["alternate_paths"], ""]
        (out / f"{task['id']}.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "docs/task-catalog.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("Rendered 12 review cards, 41 actor dossiers within cards, and the task catalog.")


if __name__ == "__main__":
    render()
