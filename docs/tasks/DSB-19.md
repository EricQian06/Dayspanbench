# DSB-19 · Clinic-gated accessible rehabilitation transport

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：healthcare_wellness。开始：2027-09-02 Thu 21:00；截止：2027-09-05 Sun 01:00（北京时间）。

参考轨迹历时：**1.19444天（28.67小时）**。结果类别：`resolved`。

跨度设计：Short term；fleet verification rewrite plus clinic release gating the return leg。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Arrange accessible transport for my September 3, 2027, 10:00 rehabilitation appointment in the Chicago test district; arrive 30 minutes early and confirm the return after the visit. Ask me about access needs, limits and authorization; verify lift, securement and companion capacity with dispatch, book the outbound first, and book the return only after the clinic records my actual release - never the estimated end time. Share pickup and access needs only, not my diagnosis. No payment.

Advisory and coordination only: search inventories, verify fleet capacity, and book at most the two approved legs; share pickup and access needs only - no diagnosis, medical records, medication advice or payment.

已给信息：

```json
{
  "date": "2027-09-03",
  "city": "Chicago test district",
  "appointment": "10:00"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- fleet verification event removes out-A and verifies out-B mid-morning
- return vehicle unlisted and unbookable until the actual clinic release
- estimated 11:00 end is a trap next to the 11:20 release
- search-discoverable clinic and vehicle inventories
- sparse prompt: access and limits only surface through dialogue
- hidden booking desks revalidate live inventory per leg

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Access Ride dispatch·Dana Whitfield (`dispatch_desk`)

角色：lift-equipped vehicle fleet, securement verification and ride bookings。Confirms live lift, securement and companion capacity in writing; vehicle inventory changes without notice; bookings go through the desks named on the entry page. Only pickup and access needs are shared - never a diagnosis.

[独立角色配置](../../tasks/actors/DSB-19/dispatch_desk.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：You are Access Ride dispatch·Dana Whitfield, responsible for lift-equipped vehicle fleet, securement verification and ride bookings. Confirms live lift, securement and companion capacity in writing; vehicle inventory changes without notice; bookings go through the desks named on the entry page. Only pickup and access needs are shared - never a diagnosis. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：lift_verified、outbound_arrival、outbound_booked、return_booked、return_pickup、total_fare

**流程：Fleet access verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`dispatch_desk.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check live lift, securement and companion-seat verification<br>`dispatch_desk.main.2.lookup` | 60工作分钟 | 读取本地事实：lift_verified |
| Issue written confirmation<br>`dispatch_desk.main.3.document` | 20工作分钟 | 签发文本证据：lift_verified |
| Reply to the requester with the results obtained<br>`dispatch_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Cedar Rehabilitation Clinic coordinator·Marcus Lee (`clinic_coordinator`)

角色：appointment logistics and release records。Confirms appointment times and logistics only; the visit ends only when the clinic records an actual release, and clinical questions stay with clinicians.

[独立角色配置](../../tasks/actors/DSB-19/clinic_coordinator.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：You are Cedar Rehabilitation Clinic coordinator·Marcus Lee, responsible for appointment logistics and release records. Confirms appointment times and logistics only; the visit ends only when the clinic records an actual release, and clinical questions stay with clinicians. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：appointment_time、clinic_release

**流程：Appointment logistics** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`clinic_coordinator.main.1.acknowledge` | 20工作分钟 | 发出受理回执： |
| check the appointment record<br>`clinic_coordinator.main.2.lookup` | 40工作分钟 | 读取本地事实：appointment_time |
| Issue written confirmation<br>`clinic_coordinator.main.3.document` | 20工作分钟 | 签发文本证据：appointment_time |
| Reply to the requester with the results obtained<br>`clinic_coordinator.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `outbound_arrival` | `"09:25"` | The booked outbound vehicle (out-B) picks up 09:00 and arrives at the clinic 09:25, inside the 09:30 arrival deadline for the 10:00 appointment. |
| `lift_verified` | `true` | Provider dispatch evidence confirms the booked vehicles have a working tested lift, wheelchair securement and one companion seat on each leg. |
| `clinic_release` | `"11:20"` | The clinic's actual release (release-XHM) records the patient ready at 11:20 on September 3; the 11:00 estimate was never release evidence. |
| `return_pickup` | `"11:40"` | The booked return vehicle (return-B) picks up 11:40, after the 11:20 clinic release, arriving home 12:10. |
| `total_fare` | `85` | The combined fare for both booked legs is 85 USD (outbound 40 + return 45), within the 100 USD roundtrip cap. |
| `outbound_booked` | `true` | One approved accessible outbound leg has been booked with written pickup and access instructions; no payment was taken. |
| `return_booked` | `true` | One approved accessible return leg has been booked after the actual clinic release, with written pickup instructions; no payment was taken. |
| `appointment_time` | `"2027-09-03T10:00:00-05:00"` | The rehabilitation appointment starts September 3, 2027 at 10:00 with arrival required by 09:30. |

