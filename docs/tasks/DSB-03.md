# DSB-03 · 学分转换：秋季补件与春季集中审议

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：高校教务。开始：2026-11-05 Thu 14:00；截止：2027-02-03 Wed 17:00（北京时间）。

参考轨迹历时：**89.0444天（2137.07小时）**。结果类别：`resolved`。

跨度设计：中长期；秋季材料预审与春季学分委员会。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

确认CS204能转换多少学分、计入哪类课程、何时生效。我目前只有旧大纲，需要向课程负责人获取正式版本。请获得教务的书面结论，不提交正式选课变更。

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

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 澄川学院教务·唐宁 (`records`)

角色：学分转换预审。必须取得当前签章大纲；不能把旧大纲送交委员会。

[独立角色配置](../../tasks/actors/DSB-03/records.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是澄川学院教务·唐宁，负责学分转换预审。必须取得当前签章大纲；不能把旧大纲送交委员会。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：学分转换咨询** (`main`)

必须提供：course_code、syllabus_version

证据门槛：{"syllabus_version": {"subject": {"task": "DSB-03", "case": {"course_code": "CS204"}}, "predicate": "syllabus_version", "authorities": ["attest:syllabus_version"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 核验签章与材料版本<br>`records.main.1.lookup` | 180工作分钟 | 读取本地事实： |
| 发出受理回执<br>`records.main.2.acknowledge` | 60工作分钟 | 发出受理回执： |
| 内部转交<br>`records.main.3.delegate` | 60工作分钟 | 内部转交并等待返回：board/main、仅传递字段：course_code, syllabus_version |
| 向请求者回复已取得的结果<br>`records.main.4.reply` | 60工作分钟 | 向父事项/Agent回复： |

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

角色：春季跨校学分审议。跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审。

[独立角色配置](../../tasks/actors/DSB-03/board.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是澄川学院学分委员会秘书·程昕，负责春季跨校学分审议。跨校课程在2027年2月2日10点春季委员会集中审议，此前只做材料预审。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：credits、effective、scope

**流程：春季跨校审议** (`main`)

必须提供：course_code、syllabus_version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`board.main.1.lookup` | 下一次周二 10:00批次，随后120工作分钟；不早于2027-02-02 Tue 10:00（北京时间） | 读取本地事实：credits、scope、effective |
| 签发书面确认<br>`board.main.2.document` | 0工作分钟 | 签发文本证据：credits、scope、effective |
| 向请求者回复已取得的结果<br>`board.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `syllabus` | `"CS204-2026-v2-signed"` | CS204课程正式签章大纲版本为CS204-2026-v2-signed。 |
| `credits` | `3` | 学分委员会确认CS204可转换3学分。 |
| `scope` | `"专业选修"` | 这3学分仅计入专业选修，不能替代必修课。 |
| `effective` | `"2027春季"` | 该转换结论从2027春季学期开始适用。 |

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
        "aliases": {}
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {}
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
            "专业选修课"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "专业选修": [
          "专业选修课"
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
            "2027年春季学期"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "2027春季": [
          "2027年春季",
          "2027年春季学期"
        ]
      }
    },
    "match": "expected"
  }
]
```

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-10 Tue 09:00 | 2026-11-10 Tue 11:18 | CS204课程负责人·梅芮 | 查询业务记录 |
| 2026-11-10 Tue 11:18 | 2026-11-10 Tue 13:24 | CS204课程负责人·梅芮 | 签发书面确认 |
| 2026-11-10 Tue 13:24 | 2026-11-10 Tue 13:39 | CS204课程负责人·梅芮 | 向请求者回复已取得的结果 |
| 2026-11-10 Tue 16:12 | 2026-11-11 Wed 11:33 | 澄川学院教务·唐宁 | 核验签章与材料版本 |
| 2026-11-11 Wed 11:33 | 2026-11-11 Wed 13:53 | 澄川学院教务·唐宁 | 发出受理回执 |
| 2026-11-11 Wed 13:53 | 2026-11-11 Wed 15:10 | 澄川学院教务·唐宁 | 内部转交 |
| 2027-02-02 Tue 10:00 | 2027-02-02 Tue 12:00 | 澄川学院学分委员会秘书·程昕 | 查询业务记录 |
| 2027-02-02 Tue 13:00 | 2027-02-02 Tue 13:29 | 澄川学院学分委员会秘书·程昕 | 签发书面确认 |
| 2027-02-02 Tue 13:29 | 2027-02-02 Tue 13:44 | 澄川学院学分委员会秘书·程昕 | 向请求者回复已取得的结果 |
| 2027-02-02 Tue 13:44 | 2027-02-02 Tue 15:04 | 澄川学院教务·唐宁 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-06 Fri 09:48：澄川学院教务·唐宁，`needs_information`，0条文本证据。
- 2026-11-10 Tue 13:39：CS204课程负责人·梅芮，`reply`，2条文本证据。
- 2026-11-11 Wed 13:53：澄川学院教务·唐宁，`acknowledgement`，0条文本证据。
- 2027-02-02 Tue 15:04：澄川学院教务·唐宁，`reply`，6条文本证据。

## 易错点

- 猜测签章编号
- 沿用2024年旧材料
- 把材料预审当作春季批准

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-03.json)
- [环境私有定义](../../tasks/private/DSB-03.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-03.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
