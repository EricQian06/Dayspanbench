# DSB-12 · 跨境原型设备：300天内的初审、二次补件与未决放行

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：跨境设备争议核查。开始：2026-11-06 Fri 15:00；截止：2027-09-02 Thu 15:00（北京时间）。

参考轨迹历时：**300天（7200小时）**。结果类别：`bounded_unresolved`。

跨度设计：长期；原型设备归类争议、第二轮补件和未决技术复核。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

跟进因归类争议留置的科研原型设备PK-608，到2027年9月2日15点汇报。核实历史入库交接、取得初审登记号，按要求向出口方取得有效新版单证和制造批次溯源资料，再发起长期复核。若放行未确认，明确已完成步骤与仍待确认事项。不要把历史入库、初审登记或补件受理当成当前放行；不支付费用或作法律承诺。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "tracking": "PK-608"
}
```

初始联系人：forwarder

## 时间机制

- 跨年度多轮事项
- 定期归类初审窗口
- 旧单证过期与跨人物证据更新
- 制造档案恢复后的第二轮补件
- 纽约夏令时切换
- 300天截止仍早于技术复核窗口

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 远澄货运客服·白榆 (`forwarder`)

角色：货件入库信息。只能确认入库并提供申报联络入口，不把入库状态说成放行。

[独立角色配置](../../tasks/actors/DSB-12/forwarder.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是远澄货运客服·白榆，负责货件入库信息。只能确认入库并提供申报联络入口，不把入库状态说成放行。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：货件状态与联系入口** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`forwarder.main.1.delegate` | 60工作分钟 | 内部转交并等待返回：warehouse/main、仅传递字段：tracking |
| 查询联系人目录并转介<br>`forwarder.main.2.refer` | 30工作分钟 | 公开转介联系人：exporter、customsdesk |
| 向请求者回复已取得的结果<br>`forwarder.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 始发仓查件员·施瑾 (`warehouse`)

角色：仓内扫描核对。周末无人工查件；核对后出具扫描记录。

