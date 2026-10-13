"""Hand-authored scenarios. Helpers only serialize repeated schema, never invent tasks.

Run from the repository root: python3 scripts/author_tasks.py
Private task files and public agent briefs are deliberately exported separately.
"""

import itertools
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Personal-name pinyin for synthesizing bench.example email addresses.
# No third-party dependencies: every authored name is transliterated by hand.
PINYIN = {
    "陈芷": "chenzhi", "姚岚": "yaolan", "赵航": "zhaohang", "周敏": "zhoumin",
    "林霁": "linji", "许乔": "xuqiao", "丁悦": "dingyue",
    "唐宁": "tangning", "梅芮": "meirui", "程昕": "chengxin",
    "叶青": "yeqing", "温遥": "wenyao", "杜和": "duhe", "宋野": "songye",
    "罗岑": "luocen", "苏渝": "suyu", "傅黎": "fuli",
    "孟竹": "mengzhu", "韩则": "hanze", "纪桐": "jitong",
    "关雨": "guanyu", "林澈": "linche",
    "蓝心": "lanxin", "蒋延": "jiangyan", "米禾": "mihe", "郑砚": "zhengyan",
    "谢茵": "xieyin", "吴弈": "wuyi", "陆笙": "lusheng",
    "沈栖": "shenqi", "柯闻": "kewen", "曾澜": "zenglan",
    "简川": "jianchuan", "唐泊": "tangbo",
    "白榆": "baiyu", "施瑾": "shijin", "贺悠": "heyou", "戴筠": "daijun",
    "柳汀": "liuting", "顾杉": "gushan",
}

_EMAILS = set()
_PHONE_SEQ = itertools.count(1)


def _email_for(actor_id, name):
    person = name.split("·")[-1]
    if person in PINYIN:
        local = PINYIN[person]
    elif person.isascii() and person.strip():
        local = "".join(person.split()).lower()
    else:
        local = actor_id.replace("_", "").replace("-", "")
    address = f"{local}@bench.example"
    suffix = 2
    while address in _EMAILS:
        address = f"{local}{suffix}@bench.example"
        suffix += 1
    _EMAILS.add(address)
    return address


def _next_phone():
    return f"+86 138{next(_PHONE_SEQ):08d}"


def business(minutes, **kwargs):
    return {"mode": "business", "minutes": minutes, **kwargs}


def elapsed(minutes):
    return {"mode": "elapsed", "minutes": minutes}


def weekly(weekday, time, minutes):
    return {"mode": "weekly", "weekday": weekday, "time": time, "minutes": minutes}


CALENDARS = {
    "office": {"timezone": "Asia/Shanghai", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "12:00"], ["13:00", "17:00"]]},
    "daily": {"timezone": "Asia/Shanghai", "weekdays": list(range(7)), "hours": [["09:00", "12:00"], ["13:00", "18:00"]]},
    "factory": {"timezone": "Asia/Shanghai", "weekdays": [0, 1, 2, 3, 4, 5], "hours": [["08:30", "12:00"], ["13:00", "17:30"]]},
    "evening": {"timezone": "Asia/Shanghai", "weekdays": list(range(7)), "hours": [["20:00", "22:00"]]},
    "landlord": {"timezone": "Asia/Shanghai", "weekdays": list(range(7)), "hours": [["19:00", "21:00"]]},
    "weekend": {"timezone": "Asia/Shanghai", "weekdays": [5, 6], "hours": [["10:00", "12:00"], ["14:00", "17:00"]]},
    "engineer": {"timezone": "Asia/Shanghai", "weekdays": [1, 3], "hours": [["10:00", "12:00"], ["14:00", "17:00"]]},
    "maintainer": {"timezone": "Asia/Shanghai", "weekdays": [0, 2, 4], "hours": [["20:00", "22:00"]]},
    "release": {"timezone": "Asia/Shanghai", "weekdays": [1, 3], "hours": [["20:00", "22:00"]]},
    "upstream": {"timezone": "Asia/Shanghai", "weekdays": [3], "hours": [["20:00", "22:00"]]},
    "new_york": {"timezone": "America/New_York", "weekdays": [0, 1, 2, 3, 4], "hours": [["09:00", "17:00"]]},
    "always": {"timezone": "UTC", "weekdays": list(range(7)), "hours": [["00:00", "23:59"]]},
}


def fact(value, text, **kwargs):
    return {"value": value, "text": text, **kwargs}


def lookup(facts, delay, label="查询业务记录"):
    return {"kind": "lookup", "facts": facts, "delay": delay, "label": label}


def document(facts, delay, label="签发书面确认"):
    return {"kind": "document", "facts": facts, "delay": delay, "label": label}


def delegate(target, delay, fields, workflow="main", label="内部转交"):
    return {"kind": "delegate", "target": target, "workflow": workflow, "forward_fields": fields, "delay": delay, "label": label}


def refer(contacts, delay):
    return {"kind": "refer", "contacts": contacts, "delay": delay, "label": "查询联系人目录并转介"}


def suggest(text, guesses, delay, label="给出猜测性答复"):
    """A vague reply answering from memory; guesses are named in prose and may
    be wrong, so the agent must verify each suggested channel itself."""
    return {"kind": "suggest", "text": text, "guesses": list(guesses), "delay": delay, "label": label}


def deny(text, delay=None, label="明确表示不知情或不归管"):
    """A dead-end reply: the recipient plainly cannot help, names no contacts,
    and the case closes as replied. Terminates a guess chain (suggest ->
    suggest -> deny) without a referral."""
    return {"kind": "deny", "text": text, "delay": delay or elapsed(0), "label": label}


def hidden_tool(name, usage, kind, params):
    """A per-task hidden agent tool: never listed in public["tools"]; its name
    surfaces only inside authored NPC replies or page text, and the agent must
    call discover_tools(name) to read `usage` (Chinese) and unlock it.
    kind is one of engine.HIDDEN_TOOL_KINDS; behavior is parameterized by
    params (see docs/environment-contract.md)."""
    return {"name": name, "usage": usage, "kind": kind, "params": params}


def form_field(name, label, required=True, hidden=False, **kwargs):
    """One field of a web form. hidden=True marks a field the page never
    renders (validation-only, e.g. a code the usage instructions supply)."""
    return {"name": name, "label": label, "required": required, "hidden": hidden, **kwargs}


def web_form(id, title, fields, submit_instructions):
    """A form carried by a public page: visit_page renders fields (minus
    hidden ones) and submit_instructions; submission goes through a hidden
    kind="form" tool, never through a common tool."""
    return {"id": id, "title": title, "fields": list(fields), "submit_instructions": submit_instructions}


def consult(target, delay, fields, workflow="main", text=None, label="内部咨询后答复"):
    """A visible internal transfer: the recipient first replies that they will
    ask a colleague, then the real answer arrives as a later second letter."""
    return {"kind": "consult", "target": target, "workflow": workflow, "forward_fields": fields,
            "delay": delay, "label": label, **({"text": text} if text else {})}


def page_update(page, at, **fields):
    """Rewrite page content at a virtual time; the schedule stays private."""
    return {"page": page, "at": at, **fields}


def doc(id, title, text, facts=(), issuer=None):
    """A published document file linked from a page; content only arrives via
    the optional fetch_document tool. Facts, if any, become evidence issued by
    the named actor when the document is fetched."""
    return {"id": id, "title": title, "text": text, "facts": list(facts), "issuer": issuer}


def document_page(id, title, text, contacts, snippet, documents=(), form=None):
    return {"id": id, "title": title, "text": text, "contacts": contacts, "snippet": snippet,
            "documents": [dict(d) for d in documents], **({"form": form} if form else {})}


def reply(delay=None):
    return {"kind": "reply", "delay": delay or elapsed(0), "label": "向请求者回复已取得的结果"}


def acknowledge(delay, label="发出受理回执"):
    return {"kind": "acknowledge", "delay": delay, "label": label}


def workflow(label, aliases, fields, steps, id="main", **kwargs):
    return {"id": id, "label": label, "aliases": aliases, "required_fields": fields, "raw_steps": steps, **kwargs}


def person(id, name, role, calendar, workflows, description, contact=None):
    tools, knowledge, prepared = {}, [], []
    for flow in workflows:
        flow = dict(flow)
        steps = []
        for index, raw in enumerate(flow.pop("raw_steps")):
            raw = dict(raw)
            tool_id = f"{id}.{flow['id']}.{index+1}.{raw['kind']}"
            delay, label = raw.pop("delay"), raw.pop("label")
            tools[tool_id] = raw
            if raw["kind"] in {"lookup", "document"}:
                knowledge.extend(raw["facts"])
            steps.append({"id": f"{flow['id']}_{index+1}", "label": label, "tool": tool_id, "delay": delay})
        flow["steps"] = steps
        prepared.append(flow)
    # Concrete contact details: email uses the person's pinyin; phones are
    # globally distinct. Only declared channels receive an address.
    declared = list(contact) if contact else ["email"]
    details = {}
    if "email" in declared:
        details["email"] = _email_for(id, name)
    if "phone" in declared:
        details["phone"] = _next_phone()
    return {"id": id, "name": name, "role": role, "description": description,
            "calendar": calendar, "channels": sorted(details), "contact_details": details,
            "knowledge": sorted(set(knowledge)), "tools": tools, "workflows": prepared,
            "process_engine": {"case_scope": "one state machine per request", "queue": "FIFO", "workers": 1,
                "states": ["new", "needs_information", "queued", "working", "waiting_internal", "replied", "failed"],
                "followup_policy": "acknowledge_without_resetting_queue", "parent_waits_for_child": True},
            "recipient": {"rule_adapter": "dayspanbench.recipient.RuleRecipient", "llm_adapter": "dayspanbench.simulator.LLMSimulator",
                "instructions": f"你是{name}，负责{role}。{description} 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。"}}


def send(to, text, label, fields=None, **kwargs):
    return {"op": "send", "to": to, "text": text, "label": label, "fields": fields if fields is not None else "$user", **kwargs}


def wait(label):
    return {"op": "wait_for", "label": label}


def goal(key, expected, *facts):
    return {"key": key, "expected": expected, "accepted_facts": list(facts)}


def task(id, title, domain, start, deadline, brief, user_fields, initial, pages, facts, actors, goals, conclusion, reference,
         mechanisms, failure_modes, completion_class="resolved", reply_delay=(20, 45),
         extra_tools=(), page_updates=(), hidden_tools=(), judge_criteria=(),
         authorization="仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。",
         display_timezone="Asia/Shanghai", alternate_paths=None):
    return {"schema_version": "0.2", "task_set_version": "0.4.0", "id": id, "title": title, "domain": domain,
        "start_at": start, "deadline_at": deadline, "display_timezone": display_timezone,
        "synthetic": True, "completion_class": completion_class, "calendars": CALENDARS,
        # Business minutes between a delivery and the recipient's first read:
        # handwritten per task, capped at 25% of the shortest contiguous work
        # window of any recipient, so a reply always lands inside the same
        # work window instead of being pushed across days.
        "reply_delay": list(reply_delay),
        # The agent-facing tool surface varies per task: common tools plus a
        # task-specific selection of optional tools (useful or decoys).
        "tools": list(BASE_TOOLS) + list(extra_tools),
        # Scheduled page rewrites; the update schedule itself stays private.
        "page_updates": list(page_updates),
        # Hidden agent tools: private definitions; names are revealed per-task
        # inside NPC replies or page text and unlocked via discover_tools.
        "hidden_tools": [dict(t) for t in hidden_tools],
        # Authored LLM-judge criteria (post-episode final-response review);
        # empty for the twelve original tasks, which are fully code-graded.
        "judge_criteria": [dict(c) for c in judge_criteria],
        "public": {"id": id, "title": title, "brief": brief, "user_fields": user_fields,
            "initial_contacts": initial, "pages": pages, "message_budget": 16,
            "tools": list(BASE_TOOLS) + list(extra_tools),
            "authorization": authorization,
            "answer_keys": [g["key"] for g in goals]},
        "facts": facts, "actors": actors, "goals": goals, "expected_conclusion": conclusion,
        "temporal_mechanisms": mechanisms, "failure_modes": failure_modes, "reference_actions": reference,
        "reference_is_privileged": True,
        "alternate_paths": alternate_paths or
            "接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。"}


def page(id, title, text, contacts, snippet, form=None):
    return {"id": id, "title": title, "text": text, "contacts": contacts, "snippet": snippet,
            **({"form": form} if form else {})}


# Every task's public pages live on one synthetic site named after the
# organization: https://<org-pinyin>.bench/{intro,contact,entry}. The internal
# page id (e.g. "venue") stays private; agents only ever see the URL.
PAGE_SITES = {
    "DSB-01": "heanhuiguan",   # 禾岸会馆
    "DSB-02": "qingli",        # 青栎公寓
    "DSB-03": "chengchuan",    # 澄川学院
    "DSB-04": "nanyu",         # 南屿共享实验室
    "DSB-05": "lengchuan",     # 棱川制造
    "DSB-06": "jiguang",       # 霁光电器
    "DSB-07": "beiting",       # 北汀档案馆
    "DSB-08": "wuzhangzhusu",  # 无障碍住宿比选
    "DSB-09": "qinggang",      # 晴港政务
    "DSB-10": "ershoushangji", # 二手相机信息
    "DSB-11": "xingzhou",      # 星舟项目
    "DSB-12": "yuancheng",     # 远澄货运
}


def page_url(task_id, page):
    """Derive the public URL from the internal id: bare ids are contact pages."""
    if page["id"].endswith("-intro"):
        suffix = "intro"
    elif page["id"].endswith("-entry"):
        suffix = "entry"
    elif page["id"].endswith("-faq"):
        suffix = "faq"
    else:
        suffix = "contact"
    return f"https://{PAGE_SITES[task_id]}.bench/{suffix}"


TASKS = []

# Common agent tools (must mirror engine.PUBLIC_TOOLS); tasks may add optional
# tools from engine.EXTRA_TOOLS via the extra_tools argument.
BASE_TOOLS = ("observe", "recall_task", "web_search", "visit_page",
              "send_email", "call", "read_inbox", "wait_until",
              "discover_tools", "submit_answer")

# 01: Venue — independent price and operations paths; weekend and two handoffs.
# The projector conclusion is deliberately form-only: the technician can only
# describe the maintenance window verbally (deny), and the written attestation
# is issued exclusively by the hidden equipment-registration form tool whose
# name surfaces in the Nov 7 page update and in the technician's own reply.
f = {"price": fact(10500, "11月13日18—21点，80人活动：场租9000元、服务费1500元，总价10500元。"),
     "cancel": fact("72小时内取消收取50%", "活动前72小时内取消收取总价的50%。"),
     "slot": fact(True, "11月13日18—21点场地有空档，80人容量可满足。"),
     "projector": fact(False, "投影设备11月13日全天维修，场地方也不能提供替代投影设备。"),
     # 陷阱证据：开局即挂在简介页的价目明细给出低于正式报价的诱人总价，但
     # 前台不具备报价签发权限，引用该证据会被评分拒绝；若直接采信该值，
     # 值本身也错（正确出处是销售岗位数日后出具的书面确认）。
     "price_ref": fact(9600, "近期80人活动价目明细：场租8200元、服务费1400元，合计9600元（留存方整理）。",
                       unauthorized_attestation=True)}
a = [person("reception", "禾岸会馆前台·陈芷", "对外咨询与转介", "office", [workflow("活动联系入口", ["活动", "场地", "联系"], [], [refer(["sales", "operations"], business(30)), reply()]),
        # 迷惑答复：前台对检修窗口给出自信但错误的口头印象（真实结论为
        # 13日全天检修），书面结论仍须经设备保障登记渠道取得。
        workflow("投影检修口头说明", ["投影"], [], [deny("投影检修的事我印象里13号上午就检修完毕，下午肯定能正常使用，错不了——不过前台不掌握检修计划，这只是口头印象，没有书面依据；设备可用性的书面结论请按官网简介页最新公告说明的设备保障登记渠道申请，以办结结论为准。")], id="projector_gossip")], "只掌握联系人目录；不能承诺报价、档期或设备。", contact=["email", "phone"]),
     person("sales", "禾岸会馆销售·姚岚", "费用与取消条款", "office", [workflow("报价及取消条件", ["报价", "价格", "费用", "取消"], ["event_date", "headcount"], [suggest("设备可用性的事我不能确认：档期归运营赵航管；投影检修情况可能要问设备主管周敏，也可能前台陈芷那边留了登记渠道。建议您分别去信确认。", ["operations", "technician", "reception"], business(30)), lookup(["price", "cancel"], business(780)), document(["price", "cancel"], business(30)), reply()])], "报价必须带日期和人数；设备可用性需要运营确认。"),
     person("operations", "禾岸会馆运营·赵航", "档期核对和设备协调", "office", [workflow("档期与投影确认", ["档期", "投影", "设备", "可用"], ["event_date", "event_time"], [lookup(["slot"], business(60)), acknowledge(business(30)), delegate("technician", business(60), ["event_date", "event_time"]), reply(business(30))])], "能够查档期；投影问题必须转给设备负责人。"),
     person("technician", "禾岸会馆设备主管·周敏", "设备维修计划", "office", [workflow("核对维修窗口", ["投影", "维修"], ["event_date"], [lookup([], business(240), "核对检修计划窗口（仅口头说明）"), deny("投影设备的检修安排我只能口头说明：11月13日全天安排检修。书面结论不随邮件出具，须通过会馆设备保障登记渠道（hean_equip_apply）申请，受理说明见官网简介页最新公告。")])], "只有本岗位知道维修窗口；书面结论须经登记渠道申请，不随邮件发放。")]
