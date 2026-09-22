# DSB-09 · 公共活动咨询：意见征集与年末联合复核

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：公共服务。开始：2026-11-03 Tue 15:00；截止：2026-12-29 Tue 17:00（北京时间）。

参考轨迹历时：**55.0319天（1320.77小时）**。结果类别：`resolved`。

跨度设计：中长期；30天征询及年末联合分类复核。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

为2027年1月晴港北广场的小型扩声活动询问主管机构、事项分类、应备材料和最早办理窗口。跟进意见征集并携回执再次申请联合复核。只做预咨询，不能写成已获许可；场景规则均为合成。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "location": "晴港北广场",
  "amplified": "使用两只扩声音箱"
}
```

初始联系人：service

## 时间机制

- 先管辖后专业咨询
- 30天跨部门征集期
- 携回执再次发起联合复核
- 跨年度后续办理窗口

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 晴港政务咨询台·谢茵 (`service`)

角色：事项识别与管辖分流。只能进行预咨询，不生成许可；先核实管辖再转专门岗位。

[独立角色配置](../../tasks/actors/DSB-09/service.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是晴港政务咨询台·谢茵，负责事项识别与管辖分流。只能进行预咨询，不生成许可；先核实管辖再转专门岗位。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：活动事项咨询** (`main`)

必须提供：location、amplified

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 登记咨询上下文<br>`service.main.1.lookup` | 60工作分钟 | 读取本地事实： |
| 内部转交<br>`service.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：land/main、仅传递字段：location |
| 查询联系人目录并转介<br>`service.main.3.refer` | 60工作分钟 | 公开转介联系人：sound |
| 向请求者回复已取得的结果<br>`service.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 公共空间管理联络员·吴弈 (`land`)

角色：场地管辖核对。每周四10点复核共享场地边界清单。

[独立角色配置](../../tasks/actors/DSB-09/land.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是公共空间管理联络员·吴弈，负责场地管辖核对。每周四10点复核共享场地边界清单。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：jurisdiction

**流程：管辖材料复核** (`main`)

必须提供：location

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`land.main.1.lookup` | 下一次周四 10:00批次，随后120工作分钟 | 读取本地事实：jurisdiction |
| 签发书面确认<br>`land.main.2.document` | 60工作分钟 | 签发文本证据：jurisdiction |
| 向请求者回复已取得的结果<br>`land.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 活动环境咨询员·陆笙 (`sound`)

角色：扩声事项分类和材料。本轮30天跨部门意见征集于12月3日汇总；申请人取得回执后须再次申请12月28日联合分类复核。

