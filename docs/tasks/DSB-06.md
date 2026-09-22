# DSB-06 · 家电保修：等待原厂补货与工程师轮值

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：售后服务。开始：2026-11-04 Wed 16:00；截止：2026-11-18 Wed 09:00（北京时间）。

参考轨迹历时：**13天（312小时）**。结果类别：`resolved`。

跨度设计：中短期；原厂配件批次与每周两天的工程师轮值。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

设备SN-A731漏水。确认是否在保修范围、需要什么配件、配件费用、最早可上门时间。购机凭证R-731已在我手中，只咨询，不预约。与各对接方往来沟通时，日期一律按委托信息原文的规范格式（YYYY-MM-DD，如2026-11-13）书写，请勿改用其他写法。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "serial": "SN-A731",
  "receipt": "R-731",
  "symptom": "机身接缝漏水"
}
```

初始联系人：support

## 时间机制

- 缺材料状态与补件
- 原厂批次补货
- 工程师每周两天办公
- 零件库周六办公
- 多级转交后回传

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 霁光电器客服·孟竹 (`support`)

角色：保修材料受理。没有凭证不能判定覆盖；拿到诊断和库存后才报告可用时段。

[独立角色配置](../../tasks/actors/DSB-06/support.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是霁光电器客服·孟竹，负责保修材料受理。没有凭证不能判定覆盖；拿到诊断和库存后才报告可用时段。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：covered

**流程：保修及维修时间咨询** (`main`)

必须提供：serial、receipt

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`support.main.1.lookup` | 60工作分钟 | 读取本地事实：covered |
| 内部转交<br>`support.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：engineer/main、仅传递字段：serial, symptom |
| 向请求者回复已取得的结果<br>`support.main.3.reply` | 60工作分钟 | 向父事项/Agent回复： |

### 霁光工程师·韩则 (`engineer`)

角色：诊断与维修窗口。仅周二、周四处理远程诊断和排期；周四14点集中诊断，补货后需复核型号和上门窗口。

[独立角色配置](../../tasks/actors/DSB-06/engineer.json) · 日历 `engineer` · 时区 `Asia/Shanghai` · 工作日：周二、周四 · 时段：10:00—12:00 / 14:00—17:00

接收者约束：你是霁光工程师·韩则，负责诊断与维修窗口。仅周二、周四处理远程诊断和排期；周四14点集中诊断，补货后需复核型号和上门窗口。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：part、visit

**流程：诊断故障** (`main`)

必须提供：serial、symptom

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`engineer.main.1.lookup` | 下一次周四 14:00批次，随后120工作分钟 | 读取本地事实：part |
| 内部转交<br>`engineer.main.2.delegate` | 60工作分钟 | 内部转交并等待返回：parts/main、仅传递字段：serial |
| 查询业务记录<br>`engineer.main.3.lookup` | 180工作分钟 | 读取本地事实：visit |
| 向请求者回复已取得的结果<br>`engineer.main.4.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 霁光零件库·纪桐 (`parts`)

角色：配件与费用。原厂补货批次11月13日到库，需16个工作小时核验；周六办公、周日关闭。

[独立角色配置](../../tasks/actors/DSB-06/parts.json) · 日历 `factory` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六 · 时段：08:30—12:00 / 13:00—17:30

接收者约束：你是霁光零件库·纪桐，负责配件与费用。原厂补货批次11月13日到库，需16个工作小时核验；周六办公、周日关闭。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：cost

**流程：零件库存复核** (`main`)

必须提供：serial

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`parts.main.1.lookup` | 960工作分钟；不早于2026-11-13 Fri 08:30（北京时间） | 读取本地事实：cost |
| 向请求者回复已取得的结果<br>`parts.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `covered` | `true` | 设备SN-A731仍在本次合成保修条款覆盖范围内。 |
| `part` | `"G-42密封圈"` | 工程师诊断需要更换G-42密封圈。 |
| `cost` | `0` | 本次更换配件费用为0元。 |
| `visit` | `"2026-11-18T10:00:00+08:00"` | 核实返厂补货批次后，最早可上门时段为11月18日10点，尚未预约。 |

目标结论：`covered_pending_booking`。

```json
[
  {
    "key": "covered",
    "expected": true,
    "accepted_facts": [
      "covered"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "机身接缝漏水"
        }
      },
      "predicate": "covered",
      "authorities": [
        "attest:covered"
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
    "key": "replacement_part",
    "expected": "G-42密封圈",
    "accepted_facts": [
      "part"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "机身接缝漏水"
        }
      },
      "predicate": "replacement_part",
      "authorities": [
        "attest:replacement_part"
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
    "key": "part_cost",
    "expected": 0,
    "accepted_facts": [
      "cost"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "机身接缝漏水"
        }
      },
      "predicate": "part_cost",
      "authorities": [
        "attest:part_cost"
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
    "key": "earliest_visit",
    "expected": "2026-11-18T10:00:00+08:00",
    "accepted_facts": [
      "visit"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-06",
        "case": {
          "serial": "SN-A731",
          "receipt": "R-731",
          "symptom": "机身接缝漏水"
        }
      },
      "predicate": "earliest_visit",
      "authorities": [
        "attest:earliest_visit"
      ],
      "normalization": {
        "type": "datetime"
      }
    },
    "normalization": {
      "type": "datetime"
    },
    "match": "expected"
  }
]
```

## 已验证参考时间线

时间为北京时间；纽约角色的日历计算仍使用America/New_York。内部阶段只出现在评审日志，不对Agent显示。

| 开始 | 完成/预计完成 | 人物 | 阶段 |
|---|---|---|---|
| 2026-11-04 Wed 16:00 | 2026-11-04 Wed 17:00 | 霁光电器客服·孟竹 | 查询业务记录 |
| 2026-11-05 Thu 09:00 | 2026-11-05 Thu 10:00 | 霁光电器客服·孟竹 | 内部转交 |
| 2026-11-05 Thu 14:00 | 2026-11-05 Thu 16:00 | 霁光工程师·韩则 | 查询业务记录 |
| 2026-11-05 Thu 16:00 | 2026-11-05 Thu 17:00 | 霁光工程师·韩则 | 内部转交 |
| 2026-11-13 Fri 08:30 | 2026-11-14 Sat 17:30 | 霁光零件库·纪桐 | 查询业务记录 |
| 2026-11-14 Sat 17:30 | 2026-11-14 Sat 17:30 | 霁光零件库·纪桐 | 向请求者回复已取得的结果 |
| 2026-11-17 Tue 10:00 | 2026-11-17 Tue 15:00 | 霁光工程师·韩则 | 查询业务记录 |
| 2026-11-17 Tue 15:00 | 2026-11-17 Tue 15:00 | 霁光工程师·韩则 | 向请求者回复已取得的结果 |
| 2026-11-17 Tue 15:00 | 2026-11-17 Tue 16:00 | 霁光电器客服·孟竹 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-04 Wed 16:00：霁光电器客服·孟竹，`needs_information`，0条文本证据。
- 2026-11-17 Tue 16:00：霁光电器客服·孟竹，`reply`，4条文本证据。

## 易错点

- 漏凭证仍要求出结果
- 库存到位即认为已预约
- 忽略工程师周一不办公

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-06.json)
- [环境私有定义](../../tasks/private/DSB-06.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-06.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
