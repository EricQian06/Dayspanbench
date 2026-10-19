# DSB-43 · Club recruitment: two app groups, staggered surveys, one interview clash

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：campus_life。开始：2026-09-11 Fri 20:00；截止：2026-09-23 Wed 18:00（北京时间）。

参考轨迹历时：**8.91944天（214.07小时）**。结果类别：`resolved`。

跨度设计：Medium term；two in-app recruitment groups with staggered surveys and interview announcements, and one cross-day interview clash。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

You are assisting Alex Chen, a first-year undergraduate at Lanxi University who visited tonight's campus festival and wants to join both the Badminton Club and the Piano Club. Two QR codes were scanned at the booths; each opens the club's recruitment group in the messaging app. Join both groups, fill each club's recruitment questionnaire with Alex's own answers (ask Alex through consult_user - do not guess), and follow the group announcements. Interview assignments are posted in the groups on September 17 and 19. If the assigned interview times clash with each other or with Alex's commitments, sort it out with the right officers so Alex can join both clubs.

Only join the two recruitment groups in the messaging app, submit the two surveys with Alex's own answers, read the group announcements, and write to the club officers about interview times. Never post in the groups on Alex's behalf, never add strangers, and never drop either club.

已给信息：

```json
{
  "full_name": "Alex Chen",
  "student_id": "2026011347"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- the two recruitment groups are separate in-app services; the browser cannot join either
- the piano group needs admin review before membership; the badminton group joins instantly
- the piano group hits its member cap between September 13 20:00 and September 14 09:00
- the surveys open on different days (September 14 and 15) and close before the interviews
- interview assignments are posted in the group timelines on September 17 and 19, not before
- the two assigned interviews clash on Tuesday, September 22 evening (19:40-20:40 and 20:00-21:10)
- badminton interviews are one-hour group slots, so rescheduling is cross-day
- the user's Wednesday-evening constraint surfaces only by asking (and was only volunteered on the badminton survey)

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Badminton Club - Lin Zhiyuan (`bwc_president`)

角色：Club president; recruitment referrals only。Public face of the club; interview scheduling belongs to the Events head, who is named in the referral.

[独立角色配置](../../tasks/actors/DSB-43/bwc_president.json) · 日历 `campus_evening` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：18:00—23:00

接收者约束：You are Badminton Club - Lin Zhiyuan, responsible for Club president; recruitment referrals only. Public face of the club; interview scheduling belongs to the Events head, who is named in the referral. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Badminton recruitment referrals** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up the contact directory and provide a referral<br>`bwc_president.main.1.refer` | 20工作分钟 | 公开转介联系人：bwc_events_head |
| Reply to the requester with the results obtained<br>`bwc_president.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Badminton Club - Zhou Yanan (`bwc_events_head`)

角色：Events; interview scheduling and rescheduling。Schedules and reschedules the one-hour group interview slots; needs the applicant's actual evening availability, especially about Wednesday, before moving anyone.

[独立角色配置](../../tasks/actors/DSB-43/bwc_events_head.json) · 日历 `campus_evening` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：18:00—23:00

接收者约束：You are Badminton Club - Zhou Yanan, responsible for Events; interview scheduling and rescheduling. Schedules and reschedules the one-hour group interview slots; needs the applicant's actual evening availability, especially about Wednesday, before moving anyone. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：bwc_rescheduled_monday、bwc_survey_recorded、bwc_wednesday_booked

**流程：Badminton interview scheduling** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Read the request and answer on its substance<br>`bwc_events_head.main.1.extract` | 30工作分钟 | LLM提取字段后按结构化分支回复： |

### Piano Club - Chen Mo (`pnc_events_head`)

角色：Events; recruitment referrals only。Answers general recruitment questions; interview assignments and any changes belong to the president, who is named in the referral.

[独立角色配置](../../tasks/actors/DSB-43/pnc_events_head.json) · 日历 `campus_evening` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：18:00—23:00

