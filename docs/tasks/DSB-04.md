# DSB-04 · 共享仪器：培训、进口耗材与七天稳定性校准

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：科研设施。开始：2026-11-04 Wed 09:30；截止：2026-11-25 Wed 17:00（北京时间）。

参考轨迹历时：**21.0556天（505.33小时）**。结果类别：`resolved`。

跨度设计：中短期；进口耗材批次与7天连续稳定性校准。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

为样品S-482确认最早测量时间和费用。我已报名11月6日14点安全培训并会按时完成，但目前没有合格记录。请在培训完成后取得凭证，并核实耗材和校准后的可用窗口，暂不预约仪器。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "sample_id": "S-482",
  "person_name": "顾晓"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- 周五培训批次
- 进口耗材批次到货
- 连续7天设备过程
- 校准结束后仍等待人员复核

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 南屿共享实验室前台·叶青 (`labdesk`)

角色：使用条件与联系人。先说明安全培训要求，再提供仪器管理员入口。

[独立角色配置](../../tasks/actors/DSB-04/labdesk.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是南屿共享实验室前台·叶青，负责使用条件与联系人。先说明安全培训要求，再提供仪器管理员入口。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：测量咨询入口** (`main`)

必须提供：无额外字段

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询联系人目录并转介<br>`labdesk.main.1.refer` | 30工作分钟 | 公开转介联系人：safety、instrument |
| 向请求者回复已取得的结果<br>`labdesk.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 南屿实验室安全员·温遥 (`safety`)

角色：安全培训与合格记录。每周五14点培训，结束后签发记录。

[独立角色配置](../../tasks/actors/DSB-04/safety.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是南屿实验室安全员·温遥，负责安全培训与合格记录。每周五14点培训，结束后签发记录。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：certificate

**流程：培训记录确认** (`main`)

必须提供：person_name

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`safety.main.1.lookup` | 下一次周五 14:00批次，随后120工作分钟 | 读取本地事实：certificate |
| 签发书面确认<br>`safety.main.2.document` | 60工作分钟 | 签发文本证据：certificate |
| 向请求者回复已取得的结果<br>`safety.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 仪器管理员·杜和 (`instrument`)

角色：耗材、校准和使用窗口。须核实培训凭证；耗材到库后才启动连续7天稳定性校准。

[独立角色配置](../../tasks/actors/DSB-04/instrument.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是仪器管理员·杜和，负责耗材、校准和使用窗口。须核实培训凭证；耗材到库后才启动连续7天稳定性校准。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：price、window

**流程：测量可用时间与费用** (`main`)

必须提供：sample_id、safety_certificate

证据门槛：{"safety_certificate": {"subject": {"task": "DSB-04", "case": {"sample_id": "S-482", "person_name": "顾晓"}}, "predicate": "safety_certificate", "authorities": ["attest:safety_certificate"], "normalization": {"type": "text", "aliases": {}}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 发出受理回执<br>`instrument.main.1.acknowledge` | 30工作分钟 | 发出受理回执： |
| 内部转交<br>`instrument.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：stores/main、仅传递字段：sample_id |
| 连续7天稳定性校准，可跨夜运行<br>`instrument.main.3.lookup` | 连续10080分钟（不停夜间/周末） | 读取本地事实： |
| 核对校准结果和使用窗口<br>`instrument.main.4.lookup` | 240工作分钟 | 读取本地事实：window、price |
| 签发书面确认<br>`instrument.main.5.document` | 30工作分钟 | 签发文本证据：window、price |
| 向请求者回复已取得的结果<br>`instrument.main.6.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 耗材库管理员·宋野 (`stores`)

角色：滤芯收货检查。本批供应商11月17日10点后送达，入库检查还需要2个工作小时。

[独立角色配置](../../tasks/actors/DSB-04/stores.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是耗材库管理员·宋野，负责滤芯收货检查。本批供应商11月17日10点后送达，入库检查还需要2个工作小时。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：filter

**流程：核实滤芯到库** (`main`)

必须提供：sample_id

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`stores.main.1.lookup` | 120工作分钟；不早于2026-11-17 Tue 10:00（北京时间） | 读取本地事实：filter |
| 向请求者回复已取得的结果<br>`stores.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `certificate` | `"SAFE-NOV06-482"` | 人员安全培训已完成，记录号SAFE-NOV06-482，可用于本次仪器使用咨询。 |
| `filter` | `"F-26B"` | 本次测量所需F-26B滤芯已到库。 |
| `window` | `"2026-11-25T13:00:00+08:00"` | 完成7天稳定性校准后，最早可用测量时段为11月25日13点。 |
| `price` | `1800` | 该样品批次测量报价1800元，尚未预约或扣费。 |

目标结论：`available_after_calibration`。

```json
[
  {
    "key": "safety_certificate",
    "expected": "SAFE-NOV06-482",
    "accepted_facts": [
      "certificate"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-04",
        "case": {
          "sample_id": "S-482",
          "person_name": "顾晓"
        }
      },
      "predicate": "safety_certificate",
      "authorities": [
        "attest:safety_certificate"
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
    "key": "filter_batch",
    "expected": "F-26B",
    "accepted_facts": [
      "filter"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-04",
        "case": {
          "sample_id": "S-482",
          "person_name": "顾晓"
        }
      },
      "predicate": "filter_batch",
      "authorities": [
        "attest:filter_batch"
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
    "key": "earliest_measurement",
    "expected": "2026-11-25T13:00:00+08:00",
    "accepted_facts": [
      "window"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-04",
        "case": {
          "sample_id": "S-482",
          "person_name": "顾晓"
        }
      },
      "predicate": "earliest_measurement",
      "authorities": [
        "attest:earliest_measurement"
      ],
      "normalization": {
        "type": "datetime"
      }
    },
    "normalization": {
      "type": "datetime"
    },
    "match": "expected"
  },
  {
    "key": "price",
    "expected": 1800,
    "accepted_facts": [
      "price"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-04",
        "case": {
          "sample_id": "S-482",
          "person_name": "顾晓"
        }
      },
      "predicate": "price",
      "authorities": [
        "attest:price"
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
  }
]
```

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-04 Wed 10:02 | 2026-11-04 Wed 10:50 | 南屿共享实验室前台·叶青 | 查询联系人目录并转介 |
| 2026-11-04 Wed 10:50 | 2026-11-04 Wed 11:05 | 南屿共享实验室前台·叶青 | 向请求者回复已取得的结果 |
| 2026-11-06 Fri 14:00 | 2026-11-06 Fri 16:00 | 南屿实验室安全员·温遥 | 查询业务记录 |
| 2026-11-06 Fri 16:00 | 2026-11-09 Mon 09:13 | 南屿实验室安全员·温遥 | 签发书面确认 |
| 2026-11-09 Mon 09:13 | 2026-11-09 Mon 09:28 | 南屿实验室安全员·温遥 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 10:04 | 2026-11-09 Mon 10:54 | 仪器管理员·杜和 | 发出受理回执 |
| 2026-11-09 Mon 10:54 | 2026-11-09 Mon 13:11 | 仪器管理员·杜和 | 内部转交 |
| 2026-11-17 Tue 10:00 | 2026-11-17 Tue 13:14 | 耗材库管理员·宋野 | 查询业务记录 |
| 2026-11-17 Tue 13:14 | 2026-11-17 Tue 13:29 | 耗材库管理员·宋野 | 向请求者回复已取得的结果 |
| 2026-11-17 Tue 13:29 | 2026-11-24 Tue 13:29 | 仪器管理员·杜和 | 连续7天稳定性校准，可跨夜运行 |
| 2026-11-24 Tue 13:29 | 2026-11-25 Wed 09:49 | 仪器管理员·杜和 | 核对校准结果和使用窗口 |
| 2026-11-25 Wed 09:49 | 2026-11-25 Wed 10:35 | 仪器管理员·杜和 | 签发书面确认 |
| 2026-11-25 Wed 10:35 | 2026-11-25 Wed 10:50 | 仪器管理员·杜和 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-04 Wed 11:05：南屿共享实验室前台·叶青，`reply`，0条文本证据。
- 2026-11-09 Mon 09:28：南屿实验室安全员·温遥，`reply`，2条文本证据。
- 2026-11-09 Mon 10:54：仪器管理员·杜和，`acknowledgement`，0条文本证据。
- 2026-11-25 Wed 10:50：仪器管理员·杜和，`reply`，5条文本证据。

## 易错点

- 7天连续运行误算为7个工作日
- 有耗材就认为可测量
- 伪造安全培训记录

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-04.json)
- [环境私有定义](../../tasks/private/DSB-04.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-04.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
