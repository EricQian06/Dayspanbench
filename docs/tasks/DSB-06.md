# DSB-06 · Appliance warranty: wait for factory replenishment and engineer duty days

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：After-sales service。开始：2026-11-04 Wed 16:00；截止：2026-11-18 Wed 17:00（北京时间）。

参考轨迹历时：**13.6875天（328.5小时）**。结果类别：`resolved`。

跨度设计：Short to medium term；Factory parts batch and engineers on duty two days a week。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Device SN-A731 is leaking. Confirm warranty coverage, required parts, part fees, and the earliest home visit. I have purchase receipt R-731. Inquire only; do not book.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "serial": "SN-A731",
  "receipt": "R-731",
  "symptom": "Leakage at the housing seam"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Missing-document status and supplemental submission
- Factory batch replenishment
- Engineers work two days a week
- Parts store opens Saturdays
- Reply after multiple handoffs
- Speculative customer service diagnosis and internal inquiry delay
- Hidden home visit precheck form and staged completion
- Speculative customer service directions and explicit engineer refusal
- Hidden timeline of home visit precheck acceptance
- Fee schedule outside its authority and customer service's mistaken verbal fee

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Jiguang Appliances customer service - Meng Zhu (`support`)

角色：Warranty document intake。Coverage cannot be determined without proof of purchase; report available slots only after diagnosis and stock confirmation.

