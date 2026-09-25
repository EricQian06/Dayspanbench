"""Hand-authored scenarios. Helpers only serialize repeated schema, never invent tasks.

Run from the repository root: python3 scripts/author_tasks.py
Private task files and public agent briefs are deliberately exported separately.
"""

import itertools
import json
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
         mechanisms, failure_modes, completion_class="resolved", reply_delay=(120, 240)):
    return {"schema_version": "0.2", "task_set_version": "0.3.0", "id": id, "title": title, "domain": domain,
        "start_at": start, "deadline_at": deadline, "display_timezone": "Asia/Shanghai",
        "synthetic": True, "completion_class": completion_class, "calendars": CALENDARS,
        # Business minutes between a delivery and the recipient's first read:
        # handwritten per task, matching the scenario's service tempo.
        "reply_delay": list(reply_delay),
        "public": {"id": id, "title": title, "brief": brief, "user_fields": user_fields,
            "initial_contacts": initial, "pages": pages, "message_budget": 16,
            "authorization": "仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。",
            "answer_keys": [g["key"] for g in goals]},
        "facts": facts, "actors": actors, "goals": goals, "expected_conclusion": conclusion,
        "temporal_mechanisms": mechanisms, "failure_modes": failure_modes, "reference_actions": reference,
        "reference_is_privileged": True,
        "alternate_paths": "接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。"}


def page(id, title, text, contacts, snippet):
    return {"id": id, "title": title, "text": text, "contacts": contacts, "snippet": snippet}


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
    else:
        suffix = "contact"
    return f"https://{PAGE_SITES[task_id]}.bench/{suffix}"


TASKS = []

# 01: Venue — independent price and operations paths; weekend and two handoffs.
f = {"price": fact(10500, "11月13日18—21点，80人活动：场租9000元、服务费1500元，总价10500元。"),
     "cancel": fact("72小时内取消收取50%", "活动前72小时内取消收取总价的50%。"),
     "slot": fact(True, "11月13日18—21点场地有空档，80人容量可满足。"),
     "projector": fact(False, "投影设备11月13日全天维修，场地方也不能提供替代投影设备。")}
a = [person("reception", "禾岸会馆前台·陈芷", "对外咨询与转介", "office", [workflow("活动联系入口", ["活动", "场地", "联系"], [], [refer(["sales", "operations"], business(30)), reply()])], "只掌握联系人目录；不能承诺报价、档期或设备。", contact=["email", "phone"]),
     person("sales", "禾岸会馆销售·姚岚", "费用与取消条款", "office", [workflow("报价及取消条件", ["报价", "价格", "费用", "取消"], ["event_date", "headcount"], [lookup(["price", "cancel"], business(180)), document(["price", "cancel"], business(30)), reply()])], "报价必须带日期和人数；设备可用性需要运营确认。"),
     person("operations", "禾岸会馆运营·赵航", "档期核对和设备协调", "office", [workflow("档期与投影确认", ["档期", "投影", "设备", "可用"], ["event_date", "event_time"], [lookup(["slot"], business(60)), delegate("technician", business(60), ["event_date", "event_time"]), reply(business(30))])], "能够查档期；投影问题必须转给设备负责人。"),
     person("technician", "禾岸会馆设备主管·周敏", "设备维修计划", "office", [workflow("核对维修窗口", ["投影", "维修"], ["event_date"], [lookup(["projector"], business(240)), document(["projector"], business(0)), reply()])], "只有本岗位知道维修窗口；内部收到转交后进入自己的队列。")]
TASKS.append(task("DSB-01", "活动场地：跨周末确认设备与报价", "活动服务", "2026-11-06T10:00:00+08:00", "2026-11-10T18:00:00+08:00",
    "请核实禾岸会馆能否在11月13日18—21点接待80人，预算12000元，必须有投影。问清总费用、取消条款、档期和投影是否可用，附可核实的书面依据。",
    {"event_date": "2026-11-13", "event_time": "18:00-21:00", "headcount": 80}, [],
    [page("venue-intro", "禾岸会馆简介", "禾岸会馆提供活动场地租赁。旧版简介：8000元起，可容纳100人，有投影。具体档期和设施请通过联系方式页咨询。", [], "禾岸会馆活动场地简介：价格起点、容量与投影设备说明。"),
     page("venue", "禾岸会馆联系方式", "各岗位联系人的联系方式（邮箱）请咨询前台陈芷，由前台提供后续对接入口。办公时间周一至周五9—12、13—17点。前台陈芷负责对外咨询与转介；报价、档期与设备须由相应对接人确认。", ["reception"], "禾岸会馆对接人与办公时间。"),
     page("venue-entry", "禾岸会馆预约入口", "预约需提供活动日期、时段和人数；本页面仅说明所需信息，不能在线完成预约，请通过邮件与对接人确认。", [], "预约所需材料与办理说明；不支持在线预约。")],
    f, a, [goal("total_cost", 10500, "price"), goal("cancellation", "72小时内取消收取50%", "cancel"), goal("slot_available", True, "slot"), goal("projector_available", False, "projector")],
    "unsuitable", [{"op": "visit_page", "page": "venue"}, send("reception", "请提供活动场地的联系入口", "front"), wait("front"), send("sales", "请发报价和取消条款", "quote"), send("operations", "请核实档期和投影", "ops"), wait("quote"), wait("ops")],
    ["周末停办", "并行询价与设备确认", "跨岗位内部转交", "过时网页与当前事实冲突"], ["将8000元起当作总价", "未核实投影即判断适用", "把内部转交受理当作完成"]))

# 02: Individual landlord — evening responses + Friday property review.
f = {"rent": fact(5600, "月租5600元；这是信息咨询，不构成租约。"), "pet": fact(True, "已核准一只8公斤成年犬符合楼宇宠物规则。"),
     "deposit": fact(4000, "该房源押金4000元，不另收宠物押金。"), "moving": fact("2026-11-13T10:00:00+08:00", "11月11日公布的新一期货梯表显示12日无可用时段，最早可安排11月13日10点搬入。")}
a = [person("landlord", "房东·林霁", "出租房源咨询", "landlord", [workflow("租金、宠物和搬入条件", ["租房", "宠物", "入住", "搬入"], ["pet_weight", "move_date"], [lookup(["rent", "deposit"], business(60)), delegate("manager", business(0), ["pet_weight", "move_date"]), reply(business(30))])], "白天上班，只在19—21点处理消息；不会代物业批准宠物或货梯。", contact=["email", "phone"]),
     person("manager", "青栎公寓物业·许乔", "楼宇规则与货梯时段", "office", [workflow("宠物与搬入复核", ["宠物", "搬入"], ["pet_weight", "move_date"], [delegate("reviewer", business(60), ["pet_weight"]), lookup(["moving"], business(60, not_before="2026-11-11T09:00:00+08:00")), reply(business(30))])], "收到房东转交后提交周五审核；11月11日才开放新一期货梯表，之后核实搬入时间。"),
     person("reviewer", "青栎公寓规则审核员·丁悦", "宠物规则复核", "office", [workflow("周五规则审核", ["宠物", "规则"], ["pet_weight"], [lookup(["pet"], weekly(4, "14:00", 60)), reply()])], "每周五14点集中复核材料；错过批次进入下一周。")]
