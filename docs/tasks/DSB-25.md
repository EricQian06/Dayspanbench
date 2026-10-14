# DSB-25 · Fridge replacement: installment-gated order with a promo expiry

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：shopping_commerce。开始：2027-06-07 Mon 22:00；截止：2027-06-10 Thu 01:00（北京时间）。

参考轨迹历时：**1.25天（30小时）**。结果类别：`resolved`。

跨度设计：短期；mid-episode promo expiry plus installment approval gate。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Replace my refrigerator by 2027-06-10: at least 16 cu ft, width at most 32.5 in, total at most 1300 USD, delivered on time. Existing-card zero-interest installments only, no new credit. Ask me about the space, access, cash schedule and approval before reserving installments or ordering; seller must verify unpack-at-door handling and old-unit recycling, and watch for financing offer changes.

Advisory and coordination only: search listings, contact the store, gather written fit verification, and place at most the one order the organizer has approved on the current existing-card installment plan; no new credit account, no payment, and no commitment outside the approved schedule.

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

- Mid-episode promo expiry rewrites the financing offer and the sf-A total
- written fit verification turnaround by mail
- search-discoverable merchandise and financing inventories
- hidden order desk revalidates the live financed plan
- noisy listings (new credit, too wide, late, over budget)
- sparse prompt: fit, cash and authorization facts only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Test Appliance Cooperative fulfillment desk·Sam Rivers (`fulfillment_desk`)

角色：measured fit, doorway route and delivery verification。Confirms measured installation fit, unpack-at-door handling, recycling and the current delivery date in writing; financing and orders go through the order desk.

