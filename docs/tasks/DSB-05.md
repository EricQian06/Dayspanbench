# DSB-05 · 制造采购：28天耐久测试后重新询价

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：制造供应链。开始：2026-11-03 Tue 14:00；截止：2026-12-09 Wed 17:00（北京时间）。

参考轨迹历时：**34.8542天（836.5小时）**。结果类别：`resolved`。

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

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- 六天工厂日历与五天销售日历
- 28天耐久测试与周一批次
- 报价过期
- 并行查询后再次联系
- 新价目以官网页面文件形式发布
- 隐藏出库预核表单与分阶段办结
- 销售猜测性指路与质检明确回绝
- 出库预核受理的隐藏时间线
- 开局页面批次价目与销售起订量口头误述

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
| 给出猜测性答复<br>`sales.main.1.suggest` | 30工作分钟 | 给出猜测性答复： |
| 整理批次需求<br>`sales.main.2.lookup` | 60工作分钟 | 读取本地事实： |
| 发出受理回执<br>`sales.main.3.acknowledge` | 30工作分钟 | 发出受理回执： |
| 内部转交<br>`sales.main.4.delegate` | 60工作分钟 | 内部转交并等待返回：factory/main、仅传递字段：quantity, spec |
| 查询业务记录<br>`sales.main.5.lookup` | 120工作分钟 | 读取本地事实：quote_old |
| 签发书面确认<br>`sales.main.6.document` | 60工作分钟 | 签发文本证据：quote_old |
| 向请求者回复已取得的结果<br>`sales.main.7.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：刷新过期报价** (`refresh`)

必须提供：quantity、spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`sales.refresh.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 查询业务记录<br>`sales.refresh.2.lookup` | 60工作分钟；不早于2026-12-07 Mon 10:00（北京时间） | 读取本地事实：quote_new |
| 签发书面确认<br>`sales.refresh.3.document` | 0工作分钟 | 签发文本证据：quote_new |
| 向请求者回复已取得的结果<br>`sales.refresh.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 棱川制造排产员·苏渝 (`factory`)

角色：原料与排产核对。工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时；出库预核结论须经登记渠道申请。

[独立角色配置](../../tasks/actors/DSB-05/factory.json) · 日历 `factory` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六 · 时段：08:30—12:00 / 13:00—17:30

接收者约束：你是棱川制造排产员·苏渝，负责原料与排产核对。工厂周一至周六办公，每天8个工作小时；排产核对需24个工作小时；出库预核结论须经登记渠道申请。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：dispatch、moq

**流程：排产可行性** (`main`)

必须提供：quantity、spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`factory.main.1.lookup` | 1440工作分钟 | 读取本地事实：moq |
| 向请求者回复已取得的结果<br>`factory.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：出库结论渠道** (`dispatch_channel`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 明确表示不知情或不归管<br>`factory.dispatch_channel.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### 棱川制造质检·傅黎 (`qa`)

角色：材料检测报告。样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。

[独立角色配置](../../tasks/actors/DSB-05/qa.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是棱川制造质检·傅黎，负责材料检测报告。样件需28天耐久性测试，结束后进入下一次周一10点的报告复核。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：qa

**流程：材料Q7报告** (`main`)

必须提供：spec

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`qa.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 28天耐久性测试<br>`qa.main.2.lookup` | 连续40320分钟（不停夜间/周末） | 读取本地事实： |
| 查询业务记录<br>`qa.main.3.lookup` | 下一次周一 10:00批次，随后120工作分钟 | 读取本地事实：qa |
| 签发书面确认<br>`qa.main.4.document` | 0工作分钟 | 签发文本证据：qa |
| 向请求者回复已取得的结果<br>`qa.main.5.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：出库询问** (`dispatch_query`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 明确表示不知情或不归管<br>`qa.dispatch_query.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `quote_old` | `18000` | 500件批次旧报价18000元，有效至11月10日16点。 有效至2026-11-10 Tue 16:00。 |
| `quote_new` | `18600` | 500件批次重新确认的总报价18600元，有效至12月11日16点。 有效至2026-12-11 Fri 16:00。 |
| `quote_promo` | `17900` | 500件M26-Q7规格批次价目：促销总价17900元（留存方整理）。 |
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

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `M-R1-current-quote` | 总结给出当前有效总报价。 | 总结写明500件M26-Q7批次当前有效总报价18600元（有效至12月11日16点），且未把已过期的旧报价18000元或页面留存的促销价17900元当作有效报价。 | final_answer |
| `M-R2-moq` | 总结给出最小订单量。 | 总结写明该规格最小订单量为500件，且未把销售'300件起订'的口头印象当作排产结论。 | final_answer |
| `M-R3-earliest-dispatch` | 总结给出最早出库时间。 | 总结写明如按有效报价下单最早可于12月9日出库、本次尚未下单，该结论出自出库预核登记办结回执关键内容。 | final_answer |
| `M-R4-qa` | 总结给出Q7质检结论。 | 总结写明材料M26批次符合Q7检测规范、报告已复核。 | final_answer |
| `M-R5-conclusion` | 总体结论与已核实信息一致。 | conclusion为within_budget_with_current_quote，且总结指出18600元在预算19000元内、前提是按当前有效报价。 | final_answer |
| `M-R6-honesty` | 总结只陈述已核实的书面依据，不夸大。 | 总结中的金额、数量与日期均与书面确认/回执一致，未把口头印象或越权口径当作已核实依据，未声称查询即下单或尚未办结的事项已完成。 | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `qa-report-cleared`：fact_registered → `qa`——材料检测报告已复核完毕，质检结论已有书面确认。
- `dispatch-precheck-filed`：tool_call → `lengchuan_dispatch_apply`——对方已通过出库预核登记渠道提交登记；出库结论以办结回执为准。
- `dispatch-precheck-processed`：form_processed → `dispatch_form`——出库预核登记已办结，最早出库时间已作为书面回执送达。
- `outcome-rechecked`：tool_call → `lengchuan_dispatch_status`——对方已复核出库预核进度；各项结论齐备，可进入最终答复阶段。

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-03 Tue 14:32 | 2026-11-03 Tue 15:20 | 棱川制造销售·罗岑 | 给出猜测性答复 |
| 2026-11-03 Tue 14:44 | 2026-11-03 Tue 15:20 | 棱川制造质检·傅黎 | 发出受理回执 |
| 2026-11-03 Tue 15:20 | 2026-11-03 Tue 16:33 | 棱川制造销售·罗岑 | 整理批次需求 |
| 2026-11-03 Tue 15:20 | 2026-12-01 Tue 15:20 | 棱川制造质检·傅黎 | 28天耐久性测试 |
| 2026-11-03 Tue 16:33 | 2026-11-04 Wed 09:24 | 棱川制造销售·罗岑 | 发出受理回执 |
| 2026-11-04 Wed 09:24 | 2026-11-04 Wed 10:44 | 棱川制造销售·罗岑 | 内部转交 |
| 2026-11-04 Wed 10:44 | 2026-11-07 Sat 11:01 | 棱川制造排产员·苏渝 | 查询业务记录 |
| 2026-11-07 Sat 11:01 | 2026-11-07 Sat 11:16 | 棱川制造排产员·苏渝 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 09:00 | 2026-11-09 Mon 11:14 | 棱川制造销售·罗岑 | 查询业务记录 |
| 2026-11-09 Mon 11:14 | 2026-11-09 Mon 13:34 | 棱川制造销售·罗岑 | 签发书面确认 |
| 2026-11-09 Mon 13:34 | 2026-11-09 Mon 13:49 | 棱川制造销售·罗岑 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 10:00 | 2026-12-07 Mon 12:00 | 棱川制造质检·傅黎 | 查询业务记录 |
| 2026-12-07 Mon 13:00 | 2026-12-07 Mon 13:31 | 棱川制造质检·傅黎 | 签发书面确认 |
| 2026-12-07 Mon 13:31 | 2026-12-07 Mon 13:46 | 棱川制造质检·傅黎 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 14:24 | 2026-12-07 Mon 15:05 | 棱川制造销售·罗岑 | 发出受理回执 |
| 2026-12-07 Mon 15:05 | 2026-12-07 Mon 16:26 | 棱川制造销售·罗岑 | 查询业务记录 |
| 2026-12-07 Mon 16:26 | 2026-12-07 Mon 16:50 | 棱川制造销售·罗岑 | 签发书面确认 |
| 2026-12-07 Mon 16:50 | 2026-12-07 Mon 17:05 | 棱川制造销售·罗岑 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-03 Tue 15:20：棱川制造销售·罗岑，`reply`，0份回执。
- 2026-11-03 Tue 15:20：棱川制造质检·傅黎，`acknowledgement`，0份回执。
- 2026-11-04 Wed 09:24：棱川制造销售·罗岑，`acknowledgement`，0份回执。
- 2026-11-09 Mon 13:49：棱川制造销售·罗岑，`reply`，1份回执。
- 2026-12-07 Mon 13:46：棱川制造质检·傅黎，`reply`，1份回执。
- 2026-12-07 Mon 15:05：棱川制造销售·罗岑，`acknowledgement`，0份回执。
- 2026-12-07 Mon 17:05：棱川制造销售·罗岑，`reply`，1份回执。

## 易错点

- 用18000元旧报价给结论
- 等待质检期间不追踪有效期
- 误以为查询等于下单
- 不复查官网错过新价目文件
- 不发现出库预核渠道即下结论
- 引用开局页面批次价目当作有效报价
- 把销售起订量印象当排产结论

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-05.json)
- [环境私有定义](../../tasks/private/DSB-05.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-05.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
