# DSB-11 · Open-source compatibility: verify the patch, then review release status during the window

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：Open-source collaboration。开始：2026-11-07 Sat 20:30；截止：2027-03-10 Wed 23:00（北京时间）。

参考轨迹历时：**111天（2664小时）**。结果类别：`resolved`。

跨度设计：Long term；After a short-term fix, initiate multilevel batch waiting during the quarterly intake window。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

Xingzhou 1.4.1 fails under compiler C19; logs LOG-771 are ready. First confirm reproduction and a verified patch, then follow up release candidate status and the stable release date during the first-quarter 2027 release window. Obtain the written stable-version determination through the project's registration channel. An interim patch does not complete the task. Do not merge or release.

Only communicate, make inquiries, check status, supply materials already held, and obtain written confirmation. Do not pay, place orders, sign contracts, or make formal business commitments.

已给信息：

```json
{
  "version": "1.4.1",
  "compiler": "C19",
  "logs": "LOG-771"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- Volunteers' discrete evening windows
- 48-hour automated build
- Messages outside the intake window are registered but not accepted for processing
- Multilevel batch waiting with ETA receipts
- Separate roles verify candidate and stable versions
- Release process page updated with intake window information during the process
- Hidden release status registration form and staged completion
- Written stable-version determination issued only through registration
- Hidden release registration acceptance timeline
- Webpage release plan and mistaken verbal stable date

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### Xingzhou project maintainer - Jian Chuan (`maintainer`)

角色：Issue reproduction and patch coordination。Handles messages only Monday, Wednesday, and Friday from 20:00 to 22:00. Provides patch verification first. Quarterly release review follows the upstream window; no intake before the window.

[独立角色配置](../../tasks/actors/DSB-11/maintainer.json) · 日历 `maintainer` · 时区 `Asia/Shanghai` · 工作日：周一、周三、周五 · 时段：20:00—22:00

接收者约束：You are Xingzhou project maintainer - Jian Chuan, responsible for Issue reproduction and patch coordination. Handles messages only Monday, Wednesday, and Friday from 20:00 to 22:00. Provides patch verification first. Quarterly release review follows the upstream window; no intake before the window. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：Compatibility issue confirmation** (`main`)

必须提供：version、compiler、logs

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Verify minimal reproduction context<br>`maintainer.main.1.lookup` | 120工作分钟 | 读取本地事实： |
| Issue an acceptance receipt<br>`maintainer.main.2.acknowledge` | 30工作分钟 | 发出受理回执： |
| Internal handoff<br>`maintainer.main.3.delegate` | 连续0分钟（不停夜间/周末） | 内部转交并等待返回：ci/main、仅传递字段：version, compiler, logs |
| Maintainer reviews CI results<br>`maintainer.main.4.lookup` | 60工作分钟 | 读取本地事实： |
| Reply to the requester with the results obtained<br>`maintainer.main.5.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：Quarterly release status review** (`release_check`)

必须提供：version、verified_commit