# The technician attests the projector fact but never looks it up in a workflow:
# the only issuance channel is the hidden registration form.
a[3]["knowledge"] = sorted(set(a[3]["knowledge"]) | {"projector"})
TASKS.append(task("DSB-01", "活动场地：跨周末确认设备与报价", "活动服务", "2026-11-06T10:00:00+08:00", "2026-11-11T18:00:00+08:00",
    "请核实禾岸会馆能否在11月13日18—21点接待80人，预算12000元，必须有投影。问清总费用、取消条款、档期和投影是否可用，附可核实的书面依据。",
    {"event_date": "2026-11-13", "event_time": "18:00-21:00", "headcount": 80}, [],
    [document_page("venue-intro", "禾岸会馆简介", "禾岸会馆提供活动场地租赁。旧版简介：8000元起，可容纳100人，有投影。具体档期和设施请通过联系方式页咨询。本页另挂有近期活动价目明细等文件。", [], "禾岸会馆活动场地简介：价格起点、容量与投影设备说明。",
                   [doc("venue-device-notice", "设备维修公告（11月）.pdf", "11月投影设备维修计划：11月13日全天安排投影设备检修，期间无法提供投影设备，也不提供替代投影设备。其余月份安排另行公告。"),
                    doc("venue-price-ref", "近期80人活动价目明细.pdf", "近期80人活动价目明细：场租8200元、服务费1400元，合计9600元。（留存方整理）", facts=["price_ref"], issuer="reception")]),
     page("venue", "禾岸会馆联系方式", "各岗位联系人的联系方式（邮箱）请咨询前台陈芷，由前台提供后续对接入口。办公时间周一至周五9—12、13—17点。前台陈芷负责对外咨询与转介；报价、档期与设备须由相应对接人确认。", ["reception"], "禾岸会馆对接人与办公时间。"),
     page("venue-entry", "禾岸会馆设备保障申请", "禾岸会馆活动场地预约说明：预约需提供活动日期、时段和人数；报价、档期与设备可用性须由禾岸会馆相应对接人分别确认。设备保障的书面结论通过本页登记表单申请后取得。本页面仅说明所需信息，不能在线完成预约。", [], "禾岸会馆活动场地预约材料与设备保障登记表单说明；不支持在线预约。",
          form=web_form("hean_equip_form", "设备保障申请",
                        [form_field("event_date", "活动日期"), form_field("event_time", "活动时段", required=False), form_field("headcount", "人数")],
                        "本表单不能在线直接提交：须通过会馆设备保障登记渠道办理，渠道名称以官网简介页最新公告为准。"))],
    f, a, [goal("total_cost", 10500, "price"), goal("cancellation", "72小时内取消收取50%", "cancel"), goal("slot_available", True, "slot"), goal("projector_available", False, "projector")],
    "unsuitable", [{"op": "visit_page", "page": "venue"}, send("reception", "请提供活动场地的联系入口", "front"), wait("front"), send("sales", "请发报价和取消条款", "quote"), send("operations", "请核实档期和投影", "ops"), {"op": "advance", "at": "2026-11-07T10:00:00+08:00"}, {"op": "discover", "name": "hean_equip_apply"}, {"op": "tool", "name": "hean_equip_apply", "args": {"fields": {"event_date": "2026-11-13", "event_time": "18:00-21:00", "headcount": 80}}}, wait("quote"), wait("ops"), {"op": "advance", "at": "2026-11-10T17:30:00+08:00"}, {"op": "discover", "name": "hean_equip_status"}, {"op": "tool", "name": "hean_equip_status", "args": {"query": "设备保障"}}],
    ["周末停办", "并行询价与设备确认", "跨岗位内部转交", "过时网页与当前事实冲突", "官网页面中途更新", "隐藏登记表单与分阶段办结", "销售猜测性指路与设备岗明确回绝", "前台越权价目明细与检修口头误述"], ["将8000元起当作总价", "未核实投影即判断适用", "把内部转交受理当作完成", "只读一次官网不再复查更新", "把设备岗口头说明当书面结论", "不发现登记渠道即下结论", "引用开局页面价目明细当作有效报价", "把前台检修口头印象当设备结论"],
    extra_tools=("check_schedule", "request_callback", "fetch_document", "leave_note"),
    hidden_tools=(hidden_tool("hean_equip_apply",
        "禾岸会馆设备保障登记渠道。调用参数：fields为对象，键为表单字段名（event_date、event_time、headcount），取值按表单说明填写。",
        "form", {"form": "hean_equip_form", "expect": {"event_date": "2026-11-13"},
                 "process_delay": 300, "calendar": "office",
                 "result_text": "设备保障登记已办结：11月13日投影设备全天检修，无法提供投影设备，也不提供替代设备；办理进度可经会馆进度查询渠道（hean_equip_status）复核。",
                 "reject_text": "登记信息与活动安排不符，已退回；请核对后重新提交。",
                 "facts": ["projector"], "issuer": "technician",
                 "page_update": {"page": "venue-entry", "snippet": "禾岸会馆设备保障申请：已提交的申请以表单状态为准。"}}),
        hidden_tool("hean_equip_status",
        "禾岸会馆办理进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "equip-1113", "label": "11月13日活动设备保障",
                                "initial": "尚未查询到设备保障登记记录。",
                                "timeline": [{"at": "2026-11-07T10:00:00+08:00", "text": "11月投影检修安排已导入系统，设备保障登记可正常提交。"}],
                                "form": "hean_equip_form"}]})),
    page_updates=[page_update("venue-intro", "2026-11-07T10:00:00+08:00",
        text="禾岸会馆活动场地说明（2026年11月7日更新）：旧版价目（8000元起、含投影）已停用作废；活动报价一律以销售岗位按活动日期与人数出具的书面确认为准。投影等设备近期安排见本页设备维修公告文件；设备保障的书面结论须通过会馆设备保障登记渠道（hean_equip_apply）申请后取得，办理进度可经会馆进度查询渠道（hean_equip_status）复核。",
        snippet="禾岸会馆活动场地说明：最新价目说明、设备维修公告文件与设备保障登记渠道。")]))

# 02: Individual landlord — evening responses + Friday property review.
# The earliest-move conclusion is form-only: the property manager verifies the
# new elevator schedule but does not commit to a time by mail; the written
# conclusion is issued by the hidden move-in registration form, whose name
# surfaces only in the Nov 11 page update (the form itself stays pending until
# the schedule is published).
f = {"rent": fact(5600, "月租5600元；这是信息咨询，不构成租约。"), "pet": fact(True, "已核准一只8公斤成年犬符合楼宇宠物规则。"),
     "deposit": fact(4000, "该房源押金4000元，不另收宠物押金。"), "moving": fact("2026-11-13T10:00:00+08:00", "11月11日公布的新一期货梯表显示12日无可用时段，最早可安排11月13日10点搬入。"),
     # 陷阱证据：开局即挂在简介页的宠物规定口径断言8公斤犬不符合条件，
     # 与周五复核的真实结论（可饲养）相反；物业经理不具备宠物规则的签发
     # 权限（规则审核员周五复核才出具），引用会被拒绝，直接采信该值也错。
     "pet_ref": fact(False, "楼宇宠物饲养规定：本楼仅限5公斤以下宠物入住，8公斤犬不符合饲养条件（留存方整理）。",
                     unauthorized_attestation=True)}
a = [person("landlord", "房东·林霁", "出租房源咨询", "landlord", [workflow("租金、宠物和搬入条件", ["租房", "宠物", "入住", "搬入"], ["pet_weight", "move_date"], [lookup(["rent", "deposit"], business(60)), acknowledge(business(30)), consult("manager", business(0), ["pet_weight", "move_date"], text="宠物规则和货梯时段要问物业，我先向青栎公寓物业转过去核实，稍后把结果回复您。"), reply(business(30))]),
        # 迷惑答复：房东对货梯时段给出自信但错误的印象（真实结论为12日
        # 无可用时段），正式安排仍以搬入登记系统的办结结论为准。
        workflow("货梯时段口头印象", ["货梯", "电梯"], [], [deny("货梯时段我印象里11月12日上午就有空档，直接搬就行，错不了——不过这只是我的印象，房东不做主；正式安排请向青栎公寓物业确认，并以青栎搬入登记系统的办结结论为准。")], id="elevator_gossip")], "白天上班，只在19—21点处理消息；不会代物业批准宠物或货梯。", contact=["email", "phone"]),
     person("manager", "青栎公寓物业·许乔", "楼宇规则与货梯时段", "office", [workflow("宠物与搬入复核", ["宠物", "搬入"], ["pet_weight", "move_date"], [delegate("reviewer", business(60), ["pet_weight"]), lookup([], business(60, not_before="2026-11-11T09:00:00+08:00"), "登记搬入并核对新一期货梯表"), reply(business(30))])], "收到房东转交后提交周五审核；搬入时段以搬入登记系统的办结结论为准，不随邮件口头承诺。"),
     person("reviewer", "青栎公寓规则审核员·丁悦", "宠物规则复核", "office", [workflow("周五规则审核", ["宠物", "规则"], ["pet_weight"], [lookup(["pet"], weekly(4, "14:00", 60)), reply()])], "每周五14点集中复核材料；错过批次进入下一周。")]
# The manager attests the earliest-move fact but never looks it up in a
# workflow: the only issuance channel is the hidden move-in registration form.
a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"moving"})
TASKS.append(task("DSB-02", "租房咨询：物业周审与新一期货梯表", "个人与物业", "2026-11-03T19:30:00+08:00", "2026-11-13T17:00:00+08:00",
    "我想11月12日搬入林霁的房子，带一只8公斤成年犬。问清租金、押金、宠物规则，以及最早可搬入时间；若12日不行请说明替代时间，暂不签约。",
    {"pet_weight": "8kg", "move_date": "2026-11-12"}, ["landlord"],
    [document_page("listing-intro", "青栎房源简介", "青栎公寓在租房源。房东通常19—21点回复。宠物需物业周五复核；11月11日开放新一期货梯表，才能确认下半月搬入时段。本页另挂有楼宇宠物饲养规定等文件。", [], "青栎在租房源概况与搬入安排说明。",
                   [doc("listing-pet-leaflet", "楼宇宠物饲养规定.pdf", "青栎公寓楼宇宠物饲养规定：本楼仅限5公斤以下宠物入住，8公斤及以上犬只不符合饲养条件。（留存方整理）", facts=["pet_ref"], issuer="manager")]),
     page("listing", "青栎房源联系方式", "出租咨询联系房东林霁；楼宇规则与货梯时段由青栎公寓物业处理。", ["landlord"], "房东与物业的对接说明。"),
     page("listing-entry", "青栎公寓搬入货梯使用登记", "青栎公寓入住办理流程：入住前需先确认楼宇宠物规则（由青栎公寓物业周五复核）与货梯时段；货梯时段的书面结论通过本页登记表单申请后取得。本页面仅说明青栎公寓入住流程，不构成租约，也不能在线签约。", [], "青栎公寓入住条件、办理流程与搬入登记表单说明；不支持在线签约。",
          form=web_form("elevator_form", "搬入货梯使用登记",
                        [form_field("move_date", "期望搬入日期"), form_field("pet_weight", "宠物重量")],
                        "本表单不能在线直接提交：须通过青栎搬入登记系统办理；系统名称与受理时间以房源简介页最新公告为准。"))],
    f, a, [goal("monthly_rent", 5600, "rent"), goal("deposit", 4000, "deposit"), goal("pet_allowed", True, "pet"), goal("earliest_move", "2026-11-13T10:00:00+08:00", "moving")],
    "requires_date_change", [send("landlord", "咨询租房、宠物及搬入条件", "housing"), wait("housing"), {"op": "advance", "at": "2026-11-11T20:00:00+08:00"}, {"op": "discover", "name": "qingli_move_register"}, {"op": "tool", "name": "qingli_move_register", "args": {"fields": {"move_date": "2026-11-12", "pet_weight": "8kg"}}}, {"op": "advance", "at": "2026-11-12T10:30:00+08:00"}, {"op": "discover", "name": "qingli_move_status"}, {"op": "tool", "name": "qingli_move_status", "args": {"query": "搬入"}}],
    ["个人只在晚间回复", "机构白天办公", "固定周五审核", "新一期货梯表尚未开放", "官网页面中途更新", "隐藏搬入登记表单与分阶段办结", "登记受理进度的隐藏时间线", "物业越权宠物规定与房东货梯口头误述"], ["把页面宠物规定当作复核结论", "忽略房东与物业时间错位", "把11月12日误报为可搬入", "货梯表公布前提交登记即认定已受理", "不发现登记系统即凭口头答复下结论", "引用楼宇宠物规定当作宠物规则有效结论", "把房东货梯印象当正式安排"],
    extra_tools=("leave_note", "fetch_document", "check_schedule"),
    hidden_tools=(hidden_tool("qingli_move_register",
        "青栎公寓搬入登记系统。调用参数：fields为对象，键为表单字段名（move_date、pet_weight），取值按表单说明填写。",
        "form", {"form": "elevator_form", "expect": {"move_date": "2026-11-12"},
                 "process_at": "2026-11-12T10:00:00+08:00",
                 "result_text": "搬入登记已办结：新一期货梯表显示11月12日无可用时段，最早可安排11月13日10点搬入；办理进度可经青栎搬入进度查询（qingli_move_status）复核。",
                 "reject_text": "登记信息与房源情况不符，已退回；请核对后重新提交。",
                 "facts": ["moving"], "issuer": "manager",
                 "page_update": {"page": "listing-intro", "text": "青栎公寓在租房源（11月12日更新）：搬入登记已按新一期货梯表办结，搬入时段以搬入登记系统的办结结论为准。房东通常19—21点回复。", "snippet": "青栎在租房源概况与搬入登记办结说明。"}}),
        hidden_tool("qingli_move_status",
        "青栎搬入进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "elevator", "label": "搬入货梯登记受理",
                                "initial": "新一期货梯表尚未公布，搬入登记暂不受理。",
                                "timeline": [{"at": "2026-11-11T09:00:00+08:00", "text": "新一期货梯表已公布，搬入登记开始受理。"}],
                                "form": "elevator_form"}]})),
    page_updates=[page_update("listing-intro", "2026-11-11T09:00:00+08:00",
        text="青栎公寓在租房源（11月11日更新）：新一期货梯表已公布，12日无可用时段；搬入须先通过青栎搬入登记系统（qingli_move_register）提交申请，受理进度可经青栎搬入进度查询（qingli_move_status）核对，办结结论以登记系统为准。房东通常19—21点回复。")],
    reply_delay=(10, 30)))
# DSB-02 landlord evening window is 2h -> reply cap 30 min (25%).

# 03: University — missing signed syllabus + missed weekly board.
# The effective term is form-only: the committee confirms credits and scope by
# mail, but the written effective-term conclusion is issued exclusively by the
# hidden credit-registration form; the registrar names the system only when
# asked about 登记 (a deny reply), and the dean's office misremembers where the
# syllabus is archived (suggest) before plainly denying (deny).
f = {"syllabus": fact("CS204-2026-v2-signed", "CS204课程正式签章大纲版本为CS204-2026-v2-signed。"),
     "credits": fact(3, "学分委员会确认CS204可转换3学分。"), "scope": fact("专业选修", "这3学分仅计入专业选修，不能替代必修课。"),
     "effective": fact("2027春季", "该转换结论从2027春季学期开始适用。"),
     # 陷阱证据：开局即挂在联系页的学分认定口径给出高于真实的诱人学分
     # （真实为3学分），且院办不具备学分结论的签发权限（正式结论由学分
     # 委员会2027年春季审议出具），引用会被拒绝，直接采信该值也错。
     "credits_ref": fact(4, "CS204学分认定情况：按现行认定口径，CS204可转换4学分（留存方整理）。",
                         unauthorized_attestation=True)}
a = [person("records", "澄川学院教务·唐宁", "学分转换预审", "office", [workflow("学分转换咨询", ["学分", "转换", "大纲"], ["course_code", "syllabus_version"], [lookup([], business(180), "核验签章与材料版本"), acknowledge(business(60), "发出受理回执"), delegate("board", business(60), ["course_code", "syllabus_version"]), reply(business(60))], evidence_fields={"syllabus_version": "syllabus"}),
        workflow("正式登记渠道说明", ["登记", "登记系统", "正式登记", "系统"], [], [deny("跨校学分转换的正式登记不在我处柜台办理：请通过澄川学院学分转换登记系统（chengchuan_credit_register）提交，登记须使用现行签章大纲版本，提交说明见办理入口页。")], id="register_channel"),
        workflow("大纲存档查询", ["存档", "大纲存档"], [], [deny("课程大纲不在教务存档范围，我处只做学分转换预审；签章大纲请向课程负责人索取。")], id="syllabus_archive")], "必须取得当前签章大纲；不能把旧大纲送交委员会；正式登记走登记系统。"),
     person("lecturer", "CS204课程负责人·梅芮", "签章课程大纲", "office", [workflow("补发正式大纲", ["大纲", "签章", "课程"], ["course_code"], [lookup(["syllabus"], business(120, not_before="2026-11-10T09:00:00+08:00")), document(["syllabus"], business(60)), reply()])], "11月6日至9日出差，11月10日恢复处理；只核准本课程材料。"),
     person("board", "澄川学院学分委员会秘书·程昕", "春季跨校学分审议", "office", [workflow("春季跨校审议", ["学分", "审议"], ["course_code", "syllabus_version"], [lookup(["credits", "scope"], {**weekly(1, "10:00", 120), "not_before": "2027-02-02T10:00:00+08:00"}), document(["credits", "scope"], business(0)), reply()])], "跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审；生效学期以正式登记结论为准。"),
     person("dean_office", "澄川学院院办教务处·柳汀", "成绩与学籍材料、文件存档查询", "office", [workflow("成绩与学籍材料受理", ["成绩单", "学籍", "成绩"], ["student_name"], [lookup([], business(60), "登记材料请求"), reply()]), workflow("文件存档查询", ["文件", "存档", "大纲"], [], [suggest("签章大纲的下落我记不准：可能在课程负责人梅芮处，也可能当时是教务唐宁经手送审的；建议您分别去信确认。另外我印象里CS204按认定口径能转4学分，错不了，供您参考，具体以委员会审议为准。", ["lecturer", "records"], business(30)), deny("经核实，院办存档范围只有成绩与学籍材料，课程大纲不在其中，我处无法出具；请以课程负责人或教务的答复为准。")], id="archive_search")], "只受理成绩单与学籍材料；课程大纲不在存档范围，误投会建议分别确认。")]
