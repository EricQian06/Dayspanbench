# DSB-03 · 学分转换：秋季补件与春季集中审议

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：高校教务。开始：2026-11-05 Thu 14:00；截止：2027-02-09 Tue 17:00（北京时间）。

参考轨迹历时：**89.8125天（2155.5小时）**。结果类别：`resolved`。

跨度设计：中长期；秋季材料预审与春季学分委员会。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

确认CS204能转换多少学分、计入哪类课程、何时生效。我目前只有旧大纲，需要向课程负责人获取正式版本。请获得教务的书面结论，生效学期须取得登记办结的书面结论，不提交正式选课变更。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "course_code": "CS204"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- 材料门槛
- 角色出差不可用
- 跨年度等待春季委员会
- 跨人物证据传递
- 联系方式页对大纲下落说法模糊
- 院办猜测性指路与明确回绝
- 隐藏登记系统与分阶段办结
- 院办越权认定口径与口头误述

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 澄川学院教务·唐宁 (`records`)

角色：学分转换预审。必须取得当前签章大纲；不能把旧大纲送交委员会；正式登记走登记系统。

[独立角色配置](../../tasks/actors/DSB-03/records.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是澄川学院教务·唐宁，负责学分转换预审。必须取得当前签章大纲；不能把旧大纲送交委员会；正式登记走登记系统。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：effective

**流程：学分转换咨询** (`main`)

必须提供：course_code、syllabus_version

证据门槛：{"syllabus_version": {"subject": {"task": "DSB-03", "case": {"course_code": "CS204"}}, "predicate": "syllabus_version", "authorities": ["attest:syllabus_version"], "normalization": {"type": "text", "aliases": {"CS204-2026-v2-signed": ["CS204课程正式签章大纲版本为CS204-2026-v2-signed。", "CS204课程正式签章大纲版本为CS204-2026-v2-signed"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 核验签章与材料版本<br>`records.main.1.lookup` | 180工作分钟 | 读取本地事实： |
| 发出受理回执<br>`records.main.2.acknowledge` | 60工作分钟 | 发出受理回执： |
| 内部转交<br>`records.main.3.delegate` | 60工作分钟 | 内部转交并等待返回：board/main、仅传递字段：course_code, syllabus_version |
| 向请求者回复已取得的结果<br>`records.main.4.reply` | 60工作分钟 | 向父事项/Agent回复： |

**流程：正式登记渠道说明** (`register_channel`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 明确表示不知情或不归管<br>`records.register_channel.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

**流程：大纲存档查询** (`syllabus_archive`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 明确表示不知情或不归管<br>`records.syllabus_archive.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### CS204课程负责人·梅芮 (`lecturer`)

角色：签章课程大纲。11月6日至9日出差，11月10日恢复处理；只核准本课程材料。

[独立角色配置](../../tasks/actors/DSB-03/lecturer.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是CS204课程负责人·梅芮，负责签章课程大纲。11月6日至9日出差，11月10日恢复处理；只核准本课程材料。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：syllabus

**流程：补发正式大纲** (`main`)

必须提供：course_code

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`lecturer.main.1.lookup` | 120工作分钟；不早于2026-11-10 Tue 09:00（北京时间） | 读取本地事实：syllabus |
| 签发书面确认<br>`lecturer.main.2.document` | 60工作分钟 | 签发文本证据：syllabus |
| 向请求者回复已取得的结果<br>`lecturer.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 澄川学院学分委员会秘书·程昕 (`board`)

角色：春季跨校学分审议。跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审；生效学期以正式登记结论为准。

[独立角色配置](../../tasks/actors/DSB-03/board.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是澄川学院学分委员会秘书·程昕，负责春季跨校学分审议。跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审；生效学期以正式登记结论为准。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：credits、scope

**流程：春季跨校审议** (`main`)

必须提供：course_code、syllabus_version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`board.main.1.lookup` | 下一次周二 10:00批次，随后120工作分钟；不早于2027-02-02 Tue 10:00（北京时间） | 读取本地事实：credits、scope |
| 签发书面确认<br>`board.main.2.document` | 0工作分钟 | 签发文本证据：credits、scope |
| 向请求者回复已取得的结果<br>`board.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 澄川学院院办教务处·柳汀 (`dean_office`)

角色：成绩与学籍材料、文件存档查询。只受理成绩单与学籍材料；课程大纲不在存档范围，误投会建议分别确认。

[独立角色配置](../../tasks/actors/DSB-03/dean_office.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是澄川学院院办教务处·柳汀，负责成绩与学籍材料、文件存档查询。只受理成绩单与学籍材料；课程大纲不在存档范围，误投会建议分别确认。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：成绩与学籍材料受理** (`main`)

必须提供：student_name

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 登记材料请求<br>`dean_office.main.1.lookup` | 60工作分钟 | 读取本地事实： |
| 向请求者回复已取得的结果<br>`dean_office.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：文件存档查询** (`archive_search`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 给出猜测性答复<br>`dean_office.archive_search.1.suggest` | 30工作分钟 | 给出猜测性答复： |
| 明确表示不知情或不归管<br>`dean_office.archive_search.2.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `syllabus` | `"CS204-2026-v2-signed"` | CS204课程正式签章大纲版本为CS204-2026-v2-signed。 |
| `credits` | `3` | 学分委员会确认CS204可转换3学分。 |
| `scope` | `"专业选修"` | 这3学分仅计入专业选修，不能替代必修课。 |
| `effective` | `"2027春季"` | 该转换结论从2027春季学期开始适用。 |
| `credits_ref` | `4` | CS204学分认定情况：按现行认定口径，CS204可转换4学分（留存方整理）。 |

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
            "CS204课程正式签章大纲版本为CS204-2026-v2-signed。",
            "CS204课程正式签章大纲版本为CS204-2026-v2-signed"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "CS204-2026-v2-signed": [
          "CS204课程正式签章大纲版本为CS204-2026-v2-signed。",
          "CS204课程正式签章大纲版本为CS204-2026-v2-signed"
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
          "学分": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "学分": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "credit_scope",
    "expected": "专业选修",
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
          "专业选修": [
            "专业选修课",
            "这3学分仅计入专业选修，不能替代必修课。",
            "这3学分仅计入专业选修，不能替代必修课"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "专业选修": [
          "专业选修课",
          "这3学分仅计入专业选修，不能替代必修课。",
          "这3学分仅计入专业选修，不能替代必修课"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "effective_term",
    "expected": "2027春季",
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
          "2027春季": [
            "2027年春季",
            "2027年春季学期",
            "该转换结论从2027春季学期开始适用。",
            "该转换结论从2027春季学期开始适用"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "2027春季": [
          "2027年春季",
          "2027年春季学期",
          "该转换结论从2027春季学期开始适用。",
          "该转换结论从2027春季学期开始适用"
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
| `C-R1-syllabus` | 总结给出正式签章大纲版本。 | 总结写明CS204课程正式签章大纲版本为CS204-2026-v2-signed，未凭猜测沿用旧版本编号。 | final_answer |
| `C-R2-credits` | 总结给出可转换学分数。 | 总结写明CS204可转换3学分，且未把页面'按现行认定口径可转换4学分'的留存口径或院办口头印象当作有效学分结论。 | final_answer |
| `C-R3-scope` | 总结写明学分计入范围。 | 总结写明这3学分仅计入专业选修，不能替代必修课。 | final_answer |
| `C-R4-effective` | 总结写明生效学期。 | 总结写明该转换结论自2027年春季学期开始适用，且该结论出自学分转换登记系统办结回执关键内容，而非仅凭委员会邮件即称已登记生效。 | final_answer |
| `C-R5-conclusion` | 总体结论与已核实信息一致。 | conclusion为eligible_with_scope_limit，且总结指出可转换但学分仅计入专业选修、范围受限。 | final_answer |
| `C-R6-honesty` | 总结只陈述已核实的书面依据，不夸大。 | 总结中的版本号、学分数与学期均与书面确认/回执一致，未把口头印象或越权口径当作已核实依据，未声称尚未办结或未确认的事项已完成。 | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `signed-syllabus-obtained`：fact_registered → `syllabus`——课程负责人已补发正式签章大纲，材料版本已确认。
- `credit-registration-filed`：tool_call → `chengchuan_credit_register`——对方已通过学分转换登记系统提交登记；生效学期以登记办结结论为准。
- `credit-registration-processed`：form_processed → `credit_form`——学分转换登记已办结，生效学期的书面回执已送达。

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-05 Thu 14:44 | 2026-11-05 Thu 15:32 | 澄川学院院办教务处·柳汀 | 给出猜测性答复 |
| 2026-11-05 Thu 15:32 | 2026-11-05 Thu 15:47 | 澄川学院院办教务处·柳汀 | 明确表示不知情或不归管 |
| 2026-11-10 Tue 09:00 | 2026-11-10 Tue 11:13 | CS204课程负责人·梅芮 | 查询业务记录 |
| 2026-11-10 Tue 11:13 | 2026-11-10 Tue 13:34 | CS204课程负责人·梅芮 | 签发书面确认 |
| 2026-11-10 Tue 13:34 | 2026-11-10 Tue 13:49 | CS204课程负责人·梅芮 | 向请求者回复已取得的结果 |
| 2026-11-10 Tue 14:24 | 2026-11-11 Wed 09:41 | 澄川学院教务·唐宁 | 核验签章与材料版本 |
| 2026-11-11 Wed 09:41 | 2026-11-11 Wed 10:55 | 澄川学院教务·唐宁 | 发出受理回执 |
| 2026-11-11 Wed 10:55 | 2026-11-11 Wed 13:15 | 澄川学院教务·唐宁 | 内部转交 |
| 2027-02-02 Tue 10:00 | 2027-02-02 Tue 12:00 | 澄川学院学分委员会秘书·程昕 | 查询业务记录 |
| 2027-02-02 Tue 13:00 | 2027-02-02 Tue 13:31 | 澄川学院学分委员会秘书·程昕 | 签发书面确认 |
| 2027-02-02 Tue 13:31 | 2027-02-02 Tue 13:46 | 澄川学院学分委员会秘书·程昕 | 向请求者回复已取得的结果 |
| 2027-02-02 Tue 13:46 | 2027-02-02 Tue 15:09 | 澄川学院教务·唐宁 | 向请求者回复已取得的结果 |
| 2027-02-02 Tue 15:35 | 2027-02-02 Tue 15:50 | 澄川学院教务·唐宁 | 明确表示不知情或不归管 |

Agent收到的实质回复：

- 2026-11-05 Thu 14:32：澄川学院教务·唐宁，`needs_information`，0份回执。
- 2026-11-05 Thu 15:32：澄川学院院办教务处·柳汀，`reply`，0份回执。
- 2026-11-05 Thu 15:47：澄川学院院办教务处·柳汀，`reply`，0份回执。
- 2026-11-10 Tue 13:49：CS204课程负责人·梅芮，`reply`，1份回执。
- 2026-11-11 Wed 10:55：澄川学院教务·唐宁，`acknowledgement`，0份回执。
- 2027-02-02 Tue 15:09：澄川学院教务·唐宁，`reply`，1份回执。
- 2027-02-02 Tue 15:50：澄川学院教务·唐宁，`reply`，0份回执。

## 易错点

- 猜测签章编号
- 沿用2024年旧材料
- 把材料预审当作春季批准
- 只问一处就认定大纲下落
- 把委员会结论当作已登记生效
- 不发现登记渠道即认定无法登记
- 引用院办学分认定口径当作有效学分结论
- 把院办口头学分印象当结论

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-03.json)
- [环境私有定义](../../tasks/private/DSB-03.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-03.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