TASKS.append(task("DSB-02", "租房咨询：物业周审与新一期货梯表", "个人与物业", "2026-11-03T19:30:00+08:00", "2026-11-12T17:00:00+08:00",
    "我想11月12日搬入林霁的房子，带一只8公斤成年犬。问清租金、押金、宠物规则，以及最早可搬入时间；若12日不行请说明替代时间，暂不签约。",
    {"pet_weight": "8kg", "move_date": "2026-11-12"}, ["landlord"],
    [page("listing-intro", "青栎房源简介", "青栎公寓在租房源。房东通常19—21点回复。宠物需物业周五复核；11月11日开放新一期货梯表，才能确认下半月搬入时段。", [], "青栎在租房源概况与搬入安排说明。"),
     page("listing", "青栎房源联系方式", "出租咨询联系房东林霁；楼宇规则与货梯时段由青栎公寓物业处理。", ["landlord"], "房东与物业的对接说明。"),
     page("listing-entry", "入住办理入口", "入住需先确认宠物规则与货梯时段；本页面仅说明流程，不构成租约，也不能在线签约。", [], "入住条件说明；不支持在线签约。")],
    f, a, [goal("monthly_rent", 5600, "rent"), goal("deposit", 4000, "deposit"), goal("pet_allowed", True, "pet"), goal("earliest_move", "2026-11-13T10:00:00+08:00", "moving")],
    "requires_date_change", [send("landlord", "咨询租房、宠物及搬入条件", "housing"), wait("housing")],
    ["个人只在晚间回复", "机构白天办公", "固定周五审核", "新一期货梯表尚未开放"], ["把广告可养宠视为批准", "忽略房东与物业时间错位", "把11月12日误报为可搬入"], reply_delay=(60, 150)))

# 03: University — missing signed syllabus + missed weekly board.
f = {"syllabus": fact("CS204-2026-v2-signed", "CS204课程正式签章大纲版本为CS204-2026-v2-signed。"),
     "credits": fact(3, "学分委员会确认CS204可转换3学分。"), "scope": fact("专业选修", "这3学分仅计入专业选修，不能替代必修课。"),
     "effective": fact("2027春季", "该转换结论从2027春季学期开始适用。")}
a = [person("records", "澄川学院教务·唐宁", "学分转换预审", "office", [workflow("学分转换咨询", ["学分", "转换", "大纲"], ["course_code", "syllabus_version"], [lookup([], business(180), "核验签章与材料版本"), acknowledge(business(60), "发出受理回执"), delegate("board", business(60), ["course_code", "syllabus_version"]), reply(business(60))], evidence_fields={"syllabus_version": "syllabus"})], "必须取得当前签章大纲；不能把旧大纲送交委员会。"),
     person("lecturer", "CS204课程负责人·梅芮", "签章课程大纲", "office", [workflow("补发正式大纲", ["大纲", "签章", "课程"], ["course_code"], [lookup(["syllabus"], business(120, not_before="2026-11-10T09:00:00+08:00")), document(["syllabus"], business(60)), reply()])], "11月6日至9日出差，11月10日恢复处理；只核准本课程材料。"),
     person("board", "澄川学院学分委员会秘书·程昕", "春季跨校学分审议", "office", [workflow("春季跨校审议", ["学分", "审议"], ["course_code", "syllabus_version"], [lookup(["credits", "scope", "effective"], {**weekly(1, "10:00", 120), "not_before": "2027-02-02T10:00:00+08:00"}), document(["credits", "scope", "effective"], business(0)), reply()])], "跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审。")]
TASKS.append(task("DSB-03", "学分转换：秋季补件与春季集中审议", "高校教务", "2026-11-05T14:00:00+08:00", "2027-02-03T17:00:00+08:00",
    "确认CS204能转换多少学分、计入哪类课程、何时生效。我目前只有旧大纲，需要向课程负责人获取正式版本。请获得教务的书面结论，不提交正式选课变更。",
    {"course_code": "CS204"}, [],
    [page("faculty-intro", "澄川学院CS204课程简介", "CS204为本学期开设课程，签章材料由课程负责人管理。跨校转换在2027年2月2日10点春季委员会集中审议；秋季预审不等于最终批准。", [], "CS204课程与跨校学分转换安排说明。"),
     page("faculty", "澄川学院联系方式", "学分转换预审联系教务唐宁；CS204课程签章大纲联系课程负责人梅芮（11月6—9日出差）。", ["records", "lecturer"], "教务与课程负责人的对接说明。"),
     page("faculty-entry", "学分转换办理入口", "办理需提供课程代码与现行签章大纲版本；本页面仅说明材料要求，不能在线提交选课变更。", [], "学分转换材料要求；不支持在线提交。")], f, a,
    [goal("syllabus_version", "CS204-2026-v2-signed", "syllabus"), goal("credits", 3, "credits"), goal("credit_scope", "专业选修", "scope"), goal("effective_term", "2027春季", "effective")],
    "eligible_with_scope_limit", [{"op": "visit_page", "page": "faculty"}, send("records", "咨询CS204学分转换", "credit"), send("lecturer", "请补发正式签章大纲", "syllabus"), wait("syllabus"), send("records", "补充正式大纲继续办理学分咨询", "credit", {"course_code": "CS204", "syllabus_version": "$fact:syllabus"}, followup="credit"), wait("credit")],
    ["材料门槛", "角色出差不可用", "跨年度等待春季委员会", "跨人物证据传递"], ["猜测签章编号", "沿用2024年旧材料", "把材料预审当作春季批准"]))

# 04: Laboratory — safety certificate + supplies + non-working-hour calibration.
f = {"certificate": fact("SAFE-NOV06-482", "人员安全培训已完成，记录号SAFE-NOV06-482，可用于本次仪器使用咨询。"),
     "filter": fact("F-26B", "本次测量所需F-26B滤芯已到库。"), "window": fact("2026-11-25T13:00:00+08:00", "完成7天稳定性校准后，最早可用测量时段为11月25日13点。"),
     "price": fact(1800, "该样品批次测量报价1800元，尚未预约或扣费。")}
