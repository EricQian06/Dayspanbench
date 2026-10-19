# DSB-37 · Rail cancellation recovery with an accompanied folding bicycle

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：mobility_transportation。开始：2027-10-07 Thu 21:30；截止：2027-10-09 Sat 22:20（北京时间）。

参考轨迹历时：**0.1875天（4.5小时）**。结果类别：`resolved`。

跨度设计：Short term；live rail delay plus accompanied-bike evidence window。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

I am stranded at Reading after the 1C27 cancellation; reach Bristol Temple Meads by 19:30 today. Ask me about the bicycle, ticket and budget before reserving; check the current disruption record (not the superseded all-clear), keep the folded bike with me on every leg, and reserve only the exact plan I approve. No payment, compensation claim or change to the original return leg.

Advisory and coordination only: search live inventory, confirm bike policy, and create at most the one approved replacement bundle; no payment, compensation claim, or change to the original return leg.

已给信息：

```json
{
  "date": "2027-10-07",
  "origin": "Reading",
  "destination": "Bristol Temple Meads"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- live rail delay at 15:05 rules out the direct rail recovery
- accompanied-bike acceptance evidence appears only after the desk reply window
- superseded all-clear alert is a trap next to the current cancellation
- search-discoverable disruption and journey inventory
- sparse prompt: bike, ticket and budget facts only surface through dialogue
- hidden booking desk revalidates the live journey

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Rail recovery desk·Tom Ashby (`rail_desk`)

角色：disruption records, bike policy and replacement reservations。Confirms accompanied folded-bike acceptance in writing; live journey inventory and reservations go through the search service and booking desk named on the entry page.

[独立角色配置](../../tasks/actors/DSB-37/rail_desk.json) · 日历 `london_daily` · 时区 `Europe/London` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：07:00—21:00

接收者约束：You are Rail recovery desk·Tom Ashby, responsible for disruption records, bike policy and replacement reservations. Confirms accompanied folded-bike acceptance in writing; live journey inventory and reservations go through the search service and booking desk named on the entry page. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：arrival、bike_accompanied、extra_cost、replacement_reserved、return_preserved、transfer_depart

**流程：Bike policy confirmation** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`rail_desk.main.1.acknowledge` | 10工作分钟 | 发出受理回执： |
| check accompanied folded-bike acceptance for the transfer and coach<br>`rail_desk.main.2.lookup` | 20工作分钟 | 读取本地事实：bike_accompanied |
| Issue written confirmation<br>`rail_desk.main.3.document` | 10工作分钟 | 签发文本证据：bike_accompanied |
| Reply to the requester with the results obtained<br>`rail_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `arrival` | `"19:00"` | The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline. |
| `extra_cost` | `18` | The complete replacement bundle costs 18 GBP extra: coach fare 14 + local transfer 4 + bicycle fee 0, at the maximum allowed outlay. |
| `bike_accompanied` | `true` | Provider evidence bike-MOB1 confirms both the local transfer and the coach accept the folded Brompton kept with the passenger, with no unattended storage and no extra bike fee. |
| `replacement_reserved` | `true` | One replacement bundle (coach plus local transfer entitlement, accompanied folded bike accepted) has been confirmed; no payment was taken. |
| `transfer_depart` | `"15:10"` | The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach. |
| `return_preserved` | `true` | The original return leg of ticket T-MOB is preserved unchanged; no compensation claim was made and no payment was taken. |

目标结论：`recovery_confirmed`。