# The registrar attests the effective-term fact but never looks it up in a
# workflow: the only issuance channel is the hidden credit-registration form.
a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) | {"effective"})
TASKS.append(task("DSB-03", "学分转换：秋季补件与春季集中审议", "高校教务", "2026-11-05T14:00:00+08:00", "2027-02-09T17:00:00+08:00",
    "确认CS204能转换多少学分、计入哪类课程、何时生效。我目前只有旧大纲，需要向课程负责人获取正式版本。请获得教务的书面结论，生效学期须取得登记办结的书面结论，不提交正式选课变更。",
    {"course_code": "CS204"}, [],
    [page("faculty-intro", "澄川学院CS204课程简介", "CS204为本学期开设课程，签章材料由课程负责人管理。跨校转换在2027年2月2日10点春季委员会集中审议；秋季预审不等于最终批准。", [], "CS204课程与跨校学分转换安排说明。"),
     document_page("faculty", "澄川学院联系方式", "学分转换预审联系教务唐宁。CS204课程签章大纲的下落各说不一：可能在课程负责人梅芮处，也可能在院办教务处存档，请分别确认后再办理。本页另挂有CS204学分认定情况等文件。", ["records", "dean_office"], "教务与院办的对接说明；大纲下落需分别确认。",
                   [doc("faculty-credit-estimate", "CS204学分认定情况.pdf", "澄川学院CS204学分认定情况：按现行认定口径，CS204可转换4学分。（留存方整理）", facts=["credits_ref"], issuer="dean_office")]),
     page("faculty-entry", "澄川学院学分转换登记", "澄川学院学分转换办理说明：办理需提供课程代码与现行签章大纲版本；跨校转换须经预审并送春季委员会集中审议，生效学期的书面结论通过本页登记表单申请后取得。本页面仅说明材料要求，不能在线提交选课变更。", [], "澄川学院学分转换材料要求与登记表单说明；不支持在线提交选课变更。",
          form=web_form("credit_form", "跨校学分转换登记",
                        [form_field("course_code", "课程代码"), form_field("syllabus_version", "现行签章大纲版本")],
                        "本表单不能在线直接提交：须通过学院学分转换登记系统办理；系统名称与提交要求请向教务唐宁咨询。"))], f, a,
    [goal("syllabus_version", "CS204-2026-v2-signed", "syllabus"), goal("credits", 3, "credits"), goal("credit_scope", "专业选修", "scope"), goal("effective_term", "2027春季", "effective")],
    "eligible_with_scope_limit", [{"op": "visit_page", "page": "faculty"}, send("records", "咨询CS204学分转换", "credit"), send("dean_office", "请查询CS204课程签章大纲存档", "dean"), wait("dean"), send("lecturer", "请补发正式签章大纲", "syllabus"), wait("syllabus"), send("records", "补充正式大纲继续办理学分咨询", "credit", {"course_code": "CS204", "syllabus_version": "$fact:syllabus"}, followup="credit"), wait("credit"), send("records", "请告知正式登记渠道", "register"), wait("register"), {"op": "discover", "name": "chengchuan_credit_register"}, {"op": "tool", "name": "chengchuan_credit_register", "args": {"fields": {"course_code": "CS204", "syllabus_version": "$fact:syllabus"}}}, {"op": "advance", "at": "2027-02-03T09:30:00+08:00"}],
    ["材料门槛", "角色出差不可用", "跨年度等待春季委员会", "跨人物证据传递", "联系方式页对大纲下落说法模糊", "院办猜测性指路与明确回绝", "隐藏登记系统与分阶段办结", "院办越权认定口径与口头误述"], ["猜测签章编号", "沿用2024年旧材料", "把材料预审当作春季批准", "只问一处就认定大纲下落", "把委员会结论当作已登记生效", "不发现登记渠道即认定无法登记", "引用院办学分认定口径当作有效学分结论", "把院办口头学分印象当结论"],
    extra_tools=("lookup_directory", "fetch_document", "request_callback"),
    hidden_tools=(hidden_tool("chengchuan_credit_register",
        "澄川学院学分转换登记系统。调用参数：fields为对象，键为表单字段名（course_code、syllabus_version），syllabus_version须填现行签章大纲版本。",
        "form", {"form": "credit_form", "expect": {"course_code": "CS204", "syllabus_version": "CS204-2026-v2-signed"},
                 "process_at": "2027-02-02T17:00:00+08:00",
                 "result_text": "学分转换登记已受理办结：该转换结论自2027春季学期开始适用；登记回执以本表单状态为准。",
                 "reject_text": "提交的课程代码或大纲版本与现行签章材料不符，已退回；请核对后重新提交。",
                 "facts": ["effective"], "issuer": "records",
                 "page_update": {"page": "faculty-entry", "snippet": "澄川学院学分转换登记：已提交的登记以表单状态为准。"}}),)))

# 04: Laboratory — safety certificate + supplies + non-working-hour calibration.
# The safety certificate is form-only: the safety officer no longer mails the
# record at all (a deny naming the record system), and the certificate is
# issued exclusively by the hidden training-record form; the desk misremembers
# who keeps training records (suggest) and the consumables clerk plainly
# denies responsibility (deny).
f = {"certificate": fact("SAFE-NOV06-482", "人员安全培训已完成，记录号SAFE-NOV06-482，可用于本次仪器使用咨询。"),
     # 陷阱证据：上月批次的合格记录已过有效期（valid_until=11月3日），
     # 且记录号与本期不同；评分会因过期与取值不符拒绝该证据。
     "cert_ref": fact("SAFE-OCT30-215", "上月（10月30日批次）安全培训合格记录SAFE-OCT30-215，有效期至2026年11月3日。", valid_until="2026-11-03T23:59:00+08:00"),
     "filter": fact("F-26B", "本次测量所需F-26B滤芯已到库。"), "window": fact("2026-11-25T13:00:00+08:00", "完成7天稳定性校准后，最早可用测量时段为11月25日13点。"),
     "price": fact(1800, "该样品批次测量报价1800元，尚未预约或扣费。")}
a = [person("labdesk", "南屿共享实验室前台·叶青", "使用条件与联系人", "office", [workflow("测量咨询入口", ["测量", "仪器", "联系"], [], [suggest("培训记录归谁管我说不准：可能是安全员温遥，也可能仪器管理员杜和那边留了登记，或者耗材库宋野能查到；建议您分别去信确认。另外我印象里这批进口滤芯11月10日就到库了，错不了，供您参考，到货情况请以耗材库核实为准。", ["safety", "instrument", "stores"], business(30)), refer(["safety", "instrument"], business(30)), reply()])], "先说明安全培训要求，再提供仪器管理员入口。", contact=["email", "phone"]),
     person("safety", "南屿实验室安全员·温遥", "安全培训与合格记录", "office", [workflow("培训记录确认", ["培训", "安全", "记录"], ["person_name"], [lookup([], {**weekly(4, "14:00", 120), "not_before": "2026-11-13T14:00:00+08:00"}, "完成培训批次"), deny("本期批次培训已结束，合格记录不随邮件发放：请通过南屿培训记录系统（nanyu_training_record）提交记录申请，批次安排与申请说明见官网安全培训安排细则文件。")])], "每周五14点培训；合格记录须经培训记录系统申请，不随邮件发放。"),
     person("instrument", "仪器管理员·杜和", "耗材、校准和使用窗口", "office", [workflow("测量可用时间与费用", ["测量", "仪器", "校准", "费用"], ["sample_id", "safety_certificate"], [acknowledge(business(30)), delegate("stores", business(60), ["sample_id"]), lookup([], elapsed(10080), "连续7天稳定性校准，可跨夜运行"), lookup(["window", "price"], business(240), "核对校准结果和使用窗口"), document(["window", "price"], business(30)), reply()])], "须核实培训凭证；耗材到库后才启动连续7天稳定性校准。"),
     person("stores", "耗材库管理员·宋野", "滤芯收货检查", "office", [workflow("核实滤芯到库", ["滤芯", "耗材"], ["sample_id"], [lookup(["filter"], business(120, not_before="2026-11-17T10:00:00+08:00")), reply()]), workflow("培训记录查询", ["培训记录", "培训"], [], [deny("我这里只负责耗材入库与收货检查，培训合格记录不归我管，也无从查询；请向安全员温遥确认，或按官网说明的记录渠道申请。")], id="training_record")], "本批供应商11月17日10点后送达，入库检查还需要2个工作小时；培训记录不在耗材库业务范围。")]
a[2]["workflows"][0]["evidence_fields"] = {"safety_certificate": "certificate"}
# The safety officer attests the certificate fact but never looks it up in a
# workflow: the only issuance channel is the hidden training-record form.
# cert_ref is the stale last-month record kept as a published decoy document.
a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"certificate", "cert_ref"})
TASKS.append(task("DSB-04", "共享仪器：培训、进口耗材与七天稳定性校准", "科研设施", "2026-11-04T09:30:00+08:00", "2026-11-27T17:00:00+08:00",
    "为样品S-482确认最早测量时间和费用。我已报名11月6日14点安全培训并会按时完成，但目前没有合格记录。请在培训完成后按官网说明的记录渠道取得凭证，并核实耗材和校准后的可用窗口，暂不预约仪器。",
    {"sample_id": "S-482", "person_name": "顾晓"}, [],
    [document_page("lab-intro", "南屿共享实验室简介", "仪器使用需安全培训记录，培训每周五14点。本批进口耗材预计11月17日到库，之后需要连续7天稳定性校准和人工复核。本页另挂有安全培训安排细则与培训合格记录等文件。", [], "共享仪器使用条件、培训批次与校准安排。",
                   [doc("lab-training-notice", "安全培训安排细则.pdf", "安全培训每周五14点举行，每批次约2小时。批次时间如有调整，以官网简介页最新公告为准；已报名批次的参训人须自行留意调整公告。合格记录不随邮件发放：参训人须通过南屿培训记录系统（nanyu_training_record）提交记录申请，处理结果以表单状态为准；批次调整情况可经南屿培训状态查询（nanyu_training_status）核对。"),
                    doc("lab-record-oct30", "安全培训合格记录（10月30日批次）.pdf", "南屿共享实验室安全培训合格记录（10月30日批次）：参训合格者记录号SAFE-OCT30-215，该记录有效期至2026年11月3日。（留存方整理）", facts=["cert_ref"], issuer="safety")]),
     page("lab", "南屿实验室联系方式", "各岗位联系人的联系方式（邮箱）请咨询前台叶青，由前台提供后续对接入口。使用条件与联系人请咨询前台叶青；安全培训记录联系安全员温遥；仪器校准、耗材和费用联系仪器管理员杜和。", ["labdesk"], "实验室各岗位对接说明。"),
     page("lab-entry", "南屿实验室安全培训记录申请", "南屿共享实验室仪器使用申请说明：申请需提供样品编号与安全培训记录号；安全培训合格记录通过本页申请表单取得，耗材到库后还需完成连续稳定性校准方可安排测量。本页面仅说明受理条件，不能在线预约仪器。", [], "南屿实验室仪器使用申请材料与培训记录表单说明；不支持在线预约。",
          form=web_form("lab_training_form", "安全培训记录申请",
                        [form_field("person_name", "参训人姓名"), form_field("training_date", "培训批次日期")],
                        "本表单不能在线直接提交：须通过实验室培训记录系统申请；系统名称与批次安排见官网安全培训安排细则文件。"))], f, a,
    [goal("safety_certificate", "SAFE-NOV06-482", "certificate"), goal("filter_batch", "F-26B", "filter"), goal("earliest_measurement", "2026-11-25T13:00:00+08:00", "window"), goal("price", 1800, "price")],
    "available_after_calibration", [{"op": "visit_page", "page": "lab"}, send("labdesk", "咨询测量仪器联系入口", "front"), wait("front"), send("safety", "请确认培训批次与记录领取方式", "safe"), {"op": "discover", "name": "nanyu_training_record"}, {"op": "tool", "name": "nanyu_training_record", "args": {"fields": {"person_name": "顾晓", "training_date": "2026-11-13"}}}, {"op": "advance", "at": "2026-11-13T16:30:00+08:00"}, wait("safe"), send("instrument", "核实测量时间、校准和费用", "measure", {"sample_id": "S-482", "safety_certificate": "$fact:certificate"}), wait("measure")],
    ["周五培训批次", "进口耗材批次到货", "连续7天设备过程", "校准结束后仍等待人员复核", "培训批次中途调整须复查页面", "隐藏培训记录表单与分阶段办结", "前台猜测性指路与耗材库明确回绝", "培训批次状态的隐藏时间线", "过期培训合格记录与前台到货口头误述"], ["7天连续运行误算为7个工作日", "有耗材就认为可测量", "伪造安全培训记录", "沿用已取消的11月6日批次安排", "不发现记录系统即认定无法取得凭证", "引用过期培训合格记录当作有效凭证", "把前台到货印象当耗材到库结论"],
    extra_tools=("fetch_document", "leave_note", "query_case_status"),
    hidden_tools=(hidden_tool("nanyu_training_record",
        "南屿共享实验室培训记录系统。调用参数：fields为对象，键为表单字段名（person_name、training_date），training_date须填实际参训的培训批次日期。",
        "form", {"form": "lab_training_form", "expect": {"person_name": "顾晓", "training_date": "2026-11-13"},
                 "process_at": "2026-11-13T16:00:00+08:00",
                 "result_text": "培训记录申请已办结：顾晓已完成11月13日批次安全培训，合格记录号SAFE-NOV06-482；办理进度可经南屿培训状态查询（nanyu_training_status）复核。",
                 "reject_text": "该日期无对应培训批次（或批次已取消），记录申请已退回；请核对最新批次安排后重新提交。",
                 "facts": ["certificate"], "issuer": "safety",
                 "page_update": {"page": "lab-entry", "snippet": "南屿实验室培训记录申请：已提交的申请以表单状态为准。"}}),
        hidden_tool("nanyu_training_status",
        "南屿培训状态查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "batch", "label": "安全培训批次安排",
                                "initial": "下一期安全培训批次：11月6日（周五）14点。",
                                "timeline": [{"at": "2026-11-05T09:00:00+08:00", "text": "原定11月6日批次已取消，下一期改至11月13日（周五）14点。"}]}]})),
    page_updates=[page_update("lab-intro", "2026-11-05T09:00:00+08:00",
        text="南屿共享实验室（11月5日更新）：原定11月6日（周五）14点安全培训批次因场地调整取消，改至11月13日（周五）14点举行。进口耗材预计11月17日到库，之后需连续7天稳定性校准和人工复核。仪器使用须持有效安全培训记录。")]))

# 05: Manufacturing — quote expires while waiting for QA.
# The dispatch conclusion is form-only: the planner verifies production and the
# MOQ by mail, but the written earliest-dispatch conclusion is issued
# exclusively by the hidden dispatch-precheck form; the sales reply guesses
# who keeps the channel (suggest), and both the planner's own dispatch reply
# and the QA desk plainly deny while naming the hidden channel.
f = {"quote_old": fact(18000, "500件批次旧报价18000元，有效至11月10日16点。", valid_until="2026-11-10T16:00:00+08:00"),
     "quote_new": fact(18600, "500件批次重新确认的总报价18600元，有效至12月11日16点。", available_at="2026-12-07T10:00:00+08:00", valid_until="2026-12-11T16:00:00+08:00"),
     # 陷阱证据：开局即挂在简介页的批次价目给出低于正式报价且在预算内的
     # 诱人总价，但排产员不具备报价签发权限（正式报价由销售出具），引用
     # 该证据会被拒绝；直接采信该值，与12月重新确认的正式报价相比也错。
     "quote_promo": fact(17900, "500件M26-Q7规格批次价目：促销总价17900元（留存方整理）。",
                         unauthorized_attestation=True),
     "moq": fact(500, "该规格最小订单量为500件。"), "dispatch": fact("2026-12-09", "如按有效报价下单，最早可于12月9日出库；本次尚未下单。"),
     "qa": fact(True, "材料M26批次符合用户要求的Q7检测规范，报告已复核。")}
a = [person("sales", "棱川制造销售·罗岑", "批次报价", "office", [workflow("初次报价", ["初次报价", "询价", "报价"], ["quantity", "spec"], [suggest("出库和排产的事我不直接管：排产核对归排产员苏渝。出库的书面预核结论走哪个渠道我记不准，可能要问排产员，也可能质检傅黎那边留了登记渠道，建议您分别去信确认。另外这个规格我记得300件就能起订，错不了，供您参考，起订量请以排产核对为准。", ["factory", "qa"], business(30)), lookup([], business(60), "整理批次需求"), acknowledge(business(30)), delegate("factory", business(60), ["quantity", "spec"]), lookup(["quote_old"], business(120)), document(["quote_old"], business(60)), reply()]), workflow("刷新过期报价", ["重新确认报价", "刷新报价", "更新报价", "重新询价", "重新报价", "新报价", "再次报价", "有效报价", "当前有效", "报价过期", "报价已过期"], ["quantity", "spec"], [acknowledge(business(30)), lookup(["quote_new"], business(60, not_before="2026-12-07T10:00:00+08:00")), document(["quote_new"], business(0)), reply()], id="refresh")], "初次报价有有效期；质检完成后若已过期，需重新确认。"),
     person("factory", "棱川制造排产员·苏渝", "原料与排产核对", "factory", [workflow("排产可行性", ["排产"], ["quantity", "spec"], [lookup(["moq"], business(1440)), reply()]), workflow("出库结论渠道", ["出库", "预核"], [], [deny("出库的书面预核结论不随邮件出具：请通过棱川出库预核登记渠道（lengchuan_dispatch_apply）提交登记，办结结论以表单状态为准；办理进度可经棱川出库进度查询（lengchuan_dispatch_status）复核。")], id="dispatch_channel")], "工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时；出库预核结论须经登记渠道申请。"),
     person("qa", "棱川制造质检·傅黎", "材料检测报告", "office", [workflow("材料Q7报告", ["质检", "报告", "Q7"], ["spec"], [acknowledge(business(30)), lookup([], elapsed(40320), "28天耐久性测试"), lookup(["qa"], weekly(0, "10:00", 120)), document(["qa"], business(0)), reply()]), workflow("出库询问", ["出库", "预核"], [], [deny("出库与排产安排不归质检管，我处只出具材料检测报告；出库预核请向排产员苏渝确认，或通过棱川出库预核登记渠道（lengchuan_dispatch_apply）申请。")], id="dispatch_query")], "样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。")]