a = [person("labdesk", "南屿共享实验室前台·叶青", "使用条件与联系人", "office", [workflow("测量咨询入口", ["测量", "仪器", "联系"], [], [refer(["safety", "instrument"], business(30)), reply()])], "先说明安全培训要求，再提供仪器管理员入口。", contact=["email", "phone"]),
     person("safety", "南屿实验室安全员·温遥", "安全培训与合格记录", "office", [workflow("培训记录确认", ["培训", "安全", "记录"], ["person_name"], [lookup(["certificate"], weekly(4, "14:00", 120)), document(["certificate"], business(60)), reply()])], "每周五14点培训，结束后签发记录。"),
     person("instrument", "仪器管理员·杜和", "耗材、校准和使用窗口", "office", [workflow("测量可用时间与费用", ["测量", "仪器", "校准", "费用"], ["sample_id", "safety_certificate"], [delegate("stores", business(60), ["sample_id"]), lookup([], elapsed(10080), "连续7天稳定性校准，可跨夜运行"), lookup(["window", "price"], business(240), "核对校准结果和使用窗口"), document(["window", "price"], business(30)), reply()])], "须核实培训凭证；耗材到库后才启动连续7天稳定性校准。"),
     person("stores", "耗材库管理员·宋野", "滤芯收货检查", "office", [workflow("核实滤芯到库", ["滤芯", "耗材"], ["sample_id"], [lookup(["filter"], business(120, not_before="2026-11-17T10:00:00+08:00")), reply()])], "本批供应商11月17日10点后送达，入库检查还需要2个工作小时。")]
a[2]["workflows"][0]["evidence_fields"] = {"safety_certificate": "certificate"}
TASKS.append(task("DSB-04", "共享仪器：培训、进口耗材与七天稳定性校准", "科研设施", "2026-11-04T09:30:00+08:00", "2026-11-25T17:00:00+08:00",
    "为样品S-482确认最早测量时间和费用。我已报名11月6日14点安全培训并会按时完成，但目前没有合格记录。请在培训完成后取得凭证，并核实耗材和校准后的可用窗口，暂不预约仪器。",
    {"sample_id": "S-482", "person_name": "顾晓"}, [],
    [page("lab-intro", "南屿共享实验室简介", "仪器使用需安全培训记录，培训每周五14点。本批进口耗材预计11月17日到库，之后需要连续7天稳定性校准和人工复核。", [], "共享仪器使用条件、培训批次与校准安排。"),
     page("lab", "南屿实验室联系方式", "各岗位联系人的联系方式（邮箱）请咨询前台叶青，由前台提供后续对接入口。使用条件与联系人请咨询前台叶青；安全培训记录联系安全员温遥；仪器校准、耗材和费用联系仪器管理员杜和。", ["labdesk"], "实验室各岗位对接说明。"),
     page("lab-entry", "仪器使用申请入口", "申请需提供样品编号与安全培训记录号；本页面仅说明受理条件，不能在线预约仪器。", [], "仪器使用申请材料说明；不支持在线预约。")], f, a,
    [goal("safety_certificate", "SAFE-NOV06-482", "certificate"), goal("filter_batch", "F-26B", "filter"), goal("earliest_measurement", "2026-11-25T13:00:00+08:00", "window"), goal("price", 1800, "price")],
    "available_after_calibration", [{"op": "visit_page", "page": "lab"}, send("labdesk", "咨询测量仪器联系入口", "front"), wait("front"), send("safety", "请求完成培训并取得安全记录", "safe"), wait("safe"), send("instrument", "核实测量时间、校准和费用", "measure", {"sample_id": "S-482", "safety_certificate": "$fact:certificate"}), wait("measure")],
    ["周五培训批次", "进口耗材批次到货", "连续7天设备过程", "校准结束后仍等待人员复核"], ["7天连续运行误算为7个工作日", "有耗材就认为可测量", "伪造安全培训记录"]))

# 05: Manufacturing — quote expires while waiting for QA.
f = {"quote_old": fact(18000, "500件批次旧报价18000元，有效至11月10日16点。", valid_until="2026-11-10T16:00:00+08:00"),
     "quote_new": fact(18600, "500件批次重新确认的总报价18600元，有效至12月8日16点。", available_at="2026-12-07T10:00:00+08:00", valid_until="2026-12-08T16:00:00+08:00"),
     "moq": fact(500, "该规格最小订单量为500件。"), "dispatch": fact("2026-12-09", "如按有效报价下单，最早可于12月9日出库；本次尚未下单。"),
     "qa": fact(True, "材料M26批次符合用户要求的Q7检测规范，报告已复核。")}
a = [person("sales", "棱川制造销售·罗岑", "批次报价", "office", [workflow("初次报价", ["初次报价", "询价", "报价"], ["quantity", "spec"], [lookup([], business(60), "整理批次需求"), delegate("factory", business(60), ["quantity", "spec"]), lookup(["quote_old"], business(120)), document(["quote_old"], business(60)), reply()]), workflow("刷新过期报价", ["重新确认报价", "刷新报价", "更新报价"], ["quantity", "spec"], [lookup(["quote_new"], business(60, not_before="2026-12-07T10:00:00+08:00")), document(["quote_new"], business(0)), reply()], id="refresh")], "初次报价有有效期；质检完成后若已过期，需重新确认。"),
     person("factory", "棱川制造排产员·苏渝", "原料与排产核对", "factory", [workflow("排产可行性", ["排产", "出库"], ["quantity", "spec"], [lookup(["moq", "dispatch"], business(1440)), reply()])], "工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时。"),
     person("qa", "棱川制造质检·傅黎", "材料检测报告", "office", [workflow("材料Q7报告", ["质检", "报告", "Q7"], ["spec"], [lookup([], elapsed(40320), "28天耐久性测试"), lookup(["qa"], weekly(0, "10:00", 120)), document(["qa"], business(0)), reply()])], "样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。")]
TASKS.append(task("DSB-05", "制造采购：28天耐久测试后重新询价", "制造供应链", "2026-11-03T14:00:00+08:00", "2026-12-08T15:00:00+08:00",
    "询问棱川制造500件M26规格产品的有效总报价、最小订单量、最早出库时间，并取得Q7质检结果。报告完成时仍需有效报价，预算19000元；不要下单。",
    {"quantity": 500, "spec": "M26-Q7"}, [],
    [page("supplier-intro", "棱川制造简介", "棱川制造承接批次制造。报价有效期短于28天耐久性测试；测试结束后的周一10点复核报告。销售与质检可并行咨询，报告完成后应重新确认报价。", [], "批次制造、耐久测试与报价有效期说明。"),
     page("supplier", "棱川制造联系方式", "批次报价联系销售罗岑；材料检测报告联系质检傅黎。", ["sales", "qa"], "销售与质检对接说明。"),
     page("supplier-entry", "采购询价入口", "询价需提供数量与规格；质检确认需材料批次规格。本页面仅说明材料要求，不能在线下单。", [], "询价与质检材料说明；不支持在线下单。")], f, a,
    [goal("current_total", 18600, "quote_new"), goal("minimum_quantity", 500, "moq"), goal("earliest_dispatch", "2026-12-09", "dispatch"), goal("qa_pass", True, "qa")],
    "within_budget_with_current_quote", [{"op": "visit_page", "page": "supplier"}, send("sales", "请给初次报价", "old"), send("qa", "请确认Q7质检报告", "qa"), wait("old"), wait("qa"), send("sales", "请重新确认报价，旧报价已过期", "new"), wait("new")],
    ["六天工厂日历与五天销售日历", "28天耐久测试与周一批次", "报价过期", "并行查询后再次联系"], ["用18000元旧报价给结论", "等待质检期间不追踪有效期", "误以为查询等于下单"]))

