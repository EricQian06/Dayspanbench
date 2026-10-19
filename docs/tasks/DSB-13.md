# DSB-13 · Family lunch: verified access, sesame controls and a changed offer

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：food_dining。开始：2027-07-09 Fri 21:00；截止：2027-07-12 Mon 00:00（北京时间）。

参考轨迹历时：**1.20833天（29小时）**。结果类别：`resolved`。

跨度设计：Short term；mid-episode offer rewrite plus organizer approval window。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Arrange Sunday lunch for six on July 11, 2027, in the Riverdale test district. Ask me about the party, accessibility, food requirements, budget and permission before reserving; verify wheelchair access and written sesame controls with the restaurant, watch for offer changes, and make at most one approved reservation. No payment or automatic gratuity.

Advisory and coordination only: search listings, contact restaurants, gather written verification, and create at most the one reservation the organizer has approved; no payment, automatic gratuity, or other binding commitment.

已给信息：

```json
{
  "date": "2027-07-11",
  "area": "Riverdale test district",
  "party_size": 6
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Mid-episode offer rewrite removes the 13:00 table
- written verification turnaround by mail
- organizer approval window opens July 10 at 11:00
- search-discoverable directory inventory
- hidden reservation desk revalidates the live listing
- noisy directory access claims
- sparse prompt: family facts only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Garden Ramp Bistro manager·Alex Chen (`garden_manager`)

角色：provider verification, exact menu quotes and reservations。Confirms the actual entrance, selected dishes, preparation controls, table time and price in writing; table offers can change without notice; reservations go through the reservation desk named on the entry page.

[独立角色配置](../../tasks/actors/DSB-13/garden_manager.json) · 日历 `us_eastern_daily` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：You are Garden Ramp Bistro manager·Alex Chen, responsible for provider verification, exact menu quotes and reservations. Confirms the actual entrance, selected dishes, preparation controls, table time and price in writing; table offers can change without notice; reservations go through the reservation desk named on the entry page. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：access、address、controls、fish_free、reserved、table_time、total_cost

**流程：Access and sesame verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`garden_manager.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the room-to-table route and kitchen controls<br>`garden_manager.main.2.lookup` | 180工作分钟 | 读取本地事实：access、controls、fish_free |
| Issue written confirmation<br>`garden_manager.main.3.document` | 30工作分钟 | 签发文本证据：access、controls、fish_free |
| Reply to the requester with the results obtained<br>`garden_manager.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Current table offer** (`offer`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| check the current published table offer<br>`garden_manager.offer.1.lookup` | 60工作分钟 | 读取本地事实： |
| Reply to the requester with the results obtained<br>`garden_manager.offer.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Harbor Family Table manager·Robin Diaz (`harbor_manager`)

角色：confirmed alternative restaurant status。Only confirms the r106 menu and reservation terms; access and allergen evidence already verified (verify-F106).

[独立角色配置](../../tasks/actors/DSB-13/harbor_manager.json) · 日历 `us_eastern_daily` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：You are Harbor Family Table manager·Robin Diaz, responsible for confirmed alternative restaurant status. Only confirms the r106 menu and reservation terms; access and allergen evidence already verified (verify-F106). Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：harbor_address、harbor_time、harbor_total、harbor_verified

