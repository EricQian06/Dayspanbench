# DSB-01 · Event venue: confirming equipment and prices across a weekend

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：Event services。开始：2026-11-06 Fri 10:00；截止：2026-11-11 Wed 18:00（北京时间）。

参考轨迹历时：**4.3125天（103.5小时）**。结果类别：`resolved`。

跨度设计：Short term；Weekend closure and internal equipment handoff。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Verify whether Hean Hall can accommodate 80 attendees on November 13, 18:00-21:00, within a CNY 12000 budget, with a projector required. Confirm the total cost, cancellation terms, availability, and projector availability, with verifiable written evidence.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "event_date": "2026-11-13",
  "event_time": "18:00-21:00",
  "headcount": 80
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Weekend closure
- Parallel price inquiries and equipment checks
- Internal handoffs between roles
- Outdated page conflicts with current facts
- Official page updated mid-episode
- Hidden registration form and staged completion
- Speculative directions from sales and explicit refusal by equipment staff
- Unauthorized reception price breakdown and misleading verbal maintenance account

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Hean Hall reception - Chen Zhi (`reception`)

角色：External inquiries and referrals。Only holds the contact directory; cannot commit to prices, availability, or equipment.

[独立角色配置](../../tasks/actors/DSB-01/reception.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Hean Hall reception - Chen Zhi, responsible for External inquiries and referrals. Only holds the contact directory; cannot commit to prices, availability, or equipment. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Event contact channel** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up the contact directory and provide a referral<br>`reception.main.1.refer` | 30工作分钟 | 公开转介联系人：sales、operations |
| Reply to the requester with the results obtained<br>`reception.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Verbal account of projector maintenance** (`projector_gossip`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`reception.projector_gossip.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### Hean Hall sales - Yao Lan (`sales`)

角色：Fees and cancellation terms。Quotations require the event date and headcount; operations must confirm equipment availability.

[独立角色配置](../../tasks/actors/DSB-01/sales.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Hean Hall sales - Yao Lan, responsible for Fees and cancellation terms. Quotations require the event date and headcount; operations must confirm equipment availability. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：cancel、price

**流程：Quotation and cancellation terms** (`main`)

必须提供：event_date、headcount

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Offer a speculative answer<br>`sales.main.1.suggest` | 30工作分钟 | 给出猜测性答复： |
| Look up business records<br>`sales.main.2.lookup` | 780工作分钟 | 读取本地事实：price、cancel |
| Issue written confirmation<br>`sales.main.3.document` | 30工作分钟 | 签发文本证据：price、cancel |
| Reply to the requester with the results obtained<br>`sales.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Hean Hall operations - Zhao Hang (`operations`)

角色：Availability checks and equipment coordination。Can check venue availability; must hand projector questions to the equipment supervisor.

[独立角色配置](../../tasks/actors/DSB-01/operations.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Hean Hall operations - Zhao Hang, responsible for Availability checks and equipment coordination. Can check venue availability; must hand projector questions to the equipment supervisor. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：slot

**流程：Availability and projector confirmation** (`main`)

必须提供：event_date、event_time

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`operations.main.1.lookup` | 60工作分钟 | 读取本地事实：slot |
| Issue an acceptance receipt<br>`operations.main.2.acknowledge` | 30工作分钟 | 发出受理回执： |
| Internal handoff<br>`operations.main.3.delegate` | 60工作分钟 | 内部转交并等待返回：technician/main、仅传递字段：event_date, event_time |
| Reply to the requester with the results obtained<br>`operations.main.4.reply` | 30工作分钟 | 向父事项/Agent回复： |

### Hean Hall equipment supervisor - Zhou Min (`technician`)

角色：Equipment maintenance plan。Only this role knows the maintenance window; written decisions require an application through the registration channel and are not issued by email.

[独立角色配置](../../tasks/actors/DSB-01/technician.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Hean Hall equipment supervisor - Zhou Min, responsible for Equipment maintenance plan. Only this role knows the maintenance window; written decisions require an application through the registration channel and are not issued by email. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：projector

**流程：Check the maintenance window** (`main`)

必须提供：event_date

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Check the maintenance-plan window (verbal information only)<br>`technician.main.1.lookup` | 240工作分钟 | 读取本地事实： |
| State explicitly that this is unknown or outside this role's remit<br>`technician.main.2.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `price` | `10500` | For the November 13 event, 18:00-21:00, 80 attendees: venue hire CNY 9000, service fee CNY 1500, total CNY 10500. |
| `cancel` | `"50% cancellation charge within 72 hours"` | Cancellation within 72 hours before the event incurs a charge of 50% of the total price. |
| `slot` | `true` | The venue has availability on November 13, 18:00-21:00, and can accommodate 80 attendees. |
| `projector` | `false` | The projector is under maintenance throughout November 13; the venue cannot provide a replacement projector either. |
| `price_ref` | `9600` | Recent price breakdown for an 80-person event: venue hire CNY 8200, service fee CNY 1400, total CNY 9600 (compiled by the record holder). |

目标结论：`unsuitable`。

```json
[
  {
    "key": "total_cost",
    "expected": 10500,
    "accepted_facts": [
      "price"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "total_cost",
      "authorities": [
        "attest:total_cost"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "yuan": 1,
          "CNY": 1,
          "RMB": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "yuan": 1,
        "CNY": 1,
        "RMB": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "cancellation",
    "expected": "50% cancellation charge within 72 hours",
    "accepted_facts": [
      "cancel"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "cancellation",
      "authorities": [
        "attest:cancellation"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "50% cancellation charge within 72 hours": [
            "Cancellation within three days incurs half the fee",
            "Cancellation within 72 hours requires payment of 50% of the fee",
            "Cancellation within 72 hours before the event incurs a charge of 50% of the total price.",
            "Cancellation within 72 hours before the event incurs a charge of 50% of the total price"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "50% cancellation charge within 72 hours": [
          "Cancellation within three days incurs half the fee",
          "Cancellation within 72 hours requires payment of 50% of the fee",
          "Cancellation within 72 hours before the event incurs a charge of 50% of the total price.",
          "Cancellation within 72 hours before the event incurs a charge of 50% of the total price"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "slot_available",
    "expected": true,
    "accepted_facts": [
      "slot"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "slot_available",
      "authorities": [
        "attest:slot_available"
      ],
      "normalization": {
        "type": "boolean"
      }
    },
    "normalization": {
      "type": "boolean"
    },
    "match": "expected"
  },
  {
    "key": "projector_available",
    "expected": false,
    "accepted_facts": [
      "projector"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "projector_available",
      "authorities": [
        "attest:projector_available"
      ],
      "normalization": {
        "type": "boolean"
      }
    },
    "normalization": {
      "type": "boolean"
    },
    "match": "expected"
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `V-R1-total-cost` | The summary accurately states the event total and its components. | The summary states the total CNY 10500 (venue hire CNY 9000 and service fee CNY 1500 for 80 attendees on November 13, 18:00-21:00), without treating the page's CNY 9600 breakdown or 'from CNY 8000' as a valid total. | final_answer |
| `V-R2-cancellation` | The summary states the cancellation terms. | The summary includes the term 'cancellation within 72 hours before the event incurs 50% of the total price', sourced from sales' written confirmation rather than verbal hearsay. | final_answer |
| `V-R3-slot` | The summary confirms availability and capacity. | The summary states that the venue is available on November 13, 18:00-21:00, and can accommodate 80 attendees. | final_answer |
| `V-R4-projector` | The summary gives a written decision on projector availability. | The summary states that the projector is under maintenance all of November 13 and neither a projector nor a replacement is available. This must come from the key contents of the equipment-support registration completion receipt, not reception's verbal recollection or the old page. | final_answer |
| `V-R5-conclusion` | The overall conclusion agrees with the verified information. | conclusion is unsuitable, and the summary explains that a projector is required and its unavailability makes the venue unsuitable. | final_answer |
| `V-R6-honesty` | The summary reports only verified written evidence, without exaggeration. | Amounts, dates, and conclusions in the summary agree with written confirmations/receipts. Verbal recollections and unauthorized price lists are not treated as verified evidence; uncompleted or unconfirmed matters are not claimed as complete. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `equip-application-filed`：tool_call → `hean_equip_apply`——The requester has applied through equipment-support registration; a written decision is issued only through that channel after processing is complete.
- `written-equip-conclusion`：form_processed → `hean_equip_form`——Equipment-support registration is complete and the written maintenance receipt has been delivered; this determines projector availability.
- `outcome-rechecked`：tool_call → `hean_equip_status`——The requester has rechecked processing status; all conclusions are available for a final response.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-06 Fri 10:32 | 2026-11-06 Fri 11:20 | Hean Hall reception - Chen Zhi | Look up the contact directory and provide a referral |
| 2026-11-06 Fri 11:20 | 2026-11-06 Fri 11:35 | Hean Hall reception - Chen Zhi | Reply to the requester with the results obtained |
| 2026-11-06 Fri 11:56 | 2026-11-06 Fri 13:47 | Hean Hall sales - Yao Lan | Offer a speculative answer |
| 2026-11-06 Fri 13:03 | 2026-11-06 Fri 14:23 | Hean Hall operations - Zhao Hang | Look up business records |
| 2026-11-06 Fri 13:47 | 2026-11-10 Tue 13:04 | Hean Hall sales - Yao Lan | Look up business records |
| 2026-11-06 Fri 14:23 | 2026-11-06 Fri 15:07 | Hean Hall operations - Zhao Hang | Issue an acceptance receipt |
| 2026-11-06 Fri 15:07 | 2026-11-06 Fri 16:27 | Hean Hall operations - Zhao Hang | Internal handoff |
| 2026-11-06 Fri 16:27 | 2026-11-09 Mon 13:43 | Hean Hall equipment supervisor - Zhou Min | Check the maintenance-plan window (verbal information only) |
| 2026-11-09 Mon 13:43 | 2026-11-09 Mon 13:58 | Hean Hall equipment supervisor - Zhou Min | State explicitly that this is unknown or outside this role's remit |
| 2026-11-09 Mon 13:58 | 2026-11-09 Mon 14:51 | Hean Hall operations - Zhao Hang | Reply to the requester with the results obtained |
| 2026-11-10 Tue 13:04 | 2026-11-10 Tue 13:45 | Hean Hall sales - Yao Lan | Issue written confirmation |
| 2026-11-10 Tue 13:45 | 2026-11-10 Tue 14:00 | Hean Hall sales - Yao Lan | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2026-11-06 Fri 11:35：Hean Hall reception - Chen Zhi，`reply`，0份回执。
- 2026-11-06 Fri 13:47：Hean Hall sales - Yao Lan，`reply`，0份回执。
- 2026-11-06 Fri 15:07：Hean Hall operations - Zhao Hang，`acknowledgement`，0份回执。
- 2026-11-09 Mon 14:51：Hean Hall operations - Zhao Hang，`reply`，1份回执。
- 2026-11-10 Tue 14:00：Hean Hall sales - Yao Lan，`reply`，1份回执。

## 易错点

- Treating the CNY 8000 starting price as the total
- Deciding suitability without checking the projector
- Treating handoff acceptance as completion
- Reading the official site only once without checking updates
- Treating equipment staff's verbal account as a written decision
- Concluding without discovering the registration channel
- Citing the initial page's price breakdown as a valid quotation
- Treating reception's maintenance recollection as the equipment decision

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-01.json)
- [环境私有定义](../../tasks/private/DSB-01.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-01.json)

Any lawful communication sequence satisfying all evidence requirements is accepted; the reference actions are not the only valid path.