# 06: Warranty — missing receipt and technician/parts/return handoff.
f = {"covered": fact(True, "设备SN-A731仍在本次合成保修条款覆盖范围内。"), "part": fact("G-42密封圈", "工程师诊断需要更换G-42密封圈。"),
     "cost": fact(0, "本次更换配件费用为0元。"), "visit": fact("2026-11-18T10:00:00+08:00", "核实返厂补货批次后，最早可上门时段为11月18日10点，尚未预约。")}
a = [person("support", "霁光电器客服·孟竹", "保修材料受理", "office", [workflow("保修及维修时间咨询", ["保修", "维修", "配件"], ["serial", "receipt"], [lookup(["covered"], business(60)), delegate("engineer", business(60), ["serial", "symptom"]), reply(business(60))])], "没有凭证不能判定覆盖；拿到诊断和库存后才报告可用时段。", contact=["email", "phone"]),
     person("engineer", "霁光工程师·韩则", "诊断与维修窗口", "engineer", [workflow("诊断故障", ["诊断", "维修"], ["serial", "symptom"], [lookup(["part"], weekly(3, "14:00", 120)), delegate("parts", business(60), ["serial"]), lookup(["visit"], business(180)), reply()])], "仅周二、周四处理远程诊断和排期；周四14点集中诊断，补货后需复核型号和上门窗口。"),
     person("parts", "霁光零件库·纪桐", "配件与费用", "factory", [workflow("零件库存复核", ["库存", "配件"], ["serial"], [lookup(["cost"], business(960, not_before="2026-11-13T08:30:00+08:00")), reply()])], "原厂补货批次11月13日到库，需16个工作小时核验；周六办公、周日关闭。")]
TASKS.append(task("DSB-06", "家电保修：等待原厂补货与工程师轮值", "售后服务", "2026-11-04T16:00:00+08:00", "2026-11-18T09:00:00+08:00",
    "设备SN-A731漏水。确认是否在保修范围、需要什么配件、配件费用、最早可上门时间。购机凭证R-731已在我手中，只咨询，不预约。",
    {"serial": "SN-A731", "receipt": "R-731", "symptom": "机身接缝漏水"}, [],
    [page("service-intro", "霁光电器售后简介", "保修咨询需序列号和购机凭证；工程师仅周二、周四处理远程诊断。", [], "保修受理条件与工程师轮值说明。"),
     page("service", "霁光电器联系方式", "保修材料受理联系客服孟竹；诊断与维修窗口由工程师另行排期。", ["support"], "售后客服对接说明。"),
     page("service-entry", "报修入口", "报修需提供设备序列号、购机凭证与故障描述；本页面仅说明材料要求，不能在线预约维修。", [], "报修材料说明；不支持在线预约。")], f, a,
    [goal("covered", True, "covered"), goal("replacement_part", "G-42密封圈", "part"), goal("part_cost", 0, "cost"), goal("earliest_visit", "2026-11-18T10:00:00+08:00", "visit")],
    "covered_pending_booking", [{"op": "visit_page", "page": "service"}, send("support", "请核实保修和维修安排", "repair", {"serial": "SN-A731", "symptom": "机身接缝漏水"}), send("support", "补充凭证后继续保修咨询", "repair", followup="repair"), wait("repair")],
    ["缺材料状态与补件", "原厂批次补货", "工程师每周两天办公", "零件库周六办公", "多级转交后回传"], ["漏凭证仍要求出结果", "库存到位即认为已预约", "忽略工程师周一不办公"], reply_delay=(60, 120)))

# 07: Archive — rights-holder succession review, then a separate digitization request.
f = {"exhibit": fact(True, "图像ARC-71获准用于本次非商业实体展览。"), "online": fact(False, "授权不包含网站或社交媒体公开发布。"),
     "fee": fact(800, "本次数字化和授权服务合计800元。"), "scan": fact(600, "可提供600dpi扫描件；文件用途仍受授权范围限制。")}
a = [person("archive", "北汀档案馆接待·关雨", "档案使用咨询", "office", [workflow("费用与权利联系人", ["档案", "费用", "联系人"], ["archive_id", "usage"], [lookup(["fee"], business(120)), refer(["rights"], business(30)), reply()]), workflow("取得许可后的数字化规格确认", ["数字化交付", "扫描规格"], ["archive_id", "exhibition_permission"], [delegate("digitizer", business(120), ["archive_id"]), reply(business(120))], id="digitize", evidence_fields={"exhibition_permission": "exhibit"})], "先提供费用和权利联系人；权利继受确认后，申请人须携确认结果再次联系档案馆，才能转数字化组。"),
     person("rights", "权利方联络员·Alex Chen", "图像权利继受与用途确认", "new_york", [workflow("权利范围核实", ["授权", "使用", "权利"], ["archive_id", "usage"], [lookup(["exhibit", "online"], business(480, not_before="2027-05-28T09:00:00-04:00")), document(["exhibit", "online"], elapsed(0)), reply()])], "权利继受文件在2027年5月28日集中核验；随后按纽约当地工作时间审查指定用途，结束时自动签发确认，此前不能批准。"),
     person("digitizer", "档案数字化员·林澈", "扫描规格", "office", [workflow("扫描质量核对", ["扫描", "规格"], ["archive_id"], [lookup([], elapsed(4320), "保护性数字化与图像恢复连续处理72小时"), document(["scan"], business(60)), reply()])], "扫描与图像恢复连续处理72小时，质量确认必须在工作时间完成。")]