目标结论：`both_legs_booked`。

```json
[
  {
    "key": "outbound_booked",
    "expected": true,
    "accepted_facts": [
      "outbound_booked"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "outbound_booked",
      "authorities": [
        "attest:outbound_booked"
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
    "key": "outbound_arrival",
    "expected": "09:25",
    "accepted_facts": [
      "outbound_arrival"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "outbound_arrival",
      "authorities": [
        "attest:outbound_arrival"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "09:25": [
            "The booked outbound vehicle (out-B) picks up 09:00 and arrives at the clinic 09:25, inside the 09:30 arrival deadline for the 10:00 appointment.",
            "The booked outbound vehicle (out-B) picks up 09:00 and arrives at the clinic 09:25, inside the 09:30 arrival deadline for the 10:00 appointment"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "09:25": [
          "The booked outbound vehicle (out-B) picks up 09:00 and arrives at the clinic 09:25, inside the 09:30 arrival deadline for the 10:00 appointment.",
          "The booked outbound vehicle (out-B) picks up 09:00 and arrives at the clinic 09:25, inside the 09:30 arrival deadline for the 10:00 appointment"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "lift_verified",
    "expected": true,
    "accepted_facts": [
      "lift_verified"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "lift_verified",
      "authorities": [
        "attest:lift_verified"
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
    "key": "clinic_release",
    "expected": "11:20",
    "accepted_facts": [
      "clinic_release"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "clinic_release",
      "authorities": [
        "attest:clinic_release"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "11:20": [
            "The clinic's actual release (release-XHM) records the patient ready at 11:20 on September 3; the 11:00 estimate was never release evidence.",
            "The clinic's actual release (release-XHM) records the patient ready at 11:20 on September 3; the 11:00 estimate was never release evidence"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "11:20": [
          "The clinic's actual release (release-XHM) records the patient ready at 11:20 on September 3; the 11:00 estimate was never release evidence.",
          "The clinic's actual release (release-XHM) records the patient ready at 11:20 on September 3; the 11:00 estimate was never release evidence"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "return_pickup",
    "expected": "11:40",
    "accepted_facts": [
      "return_pickup"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "return_pickup",
      "authorities": [
        "attest:return_pickup"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "11:40": [
            "The booked return vehicle (return-B) picks up 11:40, after the 11:20 clinic release, arriving home 12:10.",
            "The booked return vehicle (return-B) picks up 11:40, after the 11:20 clinic release, arriving home 12:10"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "11:40": [
          "The booked return vehicle (return-B) picks up 11:40, after the 11:20 clinic release, arriving home 12:10.",
          "The booked return vehicle (return-B) picks up 11:40, after the 11:20 clinic release, arriving home 12:10"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "return_booked",
    "expected": true,
    "accepted_facts": [
      "return_booked"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "return_booked",
      "authorities": [
        "attest:return_booked"
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
    "key": "total_fare",
    "expected": 85,
    "accepted_facts": [
      "total_fare"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-19",
        "case": {
          "date": "2027-09-03",
          "city": "Chicago test district",
          "appointment": "10:00"
        }
      },
      "predicate": "total_fare",
      "authorities": [
        "attest:total_fare"
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
| `XHM-R1-outbound-receipt` | The final summary carries the outbound booking's key elements. | The summary states the outbound leg on out-B with lift tested, wheelchair securement and one companion seat verified, pickup 09:00 arriving 09:25 - inside the 09:30 arrival deadline - at 40 USD with no payment taken. | final_answer |
| `XHM-R2-release-gate` | The return leg was booked only after the clinic's actual release. | The trace shows the return was booked only after the clinic recorded the actual 11:20 release (release-XHM), never on the estimated 11:00 end time, and only with the patient's approval of the exact vehicle and window. | trace |
| `XHM-R3-return-and-fare` | The return booking and combined fare are reported exactly. | The summary states the return on return-B picking up 11:40 after the 11:20 release and arriving home 12:10, with the combined fare 85 USD (40 outbound plus 45 return) inside the 100 USD roundtrip cap. | final_answer |
| `XHM-R4-live-inventory` | Bookings used current verified vehicles, not stale rows. | The trace shows the agent re-checked the ride inventory after the fleet update and booked the verified out-B row, never the out-of-service out-A, the lift-less standard sedan or the pre-release return-early row. | trace |
| `XHM-R6-privacy-claims` | Privacy is respected and claims stay bounded. | The trace shows only pickup and access needs shared with the dispatcher (no diagnosis), and the final answer reports the booked legs without claiming the return journey is completed, medical advice, or payment. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `access-needs-known`：tool_call → `patient_dialogue`——The patient has been asked about access needs, limits and approval arrangements; nothing was booked yet.
- `fleet-verified`：fact_registered → `lift_verified`——The dispatch desk's written lift, securement and companion-seat verification has landed; the access claim now rests on provider evidence.
- `outbound-approved`：tool_call → `patient_dialogue`（关键词：approve、approval）——The patient has been shown the exact outbound vehicle and window for approval; approval applies only to that leg.
- `outbound-booked`：selection_processed → `book_outbound`——The approved outbound leg has been processed; the confirmation receipt is with the agent.
- `release-recorded`：fact_registered → `clinic_release`——The clinic has recorded the actual release; only now may the return leg be finalized - the estimated end time was never release evidence.
- `return-booked`：selection_processed → `book_return`——The approved post-release return leg has been processed; both legs are booked and no payment was taken.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-09-02 Thu 21:32 | 2027-09-02 Thu 22:10 | Access Ride dispatch·Dana Whitfield | Issue an acceptance receipt |
| 2027-09-02 Thu 22:10 | 2027-09-02 Thu 23:16 | Access Ride dispatch·Dana Whitfield | check live lift, securement and companion-seat verification |
| 2027-09-02 Thu 23:16 | 2027-09-02 Thu 23:49 | Access Ride dispatch·Dana Whitfield | Issue written confirmation |
| 2027-09-02 Thu 23:49 | 2027-09-03 Fri 00:04 | Access Ride dispatch·Dana Whitfield | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2027-09-02 Thu 22:10：Access Ride dispatch·Dana Whitfield，`acknowledgement`，0份回执。
- 2027-09-03 Fri 00:04：Access Ride dispatch·Dana Whitfield，`reply`，1份回执。

## 易错点

- booking the standard sedan without a lift
- booking the return at the estimated 11:00 end or before the release
- relying on out-A after it goes out of service
- reserving a leg before the patient approves the exact vehicle and window
- sharing the diagnosis with the dispatcher
- exceeding the 100 USD roundtrip cap

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-19.json)
- [环境私有定义](../../tasks/private/DSB-19.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-19.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference books the outbound on September 2 and the return after the 11:20 release, but any order honoring the release gate scores the same.