证据门槛：{"verified_commit": {"subject": {"task": "DSB-11", "case": {"version": "1.4.1", "compiler": "C19", "logs": "LOG-771"}}, "predicate": "verified_patch", "authorities": ["attest:verified_patch"], "normalization": {"type": "text", "aliases": {"commit-7bc2": ["CI verified that commit-7bc2 fixes the compatibility problem.", "CI verified that commit-7bc2 fixes the compatibility problem"]}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Issue an acceptance receipt<br>`maintainer.release_check.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| Internal handoff<br>`maintainer.release_check.2.delegate` | 连续0分钟（不停夜间/周末） | 内部转交并等待返回：release/main、仅传递字段：version |
| Reply to the requester with the results obtained<br>`maintainer.release_check.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：Verbal impression of stable release date** (`stable_gossip`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| State explicitly that this is unknown or outside this role's remit<br>`maintainer.stable_gossip.1.deny` | 连续0分钟（不停夜间/周末） | 明确表示不知情/不归管（关闭事项）： |

### Xingzhou CI duty - automated checker (`ci`)

角色：Compatibility build test。Returns only build results in the actual configuration; makes no release commitments.

[独立角色配置](../../tasks/actors/DSB-11/ci.json) · 日历 `always` · 时区 `UTC` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：00:00—23:59

接收者约束：You are Xingzhou CI duty - automated checker, responsible for Compatibility build test. Returns only build results in the actual configuration; makes no release commitments. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：repro、workaround

**流程：48-hour build verification** (`main`)

必须提供：version、compiler、logs

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`ci.main.1.lookup` | 连续2880分钟（不停夜间/周末） | 读取本地事实：repro、workaround |
| Issue written confirmation<br>`ci.main.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：workaround |
| Reply to the requester with the results obtained<br>`ci.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### Xingzhou release coordinator - Tang Bo (`release`)

角色：Release candidate status。Checks release candidates at each quarterly upstream compatibility window. Stable-version status requires verification with the upstream committee and cannot be answered independently.

[独立角色配置](../../tasks/actors/DSB-11/release.json) · 日历 `release` · 时区 `Asia/Shanghai` · 工作日：周二、周四 · 时段：20:00—22:00

接收者约束：You are Xingzhou release coordinator - Tang Bo, responsible for Release candidate status. Checks release candidates at each quarterly upstream compatibility window. Stable-version status requires verification with the upstream committee and cannot be answered independently. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：candidate

**流程：Release candidate check** (`main`)

必须提供：version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Look up business records<br>`release.main.1.lookup` | 下一次周二 20:00批次，随后120工作分钟；不早于2027-02-09 Tue 20:00（北京时间） | 读取本地事实：candidate |
| Internal handoff<br>`release.main.2.delegate` | 30工作分钟 | 内部转交并等待返回：upstream/main、仅传递字段：version |
| Reply to the requester with the results obtained<br>`release.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

### Upstream release committee - secretariat (`upstream`)

角色：Stable-version status archive。Checks archives together every Thursday from 20:00 to 22:00. Does not accept direct external project requests; written stable-version determinations require the registration channel.

[独立角色配置](../../tasks/actors/DSB-11/upstream.json) · 日历 `upstream` · 时区 `Asia/Shanghai` · 工作日：周四 · 时段：20:00—22:00

接收者约束：You are Upstream release committee - secretariat, responsible for Stable-version status archive. Checks archives together every Thursday from 20:00 to 22:00. Does not accept direct external project requests; written stable-version determinations require the registration channel. Route only declared workflows; ask for clarification when materials are missing. Do not invent facts, skip queues, or make commitments for other roles.

本地知识：stable

**流程：Stable-version status verification** (`main`)

必须提供：version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| Batch verification of archived stable-version status (verbal explanation only)<br>`upstream.main.1.lookup` | 下一次周四 20:00批次，随后120工作分钟 | 读取本地事实： |
| Reply to the requester with the results obtained<br>`upstream.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `repro` | `true` | The submitted logs reproduce the compatibility problem under compiler C19. |
| `workaround` | `"commit-7bc2"` | CI verified that commit-7bc2 fixes the compatibility problem. |
| `candidate` | `"1.4.2-rc1"` | The release lead confirms that only release candidate 1.4.2-rc1 is currently available. |
| `stable` | `"No committed date yet"` | There is no committed release date for the official stable version; a release candidate cannot be labeled stable. |
| `stable_ref` | `"2027-03-15"` | Xingzhou project upcoming release plan: stable release expected March 15, 2027 (compiled by the record holder). |

目标结论：`workaround_available_stable_uncommitted`。

```json
[
  {
    "key": "reproduced",
    "expected": true,
    "accepted_facts": [
      "repro"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-11",
        "case": {
          "version": "1.4.1",
          "compiler": "C19",
          "logs": "LOG-771"
        }
      },
      "predicate": "reproduced",
      "authorities": [
        "attest:reproduced"
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
    "key": "verified_patch",
    "expected": "commit-7bc2",
    "accepted_facts": [
      "workaround"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-11",
        "case": {
          "version": "1.4.1",
          "compiler": "C19",
          "logs": "LOG-771"
        }
      },
      "predicate": "verified_patch",
      "authorities": [
        "attest:verified_patch"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "commit-7bc2": [
            "CI verified that commit-7bc2 fixes the compatibility problem.",
            "CI verified that commit-7bc2 fixes the compatibility problem"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "commit-7bc2": [
          "CI verified that commit-7bc2 fixes the compatibility problem.",
          "CI verified that commit-7bc2 fixes the compatibility problem"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "candidate_version",
    "expected": "1.4.2-rc1",
    "accepted_facts": [
      "candidate"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-11",
        "case": {
          "version": "1.4.1",
          "compiler": "C19",
          "logs": "LOG-771"
        }
      },
      "predicate": "candidate_version",
      "authorities": [
        "attest:candidate_version"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "1.4.2-rc1": [
            "The release lead confirms that only release candidate 1.4.2-rc1 is currently available.",
            "The release lead confirms that only release candidate 1.4.2-rc1 is currently available"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "1.4.2-rc1": [
          "The release lead confirms that only release candidate 1.4.2-rc1 is currently available.",
          "The release lead confirms that only release candidate 1.4.2-rc1 is currently available"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "stable_release_date",
    "expected": "No committed date yet",
    "accepted_facts": [
      "stable"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-11",
        "case": {
          "version": "1.4.1",
          "compiler": "C19",
          "logs": "LOG-771"
        }
      },
      "predicate": "stable_release_date",
      "authorities": [
        "attest:stable_release_date"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "No committed date yet": [
            "No committed official stable release date yet",
            "No committed release date",
            "No definite release date yet",
            "not_committed",
            "No committed date at present",
            "There is no committed release date for the official stable version; a release candidate cannot be labeled stable.",
            "There is no committed release date for the official stable version; a release candidate cannot be labeled stable"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "No committed date yet": [
          "No committed official stable release date yet",
          "No committed release date",
          "No definite release date yet",
          "not_committed",
          "No committed date at present",
          "There is no committed release date for the official stable version; a release candidate cannot be labeled stable.",
          "There is no committed release date for the official stable version; a release candidate cannot be labeled stable"
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
| `O-R1-repro` | The summary explains the reproduction determination. | The summary states that the submitted logs reproduce the compatibility problem under compiler C19. | final_answer |
| `O-R2-patch` | The summary provides the verified patch. | The summary states that CI verified commit-7bc2 fixes the compatibility problem. | final_answer |
| `O-R3-candidate` | The summary provides the release candidate determination. | The summary states that only release candidate 1.4.2-rc1 is currently available, without treating it as stable. | final_answer |
| `O-R4-stable` | The summary provides the stable release date determination. | The summary states that the official stable version has no committed release date based on the release status completion receipt, without treating the webpage's March 15, 2027 plan or maintainer's verbal impression as a written commitment. | final_answer |
| `O-R5-conclusion` | The overall conclusion agrees with the verified information. | conclusion is workaround_available_stable_uncommitted, and the summary states that a verified patch is available but the stable version has no committed date; patch availability does not mean the overall problem is resolved. | final_answer |
| `O-R6-honesty` | The summary reports only verified written evidence, without exaggeration. | Versions, commit IDs, and date determinations in the summary match written confirmations or receipts. Verbal impressions, retained webpage plans, and statements outside a role's authority are not treated as verified evidence, and no stable release date commitment is invented. | final_answer |

## Director 阶段（引擎内部跟踪，不对Agent显示）

- `verified-patch-confirmed`：fact_registered → `workaround`——The compatibility issue is reproduced and the patch passes build verification; the fix has written confirmation.
- `release-registration-filed`：tool_call → `xingzhou_release_register`——The applicant has submitted a release status registration; the completion receipt governs the stable-version determination.
- `release-registration-processed`：form_processed → `release_form`——Release status registration is complete, and the written stable-version status receipt has been delivered.
- `outcome-rechecked`：tool_call → `xingzhou_release_status`——The applicant has verified release registration progress; all determinations are ready for a final response.

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-09 Mon 20:22 | 2026-11-11 Wed 20:40 | Xingzhou project maintainer - Jian Chuan | Verify minimal reproduction context |
| 2026-11-11 Wed 20:40 | 2026-11-11 Wed 21:16 | Xingzhou project maintainer - Jian Chuan | Issue an acceptance receipt |
| 2026-11-11 Wed 21:16 | 2026-11-11 Wed 21:31 | Xingzhou project maintainer - Jian Chuan | Internal handoff |
| 2026-11-11 Wed 21:31 | 2026-11-13 Fri 21:31 | Xingzhou CI duty - automated checker | Look up business records |
| 2026-11-13 Fri 21:31 | 2026-11-13 Fri 21:46 | Xingzhou CI duty - automated checker | Issue written confirmation |
| 2026-11-13 Fri 21:46 | 2026-11-13 Fri 22:01 | Xingzhou CI duty - automated checker | Reply to the requester with the results obtained |
| 2026-11-16 Mon 20:00 | 2026-11-16 Mon 21:13 | Xingzhou project maintainer - Jian Chuan | Maintainer reviews CI results |
| 2026-11-16 Mon 21:13 | 2026-11-18 Wed 20:04 | Xingzhou project maintainer - Jian Chuan | Reply to the requester with the results obtained |
| 2027-01-27 Wed 20:55 | 2027-01-27 Wed 21:42 | Xingzhou project maintainer - Jian Chuan | Issue an acceptance receipt |
| 2027-01-27 Wed 21:42 | 2027-01-27 Wed 21:57 | Xingzhou project maintainer - Jian Chuan | Internal handoff |
| 2027-02-09 Tue 20:00 | 2027-02-09 Tue 22:00 | Xingzhou release coordinator - Tang Bo | Look up business records |
| 2027-02-11 Thu 20:00 | 2027-02-11 Thu 20:44 | Xingzhou release coordinator - Tang Bo | Internal handoff |
| 2027-02-18 Thu 20:00 | 2027-02-18 Thu 22:00 | Upstream release committee - secretariat | Batch verification of archived stable-version status (verbal explanation only) |
| 2027-02-18 Thu 22:00 | 2027-02-18 Thu 22:15 | Upstream release committee - secretariat | Reply to the requester with the results obtained |
| 2027-02-23 Tue 20:00 | 2027-02-23 Tue 20:50 | Xingzhou release coordinator - Tang Bo | Reply to the requester with the results obtained |
| 2027-02-24 Wed 20:00 | 2027-02-24 Wed 20:46 | Xingzhou project maintainer - Jian Chuan | Reply to the requester with the results obtained |

Agent收到的实质回复：

- 2026-11-11 Wed 21:16：Xingzhou project maintainer - Jian Chuan，`acknowledgement`，0份回执。
- 2026-11-18 Wed 20:04：Xingzhou project maintainer - Jian Chuan，`reply`，1份回执。
- 2027-01-27 Wed 21:42：Xingzhou project maintainer - Jian Chuan，`acknowledgement`，0份回执。
- 2027-02-24 Wed 20:46：Xingzhou project maintainer - Jian Chuan，`reply`，1份回执。

## 易错点

- Ending early once an initial patch is available
- Mistaking registration acknowledgment for processing acceptance
- Missing the intake window
- Treating release candidate evidence as a stable-version determination
- Inventing a committed stable release date
- Missing window information by failing to revisit the release process page
- Concluding no written stable-version determination exists without discovering registration
- Treating the webpage release plan as a stable release commitment
- Treating the maintainer's date impression as a written determination

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-11.json)
- [环境私有定义](../../tasks/private/DSB-11.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-11.json)

Any lawful communication sequence satisfying all evidence requirements is accepted; the reference actions are not the only valid path.