接收者约束：You are Piano Club - Chen Mo, responsible for Events; recruitment referrals only. Answers general recruitment questions; interview assignments and any changes belong to the president, who is named in the referral. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Piano recruitment referrals** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up the contact directory and provide a referral<br>`pnc_events_head.main.1.refer` | 20工作分钟 | 公开转介联系人：pnc_president |
| Reply to the requester with the results obtained<br>`pnc_events_head.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Piano Club - Wu Kexin (`pnc_president`)

角色：President; interview assignments and changes。Assigns the per-person interview slots and is the only one who can change them; may propose the Wednesday slot.

[独立角色配置](../../tasks/actors/DSB-43/pnc_president.json) · 日历 `campus_evening` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：18:00—23:00

接收者约束：You are Piano Club - Wu Kexin, responsible for President; interview assignments and changes. Assigns the per-person interview slots and is the only one who can change them; may propose the Wednesday slot. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：pnc_confirmed_original、pnc_survey_recorded、pnc_wednesday_booked

**流程：Piano interview scheduling** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Read the request and answer on its substance<br>`pnc_president.main.1.extract` | 30工作分钟 | LLM提取字段后按结构化分支回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `bwc_survey_recorded` | `true` | The Badminton Club recruitment survey recorded Alex Chen's availability: Monday 2026-09-21, Tuesday 2026-09-22, Thursday 2026-09-24, Friday 2026-09-25 (not Wednesday 2026-09-23), with department preference Competition. |
| `pnc_survey_recorded` | `true` | The Piano Club questionnaire recorded Alex Chen's answers: both offered days work, six years of playing, department preference Performance. |
| `bwc_rescheduled_monday` | `true` | The Badminton Club interview was moved to Monday, 2026-09-21, 19:30-20:30, Gym Court 2 (one-hour group slot), after Alex reported being unavailable on Wednesday 2026-09-23. |
| `pnc_confirmed_original` | `true` | The Piano Club interview stays at its original slot, Tuesday, 2026-09-22, 20:00-21:10, Music Building A201; the offered Wednesday 2026-09-23 20:00-20:10 slot was declined. |
| `bwc_wednesday_booked` | `true` | The Badminton Club interview was booked for Wednesday, 2026-09-23, 19:30-20:30, Gym Court 2 — an evening Alex cannot attend. |
| `pnc_wednesday_booked` | `true` | The Piano Club interview was moved to Wednesday, 2026-09-23, 20:00-20:10, Music Building A201 — an evening Alex cannot attend. |

目标结论：`resolved`。

```json
[
  {
    "key": "badminton_survey_recorded",
    "expected": true,
    "accepted_facts": [
      "bwc_survey_recorded"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-43",
        "case": {
          "full_name": "Alex Chen",
          "student_id": "2026011347"
        }
      },
      "predicate": "badminton_survey_recorded",
      "authorities": [
        "attest:badminton_survey_recorded"
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
    "key": "piano_survey_recorded",
    "expected": true,
    "accepted_facts": [
      "pnc_survey_recorded"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-43",
        "case": {
          "full_name": "Alex Chen",
          "student_id": "2026011347"
        }
      },
      "predicate": "piano_survey_recorded",
      "authorities": [
        "attest:piano_survey_recorded"
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
    "key": "badminton_interview_moved",
    "expected": true,
    "accepted_facts": [
      "bwc_rescheduled_monday"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-43",
        "case": {
          "full_name": "Alex Chen",
          "student_id": "2026011347"
        }
      },
      "predicate": "badminton_interview_moved",
      "authorities": [
        "attest:badminton_interview_moved"
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
    "key": "piano_interview_kept",
    "expected": true,
    "accepted_facts": [
      "pnc_confirmed_original"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-43",
        "case": {
          "full_name": "Alex Chen",
          "student_id": "2026011347"
        }
      },
      "predicate": "piano_interview_kept",
      "authorities": [
        "attest:piano_interview_kept"
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
| `C43-conflict-detected` | The final summary reports that the two assigned interviews clash on Tuesday, 2026-09-22 evening. | The final answer states the badminton slot (19:40-20:40) and the piano slot (20:00-21:10) both fall on Tuesday, 2026-09-22 and overlap. | final_answer |
| `C43-surveys-filed` | Both recruitment surveys were submitted with the user's own answers. | The trace or final answer shows the badminton survey filed with all weekday evenings except Wednesday 2026-09-23 and department Competition, and the piano questionnaire filed with both days, six years of playing, department Performance. | trace |
| `C43-wednesday-handled` | The user's Wednesday-evening unavailability was discovered and respected in both rescheduling conversations. | The agent asked the user (or learned from the survey answers) that Wednesday 2026-09-23 evenings do not work, conveyed this to the badminton Events head, and did not accept the piano president's Wednesday offer. | trace |
| `C43-badminton-resolution` | The badminton interview was moved off Tuesday to a workable evening. | The final answer reports the new badminton slot as Monday, 2026-09-21, 19:30-20:30, Gym Court 2, obtained from the Events head after stating the Wednesday constraint. | final_answer |
| `C43-piano-resolution` | The piano interview kept its original slot and the Wednesday offer was declined. | The final answer reports the piano interview stays Tuesday, 2026-09-22, 20:00-21:10, Music Building A201, and that the Wednesday 20:00-20:10 offer was not accepted. | final_answer |
| `C43-departments-conveyed` | (Ancillary, low weight.) When consulting Alex about the survey choices, the club departments were conveyed rather than guessed. | The agent's consult_user questions or letters reflect the actual department sets (badminton: Referee, Publicity, Events, Competition; piano: Performance, Publicity, Outreach) instead of inventing or omitting departments. | trace |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `groups-joined`：tool_call → `bwc_group`——Both recruitment groups must be joined in-app; one group needs admin review, one hits a cap overnight.
- `surveys-filed`：form_processed → `bwc_survey_form`——The surveys open September 14/15 and take the user's own answers.
- `schedules-read`：tool_call → `pnc_group`（关键词：interview）——Interview assignments are posted in the group timelines on September 17 and 19.
- `user-consulted`：tool_call → `consult_user`（关键词：free、available、wednesday）——The Wednesday constraint surfaces only by asking the user.
- `badminton-moved`：fact_registered → `bwc_rescheduled_monday`——The Events head moves the one-hour slot cross-day once the Wednesday constraint is stated.
- `piano-kept`：fact_registered → `pnc_confirmed_original`——The piano president confirms the original Tuesday slot when the agent keeps it.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-09-19 Sat 21:12 | 2026-09-19 Sat 22:00 | Piano Club - Wu Kexin | Read the request and answer on its substance |
| 2026-09-19 Sat 22:21 | 2026-09-20 Sun 18:04 | Badminton Club - Zhou Yanan | Read the request and answer on its substance |

Agent收到的实质回复：

- 2026-09-12 Sat 12:00：messaging-app，`reply`，0份回执。
- 2026-09-12 Sat 13:38：user，`reply`，0份回执。
- 2026-09-19 Sat 20:28：user，`reply`，0份回执。
- 2026-09-19 Sat 22:00：Piano Club - Wu Kexin，`reply`，1份回执。
- 2026-09-20 Sun 18:04：Badminton Club - Zhou Yanan，`reply`，1份回执。

## 易错点

- guessing the survey answers instead of asking Alex
- missing the hidden capacity window and concluding the piano group is closed forever
- reading the group timeline before September 17/19 and concluding no interview exists
- not noticing the Tuesday clash between 20:00 and 20:40
- emailing the presidents first instead of the officers who own interview scheduling
- telling the badminton Events head the user is free Wednesday (the rehearsal evening)
- accepting the piano president's Wednesday 20:00-20:10 offer instead of keeping Tuesday
- dropping one club instead of rescheduling

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-43.json)
- [环境私有定义](../../tasks/private/DSB-43.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-43.json)

Any lawful order of group joins, survey submissions, reads and officer mail is accepted if every goal's evidence conditions hold; either club may be sorted out first, and the clash may be resolved by moving the badminton interview to any evening the user is actually free - the reference's Monday slot is one valid outcome, not the only one.