# The planner attests the dispatch fact but never looks it up in a workflow:
# the only issuance channel is the hidden dispatch-precheck form.
a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"dispatch"})
TASKS.append(task("DSB-05", "制造采购：28天耐久测试后重新询价", "制造供应链", "2026-11-03T14:00:00+08:00", "2026-12-09T17:00:00+08:00",
    "询问棱川制造500件M26规格产品的有效总报价、最小订单量、最早出库时间，并取得Q7质检结果。报告完成时仍需有效报价，预算19000元；不要下单。",
    {"quantity": 500, "spec": "M26-Q7"}, [],
    [document_page("supplier-intro", "棱川制造简介", "棱川制造承接批次制造。报价有效期短于28天耐久性测试；测试结束后的周一10点复核报告。销售与质检可并行咨询，报告完成后应重新确认报价。本页另挂有批次价目等文件。", [], "批次制造、耐久测试与报价有效期说明。",
                   [doc("supplier-promo-ref", "500件M26批次价目.pdf", "棱川制造500件M26-Q7规格批次价目：促销总价17900元。（留存方整理）", facts=["quote_promo"], issuer="factory")]),
     page("supplier", "棱川制造联系方式", "批次报价联系销售罗岑；材料检测报告联系质检傅黎。", ["sales", "qa"], "销售与质检对接说明。"),
     page("supplier-entry", "棱川制造采购询价入口", "棱川制造采购询价说明：询价需提供数量与规格；质检确认需材料批次规格；报价有有效期，过期后需重新确认；批次出库的书面预核结论通过本页登记表单申请后取得。本页面仅说明材料要求，不能在线下单。", [], "棱川制造询价与质检材料说明；不支持在线下单。",
          form=web_form("dispatch_form", "批次出库预核登记",
                        [form_field("quantity", "数量（件）"), form_field("spec", "规格")],
                        "本表单不能在线直接提交：须通过棱川出库预核登记渠道办理；渠道名称与受理安排以官网简介页最新公告为准。"))], f, a,
    [goal("current_total", 18600, "quote_new"), goal("minimum_quantity", 500, "moq"), goal("earliest_dispatch", "2026-12-09", "dispatch"), goal("qa_pass", True, "qa")],
    "within_budget_with_current_quote", [{"op": "visit_page", "page": "supplier"}, send("sales", "请给初次报价", "old"), send("qa", "请确认Q7质检报告", "qa"), wait("old"), wait("qa"), send("sales", "请重新确认报价，旧报价已过期", "new"), wait("new"), {"op": "discover", "name": "lengchuan_dispatch_apply"}, {"op": "tool", "name": "lengchuan_dispatch_apply", "args": {"fields": {"quantity": 500, "spec": "M26-Q7"}}}, {"op": "advance", "at": "2026-12-08T10:30:00+08:00"}, {"op": "discover", "name": "lengchuan_dispatch_status"}, {"op": "tool", "name": "lengchuan_dispatch_status", "args": {"query": "出库"}}],
    ["六天工厂日历与五天销售日历", "28天耐久测试与周一批次", "报价过期", "并行查询后再次联系", "新价目以官网页面文件形式发布", "隐藏出库预核表单与分阶段办结", "销售猜测性指路与质检明确回绝", "出库预核受理的隐藏时间线", "开局页面批次价目与销售起订量口头误述"], ["用18000元旧报价给结论", "等待质检期间不追踪有效期", "误以为查询等于下单", "不复查官网错过新价目文件", "不发现出库预核渠道即下结论", "引用开局页面批次价目当作有效报价", "把销售起订量印象当排产结论"],
    extra_tools=("fetch_document", "request_callback", "leave_note"),
    hidden_tools=(hidden_tool("lengchuan_dispatch_apply",
        "棱川制造出库预核登记渠道。调用参数：fields为对象，键为表单字段名（quantity、spec），取值按表单说明填写。",
        "form", {"form": "dispatch_form", "expect": {"quantity": 500, "spec": "M26-Q7"},
                 "process_at": "2026-12-08T10:00:00+08:00",
                 "result_text": "出库预核登记已办结：如按有效报价下单，最早可于12月9日出库；本次尚未下单。办理进度可经棱川出库进度查询（lengchuan_dispatch_status）复核。",
                 "reject_text": "登记信息与批次需求不符，已退回；请核对后重新提交。",
                 "facts": ["dispatch"], "issuer": "factory",
                 "page_update": {"page": "supplier-entry", "snippet": "棱川制造采购询价入口：已提交的出库预核登记以表单状态为准。"}}),
        hidden_tool("lengchuan_dispatch_status",
        "棱川出库进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "dispatch", "label": "批次出库预核登记",
                                "initial": "尚未查询到出库预核登记记录。",
                                "timeline": [{"at": "2026-11-24T09:00:00+08:00", "text": "12月排产批次已排定，出库预核登记开始受理。"}],
                                "form": "dispatch_form"}]})),
    page_updates=[page_update("supplier-intro", "2026-12-07T10:00:00+08:00",
        text="棱川制造（12月7日更新）：旧批次报价已于11月10日过期。最新500件M26批次价目见本页价目文件。报价有效期与质检复核节奏不变。批次出库的书面预核结论须通过棱川出库预核登记渠道（lengchuan_dispatch_apply）提交登记后取得，办理进度可经棱川出库进度查询（lengchuan_dispatch_status）复核。",
        documents=[doc("supplier-quote-2026-12", "12月批次价目文件.pdf", "500件M26-Q7规格批次总报价18600元，本价目自发布之日起有效至12月11日16点；此前批次报价均已过有效期。", facts=["quote_new"], issuer="sales"),
                   doc("supplier-promo-ref", "500件M26批次价目.pdf", "棱川制造500件M26-Q7规格批次价目：促销总价17900元。（留存方整理）", facts=["quote_promo"], issuer="factory")])]))

# 06: Warranty — missing receipt and technician/parts/return handoff.
# The earliest-visit conclusion is form-only: the engineer diagnoses the part
# and consults the parts desk by mail, but the written visit-window conclusion
# is issued exclusively by the hidden visit-precheck form; the support desk
# guesses who keeps the channel (suggest), and the engineer's own dispatch
# reply plainly denies while naming the hidden channel.
f = {"covered": fact(True, "设备SN-A731仍在本次合成保修条款覆盖范围内。"), "part": fact("G-42密封圈", "工程师诊断需要更换G-42密封圈。"),
     "cost": fact(0, "本次更换配件费用为0元。"),
     # 陷阱证据：开局即挂在简介页的维修收费标准给出具体工本费，本次设备
     # 实际在保修范围内（费用为0），且客服不具备费用结论的签发权限，引用
     # 该证据会被拒绝；直接采信260元，值本身也错。
     "cost_ref": fact(260, "维修收费标准：G-42密封圈工本费260元，适用于保修范围外的送修结算（留存方整理）。",
                      unauthorized_attestation=True),
     "visit": fact("2026-11-18T10:00:00+08:00", "核实返厂补货批次后，最早可上门时段为11月18日10点，尚未预约。")}
a = [person("support", "霁光电器客服·孟竹", "保修材料受理", "office", [workflow("保修及维修时间咨询", ["保修", "维修", "配件"], ["serial", "receipt"], [lookup(["covered"], business(60)), acknowledge(elapsed(0)), suggest("根据您的描述，机身接缝漏水常见原因是密封件老化，也可能是水路主板渗漏，具体原因要等工程师诊断才能确认；这类密封圈配件我记得要自费260元，错不了，供您参考，费用以核实结论为准。上门时段的书面结论走哪个渠道我也记不准，可能要问工程师，也可能零件库那边留了登记渠道。我先把设备情况转给工程师。", ["engineer", "parts"], business(30)), delegate("engineer", business(60), ["serial", "symptom"]), reply(business(60))])], "没有凭证不能判定覆盖；拿到诊断和库存后才报告可用时段。", contact=["email", "phone"]),
     person("engineer", "霁光工程师·韩则", "诊断与维修窗口", "engineer", [workflow("诊断故障", ["诊断", "维修"], ["serial", "symptom"], [lookup(["part"], weekly(3, "14:00", 120)), consult("parts", business(60), ["serial"], text="配件补货批次要到零件库核实，我先去问一下库存和费用，稍后回复您。"), reply()]), workflow("上门结论渠道", ["上门"], [], [deny("上门时段的书面结论不随邮件出具：请通过霁光上门时段登记渠道（jiguang_visit_register）提交预核登记，办结结论以表单状态为准；办理进度可经霁光上门进度查询（jiguang_visit_status）复核。")], id="visit_channel")], "仅周二、周四处理远程诊断和排期；周四14点集中诊断，补货后需复核型号和上门窗口。"),
     person("parts", "霁光零件库·纪桐", "配件与费用", "factory", [workflow("零件库存复核", ["库存", "配件"], ["serial"], [lookup(["cost"], business(960, not_before="2026-11-13T08:30:00+08:00")), reply()])], "原厂补货批次11月13日到库，需16个工作小时核验；周六办公、周日关闭。")]
# The engineer attests the visit fact but never looks it up in a workflow:
# the only issuance channel is the hidden visit-precheck form.
a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"visit"})
TASKS.append(task("DSB-06", "家电保修：等待原厂补货与工程师轮值", "售后服务", "2026-11-04T16:00:00+08:00", "2026-11-18T17:00:00+08:00",
    "设备SN-A731漏水。确认是否在保修范围、需要什么配件、配件费用、最早可上门时间。购机凭证R-731已在我手中，只咨询，不预约。",
    {"serial": "SN-A731", "receipt": "R-731", "symptom": "机身接缝漏水"}, [],
    [document_page("service-intro", "霁光电器售后简介", "霁光电器售后保修咨询需提供设备序列号和购机凭证；是否在保修范围以受理核实为准。工程师仅周二、周四处理远程诊断，维修窗口由工程师另行排期。本页另挂有维修收费标准等文件。", [], "霁光电器保修受理条件与工程师轮值说明。",
                   [doc("service-fee-table", "维修收费标准.pdf", "霁光电器维修收费标准：G-42密封圈工本费260元，适用于保修范围外的送修结算。（留存方整理）", facts=["cost_ref"], issuer="support")]),
     page("service", "霁光电器联系方式", "保修材料受理联系客服孟竹；诊断与维修窗口由工程师另行排期。", ["support"], "售后客服对接说明。"),
     page("service-entry", "霁光电器报修入口", "霁光电器报修说明：报修需提供设备序列号、购机凭证与故障描述；是否在保修范围以受理核实为准，维修由工程师另行排期；上门时段的书面结论通过本页登记表单申请后取得。本页面仅说明材料要求，不能在线预约维修。", [], "霁光电器报修材料说明；不支持在线预约。",
          form=web_form("visit_form", "上门维修时段预核登记",
                        [form_field("serial", "设备序列号"), form_field("symptom", "故障描述", required=False)],
                        "本表单不能在线直接提交：须通过霁光上门时段登记渠道办理；渠道名称与受理安排以官网简介页最新公告为准。"))], f, a,
    [goal("covered", True, "covered"), goal("replacement_part", "G-42密封圈", "part"), goal("part_cost", 0, "cost"), goal("earliest_visit", "2026-11-18T10:00:00+08:00", "visit")],
    "covered_pending_booking", [{"op": "visit_page", "page": "service"}, send("support", "请核实保修和维修安排", "repair", {"serial": "SN-A731", "symptom": "机身接缝漏水"}), send("support", "补充凭证后继续保修咨询", "repair", followup="repair"), {"op": "advance", "at": "2026-11-12T10:00:00+08:00"}, {"op": "discover", "name": "jiguang_visit_register"}, {"op": "tool", "name": "jiguang_visit_register", "args": {"fields": {"serial": "SN-A731", "symptom": "机身接缝漏水"}}}, wait("repair"), {"op": "advance", "at": "2026-11-18T08:30:00+08:00"}, {"op": "discover", "name": "jiguang_visit_status"}, {"op": "tool", "name": "jiguang_visit_status", "args": {"query": "上门"}}],
    ["缺材料状态与补件", "原厂批次补货", "工程师每周两天办公", "零件库周六办公", "多级转交后回传", "客服猜测性诊断与内部咨询延迟", "隐藏上门预核表单与分阶段办结", "客服猜测性指路与工程师明确回绝", "上门预核受理的隐藏时间线", "越权收费标准与客服费用口头误述"], ["漏凭证仍要求出结果", "库存到位即认为已预约", "忽略工程师周一不办公", "把客服的常见原因猜测当结论", "不发现上门登记渠道即凭口头答复下结论", "引用页面维修收费标准当作本次费用", "把客服费用印象当核实结论"],
    extra_tools=("query_case_status", "leave_note", "fetch_document", "check_schedule"),
    hidden_tools=(hidden_tool("jiguang_visit_register",
        "霁光电器上门时段登记渠道。调用参数：fields为对象，键为表单字段名（serial、symptom），取值按表单说明填写。",
        "form", {"form": "visit_form", "expect": {"serial": "SN-A731"},
                 "process_at": "2026-11-17T16:00:00+08:00",
                 "result_text": "上门时段预核登记已办结：核实返厂补货批次后，最早可上门时段为11月18日10点，尚未预约；办理进度可经霁光上门进度查询（jiguang_visit_status）复核。",
                 "reject_text": "登记信息与设备记录不符，已退回；请核对后重新提交。",
                 "facts": ["visit"], "issuer": "engineer",
                 "page_update": {"page": "service-entry", "snippet": "霁光电器报修入口：已提交的上门时段预核登记以表单状态为准。"}}),
        hidden_tool("jiguang_visit_status",
        "霁光上门进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "visit", "label": "上门时段预核登记",
                                "initial": "尚未查询到上门时段预核登记记录。",
                                "timeline": [{"at": "2026-11-13T09:00:00+08:00", "text": "原厂配件补货批次已到库核验，上门时段预核登记开始受理。"}],
                                "form": "visit_form"}]})),
    page_updates=[page_update("service-intro", "2026-11-13T09:00:00+08:00",
        text="霁光电器售后（11月13日更新）：原厂配件补货批次已到库核验。上门时段的书面结论须通过霁光上门时段登记渠道（jiguang_visit_register）提交预核登记后取得，办理进度可经霁光上门进度查询（jiguang_visit_status）复核；是否在保修范围以受理核实为准，维修由工程师另行排期。")],
    reply_delay=(12, 30)))

# 07: Archive — rights-holder succession review, then a separate digitization request.
# The fee conclusion is form-only: the front desk still names the rights
# contact by mail, but the written fee conclusion is issued exclusively by the
# hidden fee-registration form; the desk misremembers where fees are settled
# (suggest) before plainly denying (deny) and naming the hidden channel.
f = {"exhibit": fact(True, "图像ARC-71获准用于本次非商业实体展览。如需办理数字化交付，请将本确认结论随信提供给档案馆。"), "online": fact(False, "授权不包含网站或社交媒体公开发布。"),
     "fee": fact(800, "本次数字化和授权服务合计800元。"), "scan": fact(600, "可提供600dpi扫描件；文件用途仍受授权范围限制。"),
     # 陷阱证据：开局即挂在简介页的历史交付记录给出高于真实规格的诱人
     # 分辨率（真实为600dpi），且接待不具备扫描规格的签发权限（数字化组
     # 数月后才出具书面结论），引用会被拒绝，直接采信该值也错。
     "scan_ref": fact(1200, "同类档案历史交付记录：扫描分辨率1200dpi（留存方整理）。",
                      unauthorized_attestation=True)}
a = [person("archive", "北汀档案馆接待·关雨", "档案使用咨询", "office", [workflow("费用与权利联系人", ["档案", "费用", "联系人"], ["archive_id", "usage"], [lookup([], business(120), "登记咨询上下文"), refer(["rights"], business(30)), reply()]), workflow("取得许可后的数字化规格确认", ["数字化交付", "数字化", "扫描规格", "扫描分辨率", "扫描件"], ["archive_id", "exhibition_permission"], [acknowledge(business(60)), consult("digitizer", business(120), ["archive_id"], text="数字化规格要由数字化组核对，我先转过去确认，稍后把扫描规格回复您。"), reply(business(120))], id="digitize", evidence_fields={"exhibition_permission": "exhibit"}), workflow("费用核定渠道说明", ["费用核定", "缴费", "费用渠道"], [], [suggest("费用核定的具体渠道我记不太清：可能由数字化组一并核定，也可能权利方联络员那边先出费用单，建议您分别去信确认。", ["digitizer", "rights"], business(30)), deny("经核实，档案利用费用核定不随邮件逐案办理：请通过北汀档案馆费用核定登记渠道（beiting_fee_apply）提交申请，办结结论以表单状态为准；办理进度可经北汀费用进度查询（beiting_fee_status）复核。")], id="fee_channel"),
        # 迷惑答复：接待对扫描分辨率给出自信但错误的口头印象（真实规格
        # 为600dpi，与开局页面上的历史交付记录同为1200dpi诱人值），书面
        # 结论仍以数字化组的确认信为准。
        workflow("扫描规格口头印象", ["分辨率", "dpi"], [], [deny("分辨率我印象里现在的设备普遍都能出到1200dpi，历史交付也都是按1200dpi做的，错不了——不过接待不掌握数字化设备参数，这只是口头印象，没有书面依据；本次交付的扫描规格以数字化组的书面确认结论为准。")], id="scan_gossip")], "先提供权利联系人；权利继受确认后，申请人须携确认结果再次联系档案馆，才能转数字化组；费用核定须走登记渠道。"),
     person("rights", "权利方联络员·Alex Chen", "图像权利继受与用途确认", "new_york", [workflow("权利范围核实", ["授权", "使用", "权利"], ["archive_id", "usage"], [acknowledge(business(60)), lookup(["exhibit", "online"], business(480, not_before="2027-05-28T09:00:00-04:00")), document(["exhibit", "online"], elapsed(0)), reply()])], "权利继受文件在2027年5月28日集中核验；随后按纽约当地工作时间审查指定用途，结束时自动签发确认，此前不能批准。"),
     person("digitizer", "档案数字化员·林澈", "扫描规格", "office", [workflow("扫描质量核对", ["扫描", "规格"], ["archive_id"], [lookup([], elapsed(4320), "保护性数字化与图像恢复连续处理72小时"), document(["scan"], business(480)), reply()])], "扫描与图像恢复连续处理72小时，质量确认必须在工作时间完成。")]