[独立角色配置](../../tasks/actors/DSB-09/sound.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是活动环境咨询员·陆笙，负责扩声事项分类和材料。本轮30天跨部门意见征集于12月3日汇总；申请人取得回执后须再次申请12月28日联合分类复核。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：category、consultation_receipt、documents、earliest

**流程：意见征集阶段确认** (`main`)

必须提供：location、amplified

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`sound.main.1.lookup` | 60工作分钟；不早于2026-12-03 Thu 09:00（北京时间） | 读取本地事实：consultation_receipt |
| 签发书面确认<br>`sound.main.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：consultation_receipt |
| 向请求者回复已取得的结果<br>`sound.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：联合分类复核** (`final`)

必须提供：location、amplified、consultation_receipt

证据门槛：{"consultation_receipt": {"subject": {"task": "DSB-09", "case": {"location": "晴港北广场", "amplified": "使用两只扩声音箱"}}, "predicate": "consultation_receipt", "authorities": ["attest:consultation_receipt"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`sound.final.1.lookup` | 240工作分钟；不早于2026-12-28 Mon 09:00（北京时间） | 读取本地事实：category、documents、earliest |
| 签发书面确认<br>`sound.final.2.document` | 60工作分钟 | 签发文本证据：category、documents、earliest |
| 向请求者回复已取得的结果<br>`sound.final.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `jurisdiction` | `"街区公共空间管理处"` | 拟用地点属于街区公共空间管理处管辖；不是私人场地。 |
| `category` | `"临时扩声活动预咨询"` | 拟议活动应按临时扩声活动进行预咨询分类，尚未受理正式申请。 |
| `documents` | `["平面图", "时段说明", "声设备清单"]` | 需要准备平面图、时段说明和声设备清单。 |
| `earliest` | `"2027-01-04"` | 按年度窗口安排，最早可进入后续正式办理的日期是2027年1月4日；不是活动批准日期。 |
| `consultation_receipt` | `"CONSULT-DEC03-19"` | 本轮30天跨部门意见征集已结束，回执CONSULT-DEC03-19；需携回执申请12月28日联合分类复核。 |

目标结论：`consultation_only_not_approval`。

```json
[
  {
    "key": "responsible_office",
    "expected": "街区公共空间管理处",
    "accepted_facts": [
      "jurisdiction"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-09",
        "case": {
          "location": "晴港北广场",
          "amplified": "使用两只扩声音箱"
        }
      },
      "predicate": "responsible_office",
      "authorities": [
        "attest:responsible_office"
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
    "key": "consultation_receipt",
    "expected": "CONSULT-DEC03-19",
    "accepted_facts": [
      "consultation_receipt"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-09",
        "case": {
          "location": "晴港北广场",
          "amplified": "使用两只扩声音箱"
        }
      },
      "predicate": "consultation_receipt",
      "authorities": [
        "attest:consultation_receipt"
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
    "key": "case_category",
    "expected": "临时扩声活动预咨询",
    "accepted_facts": [
      "category"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-09",
        "case": {
          "location": "晴港北广场",
          "amplified": "使用两只扩声音箱"
        }
      },
      "predicate": "case_category",
      "authorities": [
        "attest:case_category"
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
    "key": "required_documents",
    "expected": [
      "平面图",
      "时段说明",
      "声设备清单"
    ],
    "accepted_facts": [
      "documents"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-09",
        "case": {
          "location": "晴港北广场",
          "amplified": "使用两只扩声音箱"
        }
      },
      "predicate": "required_documents",
      "authorities": [
        "attest:required_documents"
      ],
      "normalization": {
        "type": "set"
      }
    },
    "normalization": {
      "type": "set"
    },
    "match": "expected"
  },
  {
    "key": "earliest_processing_date",
    "expected": "2027-01-04",
    "accepted_facts": [
      "earliest"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-09",
        "case": {
          "location": "晴港北广场",
          "amplified": "使用两只扩声音箱"
        }
      },
      "predicate": "earliest_processing_date",
      "authorities": [
        "attest:earliest_processing_date"
      ],
      "normalization": {
        "type": "date"
      }
    },
    "normalization": {
      "type": "date"
    },
    "match": "expected"
  }
]
```

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-03 Tue 15:37 | 2026-11-03 Tue 16:54 | 晴港政务咨询台·谢茵 | 登记咨询上下文 |
| 2026-11-03 Tue 16:54 | 2026-11-04 Wed 10:12 | 晴港政务咨询台·谢茵 | 内部转交 |
| 2026-11-05 Thu 10:00 | 2026-11-05 Thu 12:00 | 公共空间管理联络员·吴弈 | 查询业务记录 |
| 2026-11-05 Thu 13:00 | 2026-11-05 Thu 14:06 | 公共空间管理联络员·吴弈 | 签发书面确认 |
| 2026-11-05 Thu 14:06 | 2026-11-05 Thu 14:21 | 公共空间管理联络员·吴弈 | 向请求者回复已取得的结果 |
| 2026-11-05 Thu 14:21 | 2026-11-05 Thu 15:34 | 晴港政务咨询台·谢茵 | 查询联系人目录并转介 |
| 2026-11-05 Thu 15:34 | 2026-11-05 Thu 15:49 | 晴港政务咨询台·谢茵 | 向请求者回复已取得的结果 |
| 2026-12-03 Thu 09:00 | 2026-12-03 Thu 10:21 | 活动环境咨询员·陆笙 | 查询业务记录 |
| 2026-12-03 Thu 10:21 | 2026-12-03 Thu 10:36 | 活动环境咨询员·陆笙 | 签发书面确认 |
| 2026-12-03 Thu 10:36 | 2026-12-03 Thu 10:51 | 活动环境咨询员·陆笙 | 向请求者回复已取得的结果 |
| 2026-12-28 Mon 09:00 | 2026-12-28 Mon 14:17 | 活动环境咨询员·陆笙 | 查询业务记录 |
| 2026-12-28 Mon 14:17 | 2026-12-28 Mon 15:31 | 活动环境咨询员·陆笙 | 签发书面确认 |
| 2026-12-28 Mon 15:31 | 2026-12-28 Mon 15:46 | 活动环境咨询员·陆笙 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-05 Thu 15:49：晴港政务咨询台·谢茵，`reply`，2条文本证据。
- 2026-12-03 Thu 10:51：活动环境咨询员·陆笙，`reply`，2条文本证据。
- 2026-12-28 Mon 15:46：活动环境咨询员·陆笙，`reply`，6条文本证据。

## 易错点

- 咨询回执当许可证
- 没有回执即跳过征集
- 收到回执后不继续申请最终复核

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-09.json)
- [环境私有定义](../../tasks/private/DSB-09.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-09.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
