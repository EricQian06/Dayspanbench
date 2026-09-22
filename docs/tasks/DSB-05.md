# DSB-05 · 制造采购：28天耐久测试后重新询价

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：制造供应链。开始：2026-11-03 Tue 14:00；截止：2026-12-08 Tue 15:00（北京时间）。

参考轨迹历时：**34天（816小时）**。结果类别：`resolved`。

跨度设计：中长期；28天耐久性测试、周审和过期报价更新。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

询问棱川制造500件M26规格产品的有效总报价、最小订单量、最早出库时间，并取得Q7质检结果。报告完成时仍需有效报价，预算19000元；不要下单。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "quantity": 500,
  "spec": "M26-Q7"
}
```

初始联系人：sales

## 时间机制

- 六天工厂日历与五天销售日历
- 28天耐久测试与周一批次
- 报价过期
- 并行查询后再次联系

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 棱川制造销售·罗岑 (`sales`)

角色：批次报价。初次报价有有效期；质检完成后若已过期，需重新确认。

[独立角色配置](../../tasks/actors/DSB-05/sales.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是棱川制造销售·罗岑，负责批次报价。初次报价有有效期；质检完成后若已过期，需重新确认。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：quote_new、quote_old

**流程：初次报价** (`main`)

必须提供：quantity、spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 整理批次需求<br>`sales.main.1.lookup` | 60工作分钟 | 读取本地事实： |
| 内部转交<br>`sales.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：factory/main、仅传递字段：quantity, spec |
| 查询业务记录<br>`sales.main.3.lookup` | 120工作分钟 | 读取本地事实：quote_old |
| 签发书面确认<br>`sales.main.4.document` | 60工作分钟 | 签发文本证据：quote_old |
| 向请求者回复已取得的结果<br>`sales.main.5.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：刷新过期报价** (`refresh`)

必须提供：quantity、spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`sales.refresh.1.lookup` | 60工作分钟；不早于2026-12-07 Mon 10:00（北京时间） | 读取本地事实：quote_new |
| 签发书面确认<br>`sales.refresh.2.document` | 0工作分钟 | 签发文本证据：quote_new |
| 向请求者回复已取得的结果<br>`sales.refresh.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 棱川制造排产员·苏渝 (`factory`)

角色：原料与排产核对。工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时。

[独立角色配置](../../tasks/actors/DSB-05/factory.json) · 日历 `factory` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六 · 时段：08:30—12:00 / 13:00—17:30

接收者约束：你是棱川制造排产员·苏渝，负责原料与排产核对。工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：dispatch、moq

**流程：排产可行性** (`main`)

必须提供：quantity、spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`factory.main.1.lookup` | 1440工作分钟 | 读取本地事实：moq、dispatch |
| 向请求者回复已取得的结果<br>`factory.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 棱川制造质检·傅黎 (`qa`)

角色：材料检测报告。样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。

[独立角色配置](../../tasks/actors/DSB-05/qa.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是棱川制造质检·傅黎，负责材料检测报告。样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：qa

**流程：材料Q7报告** (`main`)

必须提供：spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 28天耐久性测试<br>`qa.main.1.lookup` | 连续40320分钟（不停夜间/周末） | 读取本地事实： |
| 查询业务记录<br>`qa.main.2.lookup` | 下一次周一 10:00批次，随后120工作分钟 | 读取本地事实：qa |
| 签发书面确认<br>`qa.main.3.document` | 0工作分钟 | 签发文本证据：qa |
| 向请求者回复已取得的结果<br>`qa.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `quote_old` | `18000` | 500件批次旧报价18000元，有效至11月10日16点。 有效至2026-11-10 Tue 16:00。 |
| `quote_new` | `18600` | 500件批次重新确认的总报价18600元，有效至12月8日16点。 有效至2026-12-08 Tue 16:00。 |
| `moq` | `500` | 该规格最小订单量为500件。 |
| `dispatch` | `"2026-12-09"` | 如按有效报价下单，最早可于12月9日出库；本次尚未下单。 |
| `qa` | `true` | 材料M26批次符合用户要求的Q7检测规范，报告已复核。 |

