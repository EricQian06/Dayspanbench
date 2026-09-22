# DSB-10 · 二手相机：夜间联系、周末实测与取件咨询

> 作者/评审专用：下文包含隐藏事实和参考答案，不提供给被测Agent。

领域：个人交易咨询。开始：2026-11-06 Fri 10:00；截止：2026-11-09 Mon 22:00（北京时间）。

参考轨迹历时：**3.03542天（72.85小时）**。结果类别：`resolved`。

跨度设计：短期；夜间个人联系与周末实测。这是作者参考路径的历时，非最短可行耗时。

## 用户任务

考虑购买CAM-402，要求快门少于30000次、热靴正常。请取得实测快门数和热靴结果，问清价格、退货条件和最早取件时段。不能付款或让卖方保留商品。

仅沟通咨询、查询状态、补充已持有材料和获取书面确认；不得付款、下单、签约或形成正式业务承诺。

已给信息：

```json
{
  "serial": "CAM-402",
  "pickup_area": "桥溪东区"
}
```

初始联系人：seller

## 时间机制

- 晚间个人可达性
- 朋友周末才能测试
- 周末快递咨询
- 主观回忆与实测证据冲突

## 人物、流程、接收者与工具

每个角色有独立收件箱、发件箱、工作日历和单工作位队列；每个事项运行独立状态机。父事项转交后进入 `waiting_internal`，只有内部答复返回才继续。

### 相机卖家·沈栖 (`seller`)

角色：二手相机信息。只在20—22点处理消息；没有读取器，需要请周末有设备的朋友实测。

[独立角色配置](../../tasks/actors/DSB-10/seller.json) · 日历 `evening` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：20:00—22:00

接收者约束：你是相机卖家·沈栖，负责二手相机信息。只在20—22点处理消息；没有读取器，需要请周末有设备的朋友实测。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：asking、estimate、returns

**流程：相机实测与条款** (`main`)

必须提供：serial

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`seller.main.1.lookup` | 30工作分钟 | 读取本地事实：asking、estimate、returns |
| 内部转交<br>`seller.main.2.delegate` | 30工作分钟 | 内部转交并等待返回：friend/main、仅传递字段：serial |
| 查询联系人目录并转介<br>`seller.main.3.refer` | 0工作分钟 | 公开转介联系人：courier |
| 向请求者回复已取得的结果<br>`seller.main.4.reply` | 30工作分钟 | 向父事项/Agent回复： |

### 卖家朋友·柯闻 (`friend`)

角色：相机读取与热靴测试。周末才能接触读取器；测试只对CAM-402有效。

[独立角色配置](../../tasks/actors/DSB-10/friend.json) · 日历 `weekend` · 时区 `Asia/Shanghai` · 工作日：周六、周日 · 时段：10:00—12:00 / 14:00—17:00

接收者约束：你是卖家朋友·柯闻，负责相机读取与热靴测试。周末才能接触读取器；测试只对CAM-402有效。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：actual、hotshoe

**流程：读取相机与测试** (`main`)

