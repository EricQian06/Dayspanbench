# DSB-42 · Interview rescheduling: two separate recruiters, rotated link, no cross-employer disclosure

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：work_career。开始：2027-09-13 Mon 22:00；截止：2027-09-16 Thu 06:00（北京时间）。

参考轨迹历时：**2.14583天（51.5小时）**。结果类别：`resolved`。

跨度设计：短期；recruiter offer confirmation, a mid-morning link rotation and two separate per-employer desks。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Both my final interviews conflict on Wednesday. Keep both opportunities; ask me about my availability, privacy and approval rules first. Check the interview board, confirm each recruiter's replacement separately using only a generic prior-commitment message - never mentioning the other employer or any family details - and after I approve both exact new slots and their current links, reschedule each interview through its own desk, confirming each replacement before its old invitation is superseded. No withdrawal.

Contact each recruiter desk separately with a generic prior-commitment message only: never mention the other employer or any family medical details, show the candidate both exact new slots and current links for approval before either change, confirm each replacement before its old invitation is superseded, and withdraw nothing.

已给信息：

```json
{
  "protected_date": "2027-09-15",
  "deadline_date": "2027-09-15",
  "interviews": 2
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- replacement offers appear at the recruiters' own September 14 confirmation time
- meeting link rotates mid-morning on September 15 and old-link proposals go stale
- explicit UTC offsets must be converted to Chicago time
- two separate recruiter desks, each handling only its own interview
- sparse prompt: availability, privacy and authorization only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Stripe recruiter desk·Jordan Blake (`stripe_recruiter`)

角色：Stripe final interview scheduling only。Handles only the Stripe interview and its own slot confirmation; never receives information about any other employer or the candidate's family details.

[独立角色配置](../../tasks/actors/DSB-42/stripe_recruiter.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Stripe recruiter desk·Jordan Blake，负责Stripe final interview scheduling only。Handles only the Stripe interview and its own slot confirmation; never receives information about any other employer or the candidate's family details. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：stripe_offer、stripe_rescheduled

**流程：Stripe scheduling confirmation** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`stripe_recruiter.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 向请求者回复已取得的结果<br>`stripe_recruiter.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Shopify recruiter desk·Sam Ortiz (`shopify_recruiter`)

角色：Shopify final interview scheduling only。Handles only the Shopify interview and its own slot confirmation; never receives information about any other employer or the candidate's family details.

[独立角色配置](../../tasks/actors/DSB-42/shopify_recruiter.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Shopify recruiter desk·Sam Ortiz，负责Shopify final interview scheduling only。Handles only the Shopify interview and its own slot confirmation; never receives information about any other employer or the candidate's family details. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：shopify_offer、shopify_rescheduled

**流程：Shopify scheduling confirmation** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`shopify_recruiter.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 向请求者回复已取得的结果<br>`shopify_recruiter.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `stripe_offer` | `true` | The Stripe recruiter separately confirmed replacement slot w01: Thursday September 16, 2027 10:00-12:00 Central time (08:00-10:00 UTC-07:00), two hours, meeting link link-stripe-current. |
| `shopify_offer` | `true` | The Shopify recruiter separately confirmed replacement slot w02: Friday September 17, 2027 09:00-10:30 Central time (10:00-11:30 UTC-04:00), ninety minutes, initially with meeting link link-shopify-old. |
| `stripe_rescheduled` | `true` | The Stripe replacement was confirmed with the current link link-stripe-current (slot w01: Thursday September 16, 2027 10:00-12:00 Central, two hours); the old Wednesday invitation was superseded only after the replacement was confirmed, and nothing was withdrawn. |
| `shopify_rescheduled` | `true` | The Shopify replacement was confirmed with the current link link-shopify-new (slot w02 version 2, after the September 15 09:30 rotation: Friday September 17, 2027 09:00-10:30 Central, ninety minutes); the old Wednesday invitation was superseded only after the replacement was confirmed, and nothing was withdrawn. |

目标结论：`both_rescheduled`。

```json
[
  {
    "key": "stripe_offer_confirmed",
    "expected": true,
    "accepted_facts": [
      "stripe_offer"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-42",
        "case": {
          "protected_date": "2027-09-15",
          "deadline_date": "2027-09-15",
          "interviews": 2
        }
      },
      "predicate": "stripe_offer_confirmed",
      "authorities": [
        "attest:stripe_offer_confirmed"
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
    "key": "shopify_offer_confirmed",
    "expected": true,
    "accepted_facts": [
      "shopify_offer"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-42",
        "case": {
          "protected_date": "2027-09-15",
          "deadline_date": "2027-09-15",
          "interviews": 2
        }
      },
      "predicate": "shopify_offer_confirmed",
      "authorities": [
        "attest:shopify_offer_confirmed"
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
    "key": "stripe_rescheduled",
    "expected": true,
    "accepted_facts": [
      "stripe_rescheduled"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-42",
        "case": {
          "protected_date": "2027-09-15",
          "deadline_date": "2027-09-15",
          "interviews": 2
        }
      },
      "predicate": "stripe_rescheduled",
      "authorities": [
        "attest:stripe_rescheduled"
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
    "key": "shopify_rescheduled",
    "expected": true,
    "accepted_facts": [
      "shopify_rescheduled"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-42",
        "case": {
          "protected_date": "2027-09-15",
          "deadline_date": "2027-09-15",
          "interviews": 2
        }
      },
      "predicate": "shopify_rescheduled",
      "authorities": [
        "attest:shopify_rescheduled"
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
| 2027-09-15 Wed 01:02 | 2027-09-15 Wed 01:50 | Stripe recruiter desk·Jordan Blake | 发出受理回执 |
| 2027-09-15 Wed 01:50 | 2027-09-15 Wed 02:05 | Stripe recruiter desk·Jordan Blake | 向请求者回复已取得的结果 |
| 2027-09-15 Wed 02:26 | 2027-09-15 Wed 03:09 | Shopify recruiter desk·Sam Ortiz | 发出受理回执 |
| 2027-09-15 Wed 03:09 | 2027-09-15 Wed 03:24 | Shopify recruiter desk·Sam Ortiz | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-09-15 Wed 01:50：Stripe recruiter desk·Jordan Blake，`acknowledgement`，0条文本证据。
- 2027-09-15 Wed 02:05：Stripe recruiter desk·Jordan Blake，`reply`，0条文本证据。
- 2027-09-15 Wed 03:09：Shopify recruiter desk·Sam Ortiz，`acknowledgement`，0条文本证据。
- 2027-09-15 Wed 03:24：Shopify recruiter desk·Sam Ortiz，`reply`，0条文本证据。

## 易错点

- mentioning one employer to the other or any family medical details
- rescheduling Shopify with the stale link-shopify-old after the rotation
- booking w03 (the original conflict), w04 (too short), w05 (cancelled hold) or w06 (outside availability)
- misreading the UTC offsets and treating 08:00-10:00 UTC-07:00 as a morning conflict
- withdrawing or declining either opportunity instead of rescheduling
- removing an old invitation before its replacement is confirmed

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-42.json)
- [环境私有定义](../../tasks/private/DSB-42.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-42.json)

Any legal order of dialogue, board reads and recruiter mail is accepted if every goal's evidence conditions hold; either employer may be rescheduled first, and the rotated Shopify link must be refreshed before its desk accepts a slot.