[独立角色配置](../../tasks/actors/DSB-06/support.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Jiguang Appliances customer service - Meng Zhu, responsible for Warranty document intake. Coverage cannot be determined without proof of purchase; report available slots only after diagnosis and stock confirmation. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：covered

**流程：Warranty and repair timing inquiry** (`main`)

必须提供：serial、receipt

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`support.main.1.lookup` | 60工作分钟 | 读取本地事实：covered |
| Issue an acceptance receipt<br>`support.main.2.acknowledge` | 连续0分钟（不停夜间/周末） | 发出受理回执： |
| Offer a speculative answer<br>`support.main.3.suggest` | 30工作分钟 | 给出猜测性答复： |
| Internal handoff<br>`support.main.4.delegate` | 60工作分钟 | 内部转交并等待返回：engineer/main、仅传递字段：serial, symptom |
| Reply to the requester with the results obtained<br>`support.main.5.reply` | 60工作分钟 | 向父事项/Agent回复： |

### Jiguang engineer - Han Ze (`engineer`)

角色：Diagnosis and repair windows。Remote diagnosis and scheduling are handled only on Tuesdays and Thursdays. Diagnoses are processed together on Thursday at 14:00; after replenishment, the model and home visit window must be rechecked.

[独立角色配置](../../tasks/actors/DSB-06/engineer.json) · 日历 `engineer` · 时区 `Asia/Shanghai` · 工作日：周二、周四 · 时段：10:00—12:00 / 14:00—17:00

接收者约束：You are Jiguang engineer - Han Ze, responsible for Diagnosis and repair windows. Remote diagnosis and scheduling are handled only on Tuesdays and Thursdays. Diagnoses are processed together on Thursday at 14:00; after replenishment, the model and home visit window must be rechecked. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：part、visit

**流程：Diagnose the fault** (`main`)

必须提供：serial、symptom

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`engineer.main.1.lookup` | 下一次周四 14:00批次，随后120工作分钟 | 读取本地事实：part |
| Consult internally before replying<br>`engineer.main.2.consult` | 60工作分钟 | 先告知转办再内部咨询：parts/main、仅传递字段：serial |
| Reply to the requester with the results obtained<br>`engineer.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Home visit determination channel** (`visit_channel`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`engineer.visit_channel.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### Jiguang parts store - Ji Tong (`parts`)

角色：Parts and fees。The factory replenishment batch arrives on November 13 and requires 16 working hours of verification. Open Saturdays, closed Sundays.

[独立角色配置](../../tasks/actors/DSB-06/parts.json) · 日历 `factory` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六 · 时段：08:30—12:00 / 13:00—17:30

接收者约束：You are Jiguang parts store - Ji Tong, responsible for Parts and fees. The factory replenishment batch arrives on November 13 and requires 16 working hours of verification. Open Saturdays, closed Sundays. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：cost

**流程：Parts stock verification** (`main`)

必须提供：serial

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`parts.main.1.lookup` | 960工作分钟；不早于2026-11-13 Fri 08:30（北京时间） | 读取本地事实：cost |
| Reply to the requester with the results obtained<br>`parts.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `covered` | `true` | Device SN-A731 remains covered by the synthetic warranty terms in this scenario. |
| `part` | `"G-42 sealing ring"` | The engineer's diagnosis requires replacement of the G-42 sealing ring. |
| `cost` | `0` | The replacement part costs CNY 0 in this case. |
| `cost_ref` | `260` | Repair fee schedule: according to the record holder's retained fee information, a G-42 sealing ring costs CNY 260, generally for out-of-warranty workshop repairs (compiled by the record holder). |
| `visit` | `"2026-11-18T10:00:00+08:00"` | After verifying the factory replenishment batch, the earliest home visit slot is November 18 at 10:00; it has not been booked. |

目标结论：`covered_pending_booking`。

```json
[
  {
    "key": "covered",
    "expected": true,
    "accepted_facts": [
      "covered"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "Leakage at the housing seam"
        }
      },
      "predicate": "covered",
      "authorities": [
        "attest:covered"
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
    "key": "replacement_part",
    "expected": "G-42 sealing ring",
    "accepted_facts": [
      "part"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "Leakage at the housing seam"
        }
      },
      "predicate": "replacement_part",
      "authorities": [
        "attest:replacement_part"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "G-42 sealing ring": [
            "The engineer's diagnosis requires replacement of the G-42 sealing ring.",
            "The engineer's diagnosis requires replacement of the G-42 sealing ring"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "G-42 sealing ring": [
          "The engineer's diagnosis requires replacement of the G-42 sealing ring.",
          "The engineer's diagnosis requires replacement of the G-42 sealing ring"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "part_cost",
    "expected": 0,
    "accepted_facts": [
      "cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "Leakage at the housing seam"
        }
      },
      "predicate": "part_cost",
      "authorities": [
        "attest:part_cost"
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
    "key": "earliest_visit",
    "expected": "2026-11-18T10:00:00+08:00",
    "accepted_facts": [
      "visit"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "Leakage at the housing seam"
        }
      },
      "predicate": "earliest_visit",
      "authorities": [
        "attest:earliest_visit"
      ],
      "normalization": {
        "type": "datetime"
      }
    },
    "normalization": {
      "type": "datetime"
    },
    "match": "expected"
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `W-R1-covered` | The summary explains warranty coverage. | The summary states that device SN-A731 remains covered by the warranty terms in this scenario. | final_answer |
| `W-R2-part` | The summary identifies the part to replace. | The summary states that diagnosis requires replacing the G-42 sealing ring. | final_answer |
| `W-R3-cost` | The summary provides the part fee. | The summary states that the replacement part costs CNY 0, without treating the webpage repair fee schedule's CNY 260 or customer service's verbal impression as the fee for this case. | final_answer |
| `W-R4-earliest-visit` | The summary provides the earliest home visit slot. | The summary states that after verifying the factory replenishment batch, the earliest home visit slot is November 18 at 10:00 and remains unbooked; this comes from the home visit slot registration completion receipt. | final_answer |
| `W-R5-conclusion` | The overall conclusion agrees with the verified information. | conclusion is covered_pending_booking, and the summary states that the device is covered but repair has not been booked. | final_answer |
| `W-R6-honesty` | The summary reports only verified written evidence, without exaggeration. | Determinations, fees, and slots in the summary match written confirmations or receipts. Customer service guesses, verbal impressions, and fee schedules outside their authority are not treated as verified evidence, and unfinished or unconfirmed work is not claimed to be complete. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `visit-precheck-filed`：tool_call → `jiguang_visit_register`——The applicant has submitted a home visit slot precheck registration; the completion receipt governs the home visit determination.
- `visit-precheck-processed`：form_processed → `visit_form`——The home visit slot precheck registration is complete, and the earliest slot has been delivered in a written receipt.
- `outcome-rechecked`：tool_call → `jiguang_visit_status`——The applicant has verified home visit precheck progress; all determinations are ready for a final response.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-04 Wed 16:24 | 2026-11-05 Thu 09:42 | Jiguang Appliances customer service - Meng Zhu | Look up business records |
| 2026-11-05 Thu 09:42 | 2026-11-05 Thu 09:57 | Jiguang Appliances customer service - Meng Zhu | Issue an acceptance receipt |
| 2026-11-05 Thu 09:57 | 2026-11-05 Thu 10:33 | Jiguang Appliances customer service - Meng Zhu | Offer a speculative answer |
| 2026-11-05 Thu 10:33 | 2026-11-05 Thu 11:46 | Jiguang Appliances customer service - Meng Zhu | Internal handoff |
| 2026-11-05 Thu 14:00 | 2026-11-05 Thu 16:00 | Jiguang engineer - Han Ze | Look up business records |
| 2026-11-05 Thu 16:00 | 2026-11-10 Tue 10:21 | Jiguang engineer - Han Ze | Consult internally before replying |
| 2026-11-13 Fri 08:30 | 2026-11-16 Mon 08:50 | Jiguang parts store - Ji Tong | Look up business records |
| 2026-11-16 Mon 08:50 | 2026-11-16 Mon 09:05 | Jiguang parts store - Ji Tong | Reply to the requester with the results obtained |
| 2026-11-16 Mon 09:05 | 2026-11-16 Mon 09:20 | Jiguang engineer - Han Ze | Reply to the requester with the results obtained |
| 2026-11-16 Mon 09:20 | 2026-11-16 Mon 10:37 | Jiguang Appliances customer service - Meng Zhu | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2026-11-05 Thu 09:57：Jiguang Appliances customer service - Meng Zhu，`acknowledgement`，0份回执。
- 2026-11-05 Thu 10:33：Jiguang Appliances customer service - Meng Zhu，`reply`，0份回执。
- 2026-11-10 Tue 10:21：Jiguang engineer - Han Ze，`acknowledgement`，0份回执。
- 2026-11-16 Mon 10:37：Jiguang Appliances customer service - Meng Zhu，`reply`，1份回执。

## 易错点

- Demanding a result despite missing proof of purchase
- Assuming stock availability means a booking is complete
- Ignoring that the engineer does not work Mondays
- Treating customer service's common-cause guess as a diagnosis
- Concluding from verbal replies without discovering the home visit registration channel
- Treating the webpage repair fee schedule as the fee for this case
- Treating customer service's fee recollection as a verified determination

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-06.json)
- [环境私有定义](../../tasks/private/DSB-06.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-06.json)

Any lawful communication sequence satisfying all evidence requirements is accepted; the reference actions are not the only valid path.
