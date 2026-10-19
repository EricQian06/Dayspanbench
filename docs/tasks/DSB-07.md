# DSB-07 · Archive use: restart digitization after rights succession verification

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：Cultural archives。开始：2026-11-05 Thu 15:00；截止：2027-06-11 Fri 17:00（北京时间）。

参考轨迹历时：**214.812天（5155.5小时）**。结果类别：`resolved`。

跨度设计：Long term；Request digitization again after rights succession verification。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

For a noncommercial exhibition in July 2027, verify permission to use image ARC-71 physically and on the exhibition website, and determine total fees and scan resolution. Rights succession is under review. After obtaining the rights holder's confirmation, contact the archive again to verify digitized delivery. Do not pay or publish.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "archive_id": "ARC-71",
  "usage": "Noncommercial physical exhibition and exhibition website"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Rights succession verification across calendar years
- New York standard time and daylight saving time
- A new request is required after permission
- 72-hour image restoration and manual acceptance
- Official progress page updated during the process
- Hidden fee assessment form and staged completion
- Speculative reception directions and explicit refusal
- Hidden fee assessment acceptance timeline
- Reception's historical delivery record outside its authority and mistaken scan specification recollection

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Beiting Archive reception - Guan Yu (`archive`)

角色：Archive use inquiry。Provide the rights contact first. After rights succession is confirmed, the applicant must contact the archive again with that confirmation before referral to digitization; fee assessment requires the registration channel.

