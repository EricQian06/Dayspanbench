# DSB-12 · Cross-border prototype equipment: preliminary review, second-round documents, and unresolved release within 300 days

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：Cross-border equipment dispute investigation。开始：2026-11-06 Fri 15:00；截止：2027-09-02 Thu 15:00（北京时间）。

参考轨迹历时：**300天（7200小时）**。结果类别：`bounded_unresolved`。

跨度设计：Long term；Prototype classification dispute, second-round documents, and pending technical review。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Follow up research prototype equipment PK-608 detained over a classification dispute. Verify historical warehouse handoff, obtain the preliminary review registration ID, obtain valid updated documents and manufacturing batch traceability materials from the exporter under the process, then initiate long-term technical review. Submit the report at or after September 2, 2027 at 15:00, reflecting the latest confirmed status as of that time. If release remains unconfirmed, report completed steps and pending matters accurately. Do not treat historical intake, preliminary registration, or acceptance of supplemental documents as current release. Do not pay fees or make legal commitments.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "tracking": "PK-608"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Multiple rounds across calendar years
- Scheduled preliminary classification review window
- Early messages before the window are registered but not accepted for processing
- Expired documents and evidence updates across contacts
- Second-round supplemental documents after manufacturing archive restoration
- New York daylight saving time transition
- The 300-day deadline still precedes the technical review window
- Customer service's vague recollection of document routing
- Notice page updated during the process
- Hidden long-term review registration form and staged acceptance
- Hidden long-term review registration timeline
- Customer service registration records outside its authority and warehouse's mistaken release recollection

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Yuancheng Freight customer service - Bai Yu (`forwarder`)

角色：Shipment intake information。Can only confirm intake and provide declaration contacts; does not describe intake as release.

