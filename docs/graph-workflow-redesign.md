# Workflow 图模型重构设计（v0.6 提案，讨论稿）

状态：设计讨论中，未动代码。试点任务：DSB-43。

## 0. 动机：已确认的三个现有缺陷

1. **业务类别冒充业务身份**：`routing.merge_target` 仅按 `(actor, workflow_id)` 匹配在途事项，
   同一 NPC 下同一 workflow 的两个独立业务（房源 A / 房源 B）会被错误合并——未受理 case 被字段污染
   （`case["fields"].update`），在途 case 收到误导性"办理中"ACK。
2. **修改意图变成并存新事项**：`apply_followup` 对字段变化的来信一律 `new_case`，无 cancel/supersede
   语义，新旧事项并行；且新 case 只带增量字段，往往被 `needs_information` 打回。
3. **投递与理解耦合**：`send_email` 在发送时刻同步调用 LLM 路由/抽字段；路由失败会让整集无效
   （`simulator_failure`），且预算已扣、审计已记而 agent 只看到报错——"信是否发出"在协议上不确定；
   名义上"工作时段才读信"，理解却已在发送瞬间完成。

## 1. 核心模型：世界一张图，证据驱动，无运行时实例

- **世界 = 一张静态有向图**，任务编写时全部展开。每个 NPC / 场景持有图中的若干节点（子图），
  节点之间可以有跨 NPC 的边。**没有运行时"实例/工作流对象"**：业务身份在 author 时固化进图
  （房东图的"咨询房源 A"和"咨询房源 B"是两个节点）。多业务并发天然不冲突。
- **节点 = 一个可完成的语义单元**（一次咨询、一次申请、一次审批……）。每个节点声明它需要的
  **证据集合**；证据由 NPC 的 LLM 从 agent 的自然语言解析为规范格式后标记到节点上，**跨多封信累积**。
  前置节点点亮本身是后置节点的证据之一（边即证据）。
- **推进是纯确定性的**：某节点证据集齐且未完成 → 引擎点亮该节点，并发派生其效果
  （回复 agent、执行表单/通知类副作用、在环境事件队列上排程后续、给下游节点供证据）。
- **LLM 职责边界**（沿用 v0.5 原则"理解交给 LLM、判断在结构化结果上做"）：
  - 输入解析：agent 自然语言 → 结构化证据（哪个节点、哪个证据槽、规范值）；模糊表达用 NPC 全量
    history + 当前节点近期往来消歧。
  - 输出组织：基于引擎给定的 canonical 内容（回复要点、事实、receipt）写 persona 措辞，key-token 原样保留。
  - 终审评分（judge，不变）。
  - **副作用、节点推进、分支选择全部引擎执行，LLM 永不参与。**

### 1.1 可重复业务：自环节点

"当用户咨询时如何回答"类节点：证据 = "用户提出了咨询"，点亮 → 输出回复 → **清空（易失）证据，
边指回自己**，可再次触发。重复问、追问、催办均为此型。

回复延迟的语义统一为**激活延迟**：该节点在 authored 延迟（或 NPC 工作时段边界）后激活，
激活时一次性处理积压的全部来信（LLM 批量解析），回复措辞可以提到"两封邮件都收到了"；
发出后清空，再来的询问等下一次激活统一处理。

### 1.2 一次性业务：保持完成态防重

申请提交节点点亮后保持 completed。agent 再次提交 → 证据落在已完成节点 → 按"已提交过"应答
（节点 authored 的 completed 态输出），不会二次受理。

### 1.3 证据生命周期

- **时效**：证据可带 `valid_until`。节点点亮时校验证据有效性；过期/缺失的证据在收集阶段由 NPC
  **主动询问** agent（新的主动交互行为：过期→请补充、缺失→请提供）。
- **撤销/修改**：author 一类**撤销节点**（对话型特殊节点）——先与 agent 确认：是否确认撤销、
  保留哪些信息、是否继续提交等，再按回答改写目标节点的证据。撤销节点的话术/选项**按 case、按 NPC
  分别 author**。修改意图由此有了显式语义（解决缺陷 2），不再产生并存事项。

### 1.4 分支与互斥

节点出边可带互斥条件（申请通过 / 被拒）。**LLM 只产出证据，引擎根据结构化证据评估条件选边**。
后续 case 刻意用多分支做复杂化。

### 1.5 环境侧

环境事件（form_processed、群公告发布、catalog_update、page_update、审批到时）是图中的一类
**环境节点**：其"证据"由环境事件回填（不需要 LLM），完成时向 NPC 节点 / agent 侧供证。
例如"bwc_survey 表单处理完成"节点点亮 → 供证给"面试排期公布"节点 → 群公告节点到时发布。
agent 与环境、NPC 与环境由此形成闭环。

## 2. 数据 Schema（草案）

任务 JSON 中新增 `graph`（私有），随 author_tasks 导出；actor spec 的 `workflows` 字段废除。