# The front desk attests the fee fact but never looks it up in a workflow:
# the only issuance channel is the hidden fee-registration form.
a[0]["knowledge"] = sorted(set(a[0]["knowledge"]) | {"fee"})
TASKS.append(task("DSB-07", "档案使用：权利继受核验后重新启动数字化", "文化档案", "2026-11-05T15:00:00+08:00", "2027-06-11T17:00:00+08:00",
    "为2027年7月的非商业展览核实ARC-71图像的实体及网站用途权限，问清总费用与扫描分辨率。权利继受正在核验；取得权利方确认后请再次联系档案馆核实数字化交付。不付费、不发布。",
    {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"}, [],
    [document_page("archive-intro", "北汀档案馆简介", "档案馆提供档案数字化与授权服务。该图像处于权利继受核验期，境外联络方预计2027年5月28日集中核对文件。用途获确认后需申请人再次联系档案馆核实数字化交付，实体许可不自动包括网络用途。本页另挂有同类档案历史交付记录等文件。", [], "档案使用授权与数字化交付流程说明。",
                   [doc("archive-scan-ref", "同类档案历史交付记录（扫描规格）.pdf", "北汀档案馆同类档案历史交付记录：扫描分辨率1200dpi。（留存方整理）", facts=["scan_ref"], issuer="archive")]),
     page("archive", "北汀档案馆联系方式", "各岗位联系人的联系方式（邮箱）请咨询接待关雨，由接待提供后续对接入口。档案使用咨询联系接待关雨；权利继受确认由境外权利方联络员处理。", ["archive"], "档案馆接待对接说明。"),
     page("archive-entry", "北汀档案馆档案使用申请入口", "北汀档案馆档案使用申请说明：申请需提供档案编号与用途说明；取得权利方确认后须再次联系档案馆申请数字化交付，并随信附上权利方的书面确认结论；档案利用费用的核定结论通过本页登记表单申请后取得。本页面仅说明流程，不能在线取得许可。", [], "北汀档案馆档案使用申请材料说明；不支持在线取得许可。",
          form=web_form("fee_form", "档案利用费用核定登记",
                        [form_field("archive_id", "档案编号"), form_field("usage", "用途说明")],
                        "本表单不能在线直接提交：须通过北汀档案馆费用核定登记渠道办理；渠道名称与受理安排以官网简介页最新公告为准。"))], f, a,
    [goal("physical_exhibit_allowed", True, "exhibit"), goal("online_allowed", False, "online"), goal("total_fee", 800, "fee"), goal("scan_dpi", 600, "scan")],
    "physical_only", [{"op": "visit_page", "page": "archive"}, send("archive", "咨询档案费用与权利联系人", "front"), wait("front"), send("rights", "请确认两种用途的权利授权", "rights"), wait("rights"), send("archive", "许可收到后请确认数字化交付和扫描规格", "scan", {"archive_id": "ARC-71", "exhibition_permission": "$fact:exhibit"}), wait("scan"), {"op": "discover", "name": "beiting_fee_apply"}, {"op": "tool", "name": "beiting_fee_apply", "args": {"fields": {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"}}}, {"op": "advance", "at": "2027-06-08T10:30:00+08:00"}, {"op": "discover", "name": "beiting_fee_status"}, {"op": "tool", "name": "beiting_fee_status", "args": {"query": "费用"}}],
    ["跨年度权利继受核验", "纽约冬令时和夏令时", "取得许可后必须再次发起请求", "72小时图像恢复与人工验收", "官网进度页中途更新", "隐藏费用核定表单与分阶段办结", "接待猜测性指路与明确回绝", "费用核定受理的隐藏时间线", "接待越权历史交付记录与扫描规格口头误述"], ["等待期间擅自假定许可", "实体授权误推为网络授权", "收到许可后忘记重启数字化查询", "不发现费用核定渠道即认定费用未知", "引用接待历史交付记录当作扫描规格确认", "把接待分辨率口头印象当书面结论"],
    extra_tools=("leave_note", "query_case_status", "fetch_document", "request_callback"),
    hidden_tools=(hidden_tool("beiting_fee_apply",
        "北汀档案馆费用核定登记渠道。调用参数：fields为对象，键为表单字段名（archive_id、usage），取值按表单说明填写。",
        "form", {"form": "fee_form", "expect": {"archive_id": "ARC-71"},
                 "process_at": "2027-06-04T10:00:00+08:00",
                 "result_text": "费用核定登记已办结：本次数字化和授权服务合计800元；办理进度可经北汀费用进度查询（beiting_fee_status）复核。",
                 "reject_text": "登记信息与档案记录不符，已退回；请核对后重新提交。",
                 "facts": ["fee"], "issuer": "archive",
                 "page_update": {"page": "archive-entry", "snippet": "北汀档案馆档案使用申请入口：已提交的费用核定登记以表单状态为准。"}}),
        hidden_tool("beiting_fee_status",
        "北汀费用进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "fee", "label": "费用核定登记受理",
                                "initial": "尚未查询到费用核定登记记录。",
                                "timeline": [{"at": "2027-05-28T21:00:00+08:00", "text": "2027年度档案利用收费标准已更新，费用核定登记正常受理。"}],
                                "form": "fee_form"}]})),
    page_updates=[page_update("archive-intro", "2027-05-28T09:00:00-04:00",
        text="北汀档案馆（2027年5月28日更新）：图像ARC-71权利继受集中核验已完成，权利方确认结论可向权利方联络员索取。取得书面确认后请携确认结果再次联系档案馆办理数字化交付。档案利用费用核定须通过北汀档案馆费用核定登记渠道（beiting_fee_apply）提交登记后取得，办理进度可经北汀费用进度查询（beiting_fee_status）复核。")]))

# 08: Accessible accommodation — alternative providers, measurements unavailable on weekends.
# The rate/availability conclusion is form-only: the B desk no longer quotes
# the specified dates by mail (a deny naming the hidden channel), and the A
# desk misremembers who holds the measurement records (suggest with three
# candidates, only the facilities tech is right; the B-side candidates plainly
# deny any responsibility for A's records).
f = {"a_door": fact(72, "A旅舍现场复测净门宽72cm，旧网页88cm包含门框。"), "a_bath": fact(68, "A旅舍浴室通行净宽68cm。"),
     "b_door": fact(92, "B酒店指定无障碍房净门宽92cm。"), "b_bath": fact(85, "B酒店浴室通行净宽85cm。"),
     "b_available": fact(True, "11月14—16日指定无障碍房有可售房，尚未预订。"), "b_price": fact(2360, "11月14—16日两晚总房费2360元。"),
     # 陷阱证据：开局即挂在简介页的B酒店房型说明给出高于真实净门宽的
     # 诱人数值（真实为92cm，说明称96cm），但A旅舍前台不具备B酒店尺寸
     # 的签发权限（B酒店设施主管11月11日复测才出具），引用会被拒绝，
     # 直接采信该值也错。
     "b_door_ref": fact(96, "B酒店无障碍房型说明：无障碍房净门宽96cm（留存方整理）。",
                        unauthorized_attestation=True)}
a = [person("a_desk", "A旅舍前台·蓝心", "无障碍房咨询", "daily", [workflow("通行尺寸确认", ["无障碍", "轮椅", "尺寸"], ["wheelchair_width", "stay_dates"], [suggest("净宽具体多少我说不准，旧网页的88cm好像也包含门框；现场测量可能要问我们的设施员蒋延，也可能当时和B酒店那边一起复测过，或者B酒店设施主管郑砚那边留了记录，您可以直接去信问问。另外B酒店那个无障碍房我印象里净门宽有96cm，错不了，供您参考，具体以他们复测为准。", ["a_tech", "b_desk", "b_tech"], business(30)), delegate("a_tech", business(60), ["wheelchair_width"]), reply(business(30))])], "每天营业，但不能用旧网页尺寸替代现场复测。", contact=["email", "phone"]),
     person("a_tech", "A旅舍设施员·蒋延", "现场测量", "office", [workflow("现场通行测量", ["尺寸", "测量"], ["wheelchair_width"], [lookup(["a_door", "a_bath"], business(120)), document(["a_door", "a_bath"], business(0)), reply()])], "周末不在岗；测量记录区分净宽与含框宽度。"),
     person("b_desk", "B酒店预订咨询·米禾", "房态与费用", "daily", [workflow("房态与费用查询", ["房态", "价格", "费用", "房价", "总价"], ["stay_dates"], [lookup([], business(60), "登记房态核对请求"), deny("指定日期的房态与总价不随邮件逐案答复：请通过酒店房态报价核对渠道（wuzhang_rate_check）提交登记，办结后返回可售状态与两晚总价；办理进度可经无障碍住宿进度查询（wuzhang_lodging_status）复核。")]), workflow("无障碍复测确认", ["无障碍", "轮椅", "尺寸", "复测", "测量"], ["wheelchair_width", "stay_dates"], [acknowledge(business(30)), delegate("b_tech", business(30), ["wheelchair_width"]), reply(business(30))], id="measure", accept_after="2026-11-09T09:00:00+08:00", early_reply="指定房型的无障碍复测要按临近入住的排期统一安排，目前还未开始受理，您的来信我先登记。临近入住时再来信即可，届时按流程安排现场测量。"), workflow("A旅舍询问回绝", ["A旅舍"], [], [deny("A旅舍的测量记录与通行尺寸不归B酒店查询范围，我处只处理本酒店指定房型的咨询；请向A旅舍前台确认。")], id="a_query")], "房态与价格可以先查询，是否可通行须现场量测；无障碍复测按临近入住的排期受理。", contact=["email", "phone"]),
     person("b_tech", "B酒店设施主管·郑砚", "指定房型现场尺寸", "office", [workflow("指定房间量测", ["尺寸", "测量"], ["wheelchair_width"], [lookup(["b_door", "b_bath"], business(480, not_before="2026-11-11T10:00:00+08:00")), document(["b_door", "b_bath"], business(0)), reply()]), workflow("A旅舍询问回绝", ["A旅舍"], [], [deny("我这里只有B酒店指定房间的量测记录，A旅舍的尺寸不归我管；请向A旅舍前台确认。")], id="a_query")], "指定房间11月11日10点才能进入复测；不能用同楼层其他房间数据代替。")]
# The B desk attests the rate/availability facts but never looks them up in a
# workflow: the only issuance channel is the hidden rate-check form.
a[2]["knowledge"] = sorted(set(a[2]["knowledge"]) | {"b_available", "b_price"})
TASKS.append(task("DSB-08", "无障碍住宿：两家机构比较与延后的现场测量", "出行住宿", "2026-11-06T13:30:00+08:00", "2026-11-13T18:00:00+08:00",
    "在A旅舍和B酒店中选择11月14—16日两晚住宿，预算2600元。轮椅宽78cm，房门和浴室净宽均须至少80cm。获取实测尺寸，并确认合适酒店的房态和总价，不预订。",
    {"wheelchair_width": "78cm", "stay_dates": "2026-11-14/2026-11-16"}, [],
    [document_page("hotels-intro", "候选住宿简介", "A旅舍旧网页称门宽88cm；B酒店也有无障碍房。两家的前台每天办公，设施人员另有工作时段；B酒店指定房型的无障碍复测按临近入住统一排期。本页另挂有B酒店无障碍房型说明等文件。", [], "两家候选住宿概况与现场测量安排。",
                   [doc("hotels-b-door-ref", "B酒店无障碍房型说明.pdf", "B酒店无障碍房型说明：无障碍房净门宽96cm。（留存方整理）", facts=["b_door_ref"], issuer="a_desk")]),
     page("hotels", "候选住宿联系方式", "A旅舍前台蓝心；B酒店预订咨询米禾。现场测量分别由两家设施人员处理。", ["a_desk", "b_desk"], "两家前台对接说明。"),
     page("hotels-entry", "无障碍住宿预订入口", "无障碍住宿预订说明：确认A旅舍或B酒店的无障碍房型需提供轮椅宽度与入住日期；通行尺寸以现场复测为准；B酒店指定日期的房态与总价通过本页登记表单申请后取得。本页面仅说明材料，不能在线预订。", [], "A旅舍与B酒店无障碍房确认材料说明；不支持在线预订。",
          form=web_form("rate_form", "指定日期房态与报价核对登记",
                        [form_field("stay_dates", "入住日期"), form_field("room_type", "房型", required=False)],
                        "本表单不能在线直接提交：须通过酒店房态报价核对渠道办理；渠道名称与受理安排以官网简介页最新公告为准。"))], f, a,
    [goal("a_door_cm", 72, "a_door"), goal("a_bathroom_cm", 68, "a_bath"), goal("b_door_cm", 92, "b_door"), goal("b_bathroom_cm", 85, "b_bath"), goal("b_available", True, "b_available"), goal("b_total_price", 2360, "b_price")],
    "choose_b", [{"op": "visit_page", "page": "hotels"}, send("a_desk", "请现场核实无障碍尺寸", "a"), {"op": "advance", "at": "2026-11-07T10:30:00+08:00"}, {"op": "discover", "name": "wuzhang_rate_check"}, {"op": "tool", "name": "wuzhang_rate_check", "args": {"fields": {"stay_dates": "2026-11-14/2026-11-16"}}}, {"op": "advance", "at": "2026-11-09T09:30:00+08:00"}, send("b_desk", "请安排指定房型无障碍复测", "b_measure"), wait("a"), wait("b_measure"), {"op": "discover", "name": "wuzhang_lodging_status"}, {"op": "tool", "name": "wuzhang_lodging_status", "args": {"query": "房态"}}],
    ["周末接待与工作日技术岗", "并行联系两家机构", "B侧复测受理窗口（窗口外仅登记）", "房间特定可进入时间", "过期网页尺寸", "前台对测量归属说法含糊", "隐藏房态报价表单与分阶段办结", "前台猜测性指路与B侧明确回绝", "房态报价受理的隐藏时间线", "A侧留存的越权房型说明"], ["门框宽当净宽", "把登记回执当作已受理后不再跟进", "第一家回复后过早停止", "拿一个房型数据替代另一个", "把前台含糊说法当实测数据", "不发现房态核对渠道即下结论", "引用页面B酒店房型说明当作实测结论", "把A旅舍前台门宽印象当B酒店实测结论"],
    extra_tools=("check_schedule", "fetch_document", "leave_note"),
    hidden_tools=(hidden_tool("wuzhang_rate_check",
        "酒店房态报价核对渠道。调用参数：fields为对象，键为表单字段名（stay_dates、room_type），取值按表单说明填写。",
        "form", {"form": "rate_form", "expect": {"stay_dates": "2026-11-14/2026-11-16"},
                 "process_delay": 120, "calendar": "daily",
                 "result_text": "房态报价核对已办结：11月14—16日指定无障碍房有可售房，尚未预订；两晚总房费2360元。办理进度可经无障碍住宿进度查询（wuzhang_lodging_status）复核。",
                 "reject_text": "登记的入住日期与排期不符，已退回；请核对后重新提交。",
                 "facts": ["b_available", "b_price"], "issuer": "b_desk",
                 "page_update": {"page": "hotels-entry", "snippet": "无障碍住宿预订入口：已提交的房态报价核对以表单状态为准。"}}),
        hidden_tool("wuzhang_lodging_status",
        "无障碍住宿进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "rate", "label": "指定日期房态报价核对",
                                "initial": "尚未查询到房态报价核对登记记录。",
                                "timeline": [{"at": "2026-11-07T10:00:00+08:00", "text": "11月中旬房间排期已导入，指定日期房态报价核对开始受理。"}],
                                "form": "rate_form"}]})),
    page_updates=[page_update("hotels-intro", "2026-11-07T10:00:00+08:00",
        text="候选住宿简介（11月7日更新）：A旅舍旧网页门宽88cm包含门框，通行尺寸以现场复测为准；B酒店也有无障碍房。B酒店指定日期的房态与总价须通过酒店房态报价核对渠道（wuzhang_rate_check）提交登记后取得，办理进度可经无障碍住宿进度查询（wuzhang_lodging_status）复核。两家的前台每天办公，设施人员另有工作时段；B酒店指定房型的无障碍复测按临近入住统一排期。")],
    reply_delay=(20, 45)))

# 09: Public-service consultation — jurisdiction referral + two independent reviews.
# The joint-review conclusion is form-only: the environment consultant still
# collects the consultation receipt by mail, but the written category /
# documents / earliest-window conclusions are issued exclusively by the hidden
# joint-review registration form, whose name surfaces in the consultant's own
# deny reply. The service desk's jurisdiction guess names two candidates and
# only the land liaison is right — the environment consultant plainly denies
# any jurisdiction responsibility (a transfer back to the land liaison).
f = {"jurisdiction": fact("街区公共空间管理处", "拟用地点属于街区公共空间管理处管辖；不是私人场地。"),
     "category": fact("临时扩声活动预咨询", "拟议活动应按临时扩声活动进行预咨询分类，尚未受理正式申请。"),
     "documents": fact(["平面图", "时段说明", "声设备清单"], "需要准备平面图、时段说明和声设备清单。"),
     "earliest": fact("2027-01-04", "按年度窗口安排，最早可进入后续正式办理的日期是2027年1月4日；不是活动批准日期。"),
     "consultation_receipt": fact("CONSULT-DEC03-19", "本轮30天跨部门意见征集已结束，回执CONSULT-DEC03-19；需携回执申请12月28日联合分类复核。"),
     # 陷阱证据：开局即挂在简介页的办理口径给出比真实分类更省事的诱人
     # 归类（真实为临时扩声活动预咨询，需30天征集与联合复核），且咨询台
     # 不具备事项分类的签发权限（联合复核结论12月28日才出具），引用会
     # 被拒绝，直接采信该值也错。
     "category_ref": fact("一般户外活动备案", "北广场活动事项办理口径：扩声类活动按一般户外活动备案口径登记（留存方整理）。",
                          unauthorized_attestation=True)}
a = [person("service", "晴港政务咨询台·谢茵", "事项识别与管辖分流", "office", [workflow("活动事项咨询", ["活动", "办理", "管辖"], ["location", "sound_equipment"], [lookup([], business(60), "登记咨询上下文"), suggest("北广场这类开放场地的管辖我记不很准：可能归街区公共空间管理处，也可能要走活动环境咨询那边的口径，建议您分别去函确认。另外北广场带两只音箱的活动我印象里按一般户外活动备案登记就行，错不了，供您参考，具体以联合复核结论为准。", ["land", "sound"], business(30)), delegate("land", business(60), ["location"]), refer(["sound"], business(60)), reply()])], "只能进行预咨询，不生成许可；先核实管辖再转专门岗位。", contact=["email", "phone"]),
     person("land", "公共空间管理联络员·吴弈", "场地管辖核对", "office", [workflow("管辖材料复核", ["管辖", "场地"], ["location"], [lookup(["jurisdiction"], weekly(3, "10:00", 120)), document(["jurisdiction"], business(60)), reply()])], "每周四10点复核共享场地边界清单。"),
     person("sound", "活动环境咨询员·陆笙", "扩声事项分类和材料", "office", [workflow("意见征集阶段确认", ["征集", "扩声", "材料"], ["location", "sound_equipment"], [acknowledge(business(30)), lookup(["consultation_receipt"], business(60, not_before="2026-12-03T09:00:00+08:00")), document(["consultation_receipt"], elapsed(0)), reply()]),
        workflow("联合分类复核", ["联合复核", "最终分类"], ["location", "sound_equipment", "consultation_receipt"], [acknowledge(business(30)), deny("联合分类复核的书面结论不随邮件出具：请通过晴港联合复核登记渠道（qinggang_review_register）提交登记，登记须使用本轮意见征集回执编号，办结结论以表单状态为准；办理进度可经晴港复核进度查询（qinggang_review_status）复核。")], id="final", evidence_fields={"consultation_receipt": "consultation_receipt"}),
        workflow("管辖询问回绝", ["管辖归属", "场地归属"], [], [deny("场地管辖核对不归我处：我处只负责扩声事项分类与材料说明；管辖请向公共空间管理联络员吴弈确认。")], id="jurisdiction_query")], "本轮30天跨部门意见征集于12月3日汇总；申请人取得回执后须再次申请12月28日联合分类复核；复核书面结论须经登记渠道取得。")]
