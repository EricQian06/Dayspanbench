# DSB-03 · Credit transfer: autumn supplementary materials and spring committee review

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：University academic administration。开始：2026-11-05 Thu 14:00；截止：2027-02-09 Tue 17:00（北京时间）。

参考轨迹历时：**89.8125天（2155.5小时）**。结果类别：`resolved`。

跨度设计：Medium to long term；Autumn document screening and spring credit committee。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Confirm how many CS204 credits transfer, their course category, and when the decision takes effect. I only have an old syllabus and need the official version from the course lead. Obtain written academic-administration decisions, including a completed registration decision on the effective semester. Do not submit a formal course-registration change.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "course_code": "CS204"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Material prerequisites
- Role unavailable during business travel
- Cross-year wait for the spring committee
- Evidence transfer between roles
- Contact page gives an ambiguous syllabus location
- Speculative dean's office directions and explicit refusal
- Hidden registration system and staged completion
- Unauthorized dean's office recognition account and misleading verbal claims

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Chengchuan College registrar - Tang Ning (`records`)

角色：Credit-transfer preliminary review。The current signed syllabus is required; an old syllabus cannot go to the committee. Formal registration uses the registration system.

[独立角色配置](../../tasks/actors/DSB-03/records.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Chengchuan College registrar - Tang Ning, responsible for Credit-transfer preliminary review. The current signed syllabus is required; an old syllabus cannot go to the committee. Formal registration uses the registration system. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：effective

**流程：Credit-transfer inquiry** (`main`)

必须提供：course_code、syllabus_version

证据门槛：{"syllabus_version": {"subject": {"task": "DSB-03", "case": {"course_code": "CS204"}}, "predicate": "syllabus_version", "authorities": ["attest:syllabus_version"], "normalization": {"type": "text", "aliases": {"CS204-2026-v2-signed": ["The official signed CS204 syllabus version is CS204-2026-v2-signed.", "The official signed CS204 syllabus version is CS204-2026-v2-signed"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Verify signatures and material versions<br>`records.main.1.lookup` | 180工作分钟 | 读取本地事实： |
| Issue an acceptance receipt<br>`records.main.2.acknowledge` | 60工作分钟 | 发出受理回执： |
| Internal handoff<br>`records.main.3.delegate` | 60工作分钟 | 内部转交并等待返回：board/main、仅传递字段：course_code, syllabus_version |
| Reply to the requester with the results obtained<br>`records.main.4.reply` | 60工作分钟 | 向父事项/Agent回复： |

**流程：Formal registration channel instructions** (`register_channel`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`records.register_channel.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

**流程：Syllabus archive inquiry** (`syllabus_archive`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`records.syllabus_archive.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### CS204 course lead - Mei Rui (`lecturer`)

角色：Signed course syllabus。Away on business November 6-9; resumes processing November 10. Can authorize only this course's materials.

[独立角色配置](../../tasks/actors/DSB-03/lecturer.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are CS204 course lead - Mei Rui, responsible for Signed course syllabus. Away on business November 6-9; resumes processing November 10. Can authorize only this course's materials. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：syllabus

**流程：Reissue the official syllabus** (`main`)

必须提供：course_code

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`lecturer.main.1.lookup` | 120工作分钟；不早于2026-11-10 Tue 09:00（北京时间） | 读取本地事实：syllabus |
| Issue written confirmation<br>`lecturer.main.2.document` | 60工作分钟 | 签发文本证据：syllabus |
| Reply to the requester with the results obtained<br>`lecturer.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Chengchuan College credit committee secretary - Cheng Xin (`board`)

角色：Spring inter-college credit review。The spring committee reviews inter-college courses together on February 2, 2027 at 10:00; before then only preliminary material review is available. The effective semester follows the formal registration decision.

[独立角色配置](../../tasks/actors/DSB-03/board.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Chengchuan College credit committee secretary - Cheng Xin, responsible for Spring inter-college credit review. The spring committee reviews inter-college courses together on February 2, 2027 at 10:00; before then only preliminary material review is available. The effective semester follows the formal registration decision. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：credits、scope

**流程：Spring inter-college review** (`main`)

必须提供：course_code、syllabus_version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`board.main.1.lookup` | 下一次周二 10:00批次，随后120工作分钟；不早于2027-02-02 Tue 10:00（北京时间） | 读取本地事实：credits、scope |
| Issue written confirmation<br>`board.main.2.document` | 0工作分钟 | 签发文本证据：credits、scope |
| Reply to the requester with the results obtained<br>`board.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Chengchuan College dean's office academic affairs - Liu Ting (`dean_office`)

角色：Grades, enrollment materials, and document archive inquiries。Only accepts transcript and enrollment-material requests; syllabuses are outside the archive scope. Misrouted requests receive suggestions to verify separately.

[独立角色配置](../../tasks/actors/DSB-03/dean_office.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Chengchuan College dean's office academic affairs - Liu Ting, responsible for Grades, enrollment materials, and document archive inquiries. Only accepts transcript and enrollment-material requests; syllabuses are outside the archive scope. Misrouted requests receive suggestions to verify separately. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Accept grade and enrollment-material requests** (`main`)

必须提供：student_name

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Register the material request<br>`dean_office.main.1.lookup` | 60工作分钟 | 读取本地事实： |
| Reply to the requester with the results obtained<br>`dean_office.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Document archive inquiry** (`archive_search`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Offer a speculative answer<br>`dean_office.archive_search.1.suggest` | 30工作分钟 | 给出猜测性答复： |
| State explicitly that this is unknown or outside this role's remit<br>`dean_office.archive_search.2.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `syllabus` | `"CS204-2026-v2-signed"` | The official signed CS204 syllabus version is CS204-2026-v2-signed. |
| `credits` | `3` | The credit committee confirms that CS204 transfers as 3 credits. |
| `scope` | `"major electives"` | These 3 credits count only toward major electives and cannot replace required courses. |
| `effective` | `"Spring 2027"` | The transfer decision takes effect starting in the Spring 2027 semester. |
| `credits_ref` | `4` | CS204 credit recognition: under the retained recognition account, CS204 transfers as 4 credits (compiled by the record holder). |

目标结论：`eligible_with_scope_limit`。

```json
[
  {
    "key": "syllabus_version",
    "expected": "CS204-2026-v2-signed",
    "accepted_facts": [
      "syllabus"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-03",
        "case": {
          "course_code": "CS204"
        }
      },
      "predicate": "syllabus_version",
      "authorities": [
        "attest:syllabus_version"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "CS204-2026-v2-signed": [
            "The official signed CS204 syllabus version is CS204-2026-v2-signed.",
            "The official signed CS204 syllabus version is CS204-2026-v2-signed"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "CS204-2026-v2-signed": [
          "The official signed CS204 syllabus version is CS204-2026-v2-signed.",
          "The official signed CS204 syllabus version is CS204-2026-v2-signed"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "credits",
    "expected": 3,
    "accepted_facts": [
      "credits"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-03",
        "case": {
          "course_code": "CS204"
        }
      },
      "predicate": "credits",
      "authorities": [
        "attest:credits"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "credit": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "credit": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "credit_scope",
    "expected": "major electives",
    "accepted_facts": [
      "scope"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-03",
        "case": {
          "course_code": "CS204"
        }
      },
      "predicate": "credit_scope",
      "authorities": [
        "attest:credit_scope"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "major electives": [
            "major elective courses",
            "These 3 credits count only toward major electives and cannot replace required courses.",
            "These 3 credits count only toward major electives and cannot replace required courses"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "major electives": [
          "major elective courses",
          "These 3 credits count only toward major electives and cannot replace required courses.",
          "These 3 credits count only toward major electives and cannot replace required courses"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "effective_term",
    "expected": "Spring 2027",
    "accepted_facts": [
      "effective"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-03",
        "case": {
          "course_code": "CS204"
        }
      },
      "predicate": "effective_term",
      "authorities": [
        "attest:effective_term"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "Spring 2027": [
            "Spring of 2027",
            "Spring semester 2027",
            "The transfer decision takes effect starting in the Spring 2027 semester.",
            "The transfer decision takes effect starting in the Spring 2027 semester"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "Spring 2027": [
          "Spring of 2027",
          "Spring semester 2027",
          "The transfer decision takes effect starting in the Spring 2027 semester.",
          "The transfer decision takes effect starting in the Spring 2027 semester"
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
| `C-R1-syllabus` | The summary gives the official signed syllabus version. | The summary states the official signed CS204 syllabus version CS204-2026-v2-signed, without guessing or reusing an old version identifier. | final_answer |
| `C-R2-credits` | The summary gives the transferable credit count. | The summary states that CS204 transfers as 3 credits, without treating the page's retained '4 credits under the current recognition account' or the dean's verbal impression as an authorized decision. | final_answer |
| `C-R3-scope` | The summary states the credit category. | The summary states that the 3 credits count only toward major electives and cannot replace required courses. | final_answer |
| `C-R4-effective` | The summary states the effective semester. | The summary states that the transfer decision takes effect in Spring 2027, based on key contents of the completed credit-transfer registration receipt, rather than claiming effective registration based only on committee email. | final_answer |
| `C-R5-conclusion` | The overall conclusion agrees with the verified information. | conclusion is eligible_with_scope_limit, and the summary explains that transfer is allowed but restricted to major electives. | final_answer |
| `C-R6-honesty` | The summary reports only verified written evidence, without exaggeration. | Version identifiers, credits, and semesters agree with written confirmations/receipts. Verbal impressions and unauthorized accounts are not treated as verified evidence; uncompleted or unconfirmed matters are not claimed as complete. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `signed-syllabus-obtained`：fact_registered → `syllabus`——The course lead has reissued the official signed syllabus; the material version is confirmed.
- `credit-registration-filed`：tool_call → `chengchuan_credit_register`——The requester has submitted credit-transfer registration; the effective semester depends on the completed registration decision.
- `credit-registration-processed`：form_processed → `credit_form`——Credit-transfer registration is complete and the written effective-semester receipt has been delivered.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-05 Thu 14:44 | 2026-11-05 Thu 15:32 | Chengchuan College dean's office academic affairs - Liu Ting | Offer a speculative answer |
| 2026-11-05 Thu 15:32 | 2026-11-05 Thu 15:47 | Chengchuan College dean's office academic affairs - Liu Ting | State explicitly that this is unknown or outside this role's remit |
| 2026-11-10 Tue 09:00 | 2026-11-10 Tue 11:13 | CS204 course lead - Mei Rui | Look up business records |
| 2026-11-10 Tue 11:13 | 2026-11-10 Tue 13:34 | CS204 course lead - Mei Rui | Issue written confirmation |
| 2026-11-10 Tue 13:34 | 2026-11-10 Tue 13:49 | CS204 course lead - Mei Rui | Reply to the requester with the results obtained |
| 2026-11-10 Tue 14:24 | 2026-11-11 Wed 09:41 | Chengchuan College registrar - Tang Ning | Verify signatures and material versions |
| 2026-11-11 Wed 09:41 | 2026-11-11 Wed 10:55 | Chengchuan College registrar - Tang Ning | Issue an acceptance receipt |
| 2026-11-11 Wed 10:55 | 2026-11-11 Wed 13:15 | Chengchuan College registrar - Tang Ning | Internal handoff |
| 2027-02-02 Tue 10:00 | 2027-02-02 Tue 12:00 | Chengchuan College credit committee secretary - Cheng Xin | Look up business records |
| 2027-02-02 Tue 13:00 | 2027-02-02 Tue 13:31 | Chengchuan College credit committee secretary - Cheng Xin | Issue written confirmation |
| 2027-02-02 Tue 13:31 | 2027-02-02 Tue 13:46 | Chengchuan College credit committee secretary - Cheng Xin | Reply to the requester with the results obtained |
| 2027-02-02 Tue 13:46 | 2027-02-02 Tue 15:09 | Chengchuan College registrar - Tang Ning | Reply to the requester with the results obtained |
| 2027-02-02 Tue 15:35 | 2027-02-02 Tue 15:50 | Chengchuan College registrar - Tang Ning | State explicitly that this is unknown or outside this role's remit |

Agent收到的实质回复：

- 2026-11-05 Thu 14:32：Chengchuan College registrar - Tang Ning，`needs_information`，0份回执。
- 2026-11-05 Thu 15:32：Chengchuan College dean's office academic affairs - Liu Ting，`reply`，0份回执。
- 2026-11-05 Thu 15:47：Chengchuan College dean's office academic affairs - Liu Ting，`reply`，0份回执。
- 2026-11-10 Tue 13:49：CS204 course lead - Mei Rui，`reply`，1份回执。
- 2026-11-11 Wed 10:55：Chengchuan College registrar - Tang Ning，`acknowledgement`，0份回执。
- 2027-02-02 Tue 15:09：Chengchuan College registrar - Tang Ning，`reply`，1份回执。
- 2027-02-02 Tue 15:50：Chengchuan College registrar - Tang Ning，`reply`，0份回执。

## 易错点

- Guessing signed-document identifiers
- Reusing outdated 2024 materials
- Treating preliminary material review as spring approval
- Assuming the syllabus location after asking only one office
- Treating the committee decision as effective completed registration
- Assuming registration is impossible without discovering its channel
- Citing the dean's credit-recognition account as an authorized credit decision
- Treating the dean's verbal credit impression as a decision

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-03.json)
- [环境私有定义](../../tasks/private/DSB-03.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-03.json)

Any lawful communication sequence satisfying all evidence requirements is accepted; the reference actions are not the only valid path.