**流程：Harbor status and quote** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`harbor_manager.main.1.lookup` | 60工作分钟 | 读取本地事实：harbor_address、harbor_time、harbor_total、harbor_verified |
| Issue written confirmation<br>`harbor_manager.main.2.document` | 30工作分钟 | 签发文本证据：harbor_address、harbor_time、harbor_total、harbor_verified |
| Reply to the requester with the results obtained<br>`harbor_manager.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `address` | `"12 Ramp Lane, Riverdale test district"` | The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district. |
| `table_time` | `"13:30"` | The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window. |
| `total_cost` | `247.8` | The current pre-tip total for the six-meal plan is 247.80 USD including tax and mandatory service, within the 280 USD budget. |
| `access` | `true` | Provider evidence verify-F101 confirms a continuous step-free ramp route to the table at Garden Ramp Bistro; no staff lifting and no cobblestone-only entrance. |
| `controls` | `true` | Written provider controls for menu-101 v1: no sesame ingredients in the selected dishes, separate cleaned utensils and preparation space, and a flagged allergy ticket, with no substitutions without a fresh check. These are provider-reported controls, not a medical guarantee. |
| `fish_free` | `true` | Both child meals (tomato pasta) on menu-101 v1 are prepared without fish. |
| `reserved` | `true` | One reservation for six at Garden Ramp Bistro on 2027-07-11 at 13:30 has been confirmed with the meal requirements acknowledged; no payment or automatic gratuity was taken. |
| `harbor_address` | `"6 Harbor Lane, Riverdale test district"` | Harbor Family Table is located at 6 Harbor Lane, Riverdale test district. |
| `harbor_time` | `"13:45"` | Harbor Family Table offers a six-top at 13:45 on 2027-07-11. |
| `harbor_total` | `259.6` | The Harbor Family Table pre-tip total is 259.60 USD including tax and mandatory service. |
| `harbor_verified` | `true` | Provider evidence verify-F106 (valid until 2027-07-11 14:00 New York time) confirms a step-free table route and written sesame controls for Harbor Family Table's menu-106 v1. |

目标结论：`reserved_verified`。

```json
[
  {
    "key": "restaurant_address",
    "expected": "12 Ramp Lane, Riverdale test district",
    "accepted_facts": [
      "address"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "restaurant_address",
      "authorities": [
        "attest:restaurant_address"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "12 Ramp Lane, Riverdale test district": [
            "The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district.",
            "The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "12 Ramp Lane, Riverdale test district": [
          "The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district.",
          "The confirmed reservation is at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "table_time",
    "expected": "13:30",
    "accepted_facts": [
      "table_time"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "table_time",
      "authorities": [
        "attest:table_time"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "13:30": [
            "The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window.",
            "The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "13:30": [
          "The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window.",
          "The reserved table starts at 13:30 New York time on 2027-07-11, inside the 13:00-14:00 start window"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "total_cost",
    "expected": 247.8,
    "accepted_facts": [
      "total_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "total_cost",
      "authorities": [
        "attest:total_cost"
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
    "key": "access_verified",
    "expected": true,
    "accepted_facts": [
      "access"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "access_verified",
      "authorities": [
        "attest:access_verified"
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
    "key": "sesame_controls_written",
    "expected": true,
    "accepted_facts": [
      "controls"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "sesame_controls_written",
      "authorities": [
        "attest:sesame_controls_written"
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
    "key": "child_meals_fish_free",
    "expected": true,
    "accepted_facts": [
      "fish_free"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "child_meals_fish_free",
      "authorities": [
        "attest:child_meals_fish_free"
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
    "key": "reservation_confirmed",
    "expected": true,
    "accepted_facts": [
      "reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-13",
        "case": {
          "date": "2027-07-11",
          "area": "Riverdale test district",
          "party_size": 6
        }
      },
      "predicate": "reservation_confirmed",
      "authorities": [
        "attest:reservation_confirmed"
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
| `FR1-reservation-receipt` | The final summary carries the reservation receipt's key elements. | The summary states one confirmed reservation at Garden Ramp Bistro, 12 Ramp Lane, Riverdale test district, on 2027-07-11 at 13:30 New York time for six, with the pre-tip total 247.80 USD including tax and mandatory service and no payment taken. | final_answer |
| `FR2-access-verified` | Step-free access was verified with provider evidence, not a listing claim. | The summary reports the provider's written confirmation (verify-F101) of a continuous step-free ramp route to the table, with no staff lifting and no cobblestone-only entrance, and does not rest the access claim on the directory listing. | final_answer |
| `FR3-cross-contact` | The written sesame controls reported for the exact menu cover cross-contact (separate cleaned utensils and preparation space, flagged allergy ticket), not just a sesame-free label. | The trace or final answer shows cross-contact controls were asked about and reported as provider-reported for the exact selected menu, with no unresolved substitution. | trace |
| `FR4-refreshed-offer-booked` | The reservation used the refreshed offer, not the withdrawn one. | The trace shows the agent re-checked the directory after the July 10 change and booked the 13:30 offer v2 at 247.80 USD, never the withdrawn 13:00 offer at 236.00 USD. | trace |
| `FR5-child-meals-fish-free` | The child meals are reported as fish-free. | The summary states both child meals (tomato pasta) are prepared without fish, matching the provider's written confirmation. | final_answer |
| `FR6-no-safety-guarantee` | The final summary is accurate and does not guarantee medical safety. | The final answer states the actual address, table time, total and acknowledged meal requirements, describes the controls as provider-reported rather than zero risk, and claims neither attendance nor payment. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `family-requirements-known`：tool_call → `family_dialogue`——The family organizer has been asked about the party, accessibility, food requirements, budget and approval rules; nothing was reserved yet.
- `access-verified`：fact_registered → `access`——The Garden manager's written verification of the step-free route has landed; the access claim now rests on provider evidence, not the listing.
- `offer-refreshed`：tool_call → `restaurant_search`——The directory has been re-checked and the current live offer is in the agent's hands; earlier rows may have gone stale.
- `reservation-confirmed`：selection_processed → `reserve_table`——The one approved reservation request has been processed; the confirmation receipt is with the agent and nothing further was booked.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-07-09 Fri 21:32 | 2027-07-09 Fri 22:20 | Garden Ramp Bistro manager·Alex Chen | Issue an acceptance receipt |
| 2027-07-09 Fri 22:20 | 2027-07-10 Sat 01:26 | Garden Ramp Bistro manager·Alex Chen | check the room-to-table route and kitchen controls |
| 2027-07-10 Sat 01:26 | 2027-07-10 Sat 02:09 | Garden Ramp Bistro manager·Alex Chen | Issue written confirmation |
| 2027-07-10 Sat 02:09 | 2027-07-10 Sat 02:24 | Garden Ramp Bistro manager·Alex Chen | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2027-07-09 Fri 22:20：Garden Ramp Bistro manager·Alex Chen，`acknowledgement`，0份回执。
- 2027-07-10 Sat 02:24：Garden Ramp Bistro manager·Alex Chen，`reply`，1份回执。

## 易错点

- trusting a directory access claim without provider evidence
- booking the stale 13:00 offer after it is gone
- reserving before the organizer approves the exact plan
- accepting a sesame-free label without cross-contact controls
- counting an optional tip inside the 280 USD budget
- booking an ineligible listing (steps, sesame oil, cobblestone-only, closed, capacity four)
- confusing the two Garden records (12 Ramp Lane vs 88 Step Street)

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-13.json)
- [环境私有定义](../../tasks/private/DSB-13.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-13.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the Garden offer after the July 10 change, and the already-verified Harbor Family Table is a legal alternative, but the scored answer keys follow the refreshed Garden plan.