```jsonc
{
  "graph": {
    "nodes": [
      {
        "id": "bwc_move_slot",
        "owner": "bwc_events_head",            // NPC id 或 "environment"
        "title": "Move the badminton interview slot",
        "kind": "service",                    // service | inquiry(自环) | revoke(撤销对话) | environment
        "activation": {"delay_minutes": 30, "within": "campus_evening"},   // 激活时机
        "requires": [                          // 证据槽 + 前置节点 id 混列（已确认），全部满足才点亮
          "bwc_assignment_posted",             // 前置节点（边即证据）
          {"key": "slot_change_requested", "type": "boolean", "volatile": true},
          {"key": "wednesday_unavailable", "type": "boolean", "volatile": true,
           "require": "filled"}                // 拥有该线索即可：明确"可以"或"不行"都算证据
        ],
        "branches": [                           // 互斥出边，引擎按结构化证据评估（kind=service）
          {"when": {"slot_change_requested": true, "wednesday_unavailable": true},
           "register_facts": ["bwc_rescheduled_monday"],
           "reply": "…moved to Monday 2026-09-21 19:30-20:30…"},
          {"when": {"slot_change_requested": true, "wednesday_unavailable": false},
           "register_facts": ["bwc_wednesday_booked"], "reply": "…moved to Wednesday…"}
        ],
        "default_branch": {"reply": "…tell me plainly which evenings work…"},  // 证据不足时的询问
        "effects": [                           // 点亮时引擎确定性派生（可多个并发）
          {"kind": "register_facts", "facts": [...]},
          {"kind": "submit_form", "form": "bwc_survey_form", "at": "..."},
          {"kind": "notify_group", "group": "bwc_group", "message": "...", "at": "..."},
          {"kind": "schedule_event", "at": "...", "target_node": "..."}
        ],
        "on_completed_reply": "…already submitted…"   // 完成态应答
      },
      {"id": "bwc_president_referral", "kind": "inquiry", "owner": "bwc_president",
       "requires": [{"key": "user_inquired", "type": "boolean", "volatile": true}],
       "reply": "…interview matters go to the Events head…", "self_loop": true}
    ]
  }
}
```

要点：
- `volatile` 证据 = 自环清空对象；非 volatile 证据（如姓名、学号）持久保留在节点上。

### 2.1 证据槽是三态的：未提供 / 已提供(value)

"槽里有没有东西"和"东西的值"是两个独立维度。布尔型证据槽有三种状态：
`unfilled`（agent 尚未提及）／`filled(true)`／`filled(false)`——**"agent 明确说周三不行"与
"agent 明确说周三可以"都是有值的证据**，都推进节点，只是分支走向不同。

对应地，`requires` 与 `branches.when` 里每个证据键的满足方式有两种声明：

- `{"key": "wednesday_unavailable", "require": "filled"}` —— 拥有该线索即可，值（true/false）不重要；
  "有值"本身就是要收集的证据。
- `{"key": "wants_move", "require": true}` —— 已提供且值为 true（等价 `require: {"value": true}`）；
  `false` 同理。`require` 缺省 = `filled`。

LLM 解析的职责因此也明确为两步：先判断这条消息**是否提供了**某槽的线索（没提 = 不动，
不是填 false），再给出规范值。防编造语义（缺 ≠ false）由此在 schema 层固定。
- `kind=inquiry` 自环节点：点亮即回复并清空 volatile 证据，指回自身。
- `kind=environment`：证据来自事件回填，不经 LLM。
- 现有 `steps` + `extract` 的功能由 `branches` + 结构化证据取代，`kind=extract` 的隐藏工具族随
  旧 workflow 一并退役；`form/select/catalog/record/dialogue` 类副作用成为 `effects` 的执行器，
  底层实现（tools/hidden.py）可复用。

## 3. 运行时流程

### 3.1 发送与理解解耦（解决缺陷 3）

`send_email` 退化为传输层：校验地址/预算/发现 → 落 NPC 收件箱 → 返回
`{"status": "received"}`。**不做任何语义解析**；投递失败只可能来自传输层（黑洞地址），永不来自
LLM。理解发生在**激活时**：NPC 的 activation 事件（工作时段 + authored 延迟）到期时，把该 NPC
积压的全部来信（含群、电话）作为一批交给 LLM 解析，产出证据标记。

解析失败（SimulatorError）按现行语义：记 environment failure、集无效——但因为它发生在激活事件里
而非发送时刻，语义上就是"NPC 读信失败"，与投递无关。

### 3.2 激活批处理（对应确认点 1）

节点激活 = 引擎调度的一个事件。激活时：
1. 汇总该 NPC 未处理的入站消息 → 一次 LLM 调用批量解析为结构化证据（节点 id + 证据键 + 规范值）；
2. 证据标记上节点（canonicalize 同义单位照旧）；
3. 检查受影响节点：证据齐 → 点亮 → 并发执行 effects（副作用、事实登记、下游供证、排程）；
4. 回复由 LLM 在引擎给定的 canonical 内容上写 persona 措辞（key-token 校验照旧），
   可自然提及"两封邮件都收到了"；
