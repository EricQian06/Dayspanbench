# DSB-08 · 无障碍住宿：两家机构比较与延后的现场测量

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：出行住宿。开始：2026-11-06 Fri 13:30；截止：2026-11-12 Thu 18:00（北京时间）。

参考轨迹历时：**5天（120小时）**。结果类别：`resolved`。

跨度设计：短期；指定房间可进入时间与两机构交叉核实。这是作者参考路径的历时，非最短可行耗时。

## 用户委托

在A旅舍和B酒店中选择11月14—16日两晚住宿，预算2600元。轮椅宽78cm，房门和浴室净宽均须至少80cm。获取实测尺寸，并确认合适酒店的房态和总价，不预订。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "wheelchair_width": "78cm，要求净宽至少80cm",
  "stay_dates": "2026-11-14/2026-11-16"
}
```

初始联系人：a_desk

## 时间机制

- 周末接待与工作日技术岗
- 并行联系两家机构
- 房间特定可进入时间
- 过期网页尺寸

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### A旅舍前台·蓝心 (`a_desk`)

角色：无障碍房咨询。每天营业，但不能用旧网页尺寸替代现场复测。

[独立角色配置](../../tasks/actors/DSB-08/a_desk.json) · 日历 `daily` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：09:00—12:00 / 13:00—18:00

接收者约束：你是A旅舍前台·蓝心，负责无障碍房咨询。每天营业，但不能用旧网页尺寸替代现场复测。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：没有直接持有的目标事实；按声明工具进行转介、核验或内部查询

**流程：通行尺寸确认** (`main`)

必须提供：wheelchair_width、stay_dates

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`a_desk.main.1.delegate` | 60工作分钟 | 内部转交并等待返回：a_tech/main、仅传递字段：wheelchair_width |
| 向请求者回复已取得的结果<br>`a_desk.main.2.reply` | 30工作分钟 | 向父事项/Agent回复： |

### A旅舍设施员·蒋延 (`a_tech`)

角色：现场测量。周末不在岗；测量记录区分净宽与含框宽度。

[独立角色配置](../../tasks/actors/DSB-08/a_tech.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是A旅舍设施员·蒋延，负责现场测量。周末不在岗；测量记录区分净宽与含框宽度。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：a_bath、a_door

**流程：现场通行测量** (`main`)

必须提供：wheelchair_width

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`a_tech.main.1.lookup` | 120工作分钟 | 读取本地事实：a_door、a_bath |
| 签发书面确认<br>`a_tech.main.2.document` | 0工作分钟 | 签发文本证据：a_door、a_bath |
| 向请求者回复已取得的结果<br>`a_tech.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### B酒店预订咨询·米禾 (`b_desk`)

角色：房态与费用。房态与价格可以先查询，是否可通行须现场量测。

[独立角色配置](../../tasks/actors/DSB-08/b_desk.json) · 日历 `daily` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：09:00—12:00 / 13:00—18:00

接收者约束：你是B酒店预订咨询·米禾，负责房态与费用。房态与价格可以先查询，是否可通行须现场量测。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：b_available、b_price

**流程：无障碍房确认** (`main`)

必须提供：wheelchair_width、stay_dates

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`b_desk.main.1.lookup` | 60工作分钟 | 读取本地事实：b_available、b_price |
| 内部转交<br>`b_desk.main.2.delegate` | 30工作分钟 | 内部转交并等待返回：b_tech/main、仅传递字段：wheelchair_width |
| 向请求者回复已取得的结果<br>`b_desk.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

### B酒店设施主管·郑砚 (`b_tech`)

角色：指定房型现场尺寸。指定房间11月11日10点才能进入复测；不能用同楼层其他房间数据代替。

[独立角色配置](../../tasks/actors/DSB-08/b_tech.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是B酒店设施主管·郑砚，负责指定房型现场尺寸。指定房间11月11日10点才能进入复测；不能用同楼层其他房间数据代替。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：b_bath、b_door

**流程：指定房间量测** (`main`)

必须提供：wheelchair_width

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`b_tech.main.1.lookup` | 120工作分钟；不早于2026-11-11 Wed 10:00（北京时间） | 读取本地事实：b_door、b_bath |
| 签发书面确认<br>`b_tech.main.2.document` | 0工作分钟 | 签发文本证据：b_door、b_bath |
| 向请求者回复已取得的结果<br>`b_tech.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `a_door` | `72` | A旅舍现场复测净门宽72cm，旧网页88cm包含门框。 |
| `a_bath` | `68` | A旅舍浴室通行净宽68cm。 |
| `b_door` | `92` | B酒店指定无障碍房净门宽92cm。 |
| `b_bath` | `85` | B酒店浴室通行净宽85cm。 |
| `b_available` | `true` | 11月14—16日指定无障碍房有可售房，尚未预订。 |
| `b_price` | `2360` | 11月14—16日两晚总房费2360元。 |