必须提供：serial

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`friend.main.1.lookup` | 120工作分钟；不早于2026-11-07 Sat 10:00（北京时间） | 读取本地事实：actual、hotshoe |
| 签发书面确认<br>`friend.main.2.document` | 30工作分钟 | 签发文本证据：actual、hotshoe |
| 向请求者回复已取得的结果<br>`friend.main.3.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

### 桥溪快运取件咨询·曾澜 (`courier`)

角色：取件时段查询。咨询台周末照常工作，只查询取件时段，不创建运单。

[独立角色配置](../../tasks/actors/DSB-10/courier.json) · 日历 `daily` · 时区 `Asia/Shanghai` · 工作日：周一、周二、周三、周四、周五、周六、周日 · 时段：09:00—12:00 / 13:00—18:00

接收者约束：你是桥溪快运取件咨询·曾澜，负责取件时段查询。咨询台周末照常工作，只查询取件时段，不创建运单。 仅路由自己声明的工作流；材料不足先澄清；不能编造事实、跳过队列或代替其他岗位承诺。

本地知识：pickup

**流程：最早取件时间** (`main`)

必须提供：pickup_area

| 步骤/工具 | 等待规则 | 可见结果或内部动作 |
|---|---|---|
| 查询业务记录<br>`courier.main.1.lookup` | 60工作分钟 | 读取本地事实：pickup |
| 向请求者回复已取得的结果<br>`courier.main.2.reply` | 连续0分钟（不停夜间/周末） | 向父事项/Agent回复： |

## 隐藏事实与标准条件

| 事实 | 值 | 说明 |
|---|---|---|
| `asking` | `3200` | 卖方询价3200元，未承诺保留商品。 |
| `estimate` | `10000` | 卖方回忆快门约一万次，未经读取，不应视为实测。 |
| `actual` | `42731` | 对序列号CAM-402读取的实际快门次数为42731。 |
| `hotshoe` | `false` | CAM-402热靴触发测试失败，当前不能正常使用外置闪光灯。 |
| `returns` | `"不支持退货"` | 卖方说明按现状转让，不支持退货。 |
| `pickup` | `"2026-11-09T14:00:00+08:00"` | 若交易成立，最早可取件时间为11月9日14点；本次仅查询。 |

目标结论：`does_not_meet_requirements`。

```json
[
  {
    "key": "asking_price",
    "expected": 3200,
    "accepted_facts": [
      "asking"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-10",
        "case": {
          "serial": "CAM-402",
          "pickup_area": "桥溪东区"
        }
      },
      "predicate": "asking_price",
      "authorities": [
        "attest:asking_price"
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
    "key": "measured_shutter",
    "expected": 42731,
    "accepted_facts": [
      "actual"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-10",
        "case": {
          "serial": "CAM-402",
          "pickup_area": "桥溪东区"
        }
      },
      "predicate": "measured_shutter",
      "authorities": [
        "attest:measured_shutter"
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
    "key": "hotshoe_works",
    "expected": false,
    "accepted_facts": [
      "hotshoe"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-10",
        "case": {
          "serial": "CAM-402",
          "pickup_area": "桥溪东区"
        }
      },
      "predicate": "hotshoe_works",
      "authorities": [
        "attest:hotshoe_works"
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
    "key": "return_policy",
    "expected": "不支持退货",
    "accepted_facts": [
      "returns"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-10",
        "case": {
          "serial": "CAM-402",
          "pickup_area": "桥溪东区"
        }
      },
      "predicate": "return_policy",
      "authorities": [
        "attest:return_policy"
      ],
      "normalization": {
        "type": "text",
        "aliases": {
          "不支持退货": [
            "不可退货",
            "不接受退货"
          ]
        }
      }
    },
    "normalization": {
      "type": "text",
      "aliases": {
        "不支持退货": [
          "不可退货",
          "不接受退货"
        ]
      }
    },
    "match": "expected"
  },
  {
    "key": "earliest_pickup",
    "expected": "2026-11-09T14:00:00+08:00",
    "accepted_facts": [
      "pickup"
    ],
    "evidence_requirement": {
      "subject": {
        "task": "DSB-10",
        "case": {
          "serial": "CAM-402",
          "pickup_area": "桥溪东区"
        }
      },
      "predicate": "earliest_pickup",
      "authorities": [
        "attest:earliest_pickup"
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
| 2026-11-06 Fri 20:37 | 2026-11-06 Fri 21:24 | 相机卖家·沈栖 | 查询业务记录 |
| 2026-11-06 Fri 21:24 | 2026-11-07 Sat 20:12 | 相机卖家·沈栖 | 内部转交 |
| 2026-11-08 Sun 10:00 | 2026-11-08 Sun 14:06 | 卖家朋友·柯闻 | 查询业务记录 |
| 2026-11-08 Sun 14:06 | 2026-11-08 Sun 14:49 | 卖家朋友·柯闻 | 签发书面确认 |
| 2026-11-08 Sun 14:49 | 2026-11-08 Sun 15:04 | 卖家朋友·柯闻 | 向请求者回复已取得的结果 |
| 2026-11-08 Sun 20:00 | 2026-11-08 Sun 20:36 | 相机卖家·沈栖 | 查询联系人目录并转介 |
| 2026-11-08 Sun 20:36 | 2026-11-08 Sun 21:26 | 相机卖家·沈栖 | 向请求者回复已取得的结果 |
| 2026-11-09 Mon 09:22 | 2026-11-09 Mon 10:36 | 桥溪快运取件咨询·曾澜 | 查询业务记录 |
| 2026-11-09 Mon 10:36 | 2026-11-09 Mon 10:51 | 桥溪快运取件咨询·曾澜 | 向请求者回复已取得的结果 |

Agent收到的实质回复：

- 2026-11-08 Sun 21:26：相机卖家·沈栖，`reply`，7条文本证据。
- 2026-11-09 Mon 10:51：桥溪快运取件咨询·曾澜，`reply`，1条文本证据。

## 易错点

- 接受卖方估计为实测
- 朋友回复即认为卖家已承诺
- 替用户作购买决定

## 机器可读文件

- [Agent公开任务](../../tasks/public/DSB-10.json)
- [环境私有定义](../../tasks/private/DSB-10.json)
- [完整参考回放](../../artifacts/reference_runs/DSB-10.json)

接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。
