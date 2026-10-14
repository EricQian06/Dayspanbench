# DSB-23 · Lyon pet stay: delayed late arrival, written pet acceptance and supervision

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：pets_animals。开始：2027-04-17 Sat 00:00；截止：2027-04-19 Mon 00:00（北京时间）。

参考轨迹历时：**0.875天（21小时）**。结果类别：`resolved`。

跨度设计：短期；evening train delay, overnight written extension and supervision rebound before booking。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Book two nights in Lyon for April 16-18 for me and my dog Nino, within 420 EUR including pet fees and parking; my train arrives 23:10 on Friday and I return Sunday at 10:38. Ask me for the missing constraints and authorization first; the hotel must accept this exact dog in writing, someone must stay with him the whole time, and watch the arrival time - if the train slips, re-check before booking. No payment, no pet-policy workaround.

Advisory and coordination only: search listings, contact the hotel, companion and rail desk, gather written acceptance and acknowledgements, and place at most the one booking the traveler has approved; no payment, no unattended dog, no pet-policy workaround.

已给信息：

```json
{
  "city": "Lyon",
  "checkin": "2027-04-16",
  "checkout": "2027-04-18",
  "budget_eur": 420
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- evening train delay rewrites the arrival record and breaks the 23:50 check-in fit
- written hotel extension lands the next morning and gates the booking
- companion acknowledgement exists only for the current delayed itinerary
- search-discoverable listings with five ineligible hotels
- hidden booking service revalidates the live listing at booking time
- sparse prompt: pet, logistics and authorization facts only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Villa des Roses hotel desk·Marc Aubert (`hotel_desk`)

角色：written pet acceptance, parking terms and late check-in extensions。Issues written pet acceptances naming the exact dog, weight and vet letter, parking terms and late-check-in extensions for the current itinerary; generic pets-welcome marketing never substitutes for the written permission.

[独立角色配置](../../tasks/actors/DSB-23/hotel_desk.json) · 日历 `paris_daily` · 时区 `Europe/Paris` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Villa des Roses hotel desk·Marc Aubert，负责written pet acceptance, parking terms and late check-in extensions。Issues written pet acceptances naming the exact dog, weight and vet letter, parking terms and late-check-in extensions for the current itinerary; generic pets-welcome marketing never substitutes for the written permission. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：late_extension、pet_accepted、stay_confirmed、total_cost

**流程：Pet and parking verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`hotel_desk.main.1.acknowledge` | 10工作分钟 | 发出受理回执： |
| check the written pet acceptance and parking terms<br>`hotel_desk.main.2.lookup` | 40工作分钟 | 读取本地事实：pet_accepted |
| 签发书面确认<br>`hotel_desk.main.3.document` | 10工作分钟 | 签发文本证据：pet_accepted |
| 向请求者回复已取得的结果<br>`hotel_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Late check-in extension** (`extension`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`hotel_desk.extension.1.acknowledge` | 10工作分钟 | 发出受理回执： |
| issue the written late check-in extension for the delayed itinerary<br>`hotel_desk.extension.2.lookup` | 40工作分钟 | 读取本地事实：late_extension |
| 签发书面确认<br>`hotel_desk.extension.3.document` | 10工作分钟 | 签发文本证据：late_extension |
| 向请求者回复已取得的结果<br>`hotel_desk.extension.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Travel companion·Lea Bernard (`companion_lea`)

角色：animal supervision during the trip。May stay with Nino and acknowledges supervision only for the itinerary shown to her; an acknowledgement for an older arrival time does not carry over after a delay.

[独立角色配置](../../tasks/actors/DSB-23/companion_lea.json) · 日历 `paris_daily` · 时区 `Europe/Paris` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Travel companion·Lea Bernard，负责animal supervision during the trip。May stay with Nino and acknowledges supervision only for the itinerary shown to her; an acknowledgement for an older arrival time does not carry over after a delay. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：companion_ack

**流程：Supervision acknowledgement** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`companion_lea.main.1.acknowledge` | 10工作分钟 | 发出受理回执： |
| confirm her supervision acknowledgement for the current itinerary<br>`companion_lea.main.2.lookup` | 30工作分钟 | 读取本地事实：companion_ack |
| 签发书面确认<br>`companion_lea.main.3.document` | 10工作分钟 | 签发文本证据：companion_ack |
| 向请求者回复已取得的结果<br>`companion_lea.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Rail service desk·Julien Fabre (`rail_desk`)

角色：current train arrival and delay status。Reports only the current published arrival; a delayed arrival invalidates plans whose transfer ends after the hotel's written check-in limit.

[独立角色配置](../../tasks/actors/DSB-23/rail_desk.json) · 日历 `paris_daily` · 时区 `Europe/Paris` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Rail service desk·Julien Fabre，负责current train arrival and delay status。Reports only the current published arrival; a delayed arrival invalidates plans whose transfer ends after the hotel's written check-in limit. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：train_arrival

**流程：Train arrival status** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`rail_desk.main.1.acknowledge` | 10工作分钟 | 发出受理回执： |
| check the current arrival time of train train-XPT<br>`rail_desk.main.2.lookup` | 30工作分钟 | 读取本地事实：train_arrival |
| 签发书面确认<br>`rail_desk.main.3.document` | 10工作分钟 | 签发文本证据：train_arrival |
| 向请求者回复已取得的结果<br>`rail_desk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `pet_accepted` | `true` | Written hotel permission pet-accept-XPT: the Villa des Roses accepts Nino (pet-XPT, 28 kg, current vet letter) for 2027-04-16 and 2027-04-17; the dog may not be left unattended, and open-air parking fits the 2.05 m car. |
| `train_arrival` | `"23:40"` | Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17. |
| `late_extension` | `"00:30"` | Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits. |
| `companion_ack` | `true` | Lea Bernard explicitly acknowledged staying with Nino during parking, check-in and the whole stay on the current delayed itinerary (arrival 23:40), with no unattended periods. |
| `stay_confirmed` | `true` | Reservation stay-XPT1 confirms two nights at the Villa des Roses, 2027-04-16 to 2027-04-18, for Camille Moreau and Nino: written 28 kg pet acceptance, the extended 00:30 late check-in, open-air parking for the 2.05 m car and Lea's supervision linked; total 378 EUR; no payment taken. |
| `total_cost` | `378` | The stay total is 378 EUR - 310 EUR room for two nights, 20 EUR pet fee and 48 EUR open-air parking for two nights - within the 420 EUR budget. |

目标结论：`stay_booked`。

```json
[
  {
    "key": "pet_acceptance_written",
    "expected": true,
    "accepted_facts": [
      "pet_accepted"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
        }
      },
      "predicate": "pet_acceptance_written",
      "authorities": [
        "attest:pet_acceptance_written"
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
    "key": "train_arrival_current",
    "expected": "23:40",
    "accepted_facts": [
      "train_arrival"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
        }
      },
      "predicate": "train_arrival_current",
      "authorities": [
        "attest:train_arrival_current"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "23:40": [
            "Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17.",
            "Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "23:40": [
          "Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17.",
          "Train train-XPT is delayed: the current arrival (version 2) is 23:40 on 2027-04-16; with the 25-minute station-to-hotel transfer, check-in would land at 00:05 on 2027-04-17"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "late_checkin_deadline",
    "expected": "00:30",
    "accepted_facts": [
      "late_extension"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
        }
      },
      "predicate": "late_checkin_deadline",
      "authorities": [
        "attest:late_checkin_deadline"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "00:30": [
            "Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits.",
            "Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "00:30": [
          "Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits.",
          "Written hotel confirmation late-XPT2 extends late check-in at the Villa des Roses until 00:30 on 2027-04-17 for the delayed itinerary, so the 00:05 arrival fits"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "companion_supervision_acknowledged",
    "expected": true,
    "accepted_facts": [
      "companion_ack"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
        }
      },
      "predicate": "companion_supervision_acknowledged",
      "authorities": [
        "attest:companion_supervision_acknowledged"
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
    "key": "stay_confirmed",
    "expected": true,
    "accepted_facts": [
      "stay_confirmed"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
        }
      },
      "predicate": "stay_confirmed",
      "authorities": [
        "attest:stay_confirmed"
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
    "key": "total_cost",
    "expected": 378,
    "accepted_facts": [
      "total_cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-23",
        "case": {
          "city": "Lyon",
          "checkin": "2027-04-16",
          "checkout": "2027-04-18",
          "budget_eur": 420
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
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `XPT-R1-pet-acceptance-written` | The hotel's written pet acceptance named the exact dog and conditions. | The summary reports the written permission pet-accept-XPT accepting Nino (28 kg, current vet letter) for April 16-17 with no unattended periods and open-air parking fitting the 2.05 m car - not a generic pets-welcome claim. | final_answer |
| `XPT-R2-stay-receipt` | The final summary carries the reservation receipt's key elements. | The summary states reservation stay-XPT1: two nights at the Villa des Roses, 2027-04-16 to 2027-04-18, for Camille Moreau and Nino, total 378 EUR within the 420 EUR budget, with the extended 00:30 late check-in and Lea's supervision linked, and no payment taken. | final_answer |
| `XPT-R3-arrival-matched-to-current-train` | The booking plan matched the current delayed arrival, not the withdrawn schedule. | The trace shows the plan validated against the 23:40 arrival plus the 25-minute transfer with the written 00:30 extension, with no commitment relying on the 23:50 limit or on a supervision acknowledgement made before the delay. | trace |
| `XPT-R4-supervision-rebound` | Supervision was acknowledged for the delayed itinerary. | The trace shows Lea Bernard explicitly acknowledged staying with Nino during parking, check-in and the whole stay on the current 23:40 arrival itinerary, with no unattended periods. | trace |
| `XPT-R6-no-future-stay-invented` | The final summary reports the reservation without inventing performance. | The final answer states the confirmed reservation with its written conditions, the revised check-in and the linked supervision, and claims neither arrival, stay performance nor payment. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `traveler-constraints-known`：tool_call → `camille_dialogue`——The traveler has been asked about her dog, logistics, supervision and approval conditions; nothing has been booked yet.
- `pet-acceptance-written`：fact_registered → `pet_accepted`——The hotel's written acceptance naming the exact dog is in hand; marketing claims never substitute for it.
- `supervision-acknowledged`：fact_registered → `companion_ack`——The companion has acknowledged supervision for the itinerary as it currently stands; an acknowledgement for an older arrival does not carry over.
- `extension-written`：fact_registered → `late_extension`——The hotel's written late-check-in extension for the delayed itinerary has landed; the arrival now fits the check-in limit.
- `plan-approved`：tool_call → `camille_dialogue`（关键词：approve、approval）——The traveler has been shown the exact hotel, pet policy, current arrival deadline, supervision and total for approval; approval applies only to that plan.
- `stay-booked`：selection_processed → `stay_book`——The one approved stay has been processed; the confirmation receipt is with the agent and arrival remains in the future.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-04-17 Sat 00:32 | 2027-04-17 Sat 01:05 | Villa des Roses hotel desk·Marc Aubert | 发出受理回执 |
| 2027-04-17 Sat 01:05 | 2027-04-17 Sat 01:51 | Villa des Roses hotel desk·Marc Aubert | check the written pet acceptance and parking terms |
| 2027-04-17 Sat 01:51 | 2027-04-17 Sat 14:19 | Villa des Roses hotel desk·Marc Aubert | 签发书面确认 |
| 2027-04-17 Sat 14:19 | 2027-04-17 Sat 14:34 | Villa des Roses hotel desk·Marc Aubert | 向请求者回复已取得的结果 |
| 2027-04-17 Sat 15:10 | 2027-04-17 Sat 15:45 | Travel companion·Lea Bernard | 发出受理回执 |
| 2027-04-17 Sat 15:45 | 2027-04-17 Sat 16:32 | Travel companion·Lea Bernard | confirm her supervision acknowledgement for the current itinerary |
| 2027-04-17 Sat 16:32 | 2027-04-17 Sat 17:01 | Travel companion·Lea Bernard | 签发书面确认 |
| 2027-04-17 Sat 17:01 | 2027-04-17 Sat 17:16 | Travel companion·Lea Bernard | 向请求者回复已取得的结果 |
| 2027-04-17 Sat 17:51 | 2027-04-17 Sat 18:22 | Villa des Roses hotel desk·Marc Aubert | 发出受理回执 |
| 2027-04-17 Sat 18:22 | 2027-04-17 Sat 19:25 | Villa des Roses hotel desk·Marc Aubert | issue the written late check-in extension for the delayed itinerary |
| 2027-04-17 Sat 19:25 | 2027-04-17 Sat 19:51 | Villa des Roses hotel desk·Marc Aubert | 签发书面确认 |
| 2027-04-17 Sat 19:51 | 2027-04-17 Sat 20:06 | Villa des Roses hotel desk·Marc Aubert | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-04-17 Sat 01:05：Villa des Roses hotel desk·Marc Aubert，`acknowledgement`，0份回执。
- 2027-04-17 Sat 14:34：Villa des Roses hotel desk·Marc Aubert，`reply`，1份回执。
- 2027-04-17 Sat 15:45：Travel companion·Lea Bernard，`acknowledgement`，0份回执。
- 2027-04-17 Sat 17:16：Travel companion·Lea Bernard，`reply`，1份回执。
- 2027-04-17 Sat 18:22：Villa des Roses hotel desk·Marc Aubert，`acknowledgement`，0份回执。
- 2027-04-17 Sat 20:06：Villa des Roses hotel desk·Marc Aubert，`reply`，1份回执。

## 易错点

- booking against the withdrawn 23:50 limit after the delay
- choosing an ineligible hotel (15 kg limit, 22:00 desk, 1.9 m garage, 15:00 check-in, 500 EUR)
- reusing a supervision acknowledgement made for the old 23:10 itinerary
- accepting pets-welcome marketing instead of the written exact-dog acceptance
- leaving Nino unattended during parking or check-in
- booking before the traveler approves the exact plan after the delay

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-23.json)
- [环境私有定义](../../tasks/private/DSB-23.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-23.json)

Any legal order of dialogue, verification mail and searches is accepted if every goal's evidence conditions hold; the reference path re-verifies after the 20:30 delay, obtains the written extension and Lea's rebound acknowledgement, then books. Booking on the pre-delay 23:50 terms is not a legal path.