# The environment consultant attests the joint-review facts but never looks
# them up in a workflow: the only issuance channel is the hidden review form.
a[2]["knowledge"] = sorted(set(a[2]["knowledge"]) | {"category", "documents", "earliest"})
TASKS.append(task("DSB-09", "公共活动咨询：意见征集与年末联合复核", "公共服务", "2026-11-03T15:00:00+08:00", "2027-01-05T17:00:00+08:00",
    "为2027年1月晴港北广场的小型扩声活动询问主管机构、事项分类、应备材料和最早办理窗口。跟进意见征集并携回执再次申请联合复核，书面复核结论按对方说明的渠道取得。只做预咨询，不能写成已获许可；场景规则均为合成。",
    {"location": "晴港北广场", "sound_equipment": "使用两只扩声音箱"}, [],
    [document_page("service-intro", "晴港公共活动咨询简介", "拟办活动先核实管辖。本轮意见征集在12月3日汇总；携回执再次申请12月28日联合复核。正式办理窗口另行确认。本页另挂有北广场活动事项办理口径等文件。", [], "公共活动预咨询流程与时间安排。",
                   [doc("service-category-ref", "北广场活动事项办理口径.pdf", "北广场活动事项办理口径：扩声类活动按一般户外活动备案口径登记。（留存方整理）", facts=["category_ref"], issuer="service")]),
     page("service", "晴港公共活动咨询联系方式", "各岗位联系人的联系方式（邮箱）请咨询咨询台谢茵，由咨询台提供后续对接入口。事项识别与管辖分流联系咨询台谢茵；扩声事项分类与材料联系活动环境咨询员。", ["service"], "政务咨询台对接说明。"),
     page("service-entry", "晴港活动预咨询入口", "晴港公共活动预咨询说明：办理需提供活动地点与扩声设备说明；联合分类复核的书面结论通过本页登记表单申请后取得，登记须附意见征集回执编号。本页面为预咨询说明，不构成许可申请入口，许可须另行按正式流程申请。", [], "晴港公共活动预咨询材料说明与联合复核登记表单；不支持在线申请许可。",
          form=web_form("review_form", "联合分类复核登记",
                        [form_field("location", "活动地点"), form_field("sound_equipment", "扩声设备说明"), form_field("consultation_receipt", "意见征集回执编号")],
                        "本表单不能在线直接提交：须通过晴港联合复核登记渠道办理；渠道名称与受理安排请向活动环境咨询员确认。"))], f, a,
    [goal("responsible_office", "街区公共空间管理处", "jurisdiction"), goal("consultation_receipt", "CONSULT-DEC03-19", "consultation_receipt"), goal("case_category", "临时扩声活动预咨询", "category"), goal("required_documents", ["平面图", "时段说明", "声设备清单"], "documents"), goal("earliest_processing_date", "2027-01-04", "earliest")],
    "consultation_only_not_approval", [{"op": "visit_page", "page": "service"}, send("service", "请核实活动办理管辖", "front"), wait("front"), send("sound", "请确认本轮扩声意见征集及回执", "consult"), wait("consult"), send("sound", "请按回执进行联合复核和最终分类", "sound", {"location": "晴港北广场", "sound_equipment": "使用两只扩声音箱", "consultation_receipt": "$fact:consultation_receipt"}), wait("sound"), {"op": "discover", "name": "qinggang_review_register"}, {"op": "tool", "name": "qinggang_review_register", "args": {"fields": {"location": "晴港北广场", "sound_equipment": "使用两只扩声音箱", "consultation_receipt": "$fact:consultation_receipt"}}}, {"op": "advance", "at": "2026-12-28T16:00:00+08:00"}, {"op": "discover", "name": "qinggang_review_status"}, {"op": "tool", "name": "qinggang_review_status", "args": {"query": "复核"}}],
    ["先管辖后专业咨询", "30天跨部门征集期", "携回执再次发起联合复核", "跨年度后续办理窗口", "咨询台对管辖记忆模糊", "公示页中途更新", "隐藏联合复核登记表单与分阶段办结", "咨询台猜测性指路与扩声岗对管辖询问的明确回绝", "联合复核受理的隐藏时间线", "咨询台越权办理口径与分类口头误述"], ["咨询回执当许可证", "没有回执即跳过征集", "收到回执后不继续申请最终复核", "只凭咨询台猜测认定管辖", "把扩声岗当作管辖方反复追问", "不发现登记渠道即认定无法取得书面复核结论", "引用页面办理口径当作正式分类结论", "把咨询台分类口头印象当联合复核结论"],
    extra_tools=("request_callback", "fetch_document", "lookup_directory"),
    hidden_tools=(hidden_tool("qinggang_review_register",
        "晴港联合复核登记渠道。调用参数：fields为对象，键为表单字段名（location、sound_equipment、consultation_receipt），consultation_receipt须填本轮意见征集的回执编号。",
        "form", {"form": "review_form", "expect": {"consultation_receipt": "CONSULT-DEC03-19"},
                 "process_at": "2026-12-28T15:00:00+08:00",
                 "result_text": "联合复核登记已办结：拟议活动应按临时扩声活动进行预咨询分类，尚未受理正式申请；需准备平面图、时段说明和声设备清单；按年度窗口安排，最早可进入后续正式办理的日期是2027年1月4日。办理进度可经晴港复核进度查询（qinggang_review_status）复核。",
                 "reject_text": "登记信息与意见征集记录不符，已退回；请核对回执编号后重新提交。",
                 "facts": ["category", "documents", "earliest"], "issuer": "sound",
                 "page_update": {"page": "service-entry", "snippet": "晴港活动预咨询入口：已提交的联合复核登记以表单状态为准。"}}),
        hidden_tool("qinggang_review_status",
        "晴港复核进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "review", "label": "联合分类复核登记",
                                "initial": "尚未查询到联合复核登记记录。",
                                "timeline": [{"at": "2026-12-03T09:00:00+08:00", "text": "本轮30天跨部门意见征集已汇总结束，联合复核登记开始受理。"},
                                             {"at": "2026-12-28T10:00:00+08:00", "text": "12月28日联合分类复核批次已办理，复核结论以登记办结状态为准。"}],
                                "form": "review_form"}]})),
    page_updates=[page_update("service-intro", "2026-12-03T09:00:00+08:00",
        text="晴港公共活动咨询（12月3日更新）：本轮30天跨部门意见征集已汇总结束。回执可向活动环境咨询员申请取得；取得回执后须于12月28日申请联合分类复核，复核书面结论须经登记渠道取得。正式办理窗口另行确认。")]))

# 10: Individual seller — owner depends on a friend with weekend access to a reader.
# The inspection conclusion is form-only: the friend still runs the weekend
# read-out and hotshoe test, but only describes it verbally — the written
# measurements are issued exclusively by the hidden inspection-registration
# form, whose name surfaces in the friend's own deny reply. The seller
# misremembers who holds the written report (suggest with the friend and the
# courier desk as candidates); the courier desk plainly denies any
# responsibility for inspection reports.
f = {"asking": fact(3200, "卖方询价3200元，未承诺保留商品。"), "estimate": fact(10000, "卖方回忆快门约一万次，未经读取，不应视为实测。"),
     "actual": fact(42731, "对序列号CAM-402读取的实际快门次数为42731。"), "hotshoe": fact(False, "CAM-402热靴触发测试失败，当前不能正常使用外置闪光灯。"),
     "returns": fact("不支持退货", "卖方说明按现状转让，不支持退货。"), "pickup": fact("2026-11-09T14:00:00+08:00", "若交易成立，最早可取件时间为11月9日14点；本次仅查询。"),
     # 陷阱证据：开局即挂在简介页的同批次机型流通记录给出远低于本机
     # 实测且满足购买条件的诱人快门数（真实为42731次），但卖家不具备
     # 本机实测的签发权限（验机登记渠道周末办结才出具），引用会被拒绝，
     # 直接采信该值也错。
     "actual_ref": fact(9800, "同批次机型快门流通记录：快门次数约9800次（留存方整理）。",
                        unauthorized_attestation=True)}
a = [person("seller", "相机卖家·沈栖", "二手相机信息", "evening", [workflow("相机实测与条款", ["相机", "快门", "热靴", "实测"], ["serial"], [suggest("验机的书面结果我不直接掌握：朋友柯闻周末有读取器，测完可能直接答复；书面结论走哪个渠道我记不准，也可能桥溪快运取件咨询台能代查登记，建议您分别去信确认。另外这台机器我印象里快门也就一万次上下，错不了，供您参考，实测以验机办结为准。", ["friend", "courier"], business(30)), lookup(["asking", "estimate", "returns"], business(30)), acknowledge(business(30)), consult("friend", elapsed(0), ["serial"], text="我自己没有读取器，快门和热靴要先转给周末有设备的朋友实测，测完我把结果告诉您。"), refer(["courier"], business(0)), reply(business(30))])], "只在20—22点处理消息；没有读取器，需要请周末有设备的朋友实测；书面验机结果须经登记渠道取得。", contact=["email", "phone"]),
     person("friend", "卖家朋友·柯闻", "相机读取与热靴测试", "weekend", [workflow("读取相机与测试", ["相机", "实测"], ["serial"], [lookup([], business(120, not_before="2026-11-07T10:00:00+08:00"), "周末读取相机与热靴测试（仅口头说明）"), deny("实测数据不随邮件出具：请通过二手相机验机登记渠道（ershoushangji_inspection_apply）提交申请，办结结论以表单状态为准；办理进度可经二手验机进度查询（ershoushangji_inspection_status）复核。")])], "周末才能接触读取器；测试只对CAM-402有效；书面结果须经验机登记渠道取得。"),
     person("courier", "桥溪快运取件咨询·曾澜", "取件时段查询", "daily", [workflow("最早取件时间", ["取件", "快递"], ["pickup_area"], [lookup(["pickup"], business(60)), reply()]), workflow("验机报告询问回绝", ["验机", "报告"], [], [deny("我这里只查询取件时段，验机书面报告不归咨询台管；请向卖家沈栖或其朋友确认，或按官网说明的验机登记渠道申请。")], id="inspection_query")], "咨询台周末照常工作，只查询取件时段，不创建运单；验机报告不在受理范围。", contact=["email", "phone"])]
# The friend attests the measurement facts but never documents them in a
# workflow: the only issuance channel is the hidden inspection form.
a[1]["knowledge"] = sorted(set(a[1]["knowledge"]) | {"actual", "hotshoe"})
TASKS.append(task("DSB-10", "二手相机：夜间联系、周末实测与取件咨询", "个人交易咨询", "2026-11-06T10:00:00+08:00", "2026-11-10T22:00:00+08:00",
    "考虑购买CAM-402，要求快门少于30000次、热靴正常。请取得实测快门数和热靴结果（书面结果按对方说明的渠道取得），问清价格、退货条件和最早取件时段。不能付款或让卖方保留商品。",
    {"serial": "CAM-402", "pickup_area": "桥溪东区"}, ["seller"],
    [document_page("camera-intro", "CAM-402二手信息简介", "二手相机CAM-402出售：卖家自述快门约一万次，仅为回忆估计，实测情况待核；快门次数与热靴功能需实际读取和测试确认。卖家只在晚间处理消息。本页另挂有同批次机型快门流通记录等文件。", [], "二手相机出售信息与实测安排。",
                   [doc("camera-shutter-ref", "同批次机型快门流通记录.pdf", "同批次机型快门流通记录：快门次数约9800次。（留存方整理）", facts=["actual_ref"], issuer="seller")]),
     page("camera", "卖家联系方式", "各相关方联系人的联系方式（邮箱）请咨询卖家沈栖，由卖家提供后续对接入口。相机咨询联系卖家沈栖；取件时段可联系桥溪快运咨询台。", ["seller"], "卖家与取件咨询对接说明。"),
     page("camera-entry", "二手相机交易咨询入口", "二手相机交易咨询说明：核实快门次数与热靴等实测情况需提供相机序列号，实测数据以读取结果为准，书面验机结论通过本页登记表单申请后取得。本页面仅说明信息要求，不能在线下单或付款。", [], "二手相机交易咨询材料说明与验机登记表单；不支持在线交易。",
          form=web_form("inspection_form", "验机结果登记申请",
                        [form_field("serial", "相机序列号")],
                        "本表单不能在线直接提交：须通过二手相机验机登记渠道办理；渠道名称与受理安排请向卖家朋友确认。"))], f, a,
    [goal("asking_price", 3200, "asking"), goal("measured_shutter", 42731, "actual"), goal("hotshoe_works", False, "hotshoe"), goal("return_policy", "不支持退货", "returns"), goal("earliest_pickup", "2026-11-09T14:00:00+08:00", "pickup")],
    "does_not_meet_requirements", [send("seller", "请核实相机快门热靴及实测条件", "camera"), {"op": "advance", "at": "2026-11-07T10:00:00+08:00"}, send("friend", "请提供相机CAM-402的实测结果", "friend", {"serial": "CAM-402"}), wait("friend"), {"op": "discover", "name": "ershoushangji_inspection_apply"}, {"op": "tool", "name": "ershoushangji_inspection_apply", "args": {"fields": {"serial": "CAM-402"}}}, {"op": "advance", "at": "2026-11-08T20:00:00+08:00"}, {"op": "discover", "name": "ershoushangji_inspection_status"}, {"op": "tool", "name": "ershoushangji_inspection_status", "args": {"query": "验机"}}, send("courier", "查询最早取件时段", "courier"), wait("courier"), wait("camera")],
    ["晚间个人可达性", "朋友周末才能测试", "周末快递咨询", "主观回忆与实测证据冲突", "内部转测的显式等待", "隐藏验机登记表单与分阶段办结", "卖家猜测性指路与取件咨询台明确回绝", "验机受理的隐藏时间线", "同批次机型流通记录与本机实测冲突"], ["接受卖方估计为实测", "朋友回复即认为卖家已承诺", "替用户作购买决定", "把朋友口头说明当书面实测结论", "不发现验机登记渠道即下结论", "把同批次机型流通记录当本机实测", "把卖家快门口头印象当实测结论"],
    extra_tools=("check_schedule", "request_callback", "fetch_document", "leave_note"),
    hidden_tools=(hidden_tool("ershoushangji_inspection_apply",
        "二手相机验机登记渠道。调用参数：fields为对象，键为表单字段名（serial），serial须填在售相机的序列号。",
        "form", {"form": "inspection_form", "expect": {"serial": "CAM-402"},
                 "process_at": "2026-11-08T10:00:00+08:00",
                 "result_text": "验机登记已办结：对序列号CAM-402读取的实际快门次数为42731；热靴触发测试失败，当前不能正常使用外置闪光灯。办理进度可经二手验机进度查询（ershoushangji_inspection_status）复核。",
                 "reject_text": "登记的序列号与在售相机不符，已退回；请核对后重新提交。",
                 "facts": ["actual", "hotshoe"], "issuer": "friend",
                 "page_update": {"page": "camera-entry", "snippet": "二手相机交易咨询入口：已提交的验机登记以表单状态为准。"}}),
        hidden_tool("ershoushangji_inspection_status",
        "二手验机进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "inspection", "label": "验机结果登记",
                                "initial": "尚未查询到验机登记记录。",
                                "timeline": [{"at": "2026-11-07T10:00:00+08:00", "text": "周末读取与热靴测试已开始，验机登记可提交。"},
                                             {"at": "2026-11-08T10:00:00+08:00", "text": "本轮周末验机已完成，登记结论以办结状态为准。"}],
                                "form": "inspection_form"}]})),
    reply_delay=(10, 30)))

# 11: Open-source — patch verification first, then a windowed release check.
# Information is deliberately dispersed: the quarterly rhythm lives on the
# intro page, the window date and the "filed via the maintainer" path on the
# FAQ page, the verified-patch linkage only as an indirect sentence, and the
# acceptance window edges nowhere (early mail gets a vague registration-only
# reply). The patience test sits after filing: an acknowledged multi-hop
# batch chain (release Tue batch -> upstream Thu batch -> back) with an ETA.
f = {"repro": fact(True, "提交的日志可重现在编译器C19下的兼容问题。"), "workaround": fact("commit-7bc2", "CI在commit-7bc2上验证该兼容问题已修复。"),
     "candidate": fact("1.4.2-rc1", "发布负责人确认当前仅有候选版1.4.2-rc1。", available_at="2027-02-09T20:00:00+08:00"),
     "stable": fact("尚无承诺日期", "正式稳定版没有承诺发布日期；候选版不能标为稳定版。", available_at="2027-02-09T20:00:00+08:00"),
     # 陷阱证据：开局即挂在贡献说明页的发布计划给出了诱人的具体日期
     # （真实结论为尚无承诺日期），但维护者不具备稳定版发布状态的签发
     # 权限（登记渠道才出具），引用会被拒绝，直接采信该值也错。
     "stable_ref": fact("2027-03-15", "星舟项目近期发布计划：稳定版预计2027年3月15日发布（留存方整理）。",
                        unauthorized_attestation=True)}
