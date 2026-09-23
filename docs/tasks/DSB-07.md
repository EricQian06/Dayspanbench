# DSB-07 · 档案使用：权利继受核验后重新启动数字化

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：文化档案。开始：2026-11-05 Thu 15:00；截止：2027-06-07 Mon 17:00（北京时间）。

参考轨迹历时：**213.841天（5132.18小时）**。结果类别：`resolved`。

跨度设计：长期；权利继受核验后再次申请数字化。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

为2027年7月的非商业展览核实ARC-71图像的实体及网站用途权限，问清总费用与扫描分辨率。权利继受正在核验；取得权利方确认后请再次联系档案馆核实数字化交付。不付费、不发布。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "archive_id": "ARC-71",
  "usage": "非商业实体展览及展览网站"
}
```

初始联系人：无（须由Agent搜索公开页面发现）

## 时间机制

- 跨年度权利继受核验
- 纽约冬令时和夏令时
- 取得许可后必须再次发起请求
- 72小时图像恢复与人工验收

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 北汀档案馆接待·关雨 (`archive`)

角色：档案使用咨询。先提供费用和权利联系人；权利继受确认后，申请人须携确认结果再次联系档案馆，才能转数字化组。

[独立角色配置](../../tasks/actors/DSB-07/archive.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是北汀档案馆接待·关雨，负责档案使用咨询。先提供费用和权利联系人；权利继受确认后，申请人须携确认结果再次联系档案馆，才能转数字化组。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：fee

**流程：费用与权利联系人** (`main`)

必须提供：archive_id、usage

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`archive.main.1.lookup` | 120工作分钟 | 读取本地事实：fee |
| 查询联系人目录并转介<br>`archive.main.2.refer` | 30工作分钟 | 公开转介联系人：rights |
| 向请求者回复已取得的结果<br>`archive.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

**流程：取得许可后的数字化规格确认** (`digitize`)

必须提供：archive_id、exhibition_permission

证据门槛：{"exhibition_permission": {"subject": {"task": "DSB-07", "case": {"archive_id": "ARC-71", "usage": "非商业实体展览及展览网站"}}, "predicate": "physical_exhibit_allowed", "authorities": ["attest:physical_exhibit_allowed"], "normalization": {"type": "boolean"}}}；仅猜对值不算取得凭证。

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`archive.digitize.1.delegate` | 120工作分钟 | 内部转交并等待返回：digitizer/main、仅传递字段：archive_id |
| 向请求者回复已取得的结果<br>`archive.digitize.2.reply` | 120工作分钟 | 向父事项/Agent回复： |

### 权利方联络员·Alex Chen (`rights`)

角色：图像权利继受与用途确认。权利继受文件在2027年5月28日集中核验；随后按纽约当地工作时间审查指定用途，结束时自动签发确认，此前不能批准。

[独立角色配置](../../tasks/actors/DSB-07/rights.json) · 日历 `new_york` · 时区 `America/New_York` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—17:00

接收者约束：你是权利方联络员·Alex Chen，负责图像权利继受与用途确认。权利继受文件在2027年5月28日集中核验；随后按纽约当地工作时间审查指定用途，结束时自动签发确认，此前不能批准。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：exhibit、online

**流程：权利范围核实** (`main`)

必须提供：archive_id、usage

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`rights.main.1.lookup` | 480工作分钟；不早于2027-05-28 Fri 21:00（北京时间） | 读取本地事实：exhibit、online |
| 签发书面确认<br>`rights.main.2.document` | 连续0分钟（不停夜间/周末） | 签发文本证据：exhibit、online |
| 向请求者回复已取得的结果<br>`rights.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 档案数字化员·林澈 (`digitizer`)

角色：扫描规格。扫描与图像恢复连续处理72小时，质量确认必须在工作时间完成。

[独立角色配置](../../tasks/actors/DSB-07/digitizer.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是档案数字化员·林澈，负责扫描规格。扫描与图像恢复连续处理72小时，质量确认必须在工作时间完成。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：scan

**流程：扫描质量核对** (`main`)

必须提供：archive_id

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 保护性数字化与图像恢复连续处理72小时<br>`digitizer.main.1.lookup` | 连续4320分钟（不停夜间/周末） | 读取本地事实： |
| 签发书面确认<br>`digitizer.main.2.document` | 60工作分钟 | 签发文本证据：scan |
| 向请求者回复已取得的结果<br>`digitizer.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `exhibit` | `true` | 图像ARC-71获准用于本次非商业实体展览。 |
| `online` | `false` | 授权不包含网站或社交媒体公开发布。 |
| `fee` | `800` | 本次数字化和授权服务合计800元。 |
| `scan` | `600` | 可提供600dpi扫描件；文件用途仍受授权范围限制。 |

