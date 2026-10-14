# DSB-40 · Fridge replacement: verified access and a changed delivery slot

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：shopping_commerce。开始：2027-06-07 Mon 22:00；截止：2027-06-10 Thu 01:00（北京时间）。

参考轨迹历时：**1.375天（33小时）**。结果类别：`resolved`。

跨度设计：短期；mid-episode delivery-slot rewrite plus approval window。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Our refrigerator failed. Find one with at least 16 cu ft, Energy Star, no wider than 32.5 in, at most 1300 USD all-in including tax, delivery and old-fridge recycling, delivered by 2027-06-10 09:00 Chicago time. Ask me about the space, access, address and ordering permission before ordering; the seller must verify unpack-at-door fit and recycling in writing, watch for delivery-slot changes, and make at most one approved order. Pay on delivery only - no new credit, subscription, deposit or agent payment.

Advisory and coordination only: search listings, contact the store, gather written fit verification, and place at most the one pay-on-delivery order the householder has approved; no payment, new credit account, subscription, deposit or other binding commitment.

已给信息：

```json
{
  "need": "refrigerator replacement",
  "delivery_deadline": "2027-06-10",
  "min_capacity_cuft": 16,
  "max_width_in": 32.5,
  "budget_usd": 1300
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Mid-episode delivery-slot rewrite removes COOL-17-A's June 9 route
- written fit verification publishes from June 8 09:00
- approval window opens June 8 at 13:00
- side thread: written service-elevator booking from the building manager
- unauthorized price-comparison sheet undercuts the official all-in total
- inventory desk hedge guess about building access needs verification
- search-discoverable listing inventory
- hidden order desk revalidates the live listing and slot
- noisy listings (new credit, too wide, backordered, headline-vs-all-in price)
- sparse prompt: household facts only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Test Appliance Cooperative delivery specialist·Morgan Hale (`fulfillment_agent`)

角色：measured dimensions, access verification and delivery slots。Confirms measured installation fit, the unpack-at-door route and recycling in writing; verified dimensions do not guarantee the current delivery slot still meets the deadline.

[独立角色配置](../../tasks/actors/DSB-40/fulfillment_agent.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Test Appliance Cooperative delivery specialist·Morgan Hale，负责measured dimensions, access verification and delivery slots。Confirms measured installation fit, the unpack-at-door route and recycling in writing; verified dimensions do not guarantee the current delivery slot still meets the deadline. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：fit_verified、recycling_confirmed

**流程：Fit and delivery verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`fulfillment_agent.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the measured opening, doorway route, unpack-at-door procedure and recycling<br>`fulfillment_agent.main.2.lookup` | 120工作分钟 | 读取本地事实：fit_verified、recycling_confirmed |
| 签发书面确认<br>`fulfillment_agent.main.3.document` | 30工作分钟 | 签发文本证据：fit_verified、recycling_confirmed |
| 向请求者回复已取得的结果<br>`fulfillment_agent.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Test Appliance Cooperative inventory desk·Riley Carter (`store_operations`)

角色：listings, delivery slots and orders。Quotes current all-in totals and delivery slots; uncommitted delivery routes can change without notice, so slots are revalidated at order time. Building access and elevator bookings are not store records.

[独立角色配置](../../tasks/actors/DSB-40/store_operations.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Test Appliance Cooperative inventory desk·Riley Carter，负责listings, delivery slots and orders。Quotes current all-in totals and delivery slots; uncommitted delivery routes can change without notice, so slots are revalidated at order time. Building access and elevator bookings are not store records. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：delivery_window、order_total、ordered_sku、payment_terms

**流程：Listing and delivery slot status** (`slot`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`store_operations.slot.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 给出猜测性答复<br>`store_operations.slot.2.suggest` | 30工作分钟 | 给出猜测性答复： |
| check the current listing, all-in total and delivery slot<br>`store_operations.slot.3.lookup` | 60工作分钟 | 读取本地事实：order_total、delivery_window |
| 签发书面确认<br>`store_operations.slot.4.document` | 30工作分钟 | 签发文本证据：order_total、delivery_window |
| 向请求者回复已取得的结果<br>`store_operations.slot.5.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Example Court building manager·Jolene Fischer (`building_manager`)

角色：service-elevator bookings and freight access for 18 Example Court。Books the building's service elevator for appliance deliveries in writing; the store does not manage building access, and delivery crews cannot enter without a confirmed booking.

[独立角色配置](../../tasks/actors/DSB-40/building_manager.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Example Court building manager·Jolene Fischer，负责service-elevator bookings and freight access for 18 Example Court。Books the building's service elevator for appliance deliveries in writing; the store does not manage building access, and delivery crews cannot enter without a confirmed booking. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：elevator_reserved

**流程：Service elevator booking** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`building_manager.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the service-elevator schedule and book the delivery slot<br>`building_manager.main.2.lookup` | 90工作分钟 | 读取本地事实：elevator_reserved |
| 签发书面确认<br>`building_manager.main.3.document` | 30工作分钟 | 签发文本证据：elevator_reserved |
| 向请求者回复已取得的结果<br>`building_manager.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `ordered_sku` | `"COOL-16-B"` | The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store. |
| `order_total` | `1181.6` | The ordered total is 1181.60 USD all-in - item 1020.00, tax 81.60, delivery 50.00 and old-fridge recycling 30.00 - within the 1300 USD budget. |
| `delivery_window` | `"2027-06-09 10:00-12:00"` | The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline. |
| `payment_terms` | `"pay_on_delivery"` | The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit. |
| `fit_verified` | `true` | The delivery specialist confirms in writing (fit-S206) that COOL-16-B's minimum opening (32.5 x 69 x 34 in) fits the measured 33 x 70 x 35 in opening, with a verified unpack-at-door procedure giving a 32 in route through the 33 in doorway. |
| `recycling_confirmed` | `true` | Old-appliance recycling at the ground-floor address is included in the confirmed delivery service. |
| `elevator_reserved` | `"2027-06-09 09:30-10:00"` | The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval. |
| `total_ref` | `1099.0` | Neighborhood price comparison sheet, June 2027: COOL-16-B all-in 1099.00 USD with discounted delivery and waived recycling (留存方整理). |

目标结论：`order_confirmed`。

```json
[
  {
    "key": "ordered_sku",
    "expected": "COOL-16-B",
    "accepted_facts": [
      "ordered_sku"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "ordered_sku",
      "authorities": [
        "attest:ordered_sku"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "COOL-16-B": [
            "The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store.",
            "The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "COOL-16-B": [
          "The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store.",
          "The confirmed order is for COOL-16-B (16.5 cu ft, 31.5 in wide, Energy Star) from the test appliance store"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "order_total",
    "expected": 1181.6,
    "accepted_facts": [
      "order_total"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "order_total",
      "authorities": [
        "attest:order_total"
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
    "key": "delivery_window",
    "expected": "2027-06-09 10:00-12:00",
    "accepted_facts": [
      "delivery_window"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "delivery_window",
      "authorities": [
        "attest:delivery_window"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "2027-06-09 10:00-12:00": [
            "The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline.",
            "The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "2027-06-09 10:00-12:00": [
          "The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline.",
          "The assigned confirmed delivery interval is 2027-06-09 10:00-12:00 Chicago time, inside the 08:00-18:00 access hours and ending well before the June 10 09:00 deadline"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "payment_terms",
    "expected": "pay_on_delivery",
    "accepted_facts": [
      "payment_terms"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "payment_terms",
      "authorities": [
        "attest:payment_terms"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "pay_on_delivery": [
            "The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit.",
            "The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "pay_on_delivery": [
          "The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit.",
          "The order is pay-on-delivery only: the agent took no payment, opened no credit account, subscription or deposit"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "fit_verified",
    "expected": true,
    "accepted_facts": [
      "fit_verified"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "fit_verified",
      "authorities": [
        "attest:fit_verified"
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
    "key": "recycling_confirmed",
    "expected": true,
    "accepted_facts": [
      "recycling_confirmed"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "recycling_confirmed",
      "authorities": [
        "attest:recycling_confirmed"
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
    "key": "elevator_booked",
    "expected": "2027-06-09 09:30-10:00",
    "accepted_facts": [
      "elevator_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-40",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "elevator_booked",
      "authorities": [
        "attest:elevator_booked"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "2027-06-09 09:30-10:00": [
            "The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval.",
            "The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "2027-06-09 09:30-10:00": [
          "The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval.",
          "The building manager confirms in writing (lift booking L-0906) that the service elevator at 18 Example Court is reserved for the fridge delivery on 2027-06-09 09:30-10:00, ahead of the confirmed delivery interval"
        ]
      }
    },
    "match": "expected"
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `S-R1-fit-verified` | The written fit and recycling verification is carried into the summary. | The summary carries the fit verification's key elements: fit-S206 confirming COOL-16-B's minimum opening fits the measured 33 x 70 x 35 in opening with the verified unpack-at-door route, and old-fridge recycling included in the delivery service. | final_answer |
| `S-R2-order-receipt` | The order receipt's key elements reach the summary. | The summary carries the order receipt's key elements: COOL-16-B for Angela Davis at home-A, all-in 1181.60 USD (item 1020.00, tax 81.60, delivery 50.00, recycling 30.00) within the 1300 USD budget, assigned delivery 2027-06-09 10:00-12:00 Chicago time, pay on delivery. | final_answer |
| `S-R3-elevator-booking` | The service-elevator booking receipt's key elements reach the summary. | The summary carries the building manager's booking confirmation's key elements: lift booking L-0906 reserving the service elevator at 18 Example Court for 2027-06-09 09:30-10:00, ahead of the 10:00-12:00 delivery window. | final_answer |
| `S-R6-accurate-comparison` | The final explanation is accurate about tradeoffs and remaining work. | The final answer reports the exact product, full all-in price and confirmed delivery interval, explains the rejection of the new-credit, late-delivery, backordered or over-budget offers (including the headline-vs-all-in price trap), and states that payment and delivery remain pending rather than completed. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `householder-consulted`：tool_call → `householder_dialogue`——The household facts are known: 33 x 70 x 35 in opening, 33 in doorway with no stairs, home-A delivery 08:00-18:00, recycling wanted, pay-on-delivery only and review from June 8 13:00.
- `fit-verified`：fact_registered → `fit_verified`——The delivery specialist's written verification is in: measured fit, unpack-at-door route and recycling confirmed in writing. Live slots can still change, so re-check before ordering.
- `order-placed`：selection_processed → `order_create`——The one approved pay-on-delivery order has been placed against the live listing and slot; the confirmation is read back through the order desk, never pushed.
- `elevator-booked`：fact_registered → `elevator_reserved`——The building manager confirms in writing: lift booking L-0906, service elevator reserved 2027-06-09 09:30-10:00 for the refrigerator delivery.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-06-08 Tue 23:03 | 2027-06-08 Tue 23:39 | Example Court building manager·Jolene Fischer | 发出受理回执 |
| 2027-06-08 Tue 23:14 | 2027-06-08 Tue 23:57 | Test Appliance Cooperative delivery specialist·Morgan Hale | 发出受理回执 |
| 2027-06-08 Tue 23:39 | 2027-06-09 Wed 01:30 | Example Court building manager·Jolene Fischer | check the service-elevator schedule and book the delivery slot |
| 2027-06-08 Tue 23:57 | 2027-06-09 Wed 02:17 | Test Appliance Cooperative delivery specialist·Morgan Hale | check the measured opening, doorway route, unpack-at-door procedure and recycling |
| 2027-06-09 Wed 01:30 | 2027-06-09 Wed 02:17 | Example Court building manager·Jolene Fischer | 签发书面确认 |
| 2027-06-09 Wed 02:17 | 2027-06-09 Wed 03:01 | Test Appliance Cooperative delivery specialist·Morgan Hale | 签发书面确认 |
| 2027-06-09 Wed 02:17 | 2027-06-09 Wed 02:32 | Example Court building manager·Jolene Fischer | 向请求者回复已取得的结果 |
| 2027-06-09 Wed 03:01 | 2027-06-09 Wed 03:16 | Test Appliance Cooperative delivery specialist·Morgan Hale | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-06-07 Mon 22:32：Test Appliance Cooperative delivery specialist·Morgan Hale，`reply`，0份回执。
- 2027-06-08 Tue 23:39：Example Court building manager·Jolene Fischer，`acknowledgement`，0份回执。
- 2027-06-08 Tue 23:57：Test Appliance Cooperative delivery specialist·Morgan Hale，`acknowledgement`，0份回执。
- 2027-06-09 Wed 02:32：Example Court building manager·Jolene Fischer，`reply`，1份回执。
- 2027-06-09 Wed 03:16：Test Appliance Cooperative delivery specialist·Morgan Hale，`reply`，1份回执。

## 易错点

- ordering on the headline item price instead of the all-in total
- citing the neighborhood comparison sheet's 1099.00 USD instead of the store's written total
- reusing COOL-17-A's stale June 9 delivery promise after the slot change
- ordering before the householder approves the exact plan
- opening the new-credit 990 USD offer
- treating a dispatch estimate or fit verification as a confirmed slot
- skipping the service-elevator booking and assuming the crew handles building access
- booking the too-wide, backordered or over-budget listings

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-40.json)
- [环境私有定义](../../tasks/private/DSB-40.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-40.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; ordering COOL-17-A was legal only before the June 8 12:00 slot change, but the scored answer keys follow the COOL-16-B plan.