a = [person("maintainer", "星舟项目维护者·简川", "问题复现与补丁协调", "maintainer", [workflow("兼容问题确认", ["兼容", "复现", "日志", "补丁"], ["version", "compiler", "logs"], [lookup([], business(120), "核实最小复现上下文"), acknowledge(business(30)), delegate("ci", elapsed(0), ["version", "compiler", "logs"]), lookup([], business(60), "维护者复核CI结果"), reply(business(30))]),
        workflow("季度发布状态复核", ["季度发布", "候选版", "稳定版", "发布状态", "发布窗口"], ["version", "verified_commit"], [acknowledge(business(30)), delegate("release", elapsed(0), ["version"]), reply(business(30))], id="release_check", accept_after="2027-01-26T20:00:00+08:00", accept_before="2027-02-23T22:00:00+08:00", early_reply="本季度的发布核对还没开始受理，您的来信我先登记。等临近上游兼容窗口时再来信即可，届时按流程办理。", evidence_fields={"verified_commit": "workaround"}),
        # 迷惑答复：维护者对稳定版日期给出自信但错误的口头印象（真实结论
        # 为尚无承诺日期），正式结论仍以登记渠道的办结结论为准。
        workflow("稳定版日期口头印象", ["稳定版时间", "何时发布"], [], [deny("稳定版的日期我印象里2027年3月15日就能发布，错不了——不过维护者不掌握上游的发布承诺，这只是口头印象，没有书面依据；稳定版的书面结论须通过星舟发布状态登记渠道（xingzhou_release_register）申请后以办结结论为准。")], id="stable_gossip")],
     "只在周一三五20—22点处理；先给补丁验证结果；季度发布核对按上游窗口安排，未到窗口不予受理。"),
     person("ci", "星舟CI值守·自动检查器", "兼容性构建测试", "always", [workflow("48小时构建验证", ["构建", "验证"], ["version", "compiler", "logs"], [lookup(["repro", "workaround"], elapsed(2880)), document(["workaround"], elapsed(0)), reply()])], "仅返回真实配置内的构建结果；不会承诺发布。"),
     person("release", "星舟发布协调员·唐泊", "候选版发布状态", "release", [workflow("候选版核对", ["发布", "候选版"], ["version"], [lookup(["candidate"], {**weekly(1, "20:00", 120), "not_before": "2027-02-09T20:00:00+08:00"}), delegate("upstream", business(30), ["version"]), reply(business(30))])], "每季度上游兼容窗口核对候选版；稳定版状态须向上游委员会查证，不能自行答复。"),
     person("upstream", "上游发布委员会·秘书处", "稳定版状态归档", "upstream", [workflow("稳定版状态查证", ["稳定版"], ["version"], [lookup([], weekly(3, "20:00", 120), "集中查证稳定版归档状态（仅口头说明）"), reply()])], "每周四20—22点集中查证归档；不对项目外部直接受理；稳定版的书面结论须经登记渠道取得。")]
# The upstream committee attests the stable-release fact but never issues it in
# a workflow: the only issuance channel is the hidden release-registration
# form, whose name surfaces in the FAQ page update (2027-01-15).
a[3]["knowledge"] = sorted(set(a[3]["knowledge"]) | {"stable"})
TASKS.append(task("DSB-11", "开源兼容性：补丁验证后按窗口复核发布状态", "开源协作", "2026-11-07T20:30:00+08:00", "2027-03-10T23:00:00+08:00",
    "星舟1.4.1在C19编译器上失败，日志LOG-771已备好。先确认复现和验证过的补丁；再于2027年第一季度发布窗口跟进候选版与稳定版日期，稳定版书面结论按项目说明的登记渠道取得。中间补丁可用不代表本任务完成。不要合并或发布。",
    {"version": "1.4.1", "compiler": "C19", "logs": "LOG-771"}, [],
    [document_page("repo-intro", "星舟项目贡献说明", "维护者周一三五20—22点处理来信，CI连续运行48小时。项目按季度发布，每季度上游兼容窗口统一核对候选版与稳定版状态；补丁或候选版都不能当作稳定版。本页另挂有星舟项目近期发布计划等文件。", [], "开源项目维护安排与发布节奏说明。",
                   [doc("repo-stable-rumor", "星舟项目近期发布计划.pdf", "星舟项目近期发布计划：稳定版预计2027年3月15日发布。（留存方整理）", facts=["stable_ref"], issuer="maintainer")]),
     page("repo", "星舟项目联系方式", "兼容问题与补丁协调联系维护者简川；其余事项的对接入口见对应说明页。", ["maintainer"], "项目联系与对接说明。"),
     page("repo-faq", "星舟项目发布流程说明", "季度发布核对须通过维护者转交办理；本季上游兼容窗口为2027年2月9日20点。核实发布状态需关联已验证的补丁。本页仅作流程说明，不能在线合并或发布。", [], "季度发布核对流程与窗口说明。"),
     page("repo-entry", "星舟项目问题反馈入口", "提交兼容性问题需提供版本、编译器与日志编号；补丁验证与发布状态分别在不同阶段核实；发布状态的书面结论通过本页登记表单申请后取得。本页面仅说明材料，不能在线合并或发布。", [], "星舟项目问题提交材料说明与发布状态登记表单；不支持在线合并。",
          form=web_form("release_form", "发布状态登记申请",
                        [form_field("version", "项目版本"), form_field("verified_commit", "已验证补丁提交号")],
                        "本表单不能在线直接提交：须通过星舟发布状态登记渠道办理；渠道名称与受理安排以项目发布流程说明页最新公告为准。"))], f, a,
    [goal("reproduced", True, "repro"), goal("verified_patch", "commit-7bc2", "workaround"), goal("candidate_version", "1.4.2-rc1", "candidate"), goal("stable_release_date", "尚无承诺日期", "stable")],
    "workaround_available_stable_uncommitted", [{"op": "visit_page", "page": "repo"}, send("maintainer", "请核实兼容问题与补丁", "fix"), wait("fix"), {"op": "advance", "at": "2027-01-27T20:30:00+08:00"}, {"op": "discover", "name": "xingzhou_release_register"}, {"op": "tool", "name": "xingzhou_release_register", "args": {"fields": {"version": "1.4.1", "verified_commit": "$fact:workaround"}}}, send("maintainer", "请转交核实季度发布的候选版与稳定版状态", "release", {"version": "1.4.1", "verified_commit": "$fact:workaround"}), wait("release"), {"op": "advance", "at": "2027-02-26T20:30:00+08:00"}, {"op": "discover", "name": "xingzhou_release_status"}, {"op": "tool", "name": "xingzhou_release_status", "args": {"query": "发布"}}],
    ["志愿者离散晚间窗口", "48小时自动构建", "受理窗口外的来信仅登记不受理", "带ETA回执的多级批次等待", "候选版与稳定版分岗核实", "发布流程页中途更新受理窗口信息", "隐藏发布状态登记表单与分阶段办结", "稳定版书面结论仅经登记渠道签发", "发布登记受理的隐藏时间线", "页面发布计划与稳定版日期口头误述"], ["初步补丁可用就提前结束", "把登记回执当作已受理", "错过受理窗口", "把候选版证据当作稳定版结论", "杜撰稳定版承诺日期", "不复查发布流程页错过窗口信息", "不发现登记渠道即认定稳定版无书面结论", "引用页面发布计划当作稳定版承诺", "把维护者日期印象当书面结论"],
    extra_tools=("query_case_status", "leave_note", "fetch_document", "request_callback"),
    hidden_tools=(hidden_tool("xingzhou_release_register",
        "星舟发布状态登记渠道。调用参数：fields为对象，键为表单字段名（version、verified_commit），verified_commit须填已验证补丁的提交号。",
        "form", {"form": "release_form", "expect": {"version": "1.4.1", "verified_commit": "commit-7bc2"},
                 "process_at": "2027-02-09T20:00:00+08:00",
                 "result_text": "发布状态登记已办结：正式稳定版没有承诺发布日期；候选版不能标为稳定版。办理进度可经星舟发布进度查询（xingzhou_release_status）复核。",
                 "reject_text": "登记的版本或补丁提交号与已验证记录不符，已退回；请核对后重新提交。",
                 "facts": ["stable"], "issuer": "upstream",
                 "page_update": {"page": "repo-entry", "snippet": "星舟项目问题反馈入口：已提交的发布状态登记以表单状态为准。"}}),
        hidden_tool("xingzhou_release_status",
        "星舟发布进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "release", "label": "发布状态登记",
                                "initial": "尚未查询到发布状态登记记录。",
                                "timeline": [{"at": "2027-01-26T20:00:00+08:00", "text": "本季发布核对受理窗口（1月26日20点至2月23日22点）已开启，发布状态登记开始受理。"},
                                             {"at": "2027-02-09T20:00:00+08:00", "text": "上游兼容窗口已核对，登记办结结论以上游归档为准。"}],
                                "form": "release_form"}]})),
    page_updates=[page_update("repo-faq", "2027-01-15T20:00:00+08:00",
        text="季度发布核对须通过维护者转交办理；核实发布状态需关联已验证的补丁。本季发布核对受理窗口确定为2027年1月26日20点至2月23日22点，窗口外来信仅登记不受理；上游兼容窗口仍为2027年2月9日20点。发布状态的书面结论须通过星舟发布状态登记渠道（xingzhou_release_register）提交登记后取得，办理进度可经星舟发布进度查询（xingzhou_release_status）复核。本页仅作流程说明，不能在线合并或发布。")],
    reply_delay=(10, 30)))

# 12: Prototype held for classification review. Several active stages across 300 days.
# The long-review registration form deepens the intentional block: submission
# is always accepted (pending), but processing rides an evening-only weekly
# batch calendar far past the episode deadline, so even a fully documented
# registration never returns a conclusion — or a release — before the cutoff.
# The channel names surface in the FAQ page update (2027-03-20).
f = {"warehouse": fact("2026年11月已完成始发仓入库扫描", "PK-608的2026年11月始发仓入库记录已核实；这是历史交接记录，不能据此推断目前仍在始发仓或已获放行。"),
     "declaration": fact("DEC-608-v2", "已补发首轮DEC-608-v2资料，仅用于初审；作为继续受理凭证有效至2027年3月31日17点。", valid_until="2027-03-31T17:00:00+08:00"),
     "review_case": fact("HOLD-608-9", "境外原型设备归类初审登记号为HOLD-608-9；须取得制造批次溯源材料和新版单证后再次发起长期复核。登记不等于放行。"),
     "declaration_latest": fact("DEC-608-v3", "2027年4月6日补发DEC-608-v3，取代v2；作为继续受理凭证有效至2027年9月30日17点。", available_at="2027-04-06T10:00:00+08:00", valid_until="2027-09-30T17:00:00+08:00"),
     "batch_trace": fact("TRACE-M608-2027", "制造方历史批次记录已恢复核验，溯源资料号TRACE-M608-2027。", available_at="2027-04-06T10:00:00+08:00"),
     "release": fact("技术复核结果已返回，实际放行仍需另行确认", "2027年9月中旬技术复核窗口处理完成后，仅返回技术意见；该未来结果在本题截止前不可见。"),
     # 陷阱证据：开局即挂在简介页的口岸留置件登记记录含正确的初审登记
     # 号（HOLD-608-9），属"编号对但签发方越权"型——客服不具备初审登记号
     # 的签发权限（单证联络2027年2月窗口办理后才出具），引用会被拒绝。
     "review_case_ref": fact("HOLD-608-9", "口岸归类留置件登记记录：留置件归类初审登记号HOLD-608-9（留存方整理）。",
                             unauthorized_attestation=True)}
a = [person("forwarder", "远澄货运客服·白榆", "货件入库信息", "office", [workflow("货件状态与联系入口", ["物流", "货件", "入库", "状态"], ["tracking"], [acknowledge(business(30)), suggest("归类留置涉及的单证问题，我印象里要找出口方单证员；也可能仓库那边的扫描记录就能对上，建议您分别确认。", ["exporter", "warehouse"], business(30)), delegate("warehouse", business(60), ["tracking"]), refer(["exporter", "customsdesk"], business(30)), reply()])], "只能确认入库并提供申报联络入口，不把入库状态说成放行。", contact=["email", "phone"]),
     person("warehouse", "始发仓查件员·施瑾", "仓内扫描核对", "office", [workflow("入库扫描查证", ["扫描", "入库"], ["tracking"], [lookup(["warehouse"], business(120)), document(["warehouse"], business(60)), reply()]),
        # 迷惑答复：查件员对放行状态给出自信但错误的口头印象（真实状态
        # 为截止前未确认），真值须由单证联络按流程发起长期复核后才能确认；
        # 口头早于正式确认数月，时间差天然成立。
        workflow("放行状态口头印象", ["放行", "提货"], [], [deny("放行的事我印象里这批货今年年初就放行了，早都提走了，错不了——不过查件员不掌握放行状态，这只是口头印象，没有书面依据；放行状态须由单证联络按流程发起长期复核后确认，任何回执也不是放行证明。")], id="release_gossip")], "周末无人工查件；核对后出具扫描记录。"),
     person("exporter", "出口方单证员·贺悠", "更正单证与制造批次溯源", "office", [workflow("首轮更正单证", ["首轮", "申报", "更正"], ["tracking"], [acknowledge(business(30)), lookup(["declaration"], business(120, not_before="2026-12-07T10:00:00+08:00")), document(["declaration"], business(60)), reply()], accept_after="2026-11-24T09:00:00+08:00", early_reply="首轮更正单证的核验尚未开始，您的来信已登记。待补正资料进入可取状态后再来函，届时按流程办理。"), workflow("第二轮单证和批次溯源", ["第二轮", "新版单证", "批次溯源"], ["tracking", "review_reference"], [acknowledge(business(30)), lookup(["declaration_latest", "batch_trace"], business(120, not_before="2027-04-06T10:00:00+08:00")), document(["declaration_latest", "batch_trace"], business(60)), reply()], id="refresh", accept_after="2027-03-23T09:00:00+08:00", early_reply="制造批次档案的恢复核验尚未开始，您的来信已登记。档案恢复可核验后再来函办理第二轮单证与溯源。", evidence_fields={"review_reference": "review_case"})], "首轮更正资料12月7日可核验；取得归类初审登记后，2027年4月6日恢复的制造档案才能用于第二轮单证与批次溯源。"),
     person("customsdesk", "远澄单证联络·戴筠", "设备留置核查联络", "office", [workflow("归类初审登记", ["初审", "登记"], ["tracking", "declaration_version"], [acknowledge(business(30)), delegate("broker", business(60), ["tracking", "declaration_version"], workflow="preliminary"), reply(business(30))], accept_after="2027-01-21T09:00:00+08:00", early_reply="归类初审登记的集中办理窗口尚未开始，您的来信已登记。临近初审窗口时再来函，届时按流程办理。", evidence_fields={"declaration_version": "declaration"}), workflow("第二轮长期复核", ["长期复核", "放行状态"], ["tracking", "declaration_version", "review_reference", "batch_trace"], [acknowledge(business(30)), delegate("broker", business(60), ["tracking", "declaration_version", "review_reference", "batch_trace"]), reply(business(30))], id="final", evidence_fields={"declaration_version": "declaration_latest", "review_reference": "review_case", "batch_trace": "batch_trace"})], "原型设备因归类争议留置。初审登记后须用新版单证和溯源资料重新提交长期复核；旧单证过期后不能继续受理；任何登记都不是放行。"),
     person("broker", "境外代理·Morgan Lee", "原型设备归类与技术意见复核", "new_york", [workflow("归类初审", ["初审", "归类"], ["tracking", "declaration_version"], [lookup(["review_case"], business(120, not_before="2027-02-04T09:00:00-05:00")), document(["review_case"], elapsed(0)), reply()], id="preliminary"), workflow("长期技术复核", ["长期复核", "放行"], ["tracking", "declaration_version", "review_reference", "batch_trace"], [lookup(["release"], business(1440, not_before="2027-09-10T09:00:00-04:00")), document(["release"], business(0)), reply()])], "纽约工作日办公；初审窗口2027年2月4日，技术意见集中复核窗口9月10日。需补齐制造档案再受理；不是持续工作数月，也没有放行承诺。")]