目标结论：`physical_only`。

```json
[
  {
    "key": "physical_exhibit_allowed",
    "expected": true,
    "accepted_facts": [
      "exhibit"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "非商业实体展览及展览网站"
        }
      },
      "predicate": "physical_exhibit_allowed",
      "authorities": [
        "attest:physical_exhibit_allowed"
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
    "key": "online_allowed",
    "expected": false,
    "accepted_facts": [
      "online"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "非商业实体展览及展览网站"
        }
      },
      "predicate": "online_allowed",
      "authorities": [
        "attest:online_allowed"
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
    "key": "total_fee",
    "expected": 800,
    "accepted_facts": [
      "fee"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "非商业实体展览及展览网站"
        }
      },
      "predicate": "total_fee",
      "authorities": [
        "attest:total_fee"
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
    "key": "scan_dpi",
    "expected": 600,
    "accepted_facts": [
      "scan"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-07",
        "case": {
          "archive_id": "ARC-71",
          "usage": "非商业实体展览及展览网站"
        }
      },
      "predicate": "scan_dpi",
      "authorities": [
        "attest:scan_dpi"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "dpi": 1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "dpi": 1
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
| 2026-11-06 Fri 10:48 | 2026-11-06 Fri 14:05 | 北汀档案馆接待·关雨 | 查询业务记录 |
| 2026-11-06 Fri 14:05 | 2026-11-06 Fri 14:53 | 北汀档案馆接待·关雨 | 查询联系人目录并转介 |
| 2026-11-06 Fri 14:53 | 2026-11-06 Fri 15:08 | 北汀档案馆接待·关雨 | 向请求者回复已取得的结果 |
| 2027-05-28 Fri 21:00 | 2027-05-31 Mon 21:13 | 权利方联络员·Alex Chen | 查询业务记录 |
| 2027-05-31 Mon 21:13 | 2027-05-31 Mon 21:28 | 权利方联络员·Alex Chen | 签发书面确认 |
| 2027-05-31 Mon 21:28 | 2027-05-31 Mon 21:43 | 权利方联络员·Alex Chen | 向请求者回复已取得的结果 |
| 2027-06-01 Tue 13:05 | 2027-06-01 Tue 15:25 | 北汀档案馆接待·关雨 | 内部转交 |
| 2027-06-01 Tue 15:25 | 2027-06-04 Fri 15:25 | 档案数字化员·林澈 | 保护性数字化与图像恢复连续处理72小时 |
| 2027-06-04 Fri 15:25 | 2027-06-04 Fri 16:42 | 档案数字化员·林澈 | 签发书面确认 |
| 2027-06-04 Fri 16:42 | 2027-06-04 Fri 16:57 | 档案数字化员·林澈 | 向请求者回复已取得的结果 |
| 2027-06-04 Fri 16:57 | 2027-06-07 Mon 11:11 | 北汀档案馆接待·关雨 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-06 Fri 15:08：北汀档案馆接待·关雨，`reply`，1条文本证据。
- 2027-05-31 Mon 21:43：权利方联络员·Alex Chen，`reply`，4条文本证据。
- 2027-06-07 Mon 11:11：北汀档案馆接待·关雨，`reply`，1条文本证据。

## 易错点

- 等待期间擅自假定许可
- 实体授权误推为网络授权
- 收到许可后忘记重启数字化查询

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-07.json)
- [环境私有定义](../../tasks/private/DSB-07.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-07.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
