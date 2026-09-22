# DSB-11 · 开源兼容性：补丁验证后跟进跨季度发布

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：开源协作。开始：2026-11-07 Sat 20:30；截止：2027-04-01 Thu 23:00（北京时间）。

参考轨迹历时：**144天（3456小时）**。结果类别：`resolved`。

跨度设计：长期；短期修复后跨季度跟进候选发布。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

星舟1.4.1在C19编译器上失败，日志LOG-771已备好。先确认复现和验证过的补丁；再于2027年第一季度发布窗口跟进候选版与稳定版日期。中间补丁可用不代表本任务完成。不要合并或发布。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "version": "1.4.1",
  "compiler": "C19",
  "logs": "LOG-771"
}
```

初始联系人：maintainer

## 时间机制

- 志愿者离散晚间窗口
- 48小时自动构建
- 跨季度后带原补丁证据继续沟通
- 上游兼容窗口
- 候选版与稳定版区别

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 星舟项目维护者·简川 (`maintainer`)

角色：问题复现与补丁协调。只在周一三五20—22点处理；先给补丁验证结果，申请人应在次年第一季度发布窗口另行核实候选版与稳定版。

[独立角色配置](../../tasks/actors/DSB-11/maintainer.json) · 日历 `maintainer` · 时区 `Asia/Shanghai` · 工作日：周一、周三、周五 · 时段：20:00—22:00

接收者约束：你是星舟项目维护者·简川，负责问题复现与补丁协调。只在周一三五20—22点处理；先给补丁验证结果，申请人应在次年第一季度发布窗口另行核实候选版与稳定版。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：兼容问题确认** (`main`)

必须提供：version、compiler、logs

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 核实最小复现上下文<br>`maintainer.main.1.lookup` | 120工作分钟 | 读取本地事实： |
| 内部转交<br>`maintainer.main.2.delegate` | 连续0分钟（不停夜间/周末） | 内部转交并等待返回：ci/main、仅传递字段：version, compiler, logs |
| 维护者复核CI结果<br>`maintainer.main.3.lookup` | 60工作分钟 | 读取本地事实： |
| 向请求者回复已取得的结果<br>`maintainer.main.4.reply` | 30工作分钟 | 向父事项/Agent回复： |

**流程：季度发布状态复核** (`release_check`)

必须提供：version、verified_commit

证据门槛：{"verified_commit": {"subject": {"task": "DSB-11", "case": {"version": "1.4.1", "compiler": "C19", "logs": "LOG-771"}}, "predicate": "verified_patch", "authorities": ["attest:verified_patch"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`maintainer.release_check.1.delegate` | 连续0分钟（不停夜间/周末） | 内部转交并等待返回：release/main、仅传递字段：version |
| 向请求者回复已取得的结果<br>`maintainer.release_check.2.reply` | 30工作分钟 | 向父事项/Agent回复： |

### 星舟CI值守·自动检查器 (`ci`)

角色：兼容性构建测试。仅返回真实配置内的构建结果；不会承诺发布。

[独立角色配置](../../tasks/actors/DSB-11/ci.json) · 日历 `always` · 时区 `UTC` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：00:00—23:59

接收者约束：你是星舟CI值守·自动检查器，负责兼容性构建测试。仅返回真实配置内的构建结果；不会承诺发布。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：repro、workaround

**流程：48小时构建验证** (`main`)

必须提供：version、compiler、logs

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`ci.main.1.lookup` | 连续2880分钟（不停夜间/周末） | 读取本地事实：repro、workaround |
| 签发书面确认<br>`ci.main.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：workaround |
| 向请求者回复已取得的结果<br>`ci.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 星舟发布协调员·唐泊 (`release`)

角色：候选版与稳定版状态。上游兼容窗口在2027年3月30日20点开放；候选版与稳定版需在该季度窗口分别核对。

[独立角色配置](../../tasks/actors/DSB-11/release.json) · 日历 `release` · 时区 `Asia/Shanghai` · 工作日：周二、周四 · 时段：20:00—22:00

接收者约束：你是星舟发布协调员·唐泊，负责候选版与稳定版状态。上游兼容窗口在2027年3月30日20点开放；候选版与稳定版需在该季度窗口分别核对。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：candidate、stable

**流程：季度候选发布核对** (`main`)

必须提供：version

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`release.main.1.lookup` | 下一次周二 20:00批次，随后120工作分钟；不早于2027-03-30 Tue 20:00（北京时间） | 读取本地事实：candidate、stable |
| 向请求者回复已取得的结果<br>`release.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `repro` | `true` | 提交的日志可重现在编译器C19下的兼容问题。 |
| `workaround` | `"commit-7bc2"` | CI在commit-7bc2上验证该兼容问题已修复。 |
| `candidate` | `"1.4.2-rc1"` | 发布负责人确认当前仅有候选版1.4.2-rc1。 |
| `stable` | `"尚无承诺日期"` | 正式稳定版没有承诺发布日期；候选版不能标为稳定版。 |

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
    "key": "stable_release_date",
    "expected": "尚无承诺日期",
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
          "尚无承诺日期": [
            "尚未承诺正式稳定版发布日期",
            "未承诺发布日期",
            "暂无确定的发布日期",
            "not_committed",
            "暂无承诺日期"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "尚无承诺日期": [
          "尚未承诺正式稳定版发布日期",
          "未承诺发布日期",
          "暂无确定的发布日期",
          "not_committed",
          "暂无承诺日期"
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
| 2026-11-09 Mon 20:00 | 2026-11-09 Mon 22:00 | 星舟项目维护者·简川 | 核实最小复现上下文 |
| 2026-11-09 Mon 22:00 | 2026-11-09 Mon 22:00 | 星舟项目维护者·简川 | 内部转交 |
| 2026-11-09 Mon 22:00 | 2026-11-11 Wed 22:00 | 星舟CI值守·自动检查器 | 查询业务记录 |
| 2026-11-11 Wed 22:00 | 2026-11-11 Wed 22:00 | 星舟CI值守·自动检查器 | 签发书面确认 |
| 2026-11-11 Wed 22:00 | 2026-11-11 Wed 22:00 | 星舟CI值守·自动检查器 | 向请求者回复已取得的结果 |
| 2026-11-13 Fri 20:00 | 2026-11-13 Fri 21:00 | 星舟项目维护者·简川 | 维护者复核CI结果 |
| 2026-11-13 Fri 21:00 | 2026-11-13 Fri 21:30 | 星舟项目维护者·简川 | 向请求者回复已取得的结果 |
| 2027-03-29 Mon 20:00 | 2027-03-29 Mon 20:00 | 星舟项目维护者·简川 | 内部转交 |
| 2027-03-30 Tue 20:00 | 2027-03-30 Tue 22:00 | 星舟发布协调员·唐泊 | 查询业务记录 |
| 2027-03-30 Tue 22:00 | 2027-03-30 Tue 22:00 | 星舟发布协调员·唐泊 | 向请求者回复已取得的结果 |
| 2027-03-31 Wed 20:00 | 2027-03-31 Wed 20:30 | 星舟项目维护者·简川 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-13 Fri 21:30：星舟项目维护者·简川，`reply`，3条文本证据。
- 2027-03-31 Wed 20:30：星舟项目维护者·简川，`reply`，2条文本证据。

## 易错点

- 初步补丁可用就提前结束
- 跨季度后丢失原补丁证据
- 杜撰稳定版承诺日期

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-11.json)
- [环境私有定义](../../tasks/private/DSB-11.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-11.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
