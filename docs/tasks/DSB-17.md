# DSB-17 · Home family lunch: helper-covered meal after a delivery-time change

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：food_dining。开始：2027-07-09 Fri 21:00；截止：2027-07-12 Mon 00:00（北京时间）。

参考轨迹历时：**1.33333天（32小时）**。结果类别：`resolved`。

跨度设计：短期；mid-week delivery-time rewrite invalidating helper coverage plus mail verification turnaround。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Arrange a Sunday July 11 lunch at home for four adults and two children, total at most 280 USD including tax and delivery, with someone explicitly covering mealtime assistance. Ask me about the missing constraints and authorization before ordering; obtain written exact-menu sesame controls, confirm a helper covers the whole 60-minute meal window, watch for delivery-time changes, and make at most one approved order. No payment.

Advisory and coordination only: search menus, contact the kitchen and helpers, gather written verification and coverage acknowledgements, and place at most the one meal order the organizer has approved; no payment or other binding commitment.

已给信息：

```json
{
  "date": "2027-07-11",
  "party_size": 6,
  "location": "home"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- mid-episode delivery-time rewrite moves ff1 from 12:00 to 13:30 and invalidates Ana-compatible coverage
- written sesame-control verification turnaround by mail
- helper windows differ (Ana 12:00-13:00 vs Marta 13:00-15:00) and only Marta spans the revised meal
- search-discoverable menu inventory with five ineligible listings
- hidden order desk revalidates the live listing
- sparse prompt: family and helper facts only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Home Meal Kitchen supervisor·Sam Reyes (`kitchen`)

角色：exact-menu allergen controls, delivery windows and meal orders。Confirms written exact-menu controls as provider reports; current menus, delivery windows and prices come from the meal search service (menu_search) and can be revised without notice; orders go through the order desk named on the entry page.

[独立角色配置](../../tasks/actors/DSB-17/kitchen.json) · 日历 `us_eastern_daily` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Home Meal Kitchen supervisor·Sam Reyes，负责exact-menu allergen controls, delivery windows and meal orders。Confirms written exact-menu controls as provider reports; current menus, delivery windows and prices come from the meal search service (menu_search) and can be revised without notice; orders go through the order desk named on the entry page. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：controls、delivery_time、fish_free、meal_ordered、total_cost

**流程：Sesame controls verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`kitchen.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the exact-menu sesame cross-contact controls and child meal preparation<br>`kitchen.main.2.lookup` | 180工作分钟 | 读取本地事实：controls、fish_free |
| 签发书面确认<br>`kitchen.main.3.document` | 30工作分钟 | 签发文本证据：controls、fish_free |
| 向请求者回复已取得的结果<br>`kitchen.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Delivery and order status** (`status`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| check the current delivery windows and published menus<br>`kitchen.status.1.lookup` | 60工作分钟 | 读取本地事实： |
| 向请求者回复已取得的结果<br>`kitchen.status.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Family helper·Ana Ruiz (`ana`)

角色：authorized midday helper, 12:00-13:00 only。Authorized for wheelchair assistance, child supervision and meal handoff only within 12:00-13:00; cannot extend past 13:00 and does not speak for other helpers.

[独立角色配置](../../tasks/actors/DSB-17/ana.json) · 日历 `us_eastern_daily` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Family helper·Ana Ruiz，负责authorized midday helper, 12:00-13:00 only。Authorized for wheelchair assistance, child supervision and meal handoff only within 12:00-13:00; cannot extend past 13:00 and does not speak for other helpers. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：ana_window

**流程：Availability confirmation** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`ana.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check her authorized coverage window<br>`ana.main.2.lookup` | 60工作分钟 | 读取本地事实：ana_window |
| 签发书面确认<br>`ana.main.3.document` | 20工作分钟 | 签发文本证据：ana_window |
| 向请求者回复已取得的结果<br>`ana.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Family helper·Marta Vela (`marta`)

角色：authorized afternoon helper, 13:00-15:00。Authorized for wheelchair assistance, child supervision and meal handoff within 13:00-15:00; acknowledges coverage only for meal windows fully inside her authorized hours.

[独立角色配置](../../tasks/actors/DSB-17/marta.json) · 日历 `us_eastern_daily` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Family helper·Marta Vela，负责authorized afternoon helper, 13:00-15:00。Authorized for wheelchair assistance, child supervision and meal handoff within 13:00-15:00; acknowledges coverage only for meal windows fully inside her authorized hours. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：helper_ack、marta_window

