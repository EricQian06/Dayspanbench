# DSB-17 可视化：家庭午餐 · 配送时间翻转后的帮手覆盖

- **任务**：DSB-17 Home family lunch: helper-covered meal after a delivery-time change（LATCH case `cross-food-family-mealtime-handoff-001`）
- **任务源码**：[scripts/latch_cases/dsb17_mealtime_handoff.py](../scripts/latch_cases/dsb17_mealtime_handoff.py)
- **轨迹来源**：`artifacts/evaluation_runs/1014-001-deepseek-retry3/DSB-17`（1014-001 抽查，前两次 run 因 simulator key-token bug 无效，修复后重跑）
- **Agent 模型**：deepseek-v4-flash-0731；**步数**：41（action_errors 0）
- **虚拟时间**：引擎时钟为 UTC，任务显示时区 America/New_York（UTC-4），下文时刻均已换算为纽约时间
- **最终结果**：❌ 未通过 —— judge 5/5 subpart 全过、结论 `meal_covered` 正确，但确定性锚点校验失败：总结缺失 `236.0`（Agent 写作 `236.00`，尾零格式不匹配）

```mermaid
%% 一、任务推进流程（作者设计路径）
flowchart TD
    START(["开始 2027-07-09 09:00 纽约<br/>任务：7-11 周日六人家庭午餐<br/>≤280 USD·帮手全程覆盖60分钟"]):::startNode

    subgraph SG1["信息收集（可任意顺序）"]
        direction TB
        P1["visit_page meal-intro / contacts / entry<br/>得知菜单须查 menu_search·订单走 meal_order"]
        D1["web_search 命中关键词<br/>→ discover_tools 发现三个隐藏工具<br/>menu_search / meal_order / family_dialogue"]
        FD["family_dialogue 问 David Klein<br/>问全：人数/轮椅/芝麻过敏/儿童无鱼<br/>预算280/批准规则/帮手授权"]
        MS1["menu_search 首查<br/>6个菜单：ff1-v1(12:00)·ff2含鱼<br/>ff3含芝麻·ff4无儿童份·ff5超预算·ff6"]
    end

    subgraph SG2["书面核验（邮件往返）"]
        K1["邮件 kitchen·Sam Reyes<br/>索取 ff1 书面芝麻交叉污染管控<br/>→ 书面回执：无芝麻·独立器具<br/>过敏提示票·非医疗保证"]
        A1["邮件 helper·Ana<br/>12:00-13:00 授权窗口<br/>（12:00 配送时可用）"]
    end

    TWIN{"时间翻转点<br/>2027-07-10 09:00 纽约<br/>ff1 配送 12:00 → 13:30<br/>ff1-v1 下架·ff1-v2 上架<br/>page_update 公告"}
    TWIN -->|"翻转后重查"| MS2["menu_search 复查<br/>看到 ff1-v2·13:30·236.00 USD"]
    TWIN -.->|"错过/沿用旧数据下单"| FAIL1["订单被 desk 拒收<br/>或押注 Ana 12:00-13:00<br/>无法覆盖 13:30-14:30"]:::failNode

    MS2 --> M1["邮件 helper·Marta<br/>13:00-15:00 授权窗口<br/>→ 全程覆盖 13:30-14:30 书面确认"]
    M1 --> AP["family_dialogue 问 David<br/>展示完整修改方案获批：<br/>ff1-v2·六人份·13:30窗口·236.00·指定 Marta<br/>（前置条件：组织者批准）"]
    AP --> ORD["meal_order entry=ff1-v2<br/>desk 校验 live listing<br/>→ 订单确认回执 R-0003<br/>total 236.00 USD·未付款"]

    ORD --> SUB(["提交答案 2027-07-11 12:00 截止前<br/>conclusion=meal_covered<br/>总结须含回执关键要素：<br/>ff1 v2·13:30·六人份·236.0·R-0003/R-0004"]):::endNode
    FAIL1 -.-> SUB
    SUB -->|"总结缺关键要素/结论错"| FAIL2["deterministic_anchors_ok=false<br/>或 conclusion 不合法"]:::failNode

    classDef startNode fill:#cfe8ff,stroke:#5b9bd5
    classDef endNode fill:#c6efce,stroke:#4caf50
    classDef failNode fill:#ffb3b3,stroke:#d9534f
```

