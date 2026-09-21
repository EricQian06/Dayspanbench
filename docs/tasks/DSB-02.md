# DSB-02 · 租房咨询：物业周审与新一期货梯表

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：个人与物业。开始：2026-11-03 Tue 19:30；截止：2026-11-12 Thu 17:00（北京时间）。

参考轨迹历时：**8天（192小时）**。结果类别：`resolved`。

跨度设计：中短期；宠物周审与下一期货梯安排。这是作者参考路径的历时，非最短可行耗时。

## 用户委托

我想11月12日搬入林霁的房子，带一只8公斤成年犬。问清租金、押金、宠物规则，以及最早可搬入时间；若12日不行请说明替代时间，暂不签约。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "pet_weight": "8kg",
  "move_date": "2026-11-12"
}
```

初始联系人：landlord

## 时间机制

- 个人只在晚间回复
- 机构白天办公
- 固定周五审核
- 新一期货梯表尚未开放

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 房东·林霁 (`landlord`)

角色：出租房源咨询。白天上班，只在19—21点处理消息；不会代物业批准宠物或货梯。

[独立角色配置](../../tasks/actors/DSB-02/landlord.json) · 日历 `landlord` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：19:00—21:00

接收者约束：你是房东·林霁，负责出租房源咨询。白天上班，只在19—21点处理消息；不会代物业批准宠物或货梯。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：deposit、rent

**流程：租金、宠物和搬入条件** (`main`)

必须提供：pet_weight、move_date

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`landlord.main.1.lookup` | 60工作分钟 | 读取本地事实：rent、deposit |
| 内部转交<br>`landlord.main.2.delegate` | 0工作分钟 | 内部转交并等待返回：manager/main、仅传递字段：pet_weight, move_date |
| 向请求者回复已取得的结果<br>`landlord.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

### 青栎公寓物业·许乔 (`manager`)

角色：楼宇规则与货梯时段。收到房东转交后提交周五审核；11月11日才开放新一期货梯表，之后核实搬入时间。

[独立角色配置](../../tasks/actors/DSB-02/manager.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是青栎公寓物业·许乔，负责楼宇规则与货梯时段。收到房东转交后提交周五审核；11月11日才开放新一期货梯表，之后核实搬入时间。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：moving

**流程：宠物与搬入复核** (`main`)

必须提供：pet_weight、move_date

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 内部转交<br>`manager.main.1.delegate` | 60工作分钟 | 内部转交并等待返回：reviewer/main、仅传递字段：pet_weight |
| 查询业务记录<br>`manager.main.2.lookup` | 60工作分钟；不早于2026-11-11 Wed 09:00（北京时间） | 读取本地事实：moving |
| 向请求者回复已取得的结果<br>`manager.main.3.reply` | 30工作分钟 | 向父事项/Agent回复： |

### 青栎公寓规则审核员·丁悦 (`reviewer`)

角色：宠物规则复核。每周五14点集中复核材料；错过批次进入下一周。

[独立角色配置](../../tasks/actors/DSB-02/reviewer.json) · 日历 `office` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五 · 时段：09:00—12:00 / 13:00—17:00

接收者约束：你是青栎公寓规则审核员·丁悦，负责宠物规则复核。每周五14点集中复核材料；错过批次进入下一周。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：pet

**流程：周五规则审核** (`main`)

必须提供：pet_weight

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`reviewer.main.1.lookup` | 下一次周五 14:00批次，随后60工作分钟 | 读取本地事实：pet |
| 向请求者回复已取得的结果<br>`reviewer.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `rent` | `5600` | 月租5600元；这是信息咨询，不构成租约。 |
| `pet` | `true` | 已核准一只8公斤成年犬符合楼宇宠物规则。 |
| `deposit` | `4000` | 该房源押金4000元，不另收宠物押金。 |
| `moving` | `"2026-11-13T10:00:00+08:00"` | 11月11日公布的新一期货梯表显示12日无可用时段，最早可安排11月13日10点搬入。 |

目标结论：`requires_date_change`。

```json
[
  {
    "key": "monthly_rent",
    "expected": 5600,
    "accepted_facts": [
      "rent"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-02",
        "case": {
          "pet_weight": "8kg",
          "move_date": "2026-11-12"
        }
      },
      "predicate": "monthly_rent",
      "authorities": [
        "attest:monthly_rent"
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
    "key": "deposit",
    "expected": 4000,
    "accepted_facts": [
      "deposit"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-02",
        "case": {
          "pet_weight": "8kg",
          "move_date": "2026-11-12"
        }
      },
      "predicate": "deposit",
      "authorities": [
        "attest:deposit"
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
    "key": "pet_allowed",
    "expected": true,
    "accepted_facts": [
      "pet"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-02",
        "case": {
          "pet_weight": "8kg",
          "move_date": "2026-11-12"
        }
      },
      "predicate": "pet_allowed",
      "authorities": [
        "attest:pet_allowed"
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
    "key": "earliest_move",
    "expected": "2026-11-13T10:00:00+08:00",
    "accepted_facts": [
      "moving"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-02",
        "case": {
          "pet_weight": "8kg",
          "move_date": "2026-11-12"
        }
      },
      "predicate": "earliest_move",
      "authorities": [
        "attest:earliest_move"
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
| 2026-11-03 Tue 19:30 | 2026-11-03 Tue 20:30 | 房东·林霁 | 查询业务记录 |
| 2026-11-03 Tue 20:30 | 2026-11-03 Tue 20:30 | 房东·林霁 | 内部转交 |
| 2026-11-04 Wed 09:00 | 2026-11-04 Wed 10:00 | 青栎公寓物业·许乔 | 内部转交 |
| 2026-11-06 Fri 14:00 | 2026-11-06 Fri 15:00 | 青栎公寓规则审核员·丁悦 | 查询业务记录 |
| 2026-11-06 Fri 15:00 | 2026-11-06 Fri 15:00 | 青栎公寓规则审核员·丁悦 | 向请求者回复已取得的结果 |
| 2026-11-11 Wed 09:00 | 2026-11-11 Wed 10:00 | 青栎公寓物业·许乔 | 查询业务记录 |
| 2026-11-11 Wed 10:00 | 2026-11-11 Wed 10:30 | 青栎公寓物业·许乔 | 向请求者回复已取得的结果 |
| 2026-11-11 Wed 19:00 | 2026-11-11 Wed 19:30 | 房东·林霁 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-11 Wed 19:30：房东·林霁，`reply`，4条文本证据。

## 易错点

- 把广告可养宠视为批准
- 忽略房东与物业时间错位
- 把11月12日误报为可搬入

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-02.json)
- [环境私有定义](../../tasks/private/DSB-02.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-02.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