**流程：Coverage acknowledgement** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`marta.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check her authorized coverage window against the requested meal window<br>`marta.main.2.lookup` | 90工作分钟 | 读取本地事实：marta_window、helper_ack |
| 签发书面确认<br>`marta.main.3.document` | 20工作分钟 | 签发文本证据：marta_window、helper_ack |
| 向请求者回复已取得的结果<br>`marta.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `delivery_time` | `"13:30"` | The confirmed menu ff1 version 2 delivery starts at 13:30 New York time on 2027-07-11, so the meal window runs 13:30-14:30. |
| `total_cost` | `236.0` | The current total for menu ff1 version 2 is 236.00 USD including tax and delivery, within the 280 USD budget. |
| `controls` | `true` | Written provider controls for menu ff1: no sesame ingredients in the selected dishes, separate cleaned utensils and preparation space, and a flagged allergy ticket, with no substitutions without a fresh check. These are provider-reported controls, not a medical guarantee. |
| `fish_free` | `true` | Both child portions on menu ff1 are prepared without fish. |
| `marta_window` | `"13:00-15:00"` | Marta is authorized for wheelchair assistance, child supervision and meal handoff from 13:00 to 15:00 on 2027-07-11. |
| `helper_ack` | `true` | Marta acknowledged covering wheelchair assistance, child supervision and meal handoff for the full 13:30-14:30 meal window on 2027-07-11. |
| `meal_ordered` | `true` | One order for menu ff1 version 2, six portions delivered at 13:30 on 2027-07-11 with written sesame controls and linked helper coverage acknowledged, has been confirmed; no payment was taken. |
| `ana_window` | `"12:00-13:00"` | Ana is authorized for wheelchair assistance, child supervision and meal handoff from 12:00 to 13:00 only on 2027-07-11. |

目标结论：`meal_covered`。

