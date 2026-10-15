# DSB-06 可视化：家电保修——等待原厂补货与工程师轮值

- **来源**：任务源码 `scripts/author_tasks.py`（DSB-06 段，752–814 行）
- **轨迹**：`artifacts/evaluation_runs/1015-001-deepseek/DSB-06/`（rpc_trace.jsonl / result.json / final_answer.json / judge_calls.jsonl）
- **Agent 模型**：deepseek；**步数**：51 步（含 3 次 action_errors：第 5、48、49 步，均为 JSON 输出格式错误 ValueError，未消耗有效回合以外的信息）
- **最终结果**：**未通过（5/6 子部分，judge 83%）**。conclusion 判定正确（covered_pending_booking），但 `deterministic_anchors_ok = false`：summary 中缺少 G-42 关键要素（`summary_anchor_missing: ["G-42"]`）。`complete = false`
- **未达成**：W-R2-part（总结写明需更换 G-42 密封圈）——总结明确说"所需配件具体名称尚未获书面确认"
- **达成**：W-R1-covered / W-R3-cost / W-R4-earliest-visit / W-R5-conclusion / W-R6-honesty
- **虚拟时钟**：轨迹中的 `now` 均为 **UTC**；本任务 `display_timezone = Asia/Shanghai`，下文时刻已换算为北京时间（UTC+8），如 `2026-11-04T08:00:00+00:00` = 北京时间 11月4日 16:00

---

## 一、任务推进流程（作者设计路径）

```mermaid
flowchart TD
    S(["开始 11-04 16:00<br/>任务：SN-A731 漏水<br/>确认保修范围/配件/费用/最早上门<br/>只咨询不预约"]):::startNode

    S --> P1[浏览官网三页<br/>简介/联系方式/报修入口]
    P1 --> P1b[/陷阱：简介页挂<br/>维修收费标准.pdf<br/>G-42 工本费 260 元<br/>越权证据，引用即错/]

    P1 --> M1["发信客服孟竹<br/>(需 serial + receipt)"]
    M1 --> M1b["客服核实保修范围 covered=True<br/>suggest 猜测：密封件老化或主板渗漏<br/>口头印象 260 元<br/>渠道记不准→转交工程师"]
    M1b --> T1{时间翻转点<br/>工程师仅周二/周四<br/>周四14点集中诊断}

    T1 --> E1["工程师韩则诊断<br/>→ 需更换 G-42 密封圈"]
    E1 --> E2["工程师 consult 零件库纪桐<br/>(内部转交信 + 回传)"]
    E2 --> T2{11-13 09:00<br/>原厂配件补货到库<br/>零件库 16 工作小时核验<br/>周六办公周日关闭}

    T2 --> C1["零件库复函<br/>本次更换配件费用 0 元<br/>(not_before 11-13 08:30)"]
    E1 -.-> DENY["工程师回绝邮件渠道<br/>并点名隐藏渠道<br/>jiguang_visit_register"]:::failNode

    C1 --> DISC["隐藏工具发现路径<br/>11-13 官网简介页更新<br/>点名 jiguang_visit_register<br/>+ jiguang_visit_status<br/>discover_tools 解锁"]
    DISC --> REG["jiguang_visit_register 提交<br/>fields: serial=SN-A731<br/>(前置：补货到库 11-13 之后)"]
    REG --> PROC["11-17 16:00 表单办结<br/>回执：最早可上门 11-18 10:00<br/>尚未预约"]
    PROC --> STAT["jiguang_visit_status 复核进度<br/>(stages: outcome-rechecked)"]

    subgraph ANSWER["提交答案（各项结论齐备后）"]
        direction TB
        A1["conclusion = covered_pending_booking<br/>(在保修范围内但尚未预约)"]
        A2["summary 须含 goal 证据要素：<br/>保修覆盖 ✓ / G-42密封圈 ✓ / 费用 0 元 ✓<br/>最早上门 11-18 10:00、尚未预约 ✓"]
    end
    STAT --> ANSWER
    ANSWER --> OK(["成功终点<br/>6/6 子部分 + anchors ok"]):::okNode
    DENY -.-> |不发现隐藏渠道<br/>凭口头答复下结论| FAIL(["失败出口<br/>结论无书面依据"]):::failNode

    classDef startNode fill:#cfe8ff,stroke:#3d7dbf,color:#000
    classDef okNode fill:#c8f7c5,stroke:#2e9e44,color:#000
    classDef failNode fill:#ffd6d6,stroke:#cc3333,color:#000
```

参考动作序列（ref_ops）：visit service 页 → send support（核保修）→ followup 补件 → advance 11-12 → discover jiguang_visit_register → 提交表单 → wait repair → advance 11-18 08:30 → discover + 调用 jiguang_visit_status。

---

## 二、Agent 实际路线