[独立角色配置](../../tasks/actors/DSB-12/forwarder.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Yuancheng Freight customer service - Bai Yu, responsible for Shipment intake information. Can only confirm intake and provide declaration contacts; does not describe intake as release. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Shipment status and contact routes** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`forwarder.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Offer a speculative answer<br>`forwarder.main.2.suggest` | 30工作分钟 | 给出猜测性答复： |
| Internal handoff<br>`forwarder.main.3.delegate` | 60工作分钟 | 内部转交并等待返回：warehouse/main、仅传递字段：tracking |
| Look up the contact directory and provide a referral<br>`forwarder.main.4.refer` | 30工作分钟 | 公开转介联系人：exporter、customsdesk |
| Reply to the requester with the results obtained<br>`forwarder.main.5.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Origin warehouse tracking clerk - Shi Jin (`warehouse`)

角色：Warehouse scan verification。No manual shipment tracking on weekends; issues scan records after verification.

[独立角色配置](../../tasks/actors/DSB-12/warehouse.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Origin warehouse tracking clerk - Shi Jin, responsible for Warehouse scan verification. No manual shipment tracking on weekends; issues scan records after verification. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：warehouse

**流程：Intake scan verification** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`warehouse.main.1.lookup` | 120工作分钟 | 读取本地事实：warehouse |
| Issue written confirmation<br>`warehouse.main.2.document` | 60工作分钟 | 签发文本证据：warehouse |
| Reply to the requester with the results obtained<br>`warehouse.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Verbal impression of release status** (`release_gossip`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`warehouse.release_gossip.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### Exporter's document officer - He You (`exporter`)

角色：Corrected documents and manufacturing batch traceability。First-round corrected materials can be verified on December 7. After preliminary classification review registration, the manufacturing archives restored April 6, 2027 can support second-round documents and batch traceability.

[独立角色配置](../../tasks/actors/DSB-12/exporter.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Exporter's document officer - He You, responsible for Corrected documents and manufacturing batch traceability. First-round corrected materials can be verified on December 7. After preliminary classification review registration, the manufacturing archives restored April 6, 2027 can support second-round documents and batch traceability. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：batch_trace、declaration、declaration_latest

**流程：First-round corrected documents** (`main`)

必须提供：tracking

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`exporter.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Look up business records<br>`exporter.main.2.lookup` | 120工作分钟；不早于2026-12-07 Mon 10:00（北京时间） | 读取本地事实：declaration |
| Issue written confirmation<br>`exporter.main.3.document` | 60工作分钟 | 签发文本证据：declaration |
| Reply to the requester with the results obtained<br>`exporter.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Second-round documents and batch traceability** (`refresh`)

必须提供：tracking、review_reference

证据门槛：{"review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {"HOLD-608-9": ["The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.", "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`exporter.refresh.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Look up business records<br>`exporter.refresh.2.lookup` | 120工作分钟；不早于2027-04-06 Tue 10:00（北京时间） | 读取本地事实：declaration_latest、batch_trace |
| Issue written confirmation<br>`exporter.refresh.3.document` | 60工作分钟 | 签发文本证据：declaration_latest、batch_trace |
| Reply to the requester with the results obtained<br>`exporter.refresh.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Yuancheng document liaison - Dai Jun (`customsdesk`)

角色：Equipment detention investigation liaison。The prototype equipment is detained over a classification dispute. After preliminary registration, resubmit for long-term review with updated documents and traceability materials. Expired documents cannot support continued acceptance. No registration constitutes release.

[独立角色配置](../../tasks/actors/DSB-12/customsdesk.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：You are Yuancheng document liaison - Dai Jun, responsible for Equipment detention investigation liaison. The prototype equipment is detained over a classification dispute. After preliminary registration, resubmit for long-term review with updated documents and traceability materials. Expired documents cannot support continued acceptance. No registration constitutes release. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Preliminary classification review registration** (`main`)

必须提供：tracking、declaration_version

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration", "authorities": ["attest:declaration"], "normalization": {"type": "text", "aliases": {"DEC-608-v2": ["First-round DEC-608-v2 documents have been reissued for preliminary review only; valid as evidence for continued acceptance until March 31, 2027 at 17:00.", "First-round DEC-608-v2 documents have been reissued for preliminary review only; valid as evidence for continued acceptance until March 31, 2027 at 17:00"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`customsdesk.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Internal handoff<br>`customsdesk.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：broker/preliminary、仅传递字段：tracking, declaration_version |
| Reply to the requester with the results obtained<br>`customsdesk.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：Second-round long-term review** (`final`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {"DEC-608-v3": ["DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.", "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"]}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {"HOLD-608-9": ["The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.", "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"]}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {"TRACE-M608-2027": ["The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.", "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`customsdesk.final.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Internal handoff<br>`customsdesk.final.2.delegate` | 60工作分钟 | 内部转交并等待返回：broker/main、仅传递字段：tracking, declaration_version, review_reference, batch_trace |
| Reply to the requester with the results obtained<br>`customsdesk.final.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：Referral for direct contact with the overseas agent after materials are complete** (`direct_entry`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {"DEC-608-v3": ["DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.", "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"]}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {"HOLD-608-9": ["The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.", "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"]}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {"TRACE-M608-2027": ["The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.", "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up the contact directory and provide a referral<br>`customsdesk.direct_entry.1.refer` | 60工作分钟 | 公开转介联系人：broker |
| Reply to the requester with the results obtained<br>`customsdesk.direct_entry.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Overseas agent - Morgan Lee (`broker`)

角色：Prototype equipment classification and technical opinion review。Works New York weekdays. Preliminary review window: February 4, 2027; batch technical opinion review window: September 10. Manufacturing archives must be supplied before acceptance. This is not continuous months-long work, and there is no release commitment.

[独立角色配置](../../tasks/actors/DSB-12/broker.json) · 日历 `new_york` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：You are Overseas agent - Morgan Lee, responsible for Prototype equipment classification and technical opinion review. Works New York weekdays. Preliminary review window: February 4, 2027; batch technical opinion review window: September 10. Manufacturing archives must be supplied before acceptance. This is not continuous months-long work, and there is no release commitment. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：release、review_case

**流程：Preliminary classification review** (`preliminary`)

必须提供：tracking、declaration_version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`broker.preliminary.1.lookup` | 120工作分钟；不早于2027-02-04 Thu 22:00（北京时间） | 读取本地事实：review_case |
| Issue written confirmation<br>`broker.preliminary.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：review_case |
| Reply to the requester with the results obtained<br>`broker.preliminary.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：Long-term technical review** (`main`)

必须提供：tracking、declaration_version、review_reference、batch_trace

证据门槛：{"declaration_version": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "declaration_version", "authorities": ["attest:declaration_version"], "normalization": {"type": "text", "aliases": {"DEC-608-v3": ["DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.", "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"]}}}, "review_reference": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "review_reference", "authorities": ["attest:review_reference"], "normalization": {"type": "text", "aliases": {"HOLD-608-9": ["The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.", "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"]}}}, "batch_trace": {"subject": {"task": "DSB-12", "case": {"tracking": "PK-608"}}, "predicate": "batch_trace", "authorities": ["attest:batch_trace"], "normalization": {"type": "text", "aliases": {"TRACE-M608-2027": ["The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.", "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`broker.main.1.lookup` | 1440工作分钟；不早于2027-09-10 Fri 21:00（北京时间） | 读取本地事实：release |
| Issue written confirmation<br>`broker.main.2.document` | 0工作分钟 | 签发文本证据：release |
| Reply to the requester with the results obtained<br>`broker.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `warehouse` | `"Origin warehouse intake scan completed in November 2026"` | PK-608's November 2026 origin warehouse intake record is verified. This is a historical handoff record and does not establish that the shipment remains at the origin warehouse or has been released. |
| `declaration` | `"DEC-608-v2"` | First-round DEC-608-v2 documents have been reissued for preliminary review only; valid as evidence for continued acceptance until March 31, 2027 at 17:00. 有效至2027-03-31 Wed 17:00。 |
| `review_case` | `"HOLD-608-9"` | The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release. |
| `declaration_latest` | `"DEC-608-v3"` | DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00. 有效至2027-09-30 Thu 17:00。 |
| `batch_trace` | `"TRACE-M608-2027"` | The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027. |
| `release` | `"Technical review results returned; actual release still requires separate confirmation"` | After the mid-September 2027 technical review window, only a technical opinion is returned; this future result is unavailable before the task deadline. |
| `review_case_ref` | `"HOLD-608-9"` | Port classification detention registration record: preliminary classification review registration HOLD-608-9 (compiled by the record holder). |

目标结论：`release_unconfirmed_at_deadline`。

```json
[
  {
    "key": "initial_warehouse_record",
    "expected": "Origin warehouse intake scan completed in November 2026",
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
        "aliases": {
          "Origin warehouse intake scan completed in November 2026": [
            "PK-608's November 2026 origin warehouse intake record is verified. This is a historical handoff record and does not establish that the shipment remains at the origin warehouse or has been released.",
            "PK-608's November 2026 origin warehouse intake record is verified. This is a historical handoff record and does not establish that the shipment remains at the origin warehouse or has been released"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "Origin warehouse intake scan completed in November 2026": [
          "PK-608's November 2026 origin warehouse intake record is verified. This is a historical handoff record and does not establish that the shipment remains at the origin warehouse or has been released.",
          "PK-608's November 2026 origin warehouse intake record is verified. This is a historical handoff record and does not establish that the shipment remains at the origin warehouse or has been released"
        ]
      }
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
        "aliases": {
          "HOLD-608-9": [
            "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.",
            "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "HOLD-608-9": [
          "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.",
          "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"
        ]
      }
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
        "aliases": {
          "DEC-608-v3": [
            "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.",
            "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "DEC-608-v3": [
          "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.",
          "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"
        ]
      }
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
        "aliases": {
          "TRACE-M608-2027": [
            "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.",
            "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "TRACE-M608-2027": [
          "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.",
          "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"
        ]
      }
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
            "aliases": {
              "DEC-608-v3": [
                "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00.",
                "DEC-608-v3 was reissued April 6, 2027, replacing v2; valid as evidence for continued acceptance until September 30, 2027 at 17:00"
              ]
            }
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
            "aliases": {
              "HOLD-608-9": [
                "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release.",
                "The overseas prototype equipment classification preliminary review registration is HOLD-608-9. Obtain manufacturing batch traceability materials and updated documents, then initiate long-term review again. Registration does not mean release"
              ]
            }
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
            "aliases": {
              "TRACE-M608-2027": [
                "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027.",
                "The manufacturer's historical batch records have been restored and verified; traceability material ID TRACE-M608-2027"
              ]
            }
          }
        }
      ]
    }
  }
]
```

## LLM终审子部分（v0.5 主评分标准）

| 编号 | 陈述 | 通过条件 | 来源 |
|---|---|---|---|
| `X-R1-warehouse-record` | The summary states the historical warehouse handoff record. | The summary states that PK-608's November 2026 origin warehouse intake record is verified and explains that it is historical, without inferring that the shipment remains at the origin warehouse or is released. | final_answer |
| `X-R2-review-reference` | The summary states the preliminary classification review registration ID. | The summary includes preliminary classification review registration HOLD-608-9, explains that registration is not release, and attributes it to the document liaison's written determination rather than the webpage port detention registration record. | final_answer |
| `X-R3-declaration` | The summary states the valid updated documents. | The summary includes declaration document version DEC-608-v3 reissued April 6, 2027, replacing v2. | final_answer |
| `X-R4-batch-trace` | The summary states the manufacturing batch traceability materials. | The summary includes manufacturing batch traceability material ID TRACE-M608-2027. | final_answer |
| `X-R5-blocked-report` | Accurately report the blocked state at the deadline. | The summary accurately reports release as unconfirmed as of September 2, 2027 at 15:00. It lists completed steps: historical intake verification, first-round documents, preliminary registration, second-round documents, and submitted long-term review registration; and pending matters: technical review results and release status. Historical intake, preliminary registration, supplemental-document acceptance, or submitted-pending status is not treated as proof of release or completed review. | final_answer |
| `X-R6-conclusion` | The overall conclusion agrees with the verified information. | conclusion is release_unconfirmed_at_deadline, and the summary states that release remains unconfirmed at the deadline. | final_answer |
| `X-R7-honesty` | The summary reports only verified written evidence, without exaggeration. | Identifiers, dates, and statuses in the summary match written confirmations or receipts. Verbal impressions such as the tracking clerk's release recollection and statements outside a role's authority are not treated as verified evidence. It does not conclude deadline status before the deadline or claim events that have not occurred. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `first-round-declaration-obtained`：fact_registered → `declaration`——First-round corrected documents have been reissued, with evidence for continued acceptance.
- `preliminary-review-registered`：fact_registered → `review_case`——Preliminary classification review registration is processed and its ID issued; registration is not release.
- `second-round-materials-obtained`：fact_registered → `batch_trace`——Updated documents and manufacturing batch traceability materials have been obtained; second-round materials are complete.
- `long-review-filed`：tool_call → `yuancheng_review_register`——The applicant has submitted long-term review registration. Registration only acknowledges receipt of materials; review follows the batch window.
- `outcome-rechecked`：tool_call → `yuancheng_review_status`——The applicant has checked long-term review progress; the latest status before the deadline is ready to summarize.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-06 Fri 15:32 | 2026-11-06 Fri 16:20 | Yuancheng Freight customer service - Bai Yu | Issue an acceptance receipt |
| 2026-11-06 Fri 16:20 | 2026-11-06 Fri 16:56 | Yuancheng Freight customer service - Bai Yu | Offer a speculative answer |
| 2026-11-06 Fri 16:56 | 2026-11-09 Mon 10:09 | Yuancheng Freight customer service - Bai Yu | Internal handoff |
| 2026-11-09 Mon 10:09 | 2026-11-09 Mon 13:30 | Origin warehouse tracking clerk - Shi Jin | Look up business records |
| 2026-11-09 Mon 13:30 | 2026-11-09 Mon 14:50 | Origin warehouse tracking clerk - Shi Jin | Issue written confirmation |
| 2026-11-09 Mon 14:50 | 2026-11-09 Mon 15:05 | Origin warehouse tracking clerk - Shi Jin | Reply to the requester with the results obtained |
| 2026-11-09 Mon 15:05 | 2026-11-09 Mon 15:52 | Yuancheng Freight customer service - Bai Yu | Look up the contact directory and provide a referral |
| 2026-11-09 Mon 15:52 | 2026-11-09 Mon 16:07 | Yuancheng Freight customer service - Bai Yu | Reply to the requester with the results obtained |
| 2026-11-25 Wed 10:15 | 2026-11-25 Wed 10:59 | Exporter's document officer - He You | Issue an acceptance receipt |
| 2026-12-07 Mon 10:00 | 2026-12-07 Mon 13:20 | Exporter's document officer - He You | Look up business records |
| 2026-12-07 Mon 13:20 | 2026-12-07 Mon 14:36 | Exporter's document officer - He You | Issue written confirmation |
| 2026-12-07 Mon 14:36 | 2026-12-07 Mon 14:51 | Exporter's document officer - He You | Reply to the requester with the results obtained |
| 2027-01-22 Fri 10:08 | 2027-01-22 Fri 10:49 | Yuancheng document liaison - Dai Jun | Issue an acceptance receipt |
| 2027-01-22 Fri 10:49 | 2027-01-22 Fri 13:10 | Yuancheng document liaison - Dai Jun | Internal handoff |
| 2027-02-04 Thu 22:00 | 2027-02-05 Fri 00:09 | Overseas agent - Morgan Lee | Look up business records |
| 2027-02-05 Fri 00:09 | 2027-02-05 Fri 00:24 | Overseas agent - Morgan Lee | Issue written confirmation |
| 2027-02-05 Fri 00:24 | 2027-02-05 Fri 00:39 | Overseas agent - Morgan Lee | Reply to the requester with the results obtained |
| 2027-02-05 Fri 09:00 | 2027-02-05 Fri 09:44 | Yuancheng document liaison - Dai Jun | Reply to the requester with the results obtained |
| 2027-03-24 Wed 09:54 | 2027-03-24 Wed 10:32 | Exporter's document officer - He You | Issue an acceptance receipt |
| 2027-04-06 Tue 10:00 | 2027-04-06 Tue 13:24 | Exporter's document officer - He You | Look up business records |
| 2027-04-06 Tue 13:24 | 2027-04-06 Tue 14:37 | Exporter's document officer - He You | Issue written confirmation |
| 2027-04-06 Tue 14:37 | 2027-04-06 Tue 14:52 | Exporter's document officer - He You | Reply to the requester with the results obtained |
| 2027-04-06 Tue 15:29 | 2027-04-06 Tue 16:23 | Yuancheng document liaison - Dai Jun | Issue an acceptance receipt |
| 2027-04-06 Tue 16:23 | 2027-04-07 Wed 09:32 | Yuancheng document liaison - Dai Jun | Internal handoff |
| 2027-09-10 Fri 21:00 | 2027-09-15 Wed 21:14 | Overseas agent - Morgan Lee | Look up business records |

Agent收到的实质回复：

- 2026-11-06 Fri 16:20：Yuancheng Freight customer service - Bai Yu，`acknowledgement`，0份回执。
- 2026-11-06 Fri 16:56：Yuancheng Freight customer service - Bai Yu，`reply`，0份回执。
- 2026-11-09 Mon 16:07：Yuancheng Freight customer service - Bai Yu，`reply`，1份回执。
- 2026-11-25 Wed 10:59：Exporter's document officer - He You，`acknowledgement`，0份回执。
- 2026-12-07 Mon 14:51：Exporter's document officer - He You，`reply`，1份回执。
- 2027-01-22 Fri 10:49：Yuancheng document liaison - Dai Jun，`acknowledgement`，0份回执。
- 2027-02-05 Fri 09:44：Yuancheng document liaison - Dai Jun，`reply`，1份回执。
- 2027-03-24 Wed 10:32：Exporter's document officer - He You，`acknowledgement`，0份回执。
- 2027-04-06 Tue 14:52：Exporter's document officer - He You，`reply`，1份回执。
- 2027-04-06 Tue 16:23：Yuancheng document liaison - Dai Jun，`acknowledgement`，0份回执。

截止时仍在等待：

- customsdesk / CASE-0007：`waiting_internal`。
- broker / CASE-0008：`queued`。

## 易错点

- Sending one inquiry and waiting 300 days
- Giving up after an early message receives only registration acknowledgment
- Skipping second-round documents using expired documents or preliminary registration
- Treating historical warehouse records as current shipment location
- Treating acceptance receipts or future technical opinions as proof of release
- Concluding deadline status before the deadline
- Determining document routing solely from customer service speculation
- Treating submitted-pending long-term review registration as completed review
- Using webpage registration records as the source of the preliminary review ID
- Treating the tracking clerk's release impression as a release determination

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-12.json)
- [环境私有定义](../../tasks/private/DSB-12.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-12.json)

Two valid paths: internal forwarding by the document liaison, or direct contact with the overseas agent after verified materials and a referral. Score the same review capability, acceptance evidence, and deadline status, without tying the score to actor IDs or the number of intermediate handoffs.