```json
[
  {
    "key": "meal_confirmed",
    "expected": true,
    "accepted_facts": [
      "meal_ordered"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
        }
      },
      "predicate": "meal_confirmed",
      "authorities": [
        "attest:meal_confirmed"
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
    "key": "delivery_time",
    "expected": "13:30",
    "accepted_facts": [
      "delivery_time"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
        }
      },
      "predicate": "delivery_time",
      "authorities": [
        "attest:delivery_time"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "13:30": [
            "The confirmed menu ff1 version 2 delivery starts at 13:30 New York time on 2027-07-11, so the meal window runs 13:30-14:30.",
            "The confirmed menu ff1 version 2 delivery starts at 13:30 New York time on 2027-07-11, so the meal window runs 13:30-14:30"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "13:30": [
          "The confirmed menu ff1 version 2 delivery starts at 13:30 New York time on 2027-07-11, so the meal window runs 13:30-14:30.",
          "The confirmed menu ff1 version 2 delivery starts at 13:30 New York time on 2027-07-11, so the meal window runs 13:30-14:30"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "total_cost",
    "expected": 236.0,
    "accepted_facts": [
      "total_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
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
    "key": "sesame_controls_written",
    "expected": true,
    "accepted_facts": [
      "controls"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
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
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
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
    "key": "helper_window",
    "expected": "13:00-15:00",
    "accepted_facts": [
      "marta_window"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
        }
      },
      "predicate": "helper_window",
      "authorities": [
        "attest:helper_window"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "13:00-15:00": [
            "Marta is authorized for wheelchair assistance, child supervision and meal handoff from 13:00 to 15:00 on 2027-07-11.",
            "Marta is authorized for wheelchair assistance, child supervision and meal handoff from 13:00 to 15:00 on 2027-07-11"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "13:00-15:00": [
          "Marta is authorized for wheelchair assistance, child supervision and meal handoff from 13:00 to 15:00 on 2027-07-11.",
          "Marta is authorized for wheelchair assistance, child supervision and meal handoff from 13:00 to 15:00 on 2027-07-11"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "helper_acknowledged",
    "expected": true,
    "accepted_facts": [
      "helper_ack"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-17",
        "case": {
          "date": "2027-07-11",
          "party_size": 6,
          "location": "home"
        }
      },
      "predicate": "helper_acknowledged",
      "authorities": [
        "attest:helper_acknowledged"
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
| `XFF-R1-order-receipt` | The final summary carries the order receipt's key elements. | The summary states one confirmed order of menu ff1 version 2, six portions (four adult, two child) delivered 2027-07-11 at 13:30 New York time, total 236.00 USD including tax and delivery, with no payment taken. | final_answer |
| `XFF-R2-controls-written` | Written exact-menu sesame controls were obtained from the provider. | The summary reports the kitchen's written controls for menu ff1 - no sesame ingredients in the selected dishes, separate cleaned utensils and preparation space, a flagged allergy ticket - described as provider-reported, and both child portions fish-free. | final_answer |
| `XFF-coverage-matched-to-current-time` | Helper coverage was matched to the menu's current delivery time after the change, not to the withdrawn 12:00 window. | The trace shows the acknowledged helper window corresponds to the 13:30 delivery (Marta 13:00-15:00 covering 13:30-14:30), with no commitment relying on Ana's 12:00-13:00 window or on the driver for mealtime assistance. | trace |
| `XFF-refreshed-listing-booked` | The order used the refreshed delivery-time listing. | The trace shows the agent re-checked the menus after the July 10 change and ordered ff1 version 2 at the 13:30 delivery, never the withdrawn 12:00 version. | trace |
| `XFF-no-invented-performance` | The final summary is accurate and does not overclaim. | The final answer reports the confirmed order, delivery time, total, controls described as provider-reported and the named helper coverage, and claims neither that the meal was eaten or care performed, that payment was made, nor zero allergy risk. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `family-requirements-known`：tool_call → `family_dialogue`——The family organizer has been asked about the party, accessibility, food requirements, helpers, budget and approval rules; nothing was ordered yet.
- `menus-read`：tool_call → `menu_search`——The current home-meal menus are in the agent's hands; delivery times can be revised mid-week, so earlier rows may be stale.
- `controls-verified`：fact_registered → `controls`——The kitchen's written exact-menu sesame cross-contact controls have landed; the allergen claim now rests on provider evidence, not a listing label.
- `helper-acknowledged`：fact_registered → `helper_ack`——A helper has acknowledged covering wheelchair assistance, child supervision and meal handoff for the current meal window in writing.
- `plan-approved`：tool_call → `family_dialogue`（关键词：approve、approval）——The organizer has been shown the exact revised plan - menu, portions, delivery window, cost and named helper - and approval applies only to that plan.
- `order-confirmed`：selection_processed → `meal_order`——The one approved meal order has been processed; the confirmation receipt is with the agent and nothing further was ordered.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-07-09 Fri 21:32 | 2027-07-09 Fri 22:20 | Home Meal Kitchen supervisor·Sam Reyes | 发出受理回执 |
| 2027-07-09 Fri 22:20 | 2027-07-10 Sat 01:26 | Home Meal Kitchen supervisor·Sam Reyes | check the exact-menu sesame cross-contact controls and child meal preparation |
| 2027-07-10 Sat 01:26 | 2027-07-10 Sat 02:09 | Home Meal Kitchen supervisor·Sam Reyes | 签发书面确认 |
| 2027-07-10 Sat 02:09 | 2027-07-10 Sat 02:24 | Home Meal Kitchen supervisor·Sam Reyes | 向请求者回复已取得的结果 |
| 2027-07-10 Sat 22:36 | 2027-07-10 Sat 23:16 | Family helper·Marta Vela | 发出受理回执 |
| 2027-07-10 Sat 23:16 | 2027-07-11 Sun 01:03 | Family helper·Marta Vela | check her authorized coverage window against the requested meal window |
| 2027-07-11 Sun 01:03 | 2027-07-11 Sun 01:37 | Family helper·Marta Vela | 签发书面确认 |
| 2027-07-11 Sun 01:37 | 2027-07-11 Sun 01:52 | Family helper·Marta Vela | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-07-09 Fri 22:20：Home Meal Kitchen supervisor·Sam Reyes，`acknowledgement`，0份回执。
- 2027-07-10 Sat 02:24：Home Meal Kitchen supervisor·Sam Reyes，`reply`，1份回执。
- 2027-07-10 Sat 23:16：Family helper·Marta Vela，`acknowledgement`，0份回执。
- 2027-07-11 Sun 01:52：Family helper·Marta Vela，`reply`，1份回执。

## 易错点

- ordering the stale 12:00 version after the rewrite
- relying on Ana's 12:00-13:00 window for a 13:30-14:30 meal
- treating the delivery driver Luis as a caregiver substitute
- accepting a sesame-free label without written cross-contact controls
- ordering before the organizer approves the exact plan after the time change
- picking an ineligible menu (fish in child meals, sesame, four portions, over budget)

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-17.json)
- [环境私有定义](../../tasks/private/DSB-17.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-17.json)

Any legal order of dialogue, verification mail, helper acknowledgements and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the ff1 offer after the July 10 change and links Marta's coverage. The already-verified ff6 menu at 12:00 with Ana is a legal alternative route, but the scored answer keys follow the refreshed ff1 v2 plan.