```mermaid
%% 二、Agent 实际路线（deepseek-v4-flash-0731，41步，与上图同构对照）
flowchart TD
    START(["开始 2027-07-09 09:00 纽约<br/>deepseek-v4-flash-0731"]):::startNode

    subgraph SG1["信息收集 ✔ 步1-11"]
        direction TB
        P1["步3-10 ✔ 浏览三个页面<br/>发现 menu_search / family_dialogue / meal_order"]
        FD["步11 ✔ family_dialogue 问 David<br/>一次性问全约束与批准规则<br/>（绿：结构化提问，一次覆盖6项）"]
        MS1["步5/19 ✔ menu_search 两次首查<br/>拿到 ff1-v1 12:00 等六菜单"]
    end

    subgraph SG2["书面核验 ✔ 步12-18"]
        K1["步12→18 ✔ kitchen 书面回执<br/>ff1 芝麻管控+儿童份无鱼"]
        A1["步13→17 ✔ Ana 回复<br/>仅 12:00-13:00 授权"]
    end

    EARLY{"步20 ⚠ 提前下单<br/>2027-07-09 14:43 纽约<br/>meal_order ff1-v1（12:00 旧版）<br/>未获 David 批准<br/>未察觉翻转将至"}
    EARLY -->|步21-24 等待近两天| REJ["步24 ✘ ff1-v1 被拒：<br/>listing 已过期（7-10 09:00 下架）"]:::failNode

    REJ --> MS2["步25 ✔ 翻转后重查 menu_search<br/>看到 ff1-v2 · 13:30 · 236.00"]:::okNode
    MS2 --> AP["步26 ✔ 携完整新方案问 David<br/>ff1-v2·六人份·13:30·236·Marta<br/>→ 获重新批准"]:::okNode
    AP --> M1["步27→37 ✔ 邮件 Marta<br/>→ 书面确认覆盖 13:30-14:30 全窗口<br/>回执 R-0004"]:::okNode
    AP --> K2["步28 邮件 kitchen 复核管控<br/>CASE-0004 仅收到回执已确认<br/>（步31 ack，正式回复未到即提交）"]
    AP --> ORD2["步32 meal_order ff1-v2 提交<br/>步40 processed → 订单确认 R-0003"]:::okNode

    ORD2 --> SUB(["步41 提交答案 2027-07-11 12:00 纽约<br/>conclusion=meal_covered<br/>总结：236.00 USD·13:30·ff1 v2·Marta<br/>✔ judge 5/5 全过"]):::endNode
    SUB -->|"总结写 236.00，锚点要 236.0<br/>deterministic_anchors_ok=false"| FAIL2["最终 complete=false<br/>仅败于尾零格式"]:::failNode

    classDef startNode fill:#cfe8ff,stroke:#5b9bd5
    classDef endNode fill:#c6efce,stroke:#4caf50
    classDef okNode fill:#c6efce,stroke:#4caf50
    classDef warnNode fill:#fff2b3,stroke:#d4ac0d
    classDef failNode fill:#ffb3b3,stroke:#d9534f
```

**补充**：action_errors = 0（无非法 JSON / 非法参数）。步 22-23 两次 `wait_until` 一次跳到 7-10 12:00、一次直接跳到 7-11 10:00（跳过了 7-10 09:00 的翻转点后才发现，靠 desk 拒收兜底暴露）。

## 三、设计路径 vs Agent 实际对照

| 环节 | 参考策略（reference） | Agent 实际 | 结果 |
|---|---|---|---|
| 需求收集 | family_dialogue 一次问全 | 步11 一次问全 6 项约束 | ✓ |
| 菜单获取 | discover + menu_search 首查 | 步5/19 两次查询 | ✓ |
| 首次书面核验 | kitchen 书面芝麻管控 + Ana 窗口 | 步12-18 均拿到 | ✓ |
| 等待翻转 | 推进至 7-10 10:00 后复查看 v2 | **未等待**，7-09 14:43 即下单 ff1-v1 | ✗ |
| 组织者批准 | 批准仅对展示的完整方案生效 | 首单未获批准（踩中设计陷阱之一） | ✗ |
| 翻转后刷新 | 复查 menu_search 见 ff1-v2 | 步25 拒收后刷新，看到 v2 | ✓（被动补救） |
| 帮手覆盖匹配 | Marta 13:00-15:00 覆盖 13:30-14:30 | 步27→37 书面确认 R-0004 | ✓ |
| 重新批准 | 向 David 展示修改后完整方案 | 步26 获重新批准后才下单 | ✓ |
| 一次订单 | ff1-v2 一次成功 | 首单被拒（不构成订单）→ ff1-v2 成功 | ✓ |
| 提交答案 | 总结含回执关键要素（total 236.0） | 总结写 "236.00 USD"，`236.0` 锚点字面缺失 | ✗ |

**失败链**：未等翻转点即提前下单旧版（步20）→ desk 拒收兜底（步24）→ 被动刷新补救、后续全对（judge 5/5）→ 最终总结金额写 `236.00` 而非 `236.0` → 确定性锚点校验失败 → complete=false。

**关键发现**：
1. Agent 唯一的流程性失误是步 20 的**提前下单**——同时踩中"订旧版"与"未获批准"两个设计陷阱，但环境的时间翻转机制使其自动暴露并被拒收，Agent 随后的补救路径完全正确。
2. 最终判负点是**尾零格式**：receipt 的 `total_cost` fact 值为 `236.0`，`key_tokens` 提取锚点 `236.0`，Agent 总结写 `236.00 USD`（数字上完全正确）。边界匹配把后随数字视为 token 延续，`236.00` 无法满足 `236.0`。这是确定性层的严格性问题（金额语义等价），judge 的 5/5 与所有流程锚点实际均达成——本 case 更接近"机制误伤"而非 Agent 能力失败，值得在 scoring errata 中讨论是否按数值等价放行。

## 四、合法替代路径

任务源码 `alternate_paths`：对话、核验邮件、帮手确认与搜索的任意合法顺序均被接受，只要每个 goal 的证据条件成立；参考路径在 7-10 变更后刷新 ff1 报价并链接 Marta 的覆盖。**ff6（已验证管控、12:00 配送、268.40 USD）配 Ana 12:00-13:00 是一条合法替代路线**（不依赖翻转后刷新），但计分答案键仍按刷新后的 ff1 v2 方案。
