# DSB-22 · Film and jazz evening with a current feasible return

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：leisure_entertainment。开始：2027-10-02 Sat 04:00；截止：2027-10-04 Mon 06:30（北京时间）。

参考轨迹历时：**0.791667天（19小时）**。结果类别：`resolved`。

跨度设计：短期；mid-evening return-route cancellation plus transport-before-shows gate。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Arrange an evening for two in the Chicago test district on October 1, 2027: two places for the 18:15 film and a jazz set starting at or after 21:00, home by 23:45, total at most 90 USD. Ask me about timing, transport rules, budget and approval before reserving; verify the official film timing, keep the transport bundle current, and reserve transport before either show. No payment.

Advisory and coordination only: search listings, verify official timing, and create at most the approved transport bundle and two show reservations; no payment or other binding commitment.

已给信息：

```json
{
  "date": "2027-10-01",
  "city": "Chicago test district",
  "party_size": 2
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- mid-evening return-route cancellation invalidates route-A
- official film timing only from the provider, not the aggregator label
- transport bundle reserved before either show ticket
- search-discoverable programme and route inventories
- sparse prompt: constraints only surface through dialogue
- hidden booking desks revalidate live listings

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Riverside Evening Services desk·Sam Okafor (`evening_desk`)

角色：cinema, jazz venue and booked-shuttle operator records。Confirms official film start and end times in writing; programme listings can lag; tickets and the transport bundle go through the desks named on the entry page.

[独立角色配置](../../tasks/actors/DSB-22/evening_desk.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Riverside Evening Services desk·Sam Okafor，负责cinema, jazz venue and booked-shuttle operator records。Confirms official film start and end times in writing; programme listings can lag; tickets and the transport bundle go through the desks named on the entry page. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：film_end、film_reserved、film_start、home_arrival、jazz_reserved、jazz_start、return_depart、total_cost、transport_fare、transport_reserved

**流程：Official film timing verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`evening_desk.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check the official film record for start, duration and end<br>`evening_desk.main.2.lookup` | 90工作分钟 | 读取本地事实：film_start、film_end |
| 签发书面确认<br>`evening_desk.main.3.document` | 20工作分钟 | 签发文本证据：film_start、film_end |
| 向请求者回复已取得的结果<br>`evening_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `film_start` | `"18:15"` | The confirmed film Night Bridge starts at 18:15 Chicago time on 2027-10-01. |
| `film_end` | `"20:09"` | The official film record confirms a 114-minute runtime ending at 20:09, leaving the six-minute exit buffer before the 20:25 inter-venue transfer. |
| `jazz_start` | `"21:00"` | The jazz set starts at 21:00 (entry by 20:50) and ends at 22:20. |
| `return_depart` | `"22:40"` | The reserved return service (route-B v2) departs 22:40 after the full jazz set, replacing the cancelled 22:50 route-A. |
| `home_arrival` | `"23:23"` | The reserved return arrives 23:15 with an eight-minute walk home, reaching home by 23:23 - inside the 23:45 requirement. |
| `transport_fare` | `12` | The two-person licensed transit/shuttle bundle (outbound, inter-venue and return) costs 12 USD for the party. |
| `total_cost` | `85` | The approved full plan is 85 USD: film 28 + jazz 30 + transport 12 + 15 contingency, within the 90 USD cap. |
| `transport_reserved` | `true` | One two-person transport bundle covering outbound, inter-venue and current return legs has been confirmed; no payment was taken. |
| `film_reserved` | `true` | Two seats for the 18:15 film (full 114-minute showing) have been confirmed against the reserved transport. |
| `jazz_reserved` | `true` | Two seats for the 21:00 jazz set have been confirmed against the reserved transport. |

目标结论：`evening_confirmed`。

```json
[
  {
    "key": "film_start",
    "expected": "18:15",
    "accepted_facts": [
      "film_start"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "film_start",
      "authorities": [
        "attest:film_start"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "18:15": [
            "The confirmed film Night Bridge starts at 18:15 Chicago time on 2027-10-01.",
            "The confirmed film Night Bridge starts at 18:15 Chicago time on 2027-10-01"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "18:15": [
          "The confirmed film Night Bridge starts at 18:15 Chicago time on 2027-10-01.",
          "The confirmed film Night Bridge starts at 18:15 Chicago time on 2027-10-01"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "film_end",
    "expected": "20:09",
    "accepted_facts": [
      "film_end"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "film_end",
      "authorities": [
        "attest:film_end"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "20:09": [
            "The official film record confirms a 114-minute runtime ending at 20:09, leaving the six-minute exit buffer before the 20:25 inter-venue transfer.",
            "The official film record confirms a 114-minute runtime ending at 20:09, leaving the six-minute exit buffer before the 20:25 inter-venue transfer"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "20:09": [
          "The official film record confirms a 114-minute runtime ending at 20:09, leaving the six-minute exit buffer before the 20:25 inter-venue transfer.",
          "The official film record confirms a 114-minute runtime ending at 20:09, leaving the six-minute exit buffer before the 20:25 inter-venue transfer"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "jazz_start",
    "expected": "21:00",
    "accepted_facts": [
      "jazz_start"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "jazz_start",
      "authorities": [
        "attest:jazz_start"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "21:00": [
            "The jazz set starts at 21:00 (entry by 20:50) and ends at 22:20.",
            "The jazz set starts at 21:00 (entry by 20:50) and ends at 22:20"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "21:00": [
          "The jazz set starts at 21:00 (entry by 20:50) and ends at 22:20.",
          "The jazz set starts at 21:00 (entry by 20:50) and ends at 22:20"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "return_depart",
    "expected": "22:40",
    "accepted_facts": [
      "return_depart"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "return_depart",
      "authorities": [
        "attest:return_depart"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "22:40": [
            "The reserved return service (route-B v2) departs 22:40 after the full jazz set, replacing the cancelled 22:50 route-A.",
            "The reserved return service (route-B v2) departs 22:40 after the full jazz set, replacing the cancelled 22:50 route-A"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "22:40": [
          "The reserved return service (route-B v2) departs 22:40 after the full jazz set, replacing the cancelled 22:50 route-A.",
          "The reserved return service (route-B v2) departs 22:40 after the full jazz set, replacing the cancelled 22:50 route-A"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "home_arrival",
    "expected": "23:23",
    "accepted_facts": [
      "home_arrival"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "home_arrival",
      "authorities": [
        "attest:home_arrival"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "23:23": [
            "The reserved return arrives 23:15 with an eight-minute walk home, reaching home by 23:23 - inside the 23:45 requirement.",
            "The reserved return arrives 23:15 with an eight-minute walk home, reaching home by 23:23 - inside the 23:45 requirement"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "23:23": [
          "The reserved return arrives 23:15 with an eight-minute walk home, reaching home by 23:23 - inside the 23:45 requirement.",
          "The reserved return arrives 23:15 with an eight-minute walk home, reaching home by 23:23 - inside the 23:45 requirement"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "total_cost",
    "expected": 85,
    "accepted_facts": [
      "total_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
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
    "key": "transport_reserved",
    "expected": true,
    "accepted_facts": [
      "transport_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "transport_reserved",
      "authorities": [
        "attest:transport_reserved"
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
    "key": "film_reserved",
    "expected": true,
    "accepted_facts": [
      "film_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "film_reserved",
      "authorities": [
        "attest:film_reserved"
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
    "key": "jazz_reserved",
    "expected": true,
    "accepted_facts": [
      "jazz_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-22",
        "case": {
          "date": "2027-10-01",
          "city": "Chicago test district",
          "party_size": 2
        }
      },
      "predicate": "jazz_reserved",
      "authorities": [
        "attest:jazz_reserved"
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

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-10-02 Sat 04:32 | 2027-10-02 Sat 05:10 | Riverside Evening Services desk·Sam Okafor | 发出受理回执 |
| 2027-10-02 Sat 05:10 | 2027-10-02 Sat 06:46 | Riverside Evening Services desk·Sam Okafor | check the official film record for start, duration and end |
| 2027-10-02 Sat 06:46 | 2027-10-02 Sat 07:19 | Riverside Evening Services desk·Sam Okafor | 签发书面确认 |
| 2027-10-02 Sat 07:19 | 2027-10-02 Sat 07:34 | Riverside Evening Services desk·Sam Okafor | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-10-02 Sat 05:10：Riverside Evening Services desk·Sam Okafor，`acknowledgement`，0条文本证据。
- 2027-10-02 Sat 07:34：Riverside Evening Services desk·Sam Okafor，`reply`，4条文本证据。

## 易错点

- booking the stale aggregator 18:30 label
- choosing the 20:30 jazz set the transfer cannot reach
- booking the 22:45 set with no compliant return
- reserving shows before the transport bundle
- using scooters or self-operated transport after drinks
- counting a cancelled route-A return as available

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-22.json)
- [环境私有定义](../../tasks/private/DSB-22.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-22.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference path refreshes the routes after the 17:00 cancellation and reserves transport before both shows, but any order honoring those gates scores the same.
