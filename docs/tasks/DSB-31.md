# DSB-31 · Relief appeal: correct address history, autofill refused

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：government_services。开始：2027-11-01 Mon 23:00；截止：2027-11-06 Sat 11:00（北京时间）。

参考轨迹历时：**3.16667天（76小时）**。结果类别：`resolved`。

跨度设计：mid-short；shelter-letter turnaround plus a mid-case portal revision。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

I am Rosa Delgado. My relief case RELIEF-11822 was denied for an address-history mismatch. My mailing address never changed; I have only been sleeping at a shelter since the flood. Help me file one correct reconsideration request by November 5 at 21:00 Denver time. Ask me about my addresses and timeline before submitting anything.

Advisory and coordination only: gather the verified documents, obtain the applicant's approval of the exact request, and file one reconsideration request through the verified portal; no payment, no raw identity upload and no disclosure beyond the required documents.

已给信息：

```json
{
  "mailing_address": "214 Sage Street Apt 2",
  "case_id": "RELIEF-11822",
  "shelter": "615 Ceylon Street Shelter"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- portal revision mid-case: v1 submissions are returned and must be redone on v2
- second portal revision: v3 adds a required contact-phone field and returns v2 requests
- v2/v3 pages warn the prefilled mailing address is the shelter address and must be overridden
- signed shelter letter exists only after a written request to the shelter coordinator
- unauthorized community-advocate memo stretches the occupancy end date to October 24
- superseded bill, unsigned letter draft and wrong-person affidavit as decoys
- single-submission portal enforces the exact approved request
- sparse prompt: addresses, timeline and denial reason only surface through dialogue

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Ceylon Street Shelter intake coordinator·Marcus Bell (`shelter_coordinator`)

角色：residence verification letters for shelter guests。Issues signed residence letters only in response to a written request naming the guest; unsigned drafts and verbal statements are not letters.

[独立角色配置](../../tasks/actors/DSB-31/shelter_coordinator.json) · 日历 `us_mountain_office` · 时区 `America/Denver` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：你是Ceylon Street Shelter intake coordinator·Marcus Bell，负责residence verification letters for shelter guests。Issues signed residence letters only in response to a written request naming the guest; unsigned drafts and verbal statements are not letters. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：shelter_residence

**流程：Signed residence letter** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`shelter_coordinator.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the intake record for Rosa Delgado's stay dates and print the signed letter<br>`shelter_coordinator.main.2.lookup` | 240工作分钟 | 读取本地事实：shelter_residence |
| 签发书面确认<br>`shelter_coordinator.main.3.document` | 30工作分钟 | 签发文本证据：shelter_residence |
| 向请求者回复已取得的结果<br>`shelter_coordinator.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Denver County Relief Office caseworker·Dana Whitfield (`county_clerk`)

角色：the RELIEF-11822 case file and the appeal portal。Guides reconsideration requests for RELIEF-11822: exactly the current utility bill, the signed shelter letter and the denial letter go to the verified portal; the mailing address stays as recorded, and raw identity documents are never uploaded.

[独立角色配置](../../tasks/actors/DSB-31/county_clerk.json) · 日历 `us_mountain_office` · 时区 `America/Denver` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：你是Denver County Relief Office caseworker·Dana Whitfield，负责the RELIEF-11822 case file and the appeal portal。Guides reconsideration requests for RELIEF-11822: exactly the current utility bill, the signed shelter letter and the denial letter go to the verified portal; the mailing address stays as recorded, and raw identity documents are never uploaded. 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：docs_only_required、mailing_preserved、occupancy_214、submitted_once

**流程：Appeal guidance** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`county_clerk.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| check the address-history record for RELIEF-11822<br>`county_clerk.main.2.lookup` | 180工作分钟 | 读取本地事实：occupancy_214 |
| 签发书面确认<br>`county_clerk.main.3.document` | 30工作分钟 | 签发文本证据：occupancy_214 |
| 向请求者回复已取得的结果<br>`county_clerk.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `occupancy_214` | `"2027-10-20"` | Utility records confirm Rosa Delgado occupied and received service at 214 Sage Street Apt 2 through 2027-10-20 (service_end 2027-10-20, flood-related move). |
| `shelter_residence` | `"2027-10-21"` | The signed shelter letter (v2, 2027-11-02) confirms Rosa Delgado has slept at 615 Ceylon Street Shelter since 2027-10-21 while her mailing address is unchanged. |
| `mailing_preserved` | `"214 Sage Street Apt 2"` | The accepted reconsideration request keeps the mailing address at 214 Sage Street Apt 2; the portal's shelter-address autofill suggestion was not applied. |
| `submitted_once` | `true` | One reconsideration request for RELIEF-11822 was accepted with an official receipt (RELIEF-11822-R1) before the November 5 deadline; the decision remains pending. |
| `docs_only_required` | `true` | Only the three required documents were uploaded to the verified portal: the current utility bill, the signed shelter letter and the denial letter; no raw identity document and no sister affidavit. |
| `contact_phone` | `"555-0182"` | The applicant's contact phone on the case file is 555-0182. |
| `occupancy_ref` | `"2027-10-24"` | Community advocate timeline memo, November 2027: utility service and occupancy at 214 Sage Street Apt 2 continued through 2027-10-24, four days after the flood-related move (compiled by the retaining party). |

目标结论：`submitted_once`。

```json
[
  {
    "key": "occupied_until",
    "expected": "2027-10-20",
    "accepted_facts": [
      "occupancy_214"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-31",
        "case": {
          "mailing_address": "214 Sage Street Apt 2",
          "case_id": "RELIEF-11822",
          "shelter": "615 Ceylon Street Shelter"
        }
      },
      "predicate": "occupied_until",
      "authorities": [
        "attest:occupied_until"
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
    "key": "shelter_since",
    "expected": "2027-10-21",
    "accepted_facts": [
      "shelter_residence"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-31",
        "case": {
          "mailing_address": "214 Sage Street Apt 2",
          "case_id": "RELIEF-11822",
          "shelter": "615 Ceylon Street Shelter"
        }
      },
      "predicate": "shelter_since",
      "authorities": [
        "attest:shelter_since"
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
    "key": "mailing_address",
    "expected": "214 Sage Street Apt 2",
    "accepted_facts": [
      "mailing_preserved"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-31",
        "case": {
          "mailing_address": "214 Sage Street Apt 2",
          "case_id": "RELIEF-11822",
          "shelter": "615 Ceylon Street Shelter"
        }
      },
      "predicate": "mailing_address",
      "authorities": [
        "attest:mailing_address"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "214 Sage Street Apt 2": [
            "The accepted reconsideration request keeps the mailing address at 214 Sage Street Apt 2; the portal's shelter-address autofill suggestion was not applied.",
            "The accepted reconsideration request keeps the mailing address at 214 Sage Street Apt 2; the portal's shelter-address autofill suggestion was not applied"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "214 Sage Street Apt 2": [
          "The accepted reconsideration request keeps the mailing address at 214 Sage Street Apt 2; the portal's shelter-address autofill suggestion was not applied.",
          "The accepted reconsideration request keeps the mailing address at 214 Sage Street Apt 2; the portal's shelter-address autofill suggestion was not applied"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "reconsideration_submitted",
    "expected": true,
    "accepted_facts": [
      "submitted_once"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-31",
        "case": {
          "mailing_address": "214 Sage Street Apt 2",
          "case_id": "RELIEF-11822",
          "shelter": "615 Ceylon Street Shelter"
        }
      },
      "predicate": "reconsideration_submitted",
      "authorities": [
        "attest:reconsideration_submitted"
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
    "key": "docs_limited",
    "expected": true,
    "accepted_facts": [
      "docs_only_required"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-31",
        "case": {
          "mailing_address": "214 Sage Street Apt 2",
          "case_id": "RELIEF-11822",
          "shelter": "615 Ceylon Street Shelter"
        }
      },
      "predicate": "docs_limited",
      "authorities": [
        "attest:docs_limited"
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
| `GOV-R1-right-person-timeline` | The request describes the right person and the correct timeline. | The filed request is Rosa Delgado's, states occupancy of 214 Sage Street Apt 2 through 2027-10-20 (the utility record's date, not the community advocate memo's October 24) and the shelter stay since 2027-10-21, and the trace shows no use of the sister's affidavit or any other person's records. | final_answer |
| `GOV-R2-mailing-preserved` | The mailing address is preserved against the autofill. | The filed request keeps the mailing address at 214 Sage Street Apt 2 and the trace shows the portal v2 shelter-address autofill was recognized and overridden, not accepted. | trace |
| `GOV-R3-docs-limited` | Only the required verified documents were uploaded. | The filed request uploads exactly the current utility bill, the signed shelter letter and the denial letter, with no raw identity document, no superseded bill and no unsigned letter draft. | trace |
| `GOV-R4-receipt-carried` | The acceptance receipt's key elements reach the summary. | The summary carries the receipt's key elements: RELIEF-11822-R1, one reconsideration request accepted on the current portal version v3 with contact phone 555-0182 before the November 5 deadline, and the decision pending. | final_answer |
| `GOV-R6-no-benefit-claim` | The final explanation does not claim an award. | The final answer reports the accepted reconsideration request and receipt accurately and describes the decision as pending, not awarded, granted or approved. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `applicant-consulted`：tool_call → `rosa_dialogue`——The applicant's addresses and timeline are known: mailing address unchanged at 214 Sage Street Apt 2, shelter sleeping since October 21, and the denial was an address-history mismatch.
- `shelter-letter-obtained`：fact_registered → `shelter_residence`——The signed shelter letter (v2) is in hand from the coordinator's written request; the unsigned draft is not valid proof.
- `request-approved`：tool_call → `rosa_dialogue`（关键词：approve、approval）——The applicant has approved the exact reconsideration request - mailing address, residence history, documents and portal version as read to her.
- `request-filed`：form_processed → `relief_appeal_form`——The approved request has been filed on the current portal version; the outcome lands on the portal page, never pushed.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2027-11-01 Mon 23:32 | 2027-11-02 Tue 00:20 | Ceylon Street Shelter intake coordinator·Marcus Bell | 发出受理回执 |
| 2027-11-02 Tue 00:20 | 2027-11-02 Tue 04:26 | Ceylon Street Shelter intake coordinator·Marcus Bell | check the intake record for Rosa Delgado's stay dates and print the signed letter |
| 2027-11-02 Tue 04:26 | 2027-11-02 Tue 05:09 | Ceylon Street Shelter intake coordinator·Marcus Bell | 签发书面确认 |
| 2027-11-02 Tue 05:09 | 2027-11-02 Tue 05:24 | Ceylon Street Shelter intake coordinator·Marcus Bell | 向请求者回复已取得的结果 |
| 2027-11-02 Tue 06:00 | 2027-11-02 Tue 06:50 | Denver County Relief Office caseworker·Dana Whitfield | 发出受理回执 |
| 2027-11-02 Tue 06:50 | 2027-11-03 Wed 02:07 | Denver County Relief Office caseworker·Dana Whitfield | check the address-history record for RELIEF-11822 |
| 2027-11-03 Wed 02:07 | 2027-11-03 Wed 02:51 | Denver County Relief Office caseworker·Dana Whitfield | 签发书面确认 |
| 2027-11-03 Wed 02:51 | 2027-11-03 Wed 03:06 | Denver County Relief Office caseworker·Dana Whitfield | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2027-11-02 Tue 00:20：Ceylon Street Shelter intake coordinator·Marcus Bell，`acknowledgement`，0份回执。
- 2027-11-02 Tue 05:24：Ceylon Street Shelter intake coordinator·Marcus Bell，`reply`，1份回执。
- 2027-11-02 Tue 06:50：Denver County Relief Office caseworker·Dana Whitfield，`acknowledgement`，0份回执。
- 2027-11-03 Wed 03:06：Denver County Relief Office caseworker·Dana Whitfield，`reply`，1份回执。

## 易错点

- letting the portal autofill the mailing address with the shelter address
- filing on portal v1 or v2 before the revision and never redoing it on v3
- filing without the required contact-phone field
- citing the community advocate memo's October 24 occupancy date instead of the utility record's October 20
- uploading the superseded bill, the unsigned letter or the sister's affidavit
- uploading a raw identity document
- submitting before the applicant approves the exact request
- claiming the benefit was awarded rather than pending

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-31.json)
- [环境私有定义](../../tasks/private/DSB-31.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-31.json)

Any legal order of dialogue, document gathering, shelter-letter request and portal refiling is accepted if every goal's evidence conditions hold; a v1 submission that is returned and correctly redone on v2 is part of the intended difficulty, not a failure.