[独立角色配置](../../tasks/actors/DSB-07/archive.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Beiting Archive reception - Guan Yu, responsible for Archive use inquiry. Provide the rights contact first. After rights succession is confirmed, the applicant must contact the archive again with that confirmation before referral to digitization; fee assessment requires the registration channel. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：fee

**流程：Fees and rights contacts** (`main`)

必须提供：archive_id、usage

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Register inquiry context<br>`archive.main.1.lookup` | 120工作分钟 | 读取本地事实： |
| Look up the contact directory and provide a referral<br>`archive.main.2.refer` | 30工作分钟 | 公开转介联系人：rights |
| Reply to the requester with the results obtained<br>`archive.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Confirm digitization specifications after permission** (`digitize`)

必须提供：archive_id、exhibition_permission

证据门槛：{"exhibition_permission": {"subject": {"task": "DSB-07", "case": {"archive_id": "ARC-71", "usage": "Noncommercial physical exhibition and exhibition website"}}, "predicate": "physical_exhibit_allowed", "authorities": ["attest:physical_exhibit_allowed"], "normalization": {"type": "boolean"}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`archive.digitize.1.acknowledge` | 60工作分钟 | 发出受理回执： |
| Consult internally before replying<br>`archive.digitize.2.consult` | 120工作分钟 | 先告知转办再内部咨询：digitizer/main、仅传递字段：archive_id |
| Reply to the requester with the results obtained<br>`archive.digitize.3.reply` | 120工作分钟 | 向父事项/Agent回复： |

**流程：Fee assessment channel information** (`fee_channel`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Offer a speculative answer<br>`archive.fee_channel.1.suggest` | 30工作分钟 | 给出猜测性答复： |
| State explicitly that this is unknown or outside this role's remit<br>`archive.fee_channel.2.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

**流程：Verbal impression of scan specifications** (`scan_gossip`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`archive.scan_gossip.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### Rights liaison - Alex Chen (`rights`)

角色：Image rights succession and intended-use confirmation。Rights succession documents are checked together on May 28, 2027. The specified use is then reviewed during New York local working hours, with confirmation issued automatically on completion; approval is unavailable beforehand.

[独立角色配置](../../tasks/actors/DSB-07/rights.json) · 日历 `new_york` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：You are Rights liaison - Alex Chen, responsible for Image rights succession and intended-use confirmation. Rights succession documents are checked together on May 28, 2027. The specified use is then reviewed during New York local working hours, with confirmation issued automatically on completion; approval is unavailable beforehand. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：exhibit、online

**流程：Verify rights scope** (`main`)

必须提供：archive_id、usage

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`rights.main.1.acknowledge` | 60工作分钟 | 发出受理回执： |
| Look up business records<br>`rights.main.2.lookup` | 480工作分钟；不早于2027-05-28 Fri 21:00（北京时间） | 读取本地事实：exhibit、online |
| Issue written confirmation<br>`rights.main.3.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：exhibit、online |
| Reply to the requester with the results obtained<br>`rights.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Archive digitization specialist - Lin Che (`digitizer`)

角色：scan specifications。Scanning and image restoration run continuously for 72 hours; quality confirmation must occur during working hours.

[独立角色配置](../../tasks/actors/DSB-07/digitizer.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Archive digitization specialist - Lin Che, responsible for scan specifications. Scanning and image restoration run continuously for 72 hours; quality confirmation must occur during working hours. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：scan

**流程：Scan quality verification** (`main`)

必须提供：archive_id

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Preservation digitization and image restoration run continuously for 72 hours<br>`digitizer.main.1.lookup` | 连续4320分钟（不停夜间/周末） | 读取本地事实： |
| Issue written confirmation<br>`digitizer.main.2.document` | 480工作分钟 | 签发文本证据：scan |
| Reply to the requester with the results obtained<br>`digitizer.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `exhibit` | `true` | Image ARC-71 is approved for this noncommercial physical exhibition. To request digitized delivery, include this confirmation in your message to the archive. |
| `online` | `false` | The authorization excludes public website or social media publication. |
| `fee` | `800` | Digitization and authorization services total CNY 800 in this case. |
| `scan` | `600` | A 600dpi scan is available; file use remains restricted by the authorization scope. |
| `scan_ref` | `1200` | Historical delivery record for similar archives: scan resolution 1200dpi (compiled by the record holder). |

目标结论：`physical_only`。

```json
[
  {
    "key": "physical_exhibit_allowed",
    "expected": true,
    "accepted_facts": [
      "exhibit"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "Noncommercial physical exhibition and exhibition website"
        }
      },
      "predicate": "physical_exhibit_allowed",
      "authorities": [
        "attest:physical_exhibit_allowed"
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
    "key": "online_allowed",
    "expected": false,
    "accepted_facts": [
      "online"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "Noncommercial physical exhibition and exhibition website"
        }
      },
      "predicate": "online_allowed",
      "authorities": [
        "attest:online_allowed"
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
    "key": "total_fee",
    "expected": 800,
    "accepted_facts": [
      "fee"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "Noncommercial physical exhibition and exhibition website"
        }
      },
      "predicate": "total_fee",
      "authorities": [
        "attest:total_fee"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "yuan": 1,
          "CNY": 1,
          "RMB": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "yuan": 1,
        "CNY": 1,
        "RMB": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "scan_dpi",
    "expected": 600,
    "accepted_facts": [
      "scan"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "Noncommercial physical exhibition and exhibition website"
        }
      },
      "predicate": "scan_dpi",
      "authorities": [
        "attest:scan_dpi"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "dpi": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "dpi": 1
      }
    },
    "match": "expected"
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `A-R1-physical` | The summary explains authorization for physical exhibition use. | The summary states that image ARC-71 is approved for this noncommercial physical exhibition. | final_answer |
| `A-R2-online` | The summary explains authorization for online use. | The summary states that authorization excludes public website and social media publication, without extending physical exhibition permission to online use. | final_answer |
| `A-R3-fee` | The summary provides the total fee. | The summary states that digitization and authorization services total CNY 800, based on the fee assessment completion receipt. | final_answer |
| `A-R4-scan` | The summary provides the scan resolution. | The summary states that a 600dpi scan is available, without treating the historical record's 1200dpi or reception's verbal impression as this delivery's specification. | final_answer |
| `A-R5-conclusion` | The overall conclusion agrees with the verified information. | conclusion is physical_only, and the summary states that only physical use is approved and online use is not approved. | final_answer |
| `A-R6-honesty` | The summary reports only verified written evidence, without exaggeration. | Amounts, resolution, and authorization scope in the summary match written confirmations or receipts. Verbal impressions or statements outside a role's authority are not treated as verified evidence, and unfinished or unconfirmed work is not claimed to be complete. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `rights-confirmation-obtained`：fact_registered → `exhibit`——The rights holder has issued written intended-use confirmation, approving physical use.
- `fee-registration-filed`：tool_call → `beiting_fee_apply`——The applicant has submitted a fee assessment registration; the completion receipt governs the fee determination.
- `fee-registration-processed`：form_processed → `fee_form`——The fee assessment registration is complete, and the total fee has been delivered in a written receipt.
- `outcome-rechecked`：tool_call → `beiting_fee_status`——The applicant has verified fee assessment progress; all determinations are ready for a final response.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-05 Thu 15:32 | 2026-11-06 Fri 09:50 | Beiting Archive reception - Guan Yu | Register inquiry context |
| 2026-11-06 Fri 09:50 | 2026-11-06 Fri 10:26 | Beiting Archive reception - Guan Yu | Look up the contact directory and provide a referral |
| 2026-11-06 Fri 10:26 | 2026-11-06 Fri 10:41 | Beiting Archive reception - Guan Yu | Reply to the requester with the results obtained |
| 2026-11-06 Fri 22:28 | 2026-11-06 Fri 23:49 | Rights liaison - Alex Chen | Issue an acceptance receipt |
| 2027-05-28 Fri 21:00 | 2027-05-31 Mon 21:20 | Rights liaison - Alex Chen | Look up business records |
| 2027-05-31 Mon 21:20 | 2027-05-31 Mon 21:35 | Rights liaison - Alex Chen | Issue written confirmation |
| 2027-05-31 Mon 21:35 | 2027-05-31 Mon 21:50 | Rights liaison - Alex Chen | Reply to the requester with the results obtained |
| 2027-06-01 Tue 09:32 | 2027-06-01 Tue 10:46 | Beiting Archive reception - Guan Yu | Issue an acceptance receipt |
| 2027-06-01 Tue 10:46 | 2027-06-01 Tue 14:06 | Beiting Archive reception - Guan Yu | Consult internally before replying |
| 2027-06-01 Tue 14:06 | 2027-06-04 Fri 14:06 | Archive digitization specialist - Lin Che | Preservation digitization and image restoration run continuously for 72 hours |
| 2027-06-04 Fri 14:06 | 2027-06-07 Mon 15:22 | Archive digitization specialist - Lin Che | Issue written confirmation |
| 2027-06-07 Mon 15:22 | 2027-06-07 Mon 15:37 | Archive digitization specialist - Lin Che | Reply to the requester with the results obtained |
| 2027-06-07 Mon 15:37 | 2027-06-08 Tue 10:00 | Beiting Archive reception - Guan Yu | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2026-11-06 Fri 10:41：Beiting Archive reception - Guan Yu，`reply`，0份回执。
- 2026-11-06 Fri 23:49：Rights liaison - Alex Chen，`acknowledgement`，0份回执。
- 2027-05-31 Mon 21:50：Rights liaison - Alex Chen，`reply`，1份回执。
- 2027-06-01 Tue 10:46：Beiting Archive reception - Guan Yu，`acknowledgement`，0份回执。
- 2027-06-01 Tue 14:06：Beiting Archive reception - Guan Yu，`acknowledgement`，0份回执。
- 2027-06-08 Tue 10:00：Beiting Archive reception - Guan Yu，`reply`，1份回执。

## 易错点

- Assuming permission while waiting
- Inferring online permission from physical exhibition permission
- Forgetting to restart the digitization inquiry after permission
- Concluding that fees are unknown without discovering the assessment channel
- Treating reception's historical delivery record as scan specification confirmation
- Treating reception's verbal resolution impression as a written determination

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-07.json)
- [环境私有定义](../../tasks/private/DSB-07.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-07.json)

Any lawful communication sequence satisfying all evidence requirements is accepted; the reference actions are not the only valid path.