目标结论：`within_budget_with_current_quote`。

```json
[
  {
    "key": "current_total",
    "expected": 18600,
    "accepted_facts": [
      "quote_new"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-05",
        "case": {
          "quantity": 500,
          "spec": "M26-Q7"
        }
      },
      "predicate": "current_total",
      "authorities": [
        "attest:current_total"
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
    "key": "minimum_quantity",
    "expected": 500,
    "accepted_facts": [
      "moq"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-05",
        "case": {
          "quantity": 500,
          "spec": "M26-Q7"
        }
      },
      "predicate": "minimum_quantity",
      "authorities": [
        "attest:minimum_quantity"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "件": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "件": 1
      }
    },
    "match": "expected"
  },
  {
    "key": "earliest_dispatch",
    "expected": "2026-12-09",
    "accepted_facts": [
      "dispatch"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-05",
        "case": {
          "quantity": 500,
          "spec": "M26-Q7"
        }
      },
      "predicate": "earliest_dispatch",
      "authorities": [
        "attest:earliest_dispatch"
      ],
      "normalization": {
        "type": "date"
      }
    },
    "normalization": {
      "type": "date"
    },
    "match": "expected"
  },
  {
    "key": "qa_pass",
    "expected": true,
    "accepted_facts": [
      "qa"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-05",
        "case": {
          "quantity": 500,
          "spec": "M26-Q7"
        }
      },
      "predicate": "qa_pass",
      "authorities": [
        "attest:qa_pass"
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
| 2026-11-03 Tue 14:00 | 2026-11-03 Tue 15:00 | 棱川制造销售·罗岑 | 整理批次需求 |
| 2026-11-03 Tue 14:00 | 2026-12-01 Tue 14:00 | 棱川制造质检·傅黎 | 28天耐久性测试 |
| 2026-11-03 Tue 15:00 | 2026-11-03 Tue 16:00 | 棱川制造销售·罗岑 | 内部转交 |
| 2026-11-03 Tue 16:00 | 2026-11-06 Fri 16:00 | 棱川制造排产员·苏渝 | 查询业务记录 |
| 2026-11-06 Fri 16:00 | 2026-11-06 Fri 16:00 | 棱川制造排产员·苏渝 | 向请求者回复已取得的结果 |
| 2026-11-06 Fri 16:00 | 2026-11-09 Mon 10:00 | 棱川制造销售·罗岑 | 查询业务记录 |
| 2026-11-09 Mon 10:00 | 2026-11-09 Mon 11:00 | 棱川制造销售·罗岑 | 签发书面确认 |
| 2026-11-09 Mon 11:00 | 2026-11-09 Mon 11:00 | 棱川制造销售·罗岑 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 10:00 | 2026-12-07 Mon 12:00 | 棱川制造质检·傅黎 | 查询业务记录 |
| 2026-12-07 Mon 13:00 | 2026-12-07 Mon 13:00 | 棱川制造质检·傅黎 | 签发书面确认 |
| 2026-12-07 Mon 13:00 | 2026-12-07 Mon 13:00 | 棱川制造质检·傅黎 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 13:00 | 2026-12-07 Mon 14:00 | 棱川制造销售·罗岑 | 查询业务记录 |
| 2026-12-07 Mon 14:00 | 2026-12-07 Mon 14:00 | 棱川制造销售·罗岑 | 签发书面确认 |
| 2026-12-07 Mon 14:00 | 2026-12-07 Mon 14:00 | 棱川制造销售·罗岑 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-09 Mon 11:00：棱川制造销售·罗岑，`reply`，4条文本证据。
- 2026-12-07 Mon 13:00：棱川制造质检·傅黎，`reply`，2条文本证据。
- 2026-12-07 Mon 14:00：棱川制造销售·罗岑，`reply`，2条文本证据。

## 易错点

- 用18000元旧报价给结论
- 等待质检期间不追踪有效期
- 误以为查询等于下单

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-05.json)
- [环境私有定义](../../tasks/private/DSB-05.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-05.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