TASKS.append(task("DSB-12", "跨境原型设备：300天内的初审、二次补件与未决放行", "跨境设备争议核查", "2026-11-06T15:00:00+08:00", "2027-09-02T15:00:00+08:00",
    "跟进因归类争议留置的科研原型设备PK-608。核实历史入库交接、取得初审登记号，按流程向出口方取得有效新版单证和制造批次溯源资料，再发起长期技术复核。汇报须于2027年9月2日15时及之后提交，结论须反映截至该时点的最新确认状态；若届时放行仍未确认，如实报告已完成步骤与待确认事项。不要把历史入库、初审登记或补件受理当成当前放行；不支付费用或作法律承诺。",
    {"tracking": "PK-608"}, [],
    [document_page("logistics-intro", "远澄货运简介与归类留置核查流程", "本合成场景有多阶段归类争议核查：留置货件先经客服核实历史入库交接；出口方分批次补发更正单证；归类初审登记与长期技术复核按既定窗口集中办理；补齐新版单证和制造批次溯源资料后方可发起长期复核。各阶段办理节奏与时间窗口见常见问题页。本页另挂有口岸归类留置件登记记录等文件。", [], "归类留置核查流程、初审登记与长期复核办理节奏说明。",
                   [doc("logistics-case-ref", "口岸归类留置件登记记录.pdf", "口岸归类留置件登记记录：留置件归类初审登记号HOLD-608-9。（留存方整理）", facts=["review_case_ref"], issuer="forwarder")]),
     page("logistics", "远澄货运联系方式与咨询入口", "各岗位联系人的联系方式（邮箱）请咨询客服白榆，由客服提供后续对接入口。货件状态与入库查询联系客服白榆；单证版本与批次溯源联系出口方单证员；初审登记与长期复核联系单证联络。", ["forwarder"], "客服、单证、登记、溯源、复核、放行状态等事项的联系入口。"),
     page("logistics-entry", "远澄货运留置核查办理入口与材料说明", "远澄货运留置核查办理说明：办理需提供运单号与有效申报单证版本；长期复核的登记受理通过本页登记表单提交；初审登记、长期复核与放行状态须由单证联络岗位发起，本页面仅说明材料，不能在线发起复核或支付费用。", [], "远澄货运留置核查材料、单证版本要求与长期复核登记表单说明；不支持在线发起复核或状态查询。",
          form=web_form("review_form", "长期复核登记申请",
                        [form_field("tracking", "运单号"), form_field("declaration_version", "有效申报单证版本"), form_field("review_reference", "归类初审登记号"), form_field("batch_trace", "制造批次溯源资料号")],
                        "本表单不能在线直接提交：须通过远澄长期复核登记渠道办理；渠道名称与受理安排以常见问题页最新公告为准。")),
     page("logistics-faq", "留置核查常见问题与术语说明", "常见问题：首轮更正单证预计2026年12月7日可取；归类初审登记窗口为2027年2月4日；制造批次档案预计2027年4月6日恢复核验，届时需更新单证并再次申请长期复核。归类初审登记号由单证联络岗位办理并出具，登记仅表示进入流程，不等于放行；申报单证版本以出口方单证员补发的有效版本为准，旧版本过期后不能继续受理；制造批次溯源资料由出口方提供，须在新版单证取得后一并提交；货件入库与历史扫描记录可经客服入口向始发仓查证；放行状态与长期复核结果须补齐新版单证和溯源资料后由单证联络发起查询，本站不提供在线查询，任何回执也不是放行证明。", [], "登记号、单证版本、批次溯源、入库扫描记录、状态查询、长期复核与放行等术语的办理去向说明。")], f, a,
    [goal("initial_warehouse_record", "2026年11月已完成始发仓入库扫描", "warehouse"), goal("review_reference", "HOLD-608-9", "review_case"), goal("declaration_version", "DEC-608-v3", "declaration_latest"), goal("batch_trace", "TRACE-M608-2027", "batch_trace"),
     {"key": "release_status", "status": "unconfirmed"}],
    "release_unconfirmed_at_deadline", [{"op": "visit_page", "page": "logistics"}, send("forwarder", "查询货件状态和联系入口", "front"), wait("front"), {"op": "advance", "at": "2026-11-25T09:30:00+08:00"}, send("exporter", "请补发首轮更正申报资料", "doc_v2"), wait("doc_v2"), {"op": "advance", "at": "2027-01-22T09:30:00+08:00"}, send("customsdesk", "请办理归类初审登记", "preliminary", {"tracking": "PK-608", "declaration_version": "$fact:declaration"}), wait("preliminary"), {"op": "advance", "at": "2027-03-24T09:30:00+08:00"}, send("exporter", "请取得第二轮新版单证及批次溯源", "doc_v3", {"tracking": "PK-608", "review_reference": "$fact:review_case"}), wait("doc_v3"), {"op": "discover", "name": "yuancheng_review_register"}, {"op": "tool", "name": "yuancheng_review_register", "args": {"fields": {"tracking": "PK-608", "declaration_version": "$fact:declaration_latest", "review_reference": "$fact:review_case", "batch_trace": "$fact:batch_trace"}}}, {"op": "discover", "name": "yuancheng_review_status"}, {"op": "tool", "name": "yuancheng_review_status", "args": {"query": "复核"}}, send("customsdesk", "请按新版材料发起长期复核并查询放行状态", "release", {"tracking": "PK-608", "declaration_version": "$fact:declaration_latest", "review_reference": "$fact:review_case", "batch_trace": "$fact:batch_trace"}), wait("release")],
    ["跨年度多轮事项", "定期归类初审窗口", "窗口前过早来信仅登记不受理", "旧单证过期与跨人物证据更新", "制造档案恢复后的第二轮补件", "纽约夏令时切换", "300天截止仍早于技术复核窗口", "客服对单证去向记忆模糊", "公告页中途更新", "隐藏长期复核登记表单与分阶段受理", "长期复核登记的隐藏时间线", "客服越权登记记录与仓库放行口头误述"], ["只发一条查询后等待300天", "过早来信只收登记回执便放弃", "拿旧单证或初审登记跳过第二轮补件", "把历史仓库记录当当前货位", "受理回执或未来技术意见当放行证明", "在截止时点前就'截止时状态'下结论", "只凭客服猜测认定单证去向", "把长期复核登记的'已提交待处理'当作复核已办结", "引用页面登记记录当初审登记号来源", "把查件员放行印象当放行结论"],
    extra_tools=("lookup_directory", "query_case_status", "fetch_document", "request_callback"),
    hidden_tools=(hidden_tool("yuancheng_review_register",
        "远澄货运长期复核登记渠道。调用参数：fields为对象，键为表单字段名（tracking、declaration_version、review_reference、batch_trace），取值按表单说明填写。",
        "form", {"form": "review_form", "expect": {"tracking": "PK-608", "review_reference": "HOLD-608-9"},
                 # 复核登记转入境外委员会每周一次的晚间集中批次，本集截止前
                 # 不可能排到办结：这正是放行状态保持未确认的前置原因之一。
                 "process_delay": 2880, "calendar": "upstream",
                 "result_text": "长期复核登记已转入集中技术复核批次：技术意见须待复核窗口办理完毕，放行状态仍须另行确认。",
                 "reject_text": "登记信息与留置核查记录不符，已退回；请核对后重新提交。",
                 "page_update": {"page": "logistics-entry", "snippet": "远澄货运留置核查办理入口与材料说明：已提交的长期复核登记以表单状态为准。"}}),
        hidden_tool("yuancheng_review_status",
        "远澄复核进度查询。调用参数：query为事项关键词（可省略）。",
        "status", {"records": [{"key": "review-608", "label": "PK-608长期复核登记",
                                "initial": "尚未查询到长期复核登记记录。",
                                "timeline": [{"at": "2027-02-04T22:00:00+08:00", "text": "归类初审登记窗口已办结，长期复核登记开始受理。"},
                                             {"at": "2027-08-16T09:00:00+08:00", "text": "长期技术复核定于2027年9月10日（纽约时间）集中办理；此前提交的登记仅确认材料收讫，不产生放行结论。"}],
                                "form": "review_form"}]})),
    page_updates=[page_update("logistics-faq", "2027-03-20T09:00:00+08:00",
        text="常见问题（2027年3月20日更新）：制造批次档案恢复核验已确认按期于2027年4月6日开放，届时可向出口方单证员申请新版单证与批次溯源资料；归类初审登记窗口维持2027年2月4日不变。长期复核的登记受理通过远澄长期复核登记渠道（yuancheng_review_register）提交，办理进度可经远澄复核进度查询（yuancheng_review_status）核对。登记不等于放行；申报单证版本以出口方单证员补发的有效版本为准；放行状态与长期复核结果须补齐新版单证和溯源资料后由单证联络发起查询，本站不提供在线查询，任何回执也不是放行证明。")],
    completion_class="bounded_unresolved"))


# Decoy facts deliberately share a goal's predicate so the resulting evidence
# "looks" admissible (issuer/subject/predicate all plausible); scoring still
# rejects it on issuer authority, expiry or value. These ids are never accepted
# as goal witnesses, so they can never be issued through a trusted workflow.
TRAP_PREDICATES = {
    "DSB-01": {"price_ref": "price"},
    "DSB-02": {"pet_ref": "pet"},
    "DSB-03": {"credits_ref": "credits"},
    "DSB-04": {"cert_ref": "certificate"},
    "DSB-05": {"quote_promo": "quote_new"},
    "DSB-06": {"cost_ref": "cost"},
    "DSB-07": {"scan_ref": "scan"},
    "DSB-08": {"b_door_ref": "b_door"},
    "DSB-09": {"category_ref": "category"},
    "DSB-10": {"actual_ref": "actual"},
    "DSB-11": {"stable_ref": "stable"},
    "DSB-12": {"review_case_ref": "review_case"},
}


def configure_scoring(item):
    """Author trusted attestation attributes; reference fact IDs are only witnesses."""
    subject = {"task": item["id"], "case": item["public"]["user_fields"]}
    predicates = {fid: goal["key"] for goal in item["goals"] for fid in goal.get("accepted_facts", [])}
    # Expired-quote variant: same predicate as the refreshed quote.
    if item["id"] == "DSB-05":
        predicates["quote_old"] = predicates["quote_new"]
    for fid, real in TRAP_PREDICATES.get(item["id"], {}).items():
        predicates[fid] = predicates[real]
    aliases = {
        "尚无承诺日期": ["尚未承诺正式稳定版发布日期", "未承诺发布日期", "暂无确定的发布日期", "not_committed", "暂无承诺日期"],
        "72小时内取消收取50%": ["三天内取消收取一半费用", "72小时内取消需支付50%的费用"],
        "专业选修": ["专业选修课"], "2027春季": ["2027年春季", "2027年春季学期"],
        "不支持退货": ["不可退货", "不接受退货"],
    }
    money = {"price", "rent", "deposit", "quote_old", "quote_new", "cost", "fee", "b_price", "asking"}
    def evidence_text_variants(fid):
        """The fact's written long-form text (with and without trailing
        punctuation) is a literal quote of the authoritative evidence: citing
        the original wording verbatim must never fail string matching."""
        text = str(item["facts"][fid].get("text", "")).strip()
        return [v for v in (text, text.rstrip("。.!？?")) if v and v != item["facts"][fid]["value"]]
    def normalization(fid):
        value = item["facts"][fid]["value"]
        if type(value) is bool:
            return {"type": "boolean"}
        if type(value) in (int, float):
            units = {"元": 1, "CNY": 1, "人民币": 1} if fid in money else {}
            if fid in {"a_door", "a_bath", "b_door", "b_bath"}:
                units = {"cm": 1, "厘米": 1, "m": 100, "米": 100, "mm": 0.1, "毫米": 0.1}
            if fid == "scan":
                units = {"dpi": 1}
            if fid == "moq":
                units = {"件": 1}
            if fid == "credits":
                units = {"学分": 1}
            return {"type": "number", "units": units}
        if isinstance(value, list):
            return {"type": "set"}
        if "T" in value and value[:4].isdigit():
            return {"type": "datetime"}
        if len(value) == 10 and value[4:5] == "-" and value[:4].isdigit():
            return {"type": "date"}
        return {"type": "text", "aliases": {value: aliases.get(value, []) + evidence_text_variants(fid)}}

    for fid, fact in item["facts"].items():
        fact["attributes"] = {"subject": subject, "predicate": predicates.get(fid, fid)}
    def requirement(fid):
        attrs = item["facts"][fid]["attributes"]
        return {**attrs, "authorities": ["attest:" + attrs["predicate"]], "normalization": normalization(fid)}
    for actor in item["actors"]:
        actor["evidence_authorities"] = sorted({"attest:" + item["facts"][fid]["attributes"]["predicate"] for fid in actor["knowledge"]})
        for flow in actor["workflows"]:
            flow["evidence_fields"] = {key: requirement(fid) for key, fid in flow.get("evidence_fields", {}).items()}
    for target in item["goals"]:
        if target.get("status") == "unconfirmed":
            target.clear()
            target.update({"key": "release_status", "status": "unconfirmed", "pending_condition": {
                "capability": "technical_review", "fields_equal": item["public"]["user_fields"],
                "required_evidence": [requirement(fid) for fid in ("declaration_latest", "review_case", "batch_trace")]}})
        else:
            fid = target["accepted_facts"][0]
            target["evidence_requirement"] = requirement(fid)
            target["normalization"] = normalization(fid)
            target["match"] = "evidence" if item["id"] == "DSB-12" and fid in {"declaration_latest", "review_case", "batch_trace"} else "expected"
    item["public"]["value_normalization"] = {g["key"]: {k: v for k, v in g["normalization"].items() if k != "aliases"}
                                              for g in item["goals"] if "normalization" in g}


def add_direct_review_path(item):
    if item["id"] != "DSB-12":
        return
    desk = next(a for a in item["actors"] if a["id"] == "customsdesk")
    broker = next(a for a in item["actors"] if a["id"] == "broker")
    final = next(w for w in desk["workflows"] if w["id"] == "final")
    main = next(w for w in broker["workflows"] if w["id"] == "main")
    main["capabilities"] = ["technical_review"]
    main["evidence_fields"] = dict(final["evidence_fields"])
    extra = person("customsdesk", desk["name"], desk["role"], "office", [
        workflow("材料齐备后转介境外代理直联", ["直联", "转介境外代理", "直接联系境外"], final["required_fields"],
                 [refer(["broker"], business(60)), reply()], id="direct_entry", evidence_fields=dict(final["evidence_fields"]))], desk["description"])
    desk["workflows"].extend(extra["workflows"])
    desk["tools"].update(extra["tools"])
    contact_page = next(p for p in item["public"]["pages"] if p["id"] == "logistics")
    contact_page["text"] += " 材料齐备后，也可向单证联络人申请转介境外代理，直接发起长期复核；材料门槛和处理窗口相同。"
    item["alternate_paths"] = "两条合法路径：由单证联络人内部转交，或材料核验后取得转介并直接联系境外代理。按同一复核能力、受理凭证和截止状态评分，不绑定人物ID或中间转交层数。"


def write_tasks():
    # Stratified design across time scales; not an empirical frequency model.
    horizon_design = {
        "DSB-01": (3, "短期", "周末关门与设备内部转交"),
        "DSB-02": (8, "中短期", "宠物周审与下一期货梯安排"),
        "DSB-03": (89, "中长期", "秋季材料预审与春季学分委员会"),
        "DSB-04": (21, "中短期", "进口耗材批次与7天连续稳定性校准"),
        "DSB-05": (34, "中长期", "28天耐久性测试、周审和过期报价更新"),
        "DSB-06": (13, "中短期", "原厂配件批次与每周两天的工程师轮值"),
        "DSB-07": (210, "长期", "权利继受核验后再次申请数字化"),
        "DSB-08": (5, "短期", "指定房间可进入时间与两机构交叉核实"),
        "DSB-09": (55, "中长期", "30天征询及年末联合分类复核"),
        "DSB-10": (2, "短期", "夜间个人联系与周末实测"),
        "DSB-11": (109, "长期", "短期修复后按季度受理窗口发起多级批次等待"),
        "DSB-12": (300, "长期", "原型设备归类争议、第二轮补件和未决技术复核"),
    }
    conclusion_options = {
        "DSB-01": {"suitable": "满足所有活动要求", "unsuitable": "存在不满足的必要条件", "unconfirmed": "信息不足"},
        "DSB-02": {"move_on_requested_date": "可在原定日期搬入", "requires_date_change": "须改变搬入日期", "not_eligible": "不满足租住条件", "unconfirmed": "信息不足"},
        "DSB-03": {"not_eligible": "不能转换", "eligible_with_scope_limit": "可转换但有课程范围限制", "eligible_without_scope_limit": "可转换且无范围限制", "unconfirmed": "信息不足"},
        "DSB-04": {"available_now": "已可使用", "unconfirmed": "尚未核实", "available_after_calibration": "校准完成后可用", "not_available": "不能使用"},
        "DSB-05": {"exceeds_budget": "超预算", "within_budget_with_current_quote": "有有效报价且预算内", "unconfirmed": "信息不足或报价已过期"},
        "DSB-06": {"not_covered": "不在覆盖范围", "covered_pending_booking": "在覆盖范围但尚未预约", "unconfirmed": "信息不足"},
        "DSB-07": {"physical_and_online": "实体与网络均获准", "physical_only": "仅实体用途获准", "not_permitted": "两种用途均不获准", "unconfirmed": "信息不足"},
        "DSB-08": {"choose_a": "A符合要求", "choose_b": "B符合要求", "both_suitable": "两家均符合", "neither_suitable": "两家均不符合", "unconfirmed": "信息不足"},
        "DSB-09": {"consultation_only_not_approval": "已获咨询结论，未获许可", "formal_approval_received": "已获正式许可", "unconfirmed": "信息不足"},
        "DSB-10": {"meets_requirements": "满足购买条件", "does_not_meet_requirements": "不满足购买条件", "unconfirmed": "信息不足"},
        "DSB-11": {"stable_release_available": "稳定版已可用", "workaround_available_stable_uncommitted": "有验证过的补丁，稳定版无承诺日期", "no_verified_fix": "没有验证过的修复", "unconfirmed": "信息不足"},
        "DSB-12": {"released": "已确认放行", "release_unconfirmed_at_deadline": "截止时放行尚未确认", "not_in_warehouse": "尚未入库"},
    }
    horizon_design.update(LATCH_HORIZON_DESIGN)
    conclusion_options.update(LATCH_CONCLUSION_OPTIONS)
    for scope in ("private", "public"):
        (ROOT / "tasks" / scope).mkdir(parents=True, exist_ok=True)
    for original in TASKS:
        item = deepcopy(original)
        add_direct_review_path(item)
        for page in item["public"]["pages"]:
            page["url"] = page_url(item["id"], page)
            for document in page.get("documents", []):
                document["url"] = f"https://{PAGE_SITES[item['id']]}.bench/files/{document['id']}.pdf"
        for update in item.get("page_updates", []):
            for document in update.get("documents", []):
                document["url"] = f"https://{PAGE_SITES[item['id']]}.bench/files/{document['id']}.pdf"
        configure_scoring(item)
        days, bucket, reason = horizon_design[item["id"]]
        item["horizon_design"] = {"reference_days": days, "stratum": bucket, "mechanism": reason,
                                  "distribution": "manually stratified approximately logarithmic"}
        item["public"]["conclusion_options"] = conclusion_options[item["id"]]
        item["public"]["answer_format"] = {"conclusion": "选择conclusion_options中的一个键",
            "claims": "每个answer_keys条目提供key、status=confirmed/unconfirmed、value和evidence_ids；value可采用声明的归一化表示；unconfirmed不填写value和evidence_ids。"}
        (ROOT / "tasks/private" / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        public = {**item["public"], "start_at": item["start_at"], "deadline_at": item["deadline_at"]}
        (ROOT / "tasks/public" / f"{item['id']}.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        directory = ROOT / "tasks/actors" / item["id"]
        directory.mkdir(parents=True, exist_ok=True)
        for actor in item["actors"]:
            bundle = {"private": True, "task_id": item["id"], "actor": actor,
                      "calendar": item["calendars"][actor["calendar"]],
                      "local_facts": {fid: item["facts"][fid] for fid in actor["knowledge"]},
                      "start_at": item["start_at"], "deadline_at": item["deadline_at"]}
            (directory / f"{actor['id']}.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(TASKS)} manually authored tasks and {sum(len(t['actors']) for t in TASKS)} actor configurations.")


# Tasks ported from the sibling LATCH_BENCH case corpus (cases/current/*.json):
# authored in latch_tasks.py with the same helpers, appended here so exports,
# validation, replay and card rendering treat them identically. latch_tasks
# never imports this module back (it would re-execute the whole file when run
# as a script); instead build() receives this module's globals so the shared
# email/phone allocation state stays single.
def merge_latch():
    global LATCH_HORIZON_DESIGN, LATCH_CONCLUSION_OPTIONS
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import latch_tasks
    latch_tasks.build(globals())
    TASKS.extend(latch_tasks.LATCH_TASKS)
    PAGE_SITES.update(latch_tasks.LATCH_PAGE_SITES)
    LATCH_HORIZON_DESIGN = latch_tasks.LATCH_HORIZON_DESIGN
    LATCH_CONCLUSION_OPTIONS = latch_tasks.LATCH_CONCLUSION_OPTIONS


merge_latch()


if __name__ == "__main__":
    write_tasks()