TASKS.append(task("DSB-07", "档案使用：权利继受核验后重新启动数字化", "文化档案", "2026-11-05T15:00:00+08:00", "2027-06-07T17:00:00+08:00",
    "为2027年7月的非商业展览核实ARC-71图像的实体及网站用途权限，问清总费用与扫描分辨率。权利继受正在核验；取得权利方确认后请再次联系档案馆核实数字化交付。不付费、不发布。",
    {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"}, [],
    [page("archive-intro", "北汀档案馆简介", "档案馆提供档案数字化与授权服务。该图像处于权利继受核验期，境外联络方预计2027年5月28日集中核对文件。用途获确认后需申请人再次联系档案馆核实数字化交付，实体许可不自动包括网络用途。", [], "档案使用授权与数字化交付流程说明。"),
     page("archive", "北汀档案馆联系方式", "各岗位联系人的联系方式（邮箱）请咨询接待关雨，由接待提供后续对接入口。档案使用咨询联系接待关雨；权利继受确认由境外权利方联络员处理。", ["archive"], "档案馆接待对接说明。"),
     page("archive-entry", "档案使用申请入口", "申请需提供档案编号与用途说明；取得权利确认后须再次申请数字化交付。本页面仅说明流程，不能在线取得许可。", [], "档案使用申请材料说明；不支持在线取得许可。")], f, a,
    [goal("physical_exhibit_allowed", True, "exhibit"), goal("online_allowed", False, "online"), goal("total_fee", 800, "fee"), goal("scan_dpi", 600, "scan")],
    "physical_only", [{"op": "visit_page", "page": "archive"}, send("archive", "咨询档案费用与权利联系人", "front"), wait("front"), send("rights", "请确认两种用途的权利授权", "rights"), wait("rights"), send("archive", "许可收到后请确认数字化交付和扫描规格", "scan", {"archive_id": "ARC-71", "exhibition_permission": "$fact:exhibit"}), wait("scan")],
    ["跨年度权利继受核验", "纽约冬令时和夏令时", "取得许可后必须再次发起请求", "72小时图像恢复与人工验收"], ["等待期间擅自假定许可", "实体授权误推为网络授权", "收到许可后忘记重启数字化查询"]))

# 08: Accessible accommodation — alternative providers, measurements unavailable on weekends.
f = {"a_door": fact(72, "A旅舍现场复测净门宽72cm，旧网页88cm包含门框。"), "a_bath": fact(68, "A旅舍浴室通行净宽68cm。"),
     "b_door": fact(92, "B酒店指定无障碍房净门宽92cm。"), "b_bath": fact(85, "B酒店浴室通行净宽85cm。"),
     "b_available": fact(True, "11月14—16日指定无障碍房有可售房，尚未预订。"), "b_price": fact(2360, "11月14—16日两晚总房费2360元。")}
a = [person("a_desk", "A旅舍前台·蓝心", "无障碍房咨询", "daily", [workflow("通行尺寸确认", ["无障碍", "轮椅", "尺寸"], ["wheelchair_width", "stay_dates"], [delegate("a_tech", business(60), ["wheelchair_width"]), reply(business(30))])], "每天营业，但不能用旧网页尺寸替代现场复测。", contact=["email", "phone"]),
     person("a_tech", "A旅舍设施员·蒋延", "现场测量", "office", [workflow("现场通行测量", ["尺寸", "测量"], ["wheelchair_width"], [lookup(["a_door", "a_bath"], business(120)), document(["a_door", "a_bath"], business(0)), reply()])], "周末不在岗；测量记录区分净宽与含框宽度。"),
     person("b_desk", "B酒店预订咨询·米禾", "房态与费用", "daily", [workflow("无障碍房确认", ["无障碍", "尺寸", "房态"], ["wheelchair_width", "stay_dates"], [lookup(["b_available", "b_price"], business(60)), delegate("b_tech", business(30), ["wheelchair_width"]), reply(business(30))])], "房态与价格可以先查询，是否可通行须现场量测。", contact=["email", "phone"]),
     person("b_tech", "B酒店设施主管·郑砚", "指定房型现场尺寸", "office", [workflow("指定房间量测", ["尺寸", "测量"], ["wheelchair_width"], [lookup(["b_door", "b_bath"], business(120, not_before="2026-11-11T10:00:00+08:00")), document(["b_door", "b_bath"], business(0)), reply()])], "指定房间11月11日10点才能进入复测；不能用同楼层其他房间数据代替。")]
TASKS.append(task("DSB-08", "无障碍住宿：两家机构比较与延后的现场测量", "出行住宿", "2026-11-06T13:30:00+08:00", "2026-11-12T18:00:00+08:00",
    "在A旅舍和B酒店中选择11月14—16日两晚住宿，预算2600元。轮椅宽78cm，房门和浴室净宽均须至少80cm。获取实测尺寸，并确认合适酒店的房态和总价，不预订。",
    {"wheelchair_width": "78cm，要求净宽至少80cm", "stay_dates": "2026-11-14/2026-11-16"}, [],
    [page("hotels-intro", "候选住宿简介", "A旅舍旧网页称门宽88cm；B酒店也有无障碍房。两家的前台每天办公，设施人员另有工作时段。", [], "两家候选住宿概况与现场测量安排。"),
     page("hotels", "候选住宿联系方式", "A旅舍前台蓝心；B酒店预订咨询米禾。现场测量分别由两家设施人员处理。", ["a_desk", "b_desk"], "两家前台对接说明。"),
     page("hotels-entry", "住宿预订入口", "确认无障碍房型需轮椅宽度与入住日期；本页面仅说明材料，不能在线预订。", [], "无障碍房确认材料说明；不支持在线预订。")], f, a,
    [goal("a_door_cm", 72, "a_door"), goal("a_bathroom_cm", 68, "a_bath"), goal("b_door_cm", 92, "b_door"), goal("b_bathroom_cm", 85, "b_bath"), goal("b_available", True, "b_available"), goal("b_total_price", 2360, "b_price")],
    "choose_b", [{"op": "visit_page", "page": "hotels"}, send("a_desk", "请现场核实无障碍尺寸", "a"), send("b_desk", "咨询无障碍房态、费用和尺寸", "b"), wait("a"), wait("b")],
    ["周末接待与工作日技术岗", "并行联系两家机构", "房间特定可进入时间", "过期网页尺寸"], ["门框宽当净宽", "第一家回复后过早停止", "拿一个房型数据替代另一个"], reply_delay=(60, 180)))

# 09: Public-service consultation — jurisdiction referral + two independent reviews.
f = {"jurisdiction": fact("街区公共空间管理处", "拟用地点属于街区公共空间管理处管辖；不是私人场地。"),
     "category": fact("临时扩声活动预咨询", "拟议活动应按临时扩声活动进行预咨询分类，尚未受理正式申请。"),
     "documents": fact(["平面图", "时段说明", "声设备清单"], "需要准备平面图、时段说明和声设备清单。"),
     "earliest": fact("2027-01-04", "按年度窗口安排，最早可进入后续正式办理的日期是2027年1月4日；不是活动批准日期。"),
     "consultation_receipt": fact("CONSULT-DEC03-19", "本轮30天跨部门意见征集已结束，回执CONSULT-DEC03-19；需携回执申请12月28日联合分类复核。")}
a = [person("service", "晴港政务咨询台·谢茵", "事项识别与管辖分流", "office", [workflow("活动事项咨询", ["活动", "办理", "管辖"], ["location", "amplified"], [lookup([], business(60), "登记咨询上下文"), delegate("land", business(60), ["location"]), refer(["sound"], business(60)), reply()])], "只能进行预咨询，不生成许可；先核实管辖再转专门岗位。", contact=["email", "phone"]),
     person("land", "公共空间管理联络员·吴弈", "场地管辖核对", "office", [workflow("管辖材料复核", ["管辖", "场地"], ["location"], [lookup(["jurisdiction"], weekly(3, "10:00", 120)), document(["jurisdiction"], business(60)), reply()])], "每周四10点复核共享场地边界清单。"),
     person("sound", "活动环境咨询员·陆笙", "扩声事项分类和材料", "office", [workflow("意见征集阶段确认", ["征集", "扩声", "材料"], ["location", "amplified"], [lookup(["consultation_receipt"], business(60, not_before="2026-12-03T09:00:00+08:00")), document(["consultation_receipt"], elapsed(0)), reply()]), workflow("联合分类复核", ["联合复核", "最终分类"], ["location", "amplified", "consultation_receipt"], [lookup(["category", "documents", "earliest"], business(240, not_before="2026-12-28T09:00:00+08:00")), document(["category", "documents", "earliest"], business(60)), reply()], id="final", evidence_fields={"consultation_receipt": "consultation_receipt"})], "本轮30天跨部门意见征集于12月3日汇总；申请人取得回执后须再次申请12月28日联合分类复核。")]
TASKS.append(task("DSB-09", "公共活动咨询：意见征集与年末联合复核", "公共服务", "2026-11-03T15:00:00+08:00", "2026-12-29T17:00:00+08:00",
    "为2027年1月晴港北广场的小型扩声活动询问主管机构、事项分类、应备材料和最早办理窗口。跟进意见征集并携回执再次申请联合复核。只做预咨询，不能写成已获许可；场景规则均为合成。",
    {"location": "晴港北广场", "amplified": "使用两只扩声音箱"}, [],
    [page("service-intro", "晴港公共活动咨询简介", "拟办活动先核实管辖。本轮意见征集在12月3日汇总；携回执再次申请12月28日联合复核。正式办理窗口另行确认。", [], "公共活动预咨询流程与时间安排。"),
     page("service", "晴港公共活动咨询联系方式", "各岗位联系人的联系方式（邮箱）请咨询咨询台谢茵，由咨询台提供后续对接入口。事项识别与管辖分流联系咨询台谢茵；扩声事项分类与材料联系活动环境咨询员。", ["service"], "政务咨询台对接说明。"),
     page("service-entry", "活动办理入口", "办理需提供活动地点与扩声设备说明；本页面为预咨询说明，不构成许可申请入口。", [], "活动预咨询材料说明；不支持在线申请许可。")], f, a,
    [goal("responsible_office", "街区公共空间管理处", "jurisdiction"), goal("consultation_receipt", "CONSULT-DEC03-19", "consultation_receipt"), goal("case_category", "临时扩声活动预咨询", "category"), goal("required_documents", ["平面图", "时段说明", "声设备清单"], "documents"), goal("earliest_processing_date", "2027-01-04", "earliest")],
    "consultation_only_not_approval", [{"op": "visit_page", "page": "service"}, send("service", "请核实活动办理管辖", "front"), wait("front"), send("sound", "请确认本轮扩声意见征集及回执", "consult"), wait("consult"), send("sound", "请按回执进行联合复核和最终分类", "sound", {"location": "晴港北广场", "amplified": "使用两只扩声音箱", "consultation_receipt": "$fact:consultation_receipt"}), wait("sound")],
    ["先管辖后专业咨询", "30天跨部门征集期", "携回执再次发起联合复核", "跨年度后续办理窗口"], ["咨询回执当许可证", "没有回执即跳过征集", "收到回执后不继续申请最终复核"]))

# 10: Individual seller — owner depends on a friend with weekend access to a reader.
f = {"asking": fact(3200, "卖方询价3200元，未承诺保留商品。"), "estimate": fact(10000, "卖方回忆快门约一万次，未经读取，不应视为实测。"),
     "actual": fact(42731, "对序列号CAM-402读取的实际快门次数为42731。"), "hotshoe": fact(False, "CAM-402热靴触发测试失败，当前不能正常使用外置闪光灯。"),
     "returns": fact("不支持退货", "卖方说明按现状转让，不支持退货。"), "pickup": fact("2026-11-09T14:00:00+08:00", "若交易成立，最早可取件时间为11月9日14点；本次仅查询。")}
a = [person("seller", "相机卖家·沈栖", "二手相机信息", "evening", [workflow("相机实测与条款", ["相机", "快门", "热靴", "实测"], ["serial"], [lookup(["asking", "estimate", "returns"], business(30)), delegate("friend", business(30), ["serial"]), refer(["courier"], business(0)), reply(business(30))])], "只在20—22点处理消息；没有读取器，需要请周末有设备的朋友实测。", contact=["email", "phone"]),
     person("friend", "卖家朋友·柯闻", "相机读取与热靴测试", "weekend", [workflow("读取相机与测试", ["相机", "实测"], ["serial"], [lookup(["actual", "hotshoe"], business(120, not_before="2026-11-07T10:00:00+08:00")), document(["actual", "hotshoe"], business(30)), reply()])], "周末才能接触读取器；测试只对CAM-402有效。"),
     person("courier", "桥溪快运取件咨询·曾澜", "取件时段查询", "daily", [workflow("最早取件时间", ["取件", "快递"], ["pickup_area"], [lookup(["pickup"], business(60)), reply()])], "咨询台周末照常工作，只查询取件时段，不创建运单。", contact=["email", "phone"])]
TASKS.append(task("DSB-10", "二手相机：夜间联系、周末实测与取件咨询", "个人交易咨询", "2026-11-06T10:00:00+08:00", "2026-11-09T22:00:00+08:00",
    "考虑购买CAM-402，要求快门少于30000次、热靴正常。请取得实测快门数和热靴结果，问清价格、退货条件和最早取件时段。不能付款或让卖方保留商品。",
    {"serial": "CAM-402", "pickup_area": "桥溪东区"}, ["seller"],
    [page("camera-intro", "CAM-402二手信息简介", "卖家写快门约一万次，实测情况待核。卖家晚间回复。", [], "二手相机出售信息与实测安排。"),
     page("camera", "卖家联系方式", "各相关方联系人的联系方式（邮箱）请咨询卖家沈栖，由卖家提供后续对接入口。相机咨询联系卖家沈栖；取件时段可联系桥溪快运咨询台。", ["seller"], "卖家与取件咨询对接说明。"),
     page("camera-entry", "交易咨询入口", "核实实测情况需提供序列号；本页面仅说明信息要求，不能在线下单或付款。", [], "交易咨询材料说明；不支持在线交易。")], f, a,
    [goal("asking_price", 3200, "asking"), goal("measured_shutter", 42731, "actual"), goal("hotshoe_works", False, "hotshoe"), goal("return_policy", "不支持退货", "returns"), goal("earliest_pickup", "2026-11-09T14:00:00+08:00", "pickup")],
    "does_not_meet_requirements", [send("seller", "请核实相机快门热靴及实测条件", "camera"), wait("camera"), send("courier", "查询最早取件时段", "courier"), wait("courier")],
    ["晚间个人可达性", "朋友周末才能测试", "周末快递咨询", "主观回忆与实测证据冲突"], ["接受卖方估计为实测", "朋友回复即认为卖家已承诺", "替用户作购买决定"], reply_delay=(30, 90)))

# 11: Open-source — volunteer schedules + 48h CI + release manager.
f = {"repro": fact(True, "提交的日志可重现在编译器C19下的兼容问题。"), "workaround": fact("commit-7bc2", "CI在commit-7bc2上验证该兼容问题已修复。"),
     "candidate": fact("1.4.2-rc1", "发布负责人确认当前仅有候选版1.4.2-rc1。"), "stable": fact("尚无承诺日期", "正式稳定版没有承诺发布日期；候选版不能标为稳定版。")}
a = [person("maintainer", "星舟项目维护者·简川", "问题复现与补丁协调", "maintainer", [workflow("兼容问题确认", ["兼容", "复现", "日志", "补丁"], ["version", "compiler", "logs"], [lookup([], business(120), "核实最小复现上下文"), delegate("ci", elapsed(0), ["version", "compiler", "logs"]), lookup([], business(60), "维护者复核CI结果"), reply(business(30))]), workflow("季度发布状态复核", ["季度发布", "候选发布", "稳定版状态"], ["version", "verified_commit"], [delegate("release", elapsed(0), ["version"]), reply(business(30))], id="release_check", evidence_fields={"verified_commit": "workaround"})], "只在周一三五20—22点处理；先给补丁验证结果，申请人应在次年第一季度发布窗口另行核实候选版与稳定版。"),
     person("ci", "星舟CI值守·自动检查器", "兼容性构建测试", "always", [workflow("48小时构建验证", ["构建", "验证"], ["version", "compiler", "logs"], [lookup(["repro", "workaround"], elapsed(2880)), document(["workaround"], elapsed(0)), reply()])], "仅返回真实配置内的构建结果；不会承诺发布。"),
     person("release", "星舟发布协调员·唐泊", "候选版与稳定版状态", "release", [workflow("季度候选发布核对", ["发布", "候选版"], ["version"], [lookup(["candidate", "stable"], {**weekly(1, "20:00", 120), "not_before": "2027-03-30T20:00:00+08:00"}), reply()])], "上游兼容窗口在2027年3月30日20点开放；候选版与稳定版需在该季度窗口分别核对。")]
TASKS.append(task("DSB-11", "开源兼容性：补丁验证后跟进跨季度发布", "开源协作", "2026-11-07T20:30:00+08:00", "2027-04-01T23:00:00+08:00",
    "星舟1.4.1在C19编译器上失败，日志LOG-771已备好。先确认复现和验证过的补丁；再于2027年第一季度发布窗口跟进候选版与稳定版日期。中间补丁可用不代表本任务完成。不要合并或发布。",
    {"version": "1.4.1", "compiler": "C19", "logs": "LOG-771"}, [],
    [page("repo-intro", "星舟项目贡献说明", "维护者周一三五20—22点处理，CI连续运行48小时。补丁验证后，须在2027年3月30日20点的上游兼容窗口另行核实季度发布，切勿把补丁或候选版当稳定版。", [], "开源项目维护安排与发布窗口说明。"),
     page("repo", "星舟项目联系方式", "兼容问题与补丁协调联系维护者简川；候选版与稳定版状态联系发布协调员。", ["maintainer"], "维护者与发布协调对接说明。"),
     page("repo-entry", "问题反馈入口", "提交需提供版本、编译器与日志编号；本页面仅说明材料，不能在线合并或发布。", [], "问题提交材料说明；不支持在线合并。")], f, a,
    [goal("reproduced", True, "repro"), goal("verified_patch", "commit-7bc2", "workaround"), goal("candidate_version", "1.4.2-rc1", "candidate"), goal("stable_release_date", "尚无承诺日期", "stable")],
    "workaround_available_stable_uncommitted", [{"op": "visit_page", "page": "repo"}, send("maintainer", "请核实兼容问题与补丁", "fix"), wait("fix"), {"op": "advance", "at": "2027-03-29T20:00:00+08:00"}, send("maintainer", "请跟进季度发布和稳定版状态", "release", {"version": "1.4.1", "verified_commit": "$fact:workaround"}), wait("release")],
    ["志愿者离散晚间窗口", "48小时自动构建", "跨季度后带原补丁证据继续沟通", "上游兼容窗口", "候选版与稳定版区别"], ["初步补丁可用就提前结束", "跨季度后丢失原补丁证据", "杜撰稳定版承诺日期"], reply_delay=(60, 180)))

# 12: Prototype held for classification review. Several active stages across 300 days.
f = {"warehouse": fact("2026年11月已完成始发仓入库扫描", "PK-608的2026年11月始发仓入库记录已核实；这是历史交接记录，不能据此推断目前仍在始发仓或已获放行。"),
     "declaration": fact("DEC-608-v2", "已补发首轮DEC-608-v2资料，仅用于初审；作为继续受理凭证有效至2027年3月31日17点。", valid_until="2027-03-31T17:00:00+08:00"),
     "review_case": fact("HOLD-608-9", "境外原型设备归类初审登记号为HOLD-608-9；须取得制造批次溯源材料和新版单证后再次发起长期复核。登记不等于放行。"),
     "declaration_latest": fact("DEC-608-v3", "2027年4月6日补发DEC-608-v3，取代v2；作为继续受理凭证有效至2027年9月30日17点。", available_at="2027-04-06T10:00:00+08:00", valid_until="2027-09-30T17:00:00+08:00"),
     "batch_trace": fact("TRACE-M608-2027", "制造方历史批次记录已恢复核验，溯源资料号TRACE-M608-2027。", available_at="2027-04-06T10:00:00+08:00"),
     "release": fact("技术复核结果已返回，实际放行仍需另行确认", "2027年9月中旬技术复核窗口处理完成后，仅返回技术意见；该未来结果在本题截止前不可见。")}
a = [person("forwarder", "远澄货运客服·白榆", "货件入库信息", "office", [workflow("货件状态与联系入口", ["物流", "货件", "入库", "状态"], ["tracking"], [delegate("warehouse", business(60), ["tracking"]), refer(["exporter", "customsdesk"], business(30)), reply()])], "只能确认入库并提供申报联络入口，不把入库状态说成放行。", contact=["email", "phone"]),
     person("warehouse", "始发仓查件员·施瑾", "仓内扫描核对", "office", [workflow("入库扫描查证", ["扫描", "入库"], ["tracking"], [lookup(["warehouse"], business(120)), document(["warehouse"], business(60)), reply()])], "周末无人工查件；核对后出具扫描记录。"),
     person("exporter", "出口方单证员·贺悠", "更正单证与制造批次溯源", "office", [workflow("首轮更正单证", ["首轮", "申报", "更正"], ["tracking"], [lookup(["declaration"], business(120, not_before="2026-12-07T10:00:00+08:00")), document(["declaration"], business(60)), reply()]), workflow("第二轮单证和批次溯源", ["第二轮", "新版单证", "批次溯源"], ["tracking", "review_reference"], [lookup(["declaration_latest", "batch_trace"], business(120, not_before="2027-04-06T10:00:00+08:00")), document(["declaration_latest", "batch_trace"], business(60)), reply()], id="refresh", evidence_fields={"review_reference": "review_case"})], "首轮更正资料12月7日可核验；取得归类初审登记后，2027年4月6日恢复的制造档案才能用于第二轮单证与批次溯源。"),
     person("customsdesk", "远澄单证联络·戴筠", "设备留置核查联络", "office", [workflow("归类初审登记", ["初审", "登记"], ["tracking", "declaration_version"], [delegate("broker", business(60), ["tracking", "declaration_version"], workflow="preliminary"), reply(business(30))], evidence_fields={"declaration_version": "declaration"}), workflow("第二轮长期复核", ["长期复核", "放行状态"], ["tracking", "declaration_version", "review_reference", "batch_trace"], [delegate("broker", business(60), ["tracking", "declaration_version", "review_reference", "batch_trace"]), reply(business(30))], id="final", evidence_fields={"declaration_version": "declaration_latest", "review_reference": "review_case", "batch_trace": "batch_trace"})], "原型设备因归类争议留置。初审登记后须用新版单证和溯源资料重新提交长期复核；旧单证过期后不能继续受理；任何登记都不是放行。"),
     person("broker", "境外代理·Morgan Lee", "原型设备归类与技术意见复核", "new_york", [workflow("归类初审", ["初审", "归类"], ["tracking", "declaration_version"], [lookup(["review_case"], business(120, not_before="2027-02-04T09:00:00-05:00")), document(["review_case"], elapsed(0)), reply()], id="preliminary"), workflow("长期技术复核", ["长期复核", "放行"], ["tracking", "declaration_version", "review_reference", "batch_trace"], [lookup(["release"], business(1440, not_before="2027-09-10T09:00:00-04:00")), document(["release"], business(0)), reply()])], "纽约工作日办公；初审窗口2027年2月4日，技术意见集中复核窗口9月10日。需补齐制造档案再受理；不是持续工作数月，也没有放行承诺。")]
TASKS.append(task("DSB-12", "跨境原型设备：300天内的初审、二次补件与未决放行", "跨境设备争议核查", "2026-11-06T15:00:00+08:00", "2027-09-02T15:00:00+08:00",
    "跟进因归类争议留置的科研原型设备PK-608，到2027年9月2日15点汇报。核实历史入库交接、取得初审登记号，按要求向出口方取得有效新版单证和制造批次溯源资料，再发起长期复核。若放行未确认，明确已完成步骤与仍待确认事项。不要把历史入库、初审登记或补件受理当成当前放行；不支付费用或作法律承诺。",
    {"tracking": "PK-608"}, [],
    [page("logistics-intro", "远澄货运简介", "本合成场景有多阶段归类争议核查：首轮更正单证预计2026年12月7日可取；初审窗口2027年2月4日；制造档案预计4月6日可核验，届时需更新单证并再次申请长期复核。境外技术意见窗口为9月10日，无放行承诺。", [], "留置核查流程与各阶段时间窗口。"),
     page("logistics", "远澄货运联系方式", "各岗位联系人的联系方式（邮箱）请咨询客服白榆，由客服提供后续对接入口。货件状态与联系入口联系客服白榆；单证与批次溯源联系出口方单证员。", ["forwarder"], "货运客服与单证对接说明。"),
     page("logistics-entry", "留置核查办理入口", "办理需提供运单号与有效申报单证版本；本页面仅说明材料，不能在线发起复核或支付费用。", [], "留置核查材料说明；不支持在线发起复核。")], f, a,
    [goal("initial_warehouse_record", "2026年11月已完成始发仓入库扫描", "warehouse"), goal("review_reference", "HOLD-608-9", "review_case"), goal("declaration_version", "DEC-608-v3", "declaration_latest"), goal("batch_trace", "TRACE-M608-2027", "batch_trace"),
     {"key": "release_status", "status": "unconfirmed"}],
    "release_unconfirmed_at_deadline", [{"op": "visit_page", "page": "logistics"}, send("forwarder", "查询货件状态和联系入口", "front"), wait("front"), send("exporter", "请补发首轮更正申报资料", "doc_v2"), wait("doc_v2"), send("customsdesk", "请办理归类初审登记", "preliminary", {"tracking": "PK-608", "declaration_version": "$fact:declaration"}), wait("preliminary"), send("exporter", "请取得第二轮新版单证及批次溯源", "doc_v3", {"tracking": "PK-608", "review_reference": "$fact:review_case"}), wait("doc_v3"), send("customsdesk", "请按新版材料发起长期复核并查询放行状态", "release", {"tracking": "PK-608", "declaration_version": "$fact:declaration_latest", "review_reference": "$fact:review_case", "batch_trace": "$fact:batch_trace"}), wait("release")],
    ["跨年度多轮事项", "定期归类初审窗口", "旧单证过期与跨人物证据更新", "制造档案恢复后的第二轮补件", "纽约夏令时切换", "300天截止仍早于技术复核窗口"], ["只发一条查询后等待300天", "拿旧单证或初审登记跳过第二轮补件", "把历史仓库记录当当前货位", "受理回执或未来技术意见当放行证明"], completion_class="bounded_unresolved"))


def configure_scoring(item):
    """Author trusted attestation attributes; reference fact IDs are only witnesses."""
    subject = {"task": item["id"], "case": item["public"]["user_fields"]}
    predicates = {fid: goal["key"] for goal in item["goals"] for fid in goal.get("accepted_facts", [])}
    if item["id"] == "DSB-05":
        predicates["quote_old"] = predicates["quote_new"]
    aliases = {
        "尚无承诺日期": ["尚未承诺正式稳定版发布日期", "未承诺发布日期", "暂无确定的发布日期", "not_committed", "暂无承诺日期"],
        "72小时内取消收取50%": ["三天内取消收取一半费用", "72小时内取消需支付50%的费用"],
        "专业选修": ["专业选修课"], "2027春季": ["2027年春季", "2027年春季学期"],
        "不支持退货": ["不可退货", "不接受退货"],
    }
    money = {"price", "rent", "deposit", "quote_old", "quote_new", "cost", "fee", "b_price", "asking"}
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
        return {"type": "text", "aliases": {value: aliases[value]} if value in aliases else {}}

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
        "DSB-11": (144, "长期", "短期修复后跨季度跟进候选发布"),
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
    for scope in ("private", "public"):
        (ROOT / "tasks" / scope).mkdir(parents=True, exist_ok=True)
    for original in TASKS:
        item = deepcopy(original)
        add_direct_review_path(item)
        for page in item["public"]["pages"]:
            page["url"] = page_url(item["id"], page)
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


if __name__ == "__main__":
    write_tasks()
