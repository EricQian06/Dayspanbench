# DSB-01 · 活动场地：跨周末确认设备与报价

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：活动服务。开始：2026-11-06 Fri 10:00；截止：2026-11-10 Tue 18:00（北京时间）。

参考轨迹历时：**3天（72小时）**。结果类别：`resolved`。

跨度设计：短期；周末关门与设备内部转交。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

请核实禾岸会馆能否在11月13日18—21点接待80人，预算12000元，必须有投影。问清总费用、取消条款、档期和投影是否可用，附可核实的书面依据。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "event_date": "2026-11-13",
  "event_time": "18:00-21:00",
  "headcount": 80
}
```

初始联系人：reception

## 时间机制

- 周末停办
- 并行询价与设备确认
- 跨岗位内部转交
- 过时网页与当前事实冲突

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 禾岸会馆前台·陈芷 (`reception`)

角色：对外咨询与转介。只掌握联系人目录；不能承诺报价、档期或设备。

[独立角色配置](../../tasks/actors/DSB-01/reception.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是禾岸会馆前台·陈芷，负责对外咨询与转介。只掌握联系人目录；不能承诺报价、档期或设备。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：活动联系入口** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询联系人目录并转介<br>`reception.main.1.refer` | 30工作分钟 | 公开转介联系人：sales、operations |
| 向请求者回复已取得的结果<br>`reception.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 禾岸会馆销售·姚岚 (`sales`)

角色：费用与取消条款。报价必须带日期和人数；设备可用性需要运营确认。

[独立角色配置](../../tasks/actors/DSB-01/sales.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是禾岸会馆销售·姚岚，负责费用与取消条款。报价必须带日期和人数；设备可用性需要运营确认。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：cancel、price

**流程：报价及取消条件** (`main`)

必须提供：event_date、headcount

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`sales.main.1.lookup` | 180工作分钟 | 读取本地事实：price、cancel |
| 签发书面确认<br>`sales.main.2.document` | 30工作分钟 | 签发文本证据：price、cancel |
| 向请求者回复已取得的结果<br>`sales.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 禾岸会馆运营·赵航 (`operations`)

角色：档期核对和设备协调。能够查档期；投影问题必须转给设备负责人。

[独立角色配置](../../tasks/actors/DSB-01/operations.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是禾岸会馆运营·赵航，负责档期核对和设备协调。能够查档期；投影问题必须转给设备负责人。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：slot

**流程：档期与投影确认** (`main`)

必须提供：event_date、event_time

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`operations.main.1.lookup` | 60工作分钟 | 读取本地事实：slot |
| 内部转交<br>`operations.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：technician/main、仅传递字段：event_date, event_time |
| 向请求者回复已取得的结果<br>`operations.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

### 禾岸会馆设备主管·周敏 (`technician`)

角色：设备维修计划。只有本岗位知道维修窗口；内部收到转交后进入自己的队列。

[独立角色配置](../../tasks/actors/DSB-01/technician.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是禾岸会馆设备主管·周敏，负责设备维修计划。只有本岗位知道维修窗口；内部收到转交后进入自己的队列。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：projector

**流程：核对维修窗口** (`main`)

必须提供：event_date

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`technician.main.1.lookup` | 240工作分钟 | 读取本地事实：projector |
| 签发书面确认<br>`technician.main.2.document` | 0工作分钟 | 签发文本证据：projector |
| 向请求者回复已取得的结果<br>`technician.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `price` | `10500` | 11月13日18—21点，80人活动：场租9000元、服务费1500元，总价10500元。 |
| `cancel` | `"72小时内取消收取50%"` | 活动前72小时内取消收取总价的50%。 |
| `slot` | `true` | 11月13日18—21点场地有空档，80人容量可满足。 |
| `projector` | `false` | 投影设备11月13日全天维修，场地方也不能提供替代投影设备。 |

目标结论：`unsuitable`。

```json
[
  {
    "key": "total_cost",
    "expected": 10500,
    "accepted_facts": [
      "price"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "total_cost",
      "authorities": [
        "attest:total_cost"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "元": 1,
          "CNY": 1,
          "人民币": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "元": 1,
        "CNY": 1,
        "人民币": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "cancellation",
    "expected": "72小时内取消收取50%",
    "accepted_facts": [
      "cancel"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "cancellation",
      "authorities": [
        "attest:cancellation"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "72小时内取消收取50%": [
            "三天内取消收取一半费用",
            "72小时内取消需支付50%的费用"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "72小时内取消收取50%": [
          "三天内取消收取一半费用",
          "72小时内取消需支付50%的费用"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "slot_available",
    "expected": true,
    "accepted_facts": [
      "slot"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "slot_available",
      "authorities": [
        "attest:slot_available"
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
    "key": "projector_available",
    "expected": false,
    "accepted_facts": [
      "projector"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-01",
        "case": {
          "event_date": "2026-11-13",
          "event_time": "18:00-21:00",
          "headcount": 80
        }
      },
      "predicate": "projector_available",
      "authorities": [
        "attest:projector_available"
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
| 2026-11-06 Fri 10:00 | 2026-11-06 Fri 10:30 | 禾岸会馆前台·陈芷 | 查询联系人目录并转介 |
| 2026-11-06 Fri 10:30 | 2026-11-06 Fri 10:30 | 禾岸会馆前台·陈芷 | 向请求者回复已取得的结果 |
| 2026-11-06 Fri 10:30 | 2026-11-06 Fri 14:30 | 禾岸会馆销售·姚岚 | 查询业务记录 |
| 2026-11-06 Fri 10:30 | 2026-11-06 Fri 11:30 | 禾岸会馆运营·赵航 | 查询业务记录 |
| 2026-11-06 Fri 11:30 | 2026-11-06 Fri 13:30 | 禾岸会馆运营·赵航 | 内部转交 |
| 2026-11-06 Fri 13:30 | 2026-11-09 Mon 09:30 | 禾岸会馆设备主管·周敏 | 查询业务记录 |
| 2026-11-06 Fri 14:30 | 2026-11-06 Fri 15:00 | 禾岸会馆销售·姚岚 | 签发书面确认 |
| 2026-11-06 Fri 15:00 | 2026-11-06 Fri 15:00 | 禾岸会馆销售·姚岚 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 09:30 | 2026-11-09 Mon 09:30 | 禾岸会馆设备主管·周敏 | 签发书面确认 |
| 2026-11-09 Mon 09:30 | 2026-11-09 Mon 09:30 | 禾岸会馆设备主管·周敏 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 09:30 | 2026-11-09 Mon 10:00 | 禾岸会馆运营·赵航 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-06 Fri 10:30：禾岸会馆前台·陈芷，`reply`，0条文本证据。
- 2026-11-06 Fri 15:00：禾岸会馆销售·姚岚，`reply`，4条文本证据。
- 2026-11-09 Mon 10:00：禾岸会馆运营·赵航，`reply`，3条文本证据。

## 易错点

- 将8000元起当作总价
- 未核实投影即判断适用
- 把内部转交受理当作完成

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-01.json)
- [环境私有定义](../../tasks/private/DSB-01.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-01.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
