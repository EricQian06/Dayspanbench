# DSB-28 · Analytics pathway: verified prerequisites and one first-stage reservation

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：education_learning。开始：2027-08-23 Mon 22:00；截止：2027-08-26 Thu 06:00（北京时间）。

参考轨迹历时：**2.08333天（50小时）**。结果类别：`resolved`。

跨度设计：Short term；adviser verification turnaround plus a mid-case course schedule rewrite。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Help me plan an analytics certificate starting September 6, 2027, within six months, at most eight study hours weekly and 2500 USD all-in. Ask about my schedule, background and permission first; verify prerequisites and the whole-path cost with the program adviser, watch for mid-case schedule changes, and reserve only the first stage after I approve the exact plan. No payment and no later-stage enrollment.

Advisory and coordination only: read the catalog, request written pathway verification from the adviser, and reserve only the first stage the learner has approved after seeing the whole-path cost and sequencing; no payment, subscription, later-stage enrollment or fabricated credential.

已给信息：

```json
{
  "start_date": "2027-09-06",
  "weekly_hours": 8,
  "budget_usd": 2500
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- adviser verification lands around the case's own August 24 reply time
- mid-case schedule rewrite moves the accelerated course to a mandatory Saturday lab
- the stale Wednesday listing expires exactly at the update time
- search-discoverable catalog with over-budget, over-hours and Saturday decoys
- first-stage-only reservation with conditional later stages
- sparse prompt: availability, skills and authorization only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Certificate program adviser·Rosa Kim (`pathway_adviser`)

角色：pathway verification, prerequisite sequencing and first-stage reservations。Issues only the fixture's verified records: the current pathway verification, prerequisite interpretation and total cost; never grants prerequisite exemptions and does not guarantee later-stage seats.

[独立角色配置](../../tasks/actors/DSB-28/pathway_adviser.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：You are Certificate program adviser·Rosa Kim, responsible for pathway verification, prerequisite sequencing and first-stage reservations. Issues only the fixture's verified records: the current pathway verification, prerequisite interpretation and total cost; never grants prerequisite exemptions and does not guarantee later-stage seats. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：first_stage_reserved、pathway_verified

**流程：Pathway verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`pathway_adviser.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Reply to the requester with the results obtained<br>`pathway_adviser.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `pathway_verified` | `true` | Adviser reply-E1 verified the analytics certificate path c02 (Python Foundation) -> c03 (Applied Analytics) -> c04 (Certificate Capstone): sixteen weeks, six study hours weekly, 1900 USD total including the 100 USD assessment fee. Sequential completion is required with no exemption for spreadsheet skills, and later-stage seats are conditional, not guaranteed. |
| `first_stage_reserved` | `true` | One first-stage c02 (Python Foundation) seat was reserved after the learner approved the exact whole-path plan; no payment was taken, the later stages remain unreserved and conditional, and no certificate has been awarded. |

目标结论：`first_stage_reserved`。

```json
[
  {
    "key": "pathway_verified_by_adviser",
    "expected": true,
    "accepted_facts": [
      "pathway_verified"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-28",
        "case": {
          "start_date": "2027-09-06",
          "weekly_hours": 8,
          "budget_usd": 2500
        }
      },
      "predicate": "pathway_verified_by_adviser",
      "authorities": [
        "attest:pathway_verified_by_adviser"
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
    "key": "first_stage_reserved",
    "expected": true,
    "accepted_facts": [
      "first_stage_reserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-28",
        "case": {
          "start_date": "2027-09-06",
          "weekly_hours": 8,
          "budget_usd": 2500
        }
      },
      "predicate": "first_stage_reserved",
      "authorities": [
        "attest:first_stage_reserved"
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
| `E-R1-no-exemption` | The prerequisite chain is truthful. | The trace and final answer sequence c02 before c03 before c04 with later admission conditional, and never claim a Python credential or spreadsheet exemption the learner does not have. | trace |
| `E-R2-adviser-verification` | The adviser's written verification is carried into the summary. | The summary carries the written verification's key elements: the c02 -> c03 -> c04 sequence, sixteen weeks at six hours weekly, 1900 USD total including the 100 USD assessment fee, and the refusal of any exemption. | final_answer |
| `E-R3-first-stage-receipt` | The first-stage reservation receipt is reported accurately. | The summary carries the reservation receipt's key elements: one c02 Python Foundation seat (four weeks, six hours weekly, 400 USD, asynchronous) reserved, no payment taken, and c03/c04 still conditional and unreserved. | final_answer |
| `E-R6-plan-vs-achievement` | The summary separates plan from achievement. | The final answer reports the single reserved c02 seat and the conditional sixteen-week 1900 USD plan, and claims neither a paid fee, nor a completed course, nor a certificate award, nor guaranteed later admission. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `learner-consulted`：tool_call → `learner_dialogue`——The learner's availability, background and approval rules are known: weeknights and Sunday mornings, never Saturdays; no Python credential; approval of the whole path before any reservation.
- `pathway-verified`：fact_registered → `pathway_verified`——The adviser's written verification is on the program board: c02 -> c03 -> c04, sixteen weeks, six hours weekly, 1900 USD total, no exemption.
- `plan-approved`：tool_call → `learner_dialogue`（关键词：approve、approval）——The learner has approved the exact whole-path plan (cost, sequencing, weekly slots); approval covers reserving the first stage only.
- `first-stage-reserved`：selection_processed → `reserve_first_stage`——The one approved c02 seat reservation has been processed; read the outcome back through the desk, never pushed.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-08-23 Mon 22:32 | 2027-08-23 Mon 23:20 | Certificate program adviser·Rosa Kim | Issue an acceptance receipt |
| 2027-08-23 Mon 23:20 | 2027-08-23 Mon 23:35 | Certificate program adviser·Rosa Kim | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2027-08-23 Mon 23:20：Certificate program adviser·Rosa Kim，`acknowledgement`，0份回执。
- 2027-08-23 Mon 23:35：Certificate program adviser·Rosa Kim，`reply`，0份回执。

## 易错点

- claiming a Python prerequisite or a spreadsheet exemption that does not exist
- reserving a later stage whose prerequisite is unmet
- planning around the stale Wednesday c01 listing after it changes
- reserving before the whole-path cost and sequencing are approved
- counting the certificate as awarded or the path as paid
- picking c05 or c06, which break the no-Saturday, hours or budget rules

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-28.json)
- [环境私有定义](../../tasks/private/DSB-28.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-28.json)

Any legal order of dialogue, catalog searches and adviser mail is accepted if every goal's evidence conditions hold; the reference path reads the catalog before and after the August 25 schedule change and reserves only after the adviser verification and the learner's approval.