目标结论：`choose_b`。

```json
[
  {
    "key": "a_door_cm",
    "expected": 72,
    "accepted_facts": [
      "a_door"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "a_door_cm",
      "authorities": [
        "attest:a_door_cm"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "cm": 1,
          "厘米": 1,
          "m": 100,
          "米": 100,
          "mm": 0.1,
          "毫米": 0.1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "cm": 1,
        "厘米": 1,
        "m": 100,
        "米": 100,
        "mm": 0.1,
        "毫米": 0.1
      }
    },
    "match": "expected"
  },
  {
    "key": "a_bathroom_cm",
    "expected": 68,
    "accepted_facts": [
      "a_bath"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "a_bathroom_cm",
      "authorities": [
        "attest:a_bathroom_cm"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "cm": 1,
          "厘米": 1,
          "m": 100,
          "米": 100,
          "mm": 0.1,
          "毫米": 0.1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "cm": 1,
        "厘米": 1,
        "m": 100,
        "米": 100,
        "mm": 0.1,
        "毫米": 0.1
      }
    },
    "match": "expected"
  },
  {
    "key": "b_door_cm",
    "expected": 92,
    "accepted_facts": [
      "b_door"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "b_door_cm",
      "authorities": [
        "attest:b_door_cm"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "cm": 1,
          "厘米": 1,
          "m": 100,
          "米": 100,
          "mm": 0.1,
          "毫米": 0.1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "cm": 1,
        "厘米": 1,
        "m": 100,
        "米": 100,
        "mm": 0.1,
        "毫米": 0.1
      }
    },
    "match": "expected"
  },
  {
    "key": "b_bathroom_cm",
    "expected": 85,
    "accepted_facts": [
      "b_bath"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "b_bathroom_cm",
      "authorities": [
        "attest:b_bathroom_cm"
      ],
      "normalization": {
        "type": "number",
        "units": {
          "cm": 1,
          "厘米": 1,
          "m": 100,
          "米": 100,
          "mm": 0.1,
          "毫米": 0.1
        }
      }
    },
    "normalization": {
      "type": "number",
      "units": {
        "cm": 1,
        "厘米": 1,
        "m": 100,
        "米": 100,
        "mm": 0.1,
        "毫米": 0.1
      }
    },
    "match": "expected"
  },
  {
    "key": "b_available",
    "expected": true,
    "accepted_facts": [
      "b_available"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "b_available",
      "authorities": [
        "attest:b_available"
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
    "key": "b_total_price",
    "expected": 2360,
    "accepted_facts": [
      "b_price"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-08",
        "case": {
          "wheelchair_width": "78cm，要求净宽至少80cm",
          "stay_dates": "2026-11-14/2026-11-16"
        }
      },
      "predicate": "b_total_price",
      "authorities": [
        "attest:b_total_price"
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
| 2026-11-06 Fri 13:30 | 2026-11-06 Fri 14:30 | A旅舍前台·蓝心 | 内部转交 |
| 2026-11-06 Fri 13:30 | 2026-11-06 Fri 14:30 | B酒店预订咨询·米禾 | 查询业务记录 |
| 2026-11-06 Fri 14:30 | 2026-11-06 Fri 16:30 | A旅舍设施员·蒋延 | 查询业务记录 |
| 2026-11-06 Fri 14:30 | 2026-11-06 Fri 15:00 | B酒店预订咨询·米禾 | 内部转交 |
| 2026-11-11 Wed 10:00 | 2026-11-11 Wed 12:00 | B酒店设施主管·郑砚 | 查询业务记录 |
| 2026-11-06 Fri 16:30 | 2026-11-06 Fri 16:30 | A旅舍设施员·蒋延 | 签发书面确认 |
| 2026-11-06 Fri 16:30 | 2026-11-06 Fri 16:30 | A旅舍设施员·蒋延 | 向请求者回复已取得的结果 |
| 2026-11-06 Fri 16:30 | 2026-11-06 Fri 17:00 | A旅舍前台·蓝心 | 向请求者回复已取得的结果 |
| 2026-11-11 Wed 13:00 | 2026-11-11 Wed 13:00 | B酒店设施主管·郑砚 | 签发书面确认 |
| 2026-11-11 Wed 13:00 | 2026-11-11 Wed 13:00 | B酒店设施主管·郑砚 | 向请求者回复已取得的结果 |
| 2026-11-11 Wed 13:00 | 2026-11-11 Wed 13:30 | B酒店预订咨询·米禾 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-06 Fri 17:00：A旅舍前台·蓝心，`reply`，4条文本证据。
- 2026-11-11 Wed 13:30：B酒店预订咨询·米禾，`reply`，6条文本证据。

## 易错点

- 门框宽当净宽
- 第一家回复后过早停止
- 拿一个房型数据替代另一个

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-08.json)
- [环境私有定义](../../tasks/private/DSB-08.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-08.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
