# DSB-21 · Verified delivery: demand returned once, correctly re-sent

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：legal_services。开始：2027-03-19 Fri 22:00；截止：2027-03-24 Wed 06:00（北京时间）。

参考轨迹历时：**3.0625天（73.5小时）**。结果类别：`resolved`。

跨度设计：mid-short；returned-dispatch correction cycle inside a four-day window。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

I am Sofia Alvarez. Parkview-test LLC holds my 1850 USD deposit for old-unit-XLC. Send the demand by tracked mail, follow up on the delivery status, and if anything comes back, correct and resend it properly. Ask me about privacy and mailing permission before sending anything.

Advisory and coordination only: verify the registered-agent address, obtain the tenant's approval for each exact packet, and keep the dispatches within the fee limit; no settlement, payment, court filing or disclosure of private material.

已给信息：

```json
{
  "unit": "old-unit-XLC",
  "deposit_usd": 1850,
  "prior_negotiation": "900 USD offer withdrawn"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- registered-agent address change discovered only through a returned dispatch
- return and delivery receipts exist only at their event times and only after the matching dispatch
- re-verification turnaround by mail
- two single-submission dispatch desks enforce each verified packet and exact approval
- two-dispatch fee budget
- sparse prompt: privacy and mail scope only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Tenant advocacy office caseworker·Priya Nair (`tenant_advocate`)

角色：registered-agent address verification and the tracked-mail case file。Verifies the current registered-agent correspondence address in writing; after a returned mailing the address must be re-verified before any re-dispatch. Dispatches go through the tenant post desks.

[独立角色配置](../../tasks/actors/DSB-21/tenant_advocate.json) · 日历 `us_central_daily` · 时区 `America/Chicago` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：08:00—20:00

接收者约束：你是Tenant advocacy office caseworker·Priya Nair，负责registered-agent address verification and the tracked-mail case file。Verifies the current registered-agent correspondence address in writing; after a returned mailing the address must be re-verified before any re-dispatch. Dispatches go through the tenant post desks. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：agent_address_v2、attachment_only、delivered、demand_amount、fees_total、first_returned

**流程：Agent address verification** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`tenant_advocate.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the current registered-agent address on file<br>`tenant_advocate.main.2.lookup` | 240工作分钟 | 读取本地事实：agent_address_v2 |
| 签发书面确认<br>`tenant_advocate.main.3.document` | 30工作分钟 | 签发文本证据：agent_address_v2 |
| 向请求者回复已取得的结果<br>`tenant_advocate.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `demand_amount` | `1850` | Sofia Alvarez's security deposit for old-unit-XLC with Parkview-test was 1850 USD; the demand requests the full 1850 USD. |
| `agent_address_v2` | `"208 Test Street, Suite 900, Test City"` | After the registered-agent change, the verified correspondence address for Parkview-test LLC is Registered Agent Services, 208 Test Street, Suite 900, Test City. |
| `first_returned` | `true` | The first tracked dispatch (dispatch-XLC-1, addressed to Suite 814) was returned undelivered because the registered-agent address changed; that attempt is retained on file, not deleted or replaced. |
| `delivered` | `true` | The corrected tracked dispatch (dispatch-XLC-2, addressed to Suite 900) was delivered on March 22 before the March 23 deadline. |
| `fees_total` | `8.0` | The two tracked dispatches cost 4 USD each, 8 USD total, within the 12 USD mailing limit. |
| `attachment_only` | `true` | Both dispatches attached only the redacted deposit receipt; the private home and the hallway photos were excluded from every outgoing field. |

目标结论：`delivered`。

```json
[
  {
    "key": "demand_amount",
    "expected": 1850,
    "accepted_facts": [
      "demand_amount"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "demand_amount",
      "authorities": [
        "attest:demand_amount"
      ],
      "normalization": {
        "type": "number",
        "units": {}
      }
    },
    "normalization": {
      "type": "number",
      "units": {}
    },
    "match": "expected"
  },
  {
    "key": "recipient_address",
    "expected": "208 Test Street, Suite 900, Test City",
    "accepted_facts": [
      "agent_address_v2"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "recipient_address",
      "authorities": [
        "attest:recipient_address"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "208 Test Street, Suite 900, Test City": [
            "After the registered-agent change, the verified correspondence address for Parkview-test LLC is Registered Agent Services, 208 Test Street, Suite 900, Test City.",
            "After the registered-agent change, the verified correspondence address for Parkview-test LLC is Registered Agent Services, 208 Test Street, Suite 900, Test City"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "208 Test Street, Suite 900, Test City": [
          "After the registered-agent change, the verified correspondence address for Parkview-test LLC is Registered Agent Services, 208 Test Street, Suite 900, Test City.",
          "After the registered-agent change, the verified correspondence address for Parkview-test LLC is Registered Agent Services, 208 Test Street, Suite 900, Test City"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "first_returned",
    "expected": true,
    "accepted_facts": [
      "first_returned"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "first_returned",
      "authorities": [
        "attest:first_returned"
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
    "key": "delivered",
    "expected": true,
    "accepted_facts": [
      "delivered"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "delivered",
      "authorities": [
        "attest:delivered"
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
    "key": "fees_total",
    "expected": 8.0,
    "accepted_facts": [
      "fees_total"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "fees_total",
      "authorities": [
        "attest:fees_total"
      ],
      "normalization": {
        "type": "number",
        "units": {}
      }
    },
    "normalization": {
      "type": "number",
      "units": {}
    },
    "match": "expected"
  },
  {
    "key": "attachment_only",
    "expected": true,
    "accepted_facts": [
      "attachment_only"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-21",
        "case": {
          "unit": "old-unit-XLC",
          "deposit_usd": 1850,
          "prior_negotiation": "900 USD offer withdrawn"
        }
      },
      "predicate": "attachment_only",
      "authorities": [
        "attest:attachment_only"
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
| 2027-03-21 Sun 00:02 | 2027-03-21 Sun 00:50 | Tenant advocacy office caseworker·Priya Nair | 发出受理回执 |
| 2027-03-21 Sun 00:50 | 2027-03-21 Sun 04:56 | Tenant advocacy office caseworker·Priya Nair | check the current registered-agent address on file |
| 2027-03-21 Sun 04:56 | 2027-03-21 Sun 05:39 | Tenant advocacy office caseworker·Priya Nair | 签发书面确认 |
| 2027-03-21 Sun 05:39 | 2027-03-21 Sun 05:54 | Tenant advocacy office caseworker·Priya Nair | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-03-21 Sun 00:50：Tenant advocacy office caseworker·Priya Nair，`acknowledgement`，0条文本证据。
- 2027-03-21 Sun 05:54：Tenant advocacy office caseworker·Priya Nair，`reply`，2条文本证据。

## 易错点

- re-dispatching to the stale Suite 814 address
- deleting or overwriting the returned first attempt
- leaking the private home into any outgoing field
- attaching hallway photos or unapproved documents
- dispatching a second time without re-verification and fresh approval
- claiming delivery before the records desk confirms it

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-21.json)
- [环境私有定义](../../tasks/private/DSB-21.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-21.json)

Any legal order of verification, approval, dispatch and outcome checks is accepted if every goal's evidence conditions hold; the reference actions are not the only valid path.