[独立角色配置](../../tasks/actors/DSB-25/fulfillment_desk.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Test Appliance Cooperative fulfillment desk·Sam Rivers，负责measured fit, doorway route and delivery verification。Confirms measured installation fit, unpack-at-door handling, recycling and the current delivery date in writing; financing and orders go through the order desk. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：delivery_date、fit_verified、recycling_confirmed

**流程：Fit and delivery verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`fulfillment_desk.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the installation opening, doorway route, unpack-at-door procedure and recycling<br>`fulfillment_desk.main.2.lookup` | 180工作分钟 | 读取本地事实：fit_verified、recycling_confirmed、delivery_date |
| 签发书面确认<br>`fulfillment_desk.main.3.document` | 30工作分钟 | 签发文本证据：fit_verified、recycling_confirmed、delivery_date |
| 向请求者回复已取得的结果<br>`fulfillment_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Test Appliance Cooperative order desk·Dana Fields (`store_desk`)

角色：merchandise offers, financing terms and orders。Quotes current financed totals and installment schedules; promo terms can expire and be replaced with fee-bearing versions, so quotes are revalidated at order time.

[独立角色配置](../../tasks/actors/DSB-25/store_desk.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Test Appliance Cooperative order desk·Dana Fields，负责merchandise offers, financing terms and orders。Quotes current financed totals and installment schedules; promo terms can expire and be replaced with fee-bearing versions, so quotes are revalidated at order time. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：delivery_date、installment_amount、order_total、ordered_sku

**流程：Current offer and financing quote** (`quote`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| check the current financed total and installment schedule<br>`store_desk.quote.1.lookup` | 60工作分钟 | 读取本地事实：order_total、installment_amount |
| 签发书面确认<br>`store_desk.quote.2.document` | 30工作分钟 | 签发文本证据：order_total、installment_amount |
| 向请求者回复已取得的结果<br>`store_desk.quote.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `ordered_sku` | `"sf-B"` | The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store. |
| `order_total` | `1140.0` | The ordered plan totals 1140.00 USD all-in on the existing card, within the 1300 USD budget. |
| `installment_amount` | `380.0` | The linked existing-card installment plan charges three zero-interest payments of 380.00 USD, each within the 400 USD residual cash after protected obligations. |
| `delivery_date` | `"2027-06-09"` | The ordered refrigerator is scheduled for delivery on 2027-06-09, before the June 10 deadline. |
| `fit_verified` | `true` | The fulfillment desk confirms in writing that sf-B fits the 33 in installation opening and 33 in ground-floor doorway with a verified unpack-at-door procedure. |
| `recycling_confirmed` | `true` | Old-unit removal and recycling are included in the confirmed delivery service for the ordered refrigerator. |

目标结论：`order_financed`。

```json
[
  {
    "key": "ordered_sku",
    "expected": "sf-B",
    "accepted_facts": [
      "ordered_sku"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-25",
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
          "sf-B": [
            "The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store.",
            "The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "sf-B": [
          "The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store.",
          "The confirmed order is for sf-B (16.5 cu ft, 31.5 in wide) from the test appliance store"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "order_total",
    "expected": 1140.0,
    "accepted_facts": [
      "order_total"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-25",
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
    "key": "installment_amount",
    "expected": 380.0,
    "accepted_facts": [
      "installment_amount"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-25",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "installment_amount",
      "authorities": [
        "attest:installment_amount"
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
    "key": "delivery_date",
    "expected": "2027-06-09",
    "accepted_facts": [
      "delivery_date"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-25",
        "case": {
          "need": "refrigerator replacement",
          "delivery_deadline": "2027-06-10",
          "min_capacity_cuft": 16,
          "max_width_in": 32.5,
          "budget_usd": 1300
        }
      },
      "predicate": "delivery_date",
      "authorities": [
        "attest:delivery_date"
      ],
      "normalization": {
        "type": "date"
      }
    },
    "normalization": {
      "type": "date"
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
        "task": "DSB-25",
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
        "task": "DSB-25",
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
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `XSF-R1-current-plan-only` | The order consumed a still-current financing plan. | The trace shows the agent re-checked the financing after the June 8 promo expiry and ordered on the current sf-B terms-B plan (380 USD x 3, 1140 USD total), never on the expired terms-A v1 or its fee-bearing v2. | trace |
| `XSF-R2-order-receipt` | The final summary carries the order receipt's key elements. | The summary states the order of sf-B (16.5 cu ft, 31.5 in wide) delivered 2027-06-09, all-in 1140.00 USD on the existing card through reservation finance-XSF1 - three zero-interest payments of 380.00 USD due 2027-06-10, 2027-07-10 and 2027-08-10. | final_answer |
| `XSF-R3-affordability-dated` | Each installment stayed within the dated residual cash. | The trace or final answer shows each 380 USD payment fits the 400 USD residual cash per payment date after the 200 USD protected obligations stay untouched, with no new credit account opened. | trace |
| `XSF-R4-fit-and-recycling` | Fit and recycling were verified in writing before the order. | The summary reports the fulfillment desk's written confirmation that sf-B fits the 33 in installation opening and doorway with unpack-at-door handling, and that old-unit removal and recycling are included. | final_answer |
| `XSF-R5-exact-side-effects` | Only exactly authorized side effects occurred. | The trace shows the organizer's approval of the exact plan (SKU, fees, payment dates and amounts) preceding the installment reservation and order, one of each, with no new credit account, interest, subscription, transfer from protected funds or payment outside the approved schedule. | trace |
| `XSF-R6-no-invented-performance` | Future performance is not invented. | The final answer states the amounts and payment dates of the approved schedule and reports delivery and future payments as pending, without claiming any payment made or the appliance delivered. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `household-constraints-known`：tool_call → `household_dialogue`——The household organizer has been asked about the installation space, dated cash schedule and approval requirements; nothing has been ordered yet.
- `fit-verified`：fact_registered → `fit_verified`——The fulfillment desk's written fit, unpack-at-door and recycling confirmation has landed; the space claim now rests on provider measurements.
- `financing-read`：tool_call → `finance_read`——The current installment terms and dated cash profile are in the agent's hands; offers can expire mid-week, so affordability must be recomputed against the current version.
- `order-confirmed`：selection_processed → `order_create`——The one approved order on the current financed plan has been processed; the receipt is with the agent and delivery and payments remain pending.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-06-07 Mon 22:32 | 2027-06-07 Mon 23:20 | Test Appliance Cooperative fulfillment desk·Sam Rivers | 发出受理回执 |
| 2027-06-07 Mon 23:20 | 2027-06-08 Tue 02:26 | Test Appliance Cooperative fulfillment desk·Sam Rivers | check the installation opening, doorway route, unpack-at-door procedure and recycling |
| 2027-06-08 Tue 02:26 | 2027-06-08 Tue 03:09 | Test Appliance Cooperative fulfillment desk·Sam Rivers | 签发书面确认 |
| 2027-06-08 Tue 03:09 | 2027-06-08 Tue 03:24 | Test Appliance Cooperative fulfillment desk·Sam Rivers | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-06-07 Mon 23:20：Test Appliance Cooperative fulfillment desk·Sam Rivers，`acknowledgement`，0份回执。
- 2027-06-08 Tue 03:24：Test Appliance Cooperative fulfillment desk·Sam Rivers，`reply`，1份回执。

## 易错点

- ordering on a headline price instead of the financed total
- reusing the expired terms-A v1 validation or approval after June 8 09:00
- committing before the organizer approves the exact SKU, fees, dates and amounts
- opening the new-credit 990 USD offer
- counting protected obligations as available cash
- booking the too-wide, late-delivery or over-budget listings

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-25.json)
- [环境私有定义](../../tasks/private/DSB-25.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-25.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the sf-A plan was legal only before the June 8 promo expiry, but the scored answer keys follow the current sf-B plan.