```json
[
  {
    "key": "replacement_reserved",
    "expected": true,
    "accepted_facts": [
      "replacement_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "replacement_reserved",
      "authorities": [
        "attest:replacement_reserved"
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
    "key": "arrival",
    "expected": "19:00",
    "accepted_facts": [
      "arrival"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "arrival",
      "authorities": [
        "attest:arrival"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "19:00": [
            "The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline.",
            "The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "19:00": [
          "The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline.",
          "The reserved replacement (m02 coach) departs Mereoak 15:30 and arrives Bristol Temple Meads 19:00, inside the 19:30 deadline"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "extra_cost",
    "expected": 18,
    "accepted_facts": [
      "extra_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "extra_cost",
      "authorities": [
        "attest:extra_cost"
      ],
      "normalization": {
        "type": "number",
        "units": {}
      }
    },
    "normalization": {
      "type": "number",
      "units": {}
    },
    "match": "expected"
  },
  {
    "key": "bike_accompanied",
    "expected": true,
    "accepted_facts": [
      "bike_accompanied"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "bike_accompanied",
      "authorities": [
        "attest:bike_accompanied"
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
    "key": "transfer_depart",
    "expected": "15:10",
    "accepted_facts": [
      "transfer_depart"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "transfer_depart",
      "authorities": [
        "attest:transfer_depart"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "15:10": [
            "The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach.",
            "The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "15:10": [
          "The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach.",
          "The local transfer departs Reading 15:10 and reaches Mereoak 15:20, giving a ten-minute boarding buffer before the 15:30 coach"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "return_preserved",
    "expected": true,
    "accepted_facts": [
      "return_preserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-37",
        "case": {
          "date": "2027-10-07",
          "origin": "Reading",
          "destination": "Bristol Temple Meads"
        }
      },
      "predicate": "return_preserved",
      "authorities": [
        "attest:return_preserved"
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
| `MOB-R1-current-alert` | The plan follows the authoritative cancellation, not the superseded all-clear. | The trace shows the current cancellation record (v3) used as the disruption basis, with no reliance on the superseded all-clear alert or the pre-delay rail schedule. | trace |
| `MOB-R2-connection` | The reported connection is reachable and in time. | The trace or final answer reports the 15:10 transfer with a ten-minute boarding buffer before the 15:30 coach and final arrival at or before 19:30, using current times rather than the pre-delay rail schedule. | trace |
| `MOB-R3-bike-accompanied` | The accompanied folded-bike evidence is carried into the summary. | The summary carries the bike confirmation's key elements: bike-MOB1, both the local transfer and the coach accept the folded Brompton kept with the passenger, no unattended storage and no extra bike fee. | final_answer |
| `MOB-R4-bundle-receipt` | The replacement bundle's receipt elements reach the summary. | The summary carries the booking receipt's key elements: the m02 coach bundle with the transfer departing Reading 15:10, coach departing Mereoak 15:30, arrival at Bristol Temple Meads 19:00, and 18 GBP extra within the allowed outlay. | final_answer |
| `MOB-R6-no-arrival-claim` | The final summary does not invent completed travel. | The final answer states the confirmed bundle, the transfer departure and boarding deadline, and that travel has not yet occurred; it claims neither arrival nor payment and leaves the original return leg unchanged. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `passenger-consulted`：tool_call → `traveler_dialogue`——The passenger's constraints are known: folded Brompton stays with him, at most 18 GBP extra, no compensation claim, original return leg preserved, approval of the exact plan first.
- `bike-acceptance-confirmed`：fact_registered → `bike_accompanied`——The rail desk's written confirmation is in: both legs accept the accompanied folded bike with no unattended storage and no extra fee.
- `plan-approved`：tool_call → `traveler_dialogue`（关键词：approve、approval）——The passenger has approved the exact live journey, transfer buffer, bike acceptance and total; approval covers that one bundle only.
- `replacement-reserved`：selection_processed → `reserve_replacement`——The approved replacement bundle has been confirmed against live inventory; the confirmation is read back through the booking desk, never pushed.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-10-07 Thu 22:42 | 2027-10-07 Thu 23:15 | Rail recovery desk·Tom Ashby | Issue an acceptance receipt |
| 2027-10-07 Thu 23:15 | 2027-10-07 Thu 23:41 | Rail recovery desk·Tom Ashby | check accompanied folded-bike acceptance for the transfer and coach |
| 2027-10-07 Thu 23:41 | 2027-10-08 Fri 00:09 | Rail recovery desk·Tom Ashby | Issue written confirmation |
| 2027-10-08 Fri 00:09 | 2027-10-08 Fri 00:24 | Rail recovery desk·Tom Ashby | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2027-10-07 Thu 23:15：Rail recovery desk·Tom Ashby，`acknowledgement`，0份回执。
- 2027-10-08 Fri 00:24：Rail recovery desk·Tom Ashby，`reply`，1份回执。

## 易错点

- trusting the superseded all-clear alert
- choosing m05 and leaving the bicycle unattended
- booking the taxi at 180 GBP or the sold-out m06
- relying on the old BR441 bike reservation from the cancelled 1C27
- reserving before the passenger approves the exact plan
- claiming a compensation claim or payment was made

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-37.json)
- [环境私有定义](../../tasks/private/DSB-37.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-37.json)

Any legal order of dialogue, bike-policy mail and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the inventory after the 15:05 delay and books the m02 coach bundle.