[独立角色配置](../../tasks/actors/DSB-12/warehouse.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是始发仓查件员·施瑾，负责仓内扫描核对。周末无人工查件；核对后出具扫描记录。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：warehouse

**流程：入库扫描查证** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`warehouse.main.1.lookup` | 120工作分钟 | 读取本地事实：warehouse |
| 签发书面确认<br>`warehouse.main.2.document` | 60工作分钟 | 签发文本证据：warehouse |
| 向请求者回复已取得的结果<br>`warehouse.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 出口方单证员·贺悠 (`exporter`)

角色：更正单证与制造批次溯源。首轮更正资料12月7日可核验；取得归类初审登记后，2027年4月6日恢复的制造档案才能用于第二轮单证与批次溯源。

[独立角色配置](../../tasks/actors/DSB-12/exporter.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是出口方单证员·贺悠，负责更正单证与制造批次溯源。首轮更正资料12月7日可核验；取得归类初审登记后，2027年4月6日恢复的制造档案才能用于第二轮单证与批次溯源。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：batch_trace、declaration、declaration_latest

**流程：首轮更正单证** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`exporter.main.1.lookup` | 120工作分钟；不早于2026-12-07 Mon 10:00（北京时间） | 读取本地事实：declaration |
| 签发书面确认<br>`exporter.main.2.document` | 60工作分钟 | 签发文本证据：declaration |
| 向请求者回复已取得的结果<br>`exporter.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：第二轮单证和批次溯源** (`refresh`)

必须提供：tracking、review_reference

证据门槛：{"review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`exporter.refresh.1.lookup` | 120工作分钟；不早于2027-04-06 Tue 10:00（北京时间） | 读取本地事实：declaration_latest、batch_trace |
| 签发书面确认<br>`exporter.refresh.2.document` | 60工作分钟 | 签发文本证据：declaration_latest、batch_trace |
| 向请求者回复已取得的结果<br>`exporter.refresh.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 远澄单证联络·戴筠 (`customsdesk`)

角色：设备留置核查联络。原型设备因归类争议留置。初审登记后须用新版单证和溯源资料重新提交长期复核；旧单证过期后不能继续受理；任何登记都不是放行。

[独立角色配置](../../tasks/actors/DSB-12/customsdesk.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是远澄单证联络·戴筠，负责设备留置核查联络。原型设备因归类争议留置。初审登记后须用新版单证和溯源资料重新提交长期复核；旧单证过期后不能继续受理；任何登记都不是放行。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：归类初审登记** (`main`)

必须提供：tracking、declaration_version

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration", "authorities": ["attest:declaration"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`customsdesk.main.1.delegate` | 60工作分钟 | 内部转交并等待返回：broker/preliminary、仅传递字段：tracking, declaration_version |
| 向请求者回复已取得的结果<br>`customsdesk.main.2.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：第二轮长期复核** (`final`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`customsdesk.final.1.delegate` | 60工作分钟 | 内部转交并等待返回：broker/main、仅传递字段：tracking, declaration_version, review_reference, batch_trace |
| 向请求者回复已取得的结果<br>`customsdesk.final.2.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：材料齐备后转介境外代理直联** (`direct_entry`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询联系人目录并转介<br>`customsdesk.direct_entry.1.refer` | 60工作分钟 | 公开转介联系人：broker |
| 向请求者回复已取得的结果<br>`customsdesk.direct_entry.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 境外代理·Morgan Lee (`broker`)

角色：原型设备归类与技术意见复核。纽约工作日办公；初审窗口2027年2月4日，技术意见集中复核窗口9月10日。需补齐制造档案再受理；不是持续工作数月，也没有放行承诺。

[独立角色配置](../../tasks/actors/DSB-12/broker.json) · 日历 `new_york` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：你是境外代理·Morgan Lee，负责原型设备归类与技术意见复核。纽约工作日办公；初审窗口2027年2月4日，技术意见集中复核窗口9月10日。需补齐制造档案再受理；不是持续工作数月，也没有放行承诺。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：release、review_case

**流程：归类初审** (`preliminary`)

必须提供：tracking、declaration_version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`broker.preliminary.1.lookup` | 120工作分钟；不早于2027-02-04 Thu 22:00（北京时间） | 读取本地事实：review_case |
| 签发书面确认<br>`broker.preliminary.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：review_case |
| 向请求者回复已取得的结果<br>`broker.preliminary.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：长期技术复核** (`main`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`broker.main.1.lookup` | 1440工作分钟；不早于2027-09-10 Fri 21:00（北京时间） | 读取本地事实：release |
| 签发书面确认<br>`broker.main.2.document` | 0工作分钟 | 签发文本证据：release |
| 向请求者回复已取得的结果<br>`broker.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `warehouse` | `"2026年11月已完成始发仓入库扫描"` | PK-608的2026年11月始发仓入库记录已核实；这是历史交接记录，不能据此推断目前仍在始发仓或已获放行。 |
| `declaration` | `"DEC-608-v2"` | 已补发首轮DEC-608-v2资料，仅用于初审；作为继续受理凭证有效至2027年3月31日17点。 有效至2027-03-31 Wed 17:00。 |
| `review_case` | `"HOLD-608-9"` | 境外原型设备归类初审登记号为HOLD-608-9；须取得制造批次溯源材料和新版单证后再次发起长期复核。登记不等于放行。 |
| `declaration_latest` | `"DEC-608-v3"` | 2027年4月6日补发DEC-608-v3，取代v2；作为继续受理凭证有效至2027年9月30日17点。 有效至2027-09-30 Thu 17:00。 |
| `batch_trace` | `"TRACE-M608-2027"` | 制造方历史批次记录已恢复核验，溯源资料号TRACE-M608-2027。 |
| `release` | `"技术复核结果已返回，实际放行仍需另行确认"` | 2027年9月中旬技术复核窗口处理完成后，仅返回技术意见；该未来结果在本题截止前不可见。 |

目标结论：`release_unconfirmed_at_deadline`。

```json
[
  {
    "key": "initial_warehouse_record",
    "expected": "2026年11月已完成始发仓入库扫描",
    "accepted_facts": [
      "warehouse"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-12",
        "case": {
          "tracking": "PK-608"
        }
      },
      "predicate": "initial_warehouse_record",
      "authorities": [
        "attest:initial_warehouse_record"
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
    "key": "review_reference",
    "expected": "HOLD-608-9",
    "accepted_facts": [
      "review_case"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-12",
        "case": {
          "tracking": "PK-608"
        }
      },
      "predicate": "review_reference",
      "authorities": [
        "attest:review_reference"
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
    "match": "evidence"
  },
  {
    "key": "declaration_version",
    "expected": "DEC-608-v3",
    "accepted_facts": [
      "declaration_latest"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-12",
        "case": {
          "tracking": "PK-608"
        }
      },
      "predicate": "declaration_version",
      "authorities": [
        "attest:declaration_version"
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
    "match": "evidence"
  },
  {
    "key": "batch_trace",
    "expected": "TRACE-M608-2027",
    "accepted_facts": [
      "batch_trace"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-12",
        "case": {
          "tracking": "PK-608"
        }
      },
      "predicate": "batch_trace",
      "authorities": [
        "attest:batch_trace"
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
    "match": "evidence"
  },
  {
    "key": "release_status",
    "status": "unconfirmed",
    "pending_condition": {
      "capability": "technical_review",
      "fields_equal": {
        "tracking": "PK-608"
      },
      "required_evidence": [
        {
          "subject": {
            "task": "DSB-12",
            "case": {
              "tracking": "PK-608"
            }
          },
          "predicate": "declaration_version",
          "authorities": [
            "attest:declaration_version"
          ],
          "normalization": {
            "type": "text",
            "aliases": {}
          }
        },
        {
          "subject": {
            "task": "DSB-12",
            "case": {
              "tracking": "PK-608"
            }
          },
          "predicate": "review_reference",
          "authorities": [
            "attest:review_reference"
          ],
          "normalization": {
            "type": "text",
            "aliases": {}
          }
        },
        {
          "subject": {
            "task": "DSB-12",
            "case": {
              "tracking": "PK-608"
            }
          },
          "predicate": "batch_trace",
          "authorities": [
            "attest:batch_trace"
          ],
          "normalization": {
            "type": "text",
            "aliases": {}
          }
        }
      ]
    }
  }
]
```

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-06 Fri 15:37 | 2026-11-06 Fri 16:54 | 远澄货运客服·白榆 | 内部转交 |
| 2026-11-06 Fri 16:54 | 2026-11-09 Mon 11:12 | 始发仓查件员·施瑾 | 查询业务记录 |
| 2026-11-09 Mon 11:12 | 2026-11-09 Mon 13:18 | 始发仓查件员·施瑾 | 签发书面确认 |
| 2026-11-09 Mon 13:18 | 2026-11-09 Mon 13:33 | 始发仓查件员·施瑾 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 13:33 | 2026-11-09 Mon 14:16 | 远澄货运客服·白榆 | 查询联系人目录并转介 |
| 2026-11-09 Mon 14:16 | 2026-11-09 Mon 14:31 | 远澄货运客服·白榆 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 10:00 | 2026-12-07 Mon 13:21 | 出口方单证员·贺悠 | 查询业务记录 |
| 2026-12-07 Mon 13:21 | 2026-12-07 Mon 14:41 | 出口方单证员·贺悠 | 签发书面确认 |
| 2026-12-07 Mon 14:41 | 2026-12-07 Mon 14:56 | 出口方单证员·贺悠 | 向请求者回复已取得的结果 |
| 2026-12-07 Mon 15:18 | 2026-12-07 Mon 16:32 | 远澄单证联络·戴筠 | 内部转交 |
| 2027-02-04 Thu 22:00 | 2027-02-05 Fri 00:20 | 境外代理·Morgan Lee | 查询业务记录 |
| 2027-02-05 Fri 00:20 | 2027-02-05 Fri 00:35 | 境外代理·Morgan Lee | 签发书面确认 |
| 2027-02-05 Fri 00:35 | 2027-02-05 Fri 00:50 | 境外代理·Morgan Lee | 向请求者回复已取得的结果 |
| 2027-02-05 Fri 09:00 | 2027-02-05 Fri 09:46 | 远澄单证联络·戴筠 | 向请求者回复已取得的结果 |
| 2027-04-06 Tue 10:00 | 2027-04-06 Tue 13:11 | 出口方单证员·贺悠 | 查询业务记录 |
| 2027-04-06 Tue 13:11 | 2027-04-06 Tue 14:32 | 出口方单证员·贺悠 | 签发书面确认 |
| 2027-04-06 Tue 14:32 | 2027-04-06 Tue 14:47 | 出口方单证员·贺悠 | 向请求者回复已取得的结果 |
| 2027-04-06 Tue 15:01 | 2027-04-06 Tue 16:15 | 远澄单证联络·戴筠 | 内部转交 |
| 2027-09-10 Fri 21:00 | 2027-09-15 Wed 21:09 | 境外代理·Morgan Lee | 查询业务记录 |

Agent收到的实质回复：

- 2026-11-09 Mon 14:31：远澄货运客服·白榆，`reply`，2条文本证据。
- 2026-12-07 Mon 14:56：出口方单证员·贺悠，`reply`，2条文本证据。
- 2027-02-05 Fri 09:46：远澄单证联络·戴筠，`reply`，2条文本证据。
- 2027-04-06 Tue 14:47：出口方单证员·贺悠，`reply`，4条文本证据。

截止时仍在等待：

- customsdesk / CASE-0007：`waiting_internal`。
- broker / CASE-0008：`queued`。

## 易错点

- 只发一条查询后等待300天
- 拿旧单证或初审登记跳过第二轮补件
- 把历史仓库记录当当前货位
- 受理回执或未来技术意见当放行证明

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-12.json)
- [环境私有定义](../../tasks/private/DSB-12.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-12.json)

两条合法路径：由单证联络人内部转交，或材料核验后取得转介并直接联系境外代理。按同一复核能力、受理凭证和截止状态评分，不绑定人物ID或中间转交层数。