5. 发出后清空 volatile 证据，自环节点回到待触态。

### 3.3 节点状态机（替代 case 状态机）

每节点四态：`collecting`（有部分证据或前置未齐）→ `ready`（证据齐、等激活）→ `firing`
（effects 执行中）→ `completed`。`TRANSITIONS` / `merge_target` / `apply_followup` /
`deduplicate_by` / follow-up 合并启发式**全部删除**。

### 3.4 无 LLM 的确定性回放（replay/validate）

参考策略动作直接携带结构化证据（等价于现在 reference 传 fields），引擎照常点亮节点；
reference/validate/replay 全程零 LLM 调用，哈希可复现（沿用工具层重构时的验收标准）。

## 4. 模块影响面

| 模块 | 改动 |
|---|---|
| `engine.py` | 删 case 状态机/routing 调用；新增 GraphRuntime（节点状态、激活事件、effects 派发）；`Environment` 保留时钟/事件堆/邮件/审计/director 挂点 |
| `routing.py` | **删除**（问题 1、2 随之消失） |
| `scheduling.py` | admit/step 事件改为 activation 事件；ETA 投影改为对节点激活链的投影（保留） |
| `simulator.py` | `route` → `interpret`（批解析：消息批次 → 证据标记）；`render` 保留（canonical 内容 + persona 措辞） |
| `interactor.py` | 不变（consent 门与图模型正交） |
| `director.py` | stage 图改挂节点粒度：`node_lit` / `node_completed` 审计事件驱动 |
| `scoring.py` | 确定性锚点改为节点完成判定 + receipt 关键要素字面检查（judge 主分数不变） |
| `reference.py` | 参考策略 schema 改为直接喂证据 |
| `tools/` | `send_email`/`call` 简化为传输 + 激活排程；hidden 工具族中 form/select/catalog/record 保留为 effects 执行器，extract/dialogue 的对话型节点并入图节点 |
| 任务 author 层 | 新 helper（`node`/`evidence`/`branch`/`effect`）；43 个任务全部迁移，先试点 |

## 5. DSB-43 试点改写草案

现结构 → 图节点映射（体现全部特性）：

- **自环 inquiry 节点**：`bwc_president_referral`（原 referral workflow；证据 = user_inquired，
  回复指向 events head）、`pnc_events_head_referral` 同理。
- **环境节点**：`bwc_survey_processed`（form 处理完成回填，供证 `bwc_survey_recorded`）、
  `bwc_assignment_posted`（09-17 群公告发布事件）、`pnc_assignment_posted`（09-19）。
- **service 分支节点**：`bwc_move_slot`（owner=bwc_events_head；requires = 前置 assignment_posted +
  `slot_change_requested`（agent 明确要求挪时间，原 extract 字段 `wants_move` 改名）+
  `wednesday_unavailable`（require= "filled"：明确说"周三不行"或"周三可以"都算收集到该线索）；
  branches = rescheduled_monday / wednesday_booked 互斥，原 extract_step 的分支表原样翻译）、
  `pnc_keep_slot`（keep_original / wednesday_free 三分支）。
- **自环收集节点**（体现"一封信给不全、多封凑齐"）：badminton 排期询问节点可拆为
  `slot_change_requested` 与 `wednesday_unavailable` 两个证据槽分多封信累积，集齐才点亮；
  例如第一封只说"想挪时间"、第二封才补上"周三晚上不行"。
- interactor（consult_user）与 group 工具不动，作为图的输入侧通道。

验收：replay 逐节点审计比对原 facts 结果不变；judge_criteria 六条不改；`stages` 映射到节点。

## 6. 实施顺序

1. 本文档定稿（本文档即当前阶段）。
2. 图 schema + GraphRuntime 落地（新模块 `dayspanbench/graph.py`，engine 改为委托）。
3. DSB-43 改写 + `test_extract_group.py` 等测试迁移；replay/validate 全绿。
4. 用户审查试点 → 意见迭代 → 再铺开到其余 42 个任务。
5. 新旧引擎不并存（已确认）：切换即全量，43 个任务在同版本内完成迁移，不保留旧 case 状态机的
   双路径。

## 7. 风险与开放问题

- **author 成本**：图比 workflow 冗长，需在 author_tasks/club_cases 层做紧凑 helper 压缩。
- **LLM 归属判定质量**：节点多时"这封信属于哪个节点"的错误归属会污染证据；缓解 = 归属输出
  必须含节点 id + 证据键（结构化、可校验），且解读失败走 default_branch 询问而非猜测。
- **激活粒度与消息预算**：批处理激活可能改变 agent 的最优节奏（等回复 vs 连发），需要试点观察
  是否影响任务难度校准。
- `serve.py` / `docs/agent-tools.json` 对 agent 的对外协议不变（仍是九个公共工具），agent 侧无感。
