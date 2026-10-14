# DSB-36 · Accessible festival evening: the correct 21:00 set with step-free travel

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：leisure_entertainment。开始：2027-07-31 Sat 21:00；截止：2027-08-03 Tue 04:00（北京时间）。

参考轨迹历时：**0.208333天（5小时）**。结果类别：`resolved`。

跨度设计：短期；official show confirmation plus midday ferry lift outage。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Plan our three-person family visit to Pancho Libre's 21:00 set on July 31, 2027, in the Halifax test district, total at most 360 CAD. Ask me about access needs, travel and approval; confirm the current official show and step-free seating with the festival, watch for route changes, and reserve only the approved free access places. No purchases or payments.

Advisory and coordination only: search listings, verify the current show and step-free routes, and reserve at most the approved free access places; no purchases, payments or alcohol packages.

已给信息：

```json
{
  "date": "2027-07-31",
  "city": "Halifax test district",
  "party_size": 3
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- official show confirmation and access offer appear mid-morning
- ferry lift outage at midday invalidates the step-free alternative
- prior-year paid ticket listing is stale; admission is free
- search-discoverable show and route inventory
- sparse prompt: family constraints only surface through dialogue
- hidden access desk revalidates the live offer

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Harbour Festival access desk·Priya Nair (`access_desk`)

角色：festival accessibility, seated viewing and step-free route records。Confirms seated step-free viewing capacity and the step-free bus route in writing; festival admission is free and prior-year paid ticket listings are stale; access places are reserved through the desk named on the entry page.

[独立角色配置](../../tasks/actors/DSB-36/access_desk.json) · 日历 `halifax_daily` · 时区 `America/Halifax` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：09:00—21:00

接收者约束：你是Harbour Festival access desk·Priya Nair，负责festival accessibility, seated viewing and step-free route records。Confirms seated step-free viewing capacity and the step-free bus route in writing; festival admission is free and prior-year paid ticket listings are stale; access places are reserved through the desk named on the entry page. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：access_reserved、bus_fare、home_arrival、route_step_free、seats、show_end、show_start、stage、total_cost

**流程：Seated access and step-free route status** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`access_desk.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check seated viewing capacity and step-free route status<br>`access_desk.main.2.lookup` | 60工作分钟 | 读取本地事实：seats、route_step_free、bus_fare |
| 签发书面确认<br>`access_desk.main.3.document` | 20工作分钟 | 签发文本证据：seats、route_step_free、bus_fare |
| 向请求者回复已取得的结果<br>`access_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `show_start` | `"21:00"` | The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35. |
| `stage` | `"Maritime Museum"` | The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage. |
| `show_end` | `"21:35"` | The current official set ends at 21:35, leaving the 21:50 return bus feasible. |
| `route_step_free` | `true` | The reserved bus-L route is step-free on every leg: outbound 20:00-20:20 with an eight-minute walk, standing stretches at most seven minutes, and return departing 21:50 after an eight-minute walk from the stage. |
| `home_arrival` | `"22:15"` | The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement. |
| `bus_fare` | `18` | The step-free bus-L round trip costs 18 CAD for the three-person family. |
| `total_cost` | `108` | The full family plan is 108 CAD: admission 0 (free) + transport 18 + food 60 + contingency 30, within the 360 CAD cap. |
| `access_reserved` | `true` | Three free seated step-free access places for the 21:00 set have been confirmed with check-in from 20:30 to 20:45; no payment was taken. |
| `seats` | `3` | Three seated access places are confirmed for the family (Wei, Mei and Lila). |

目标结论：`access_confirmed`。

```json
[
  {
    "key": "show_start",
    "expected": "21:00",
    "accepted_facts": [
      "show_start"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "show_start",
      "authorities": [
        "attest:show_start"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "21:00": [
            "The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35.",
            "The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "21:00": [
          "The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35.",
          "The current official Pancho Libre set (l02 v2) starts at 21:00 at the Maritime Museum stage and ends at 21:35"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "stage",
    "expected": "Maritime Museum",
    "accepted_facts": [
      "stage"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "stage",
      "authorities": [
        "attest:stage"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "Maritime Museum": [
            "The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage.",
            "The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "Maritime Museum": [
          "The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage.",
          "The current 21:00 Pancho Libre set plays the Maritime Museum stage, not the prior-year Pier stage"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "show_end",
    "expected": "21:35",
    "accepted_facts": [
      "show_end"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "show_end",
      "authorities": [
        "attest:show_end"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "21:35": [
            "The current official set ends at 21:35, leaving the 21:50 return bus feasible.",
            "The current official set ends at 21:35, leaving the 21:50 return bus feasible"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "21:35": [
          "The current official set ends at 21:35, leaving the 21:50 return bus feasible.",
          "The current official set ends at 21:35, leaving the 21:50 return bus feasible"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "route_step_free",
    "expected": true,
    "accepted_facts": [
      "route_step_free"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "route_step_free",
      "authorities": [
        "attest:route_step_free"
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
    "key": "home_arrival",
    "expected": "22:15",
    "accepted_facts": [
      "home_arrival"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "home_arrival",
      "authorities": [
        "attest:home_arrival"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "22:15": [
            "The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement.",
            "The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "22:15": [
          "The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement.",
          "The bus-L return arrives 22:10 with a five-minute walk home, reaching home by 22:15 - inside the requirement"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "total_cost",
    "expected": 108,
    "accepted_facts": [
      "total_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
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
    "key": "access_reserved",
    "expected": true,
    "accepted_facts": [
      "access_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "access_reserved",
      "authorities": [
        "attest:access_reserved"
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
    "key": "seats",
    "expected": 3,
    "accepted_facts": [
      "seats"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-36",
        "case": {
          "date": "2027-07-31",
          "city": "Halifax test district",
          "party_size": 3
        }
      },
      "predicate": "seats",
      "authorities": [
        "attest:seats"
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
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `L-R1-current-show` | The plan follows the current official show, not the stale listings. | The summary carries the official confirmation's key elements: the 21:00 Pancho Libre set at the Maritime Museum stage ending 21:35 with free admission - not the prior-year paid Pier listing, the 18:00 set or another artist. | final_answer |
| `L-R2-accessible-journey` | The reported journey is accessible end to end. | The trace or final answer reports step-free legs throughout, walks at most twelve minutes, standing at most twenty-five minutes, confirmed seats and a feasible 20:30-20:45 check-in, without relying on the ferry after the outage. | trace |
| `L-R6-no-attendance-claim` | The final summary claims no attendance or purchase. | The final answer states the confirmed three seated places, the current show and the step-free bus plan with home by 22:15, describes remaining travel as future, and claims neither attendance, purchase, nor payment. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `family-consulted`：tool_call → `family_dialogue`——The family's constraints are known: no stairs, walks at most twelve minutes, standing at most twenty-five minutes, confirmed seats, home by 22:15, total at most 360 CAD.
- `show-confirmed`：fact_registered → `show_start`——The official confirmation is in: the 21:00 Pancho Libre set at the Maritime Museum stage, ending 21:35, admission free; the prior-year paid listing is stale.
- `plan-approved`：tool_call → `family_dialogue`（关键词：approve、approval）——The organizer has approved the exact plan - current stage, step-free route, three seated places and budget; approval covers reserving those free places only.
- `access-reserved`：selection_processed → `reserve_access`——The three approved free seated step-free places have been reserved from the live offer; the confirmation is read back through the access desk.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-07-31 Sat 21:57 | 2027-07-31 Sat 22:35 | Harbour Festival access desk·Priya Nair | 发出受理回执 |
| 2027-07-31 Sat 22:35 | 2027-07-31 Sat 23:41 | Harbour Festival access desk·Priya Nair | check seated viewing capacity and step-free route status |
| 2027-07-31 Sat 23:41 | 2027-08-01 Sun 00:14 | Harbour Festival access desk·Priya Nair | 签发书面确认 |
| 2027-08-01 Sun 00:14 | 2027-08-01 Sun 00:29 | Harbour Festival access desk·Priya Nair | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-07-31 Sat 22:35：Harbour Festival access desk·Priya Nair，`acknowledgement`，0份回执。
- 2027-08-01 Sun 00:29：Harbour Festival access desk·Priya Nair，`reply`，1份回执。

## 易错点

- trusting the stale 2026 paid Pier listing
- reserving the 18:00 wrong-time set or another artist
- using the ferry after the lift outage or the 12-stair shortcut
- booking the 22:00 fireworks with no feasible return
- paying for admission or adding an alcohol package
- reserving before the organizer approves the exact plan

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-36.json)
- [环境私有定义](../../tasks/private/DSB-36.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-36.json)

Any legal order of dialogue, desk mail and searches is accepted if every goal's evidence conditions hold; choosing the ferry before the outage then switching to the bus after it is a legal alternative, but the scored answer keys follow the step-free bus plan.