```mermaid
flowchart TD
    S(["开始 11-04 16:00 (步1)"]):::startNode

    S --> P1["步2-4: web_search + 浏览简介/联系/入口三页<br/>fetch 收费标准.pdf ✔<br/>(读到 260 元陷阱但最终未采信)"]:::okNode
    P1 --> ERR1["步5: action_error<br/>JSON 格式 ValueError"]:::warnNode
    ERR1 --> M1["步9: 发信客服孟竹 CASE-0001 ✔<br/>(11-04 16:00)"]:::okNode
    M1 --> M1b["步10-16: 等待并读回信 ✔<br/>客服: 在保修范围内 + suggest 猜测<br/>口头印象 260 元、渠道记不准"]:::okNode
    M1b --> D15["步15: discover_tools 名字猜错<br/>'上门时段登记' → found=false ⚠"]:::warnNode
    D15 --> E1["步17-18: 直接并行发信<br/>工程师 CASE-0002 ✔ / 零件库 CASE-0003 ✔"]:::okNode

    E1 --> W1["步19-30: 连续 wait_until 空转 ×8<br/>11-05 → 11-16<br/>(工程师周二周四才办公<br/>零件库 not_before 11-13)<br/>期间步24-25 重复刷简介页/搜索"]:::warnNode
    W1 --> C1["步31: 收到零件库回信 ✔<br/>费用 0 元 (11-16 09:03)"]:::okNode
    W1 --> T1{"步33-34: CASE-0002 working<br/>11-17 10:23 收工程师<br/>acknowledge + consult 转交信"}
    T1 --> P2["步35: 重访简介页 ✔<br/>看到 11-13 更新<br/>隐藏渠道已点名"]:::okNode
    P2 --> DISC["步36-37: discover_tools<br/>jiguang_visit_register ✔<br/>jiguang_visit_status ✔"]:::okNode
    DISC --> REG["步38: 提交上门预核登记 ✔<br/>(11-17 10:23)"]:::okNode
    REG --> STAT["步39: status 查询=已提交待办结 ✔"]:::okNode
    STAT --> W2["步40-42: 等待<br/>11-18 16:00 收 MSG-0006<br/>步43: status 查询 ✔<br/>办结: 最早上门 11-18 10:00"]:::okNode

    W2 --> MISSING["步44-47: CASE-0002 仍 waiting_internal<br/>工程师诊断复函 (G-42) 未到<br/>未等、未催 → 总结缺 G-42 ✘"]:::failNode
    MISSING --> ERR2["步48-49: action_error ×2<br/>JSON 格式 ValueError"]:::warnNode
    ERR2 --> A1["步50-51: 重读简介页<br/>11-18 17:00 提交答案<br/>conclusion=covered_pending_booking ✔<br/>summary: 保修覆盖/费用0/最早上门11-18 10:00 ✔<br/>但写'配件名称尚未获书面确认' ✘"]:::failNode
    A1 --> R(["终局: 5/6 子部分<br/>judge 83% · anchors ✘<br/>G-42 缺失 → 未通过"]):::failNode

    classDef startNode fill:#cfe8ff,stroke:#3d7dbf,color:#000
    classDef okNode fill:#c8f7c5,stroke:#2e9e44,color:#000
    classDef warnNode fill:#fff3c4,stroke:#d4a017,color:#000
    classDef failNode fill:#ffd6d6,stroke:#cc3333,color:#000
```

补充：action_errors 共 **3 次**（第 5、48、49 步，均为 LLM 输出非单个 JSON 对象导致的 ValueError，重试后恢复）。步19–30 的连续 wait_until 为跨日等待（工程师仅周二/周四办公、零件库 11-13 后才核验），属合理等待而非死循环；步24-25、46、50 在等待间隙重复访问已见过的页面，无信息增量。

---

## 三、设计路径 vs Agent 实际对照

| 环节 | 参考策略 | Agent 实际 | 结果 |
|---|---|---|---|
| 信息入口 | 浏览官网三页 + 识别收费标准为越权陷阱 | 步2-8 浏览三页并 fetch 收费标准 | ✔（260 元最终未被采信） |
| 保修核实 | 发信客服孟竹，提供 serial+receipt | 步9 发信 CASE-0001 | ✔ |
| 配件/费用/渠道线索 | 等客服转交工程师，沿 consult 回传链拿 G-42 与 0 元 | 直接并行发信工程师与零件库（合法替代），费用 0 元于 11-16 到手；工程师复函未等到 | ⚠ |
| 隐藏渠道发现 | 客服 suggest / 工程师 deny 点名 jiguang_visit_register；11-13 页面更新 | 步15 猜名失败；步35 重访更新后的简介页后步36-37 解锁双工具 | ✔（晚于设计但成功） |
| 上门时段书面结论 | 提交 visit_form → 11-17 16:00 办结回执 → status 复核 | 步38 提交、步43 复核，拿到 11-18 10:00 尚未预约 | ✔ |
| G-42 配件确认 | 工程师周四 14:00 诊断 lookup(part) 后复函 "G-42密封圈" | CASE-0002 至提交时仍 waiting_internal，agent 未等待/未催办，总结写"配件尚未书面确认" | ✘ |
| 提交答案 | conclusion=covered_pending_booking；summary 含 4 项 goal 证据（含 G-42） | conclusion ✔；summary 含保修/0 元/11-18 10:00，独缺 G-42 | ✘ |

**失败链**：工程师诊断复函未到达（CASE-0002 waiting_internal，步44）→ agent 提前于 11-18 17:00 提交答案（步51）→ summary 写"配件名称尚未获书面确认" → 缺少 G-42 关键要素 → W-R2-part 未通过 + deterministic anchor G-42 缺失 → 5/6、anchors_ok=false → complete=false。

---

## 四、合法替代路径

任务源码 `alternate_paths` 采用默认表述：

> "接受任意满足全部目标证据条件的合法沟通顺序；参考动作不是唯一标准路径。"

本任务中 agent 的两处偏离均属合法替代：(1) 不经客服转交、直接并行发信工程师与零件库（收到了零件库 0 元费用复函）；(2) 隐藏渠道经由 11-13 页面更新而非 NPC 回复点名发现。失败不在路径选择，而在**提前提交**——G-42 尚未拿到书面确认即提交答案，同时违反 W-R2-part 判据与 G-42 anchor。
