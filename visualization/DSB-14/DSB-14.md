# DSB-14 可视化：任务推进流程 + Agent 实际路线

来源：`scripts/latch_cases/dsb14_outage_correction.py`（任务设计）
轨迹：`artifacts/evaluation_runs/1013-004-deepseek-rerun3/DSB-14/rpc_trace.jsonl`（deepseek-v4-flash，80 步，最终失败 3/5 goals，conclusion=not_feasible）

背景：Keisha Brown（通讯负责人）的更正流程——JOB441 昨晚把错误的停水通知投到了 1501 U Street；正确的双语门挂通知必须在 06:00 随印刷车出厂。虚拟时钟为 UTC，当地 = UTC-4，下文均换算为当地时间。

## 一、任务推进流程（作者设计路径）

```mermaid
flowchart TD
    START(["04:40 开始<br/>(虚拟时间 06-11)"]) --> OBS["observe / recall_task<br/>认识任务面"]
    OBS --> RULES["web_search → intro 页<br/>发现 keisha_dialogue"]
    RULES --> ASK["keisha_dialogue 问规则<br/>·停印可自行授权<br/>·发布须展示确切受众+文案<br/>·永不全域发送<br/>·06:00 为硬截止"]
    ASK --> CREW_BEFORE{"查 crew_listings<br/>(04:55 前)"}
    CREW_BEFORE -->|"pending：<br/>现场确认中"| WAIT("wait_until / 期间做其他事")
    WAIT --> CREW_AFTER
    CREW_AFTER["04:55 后 crew_listings<br/>确认名单：1400/1408/1410/1418<br/>排除 1501 U<br/>1400 需双语"]
    CREW_AFTER --> HALT

    subgraph ACT1["动作1 · 停印（顺序不强制但被鼓励最先做）"]
        HALT["print_halt_desk<br/>job=JOB441<br/>action=halt+quarantine<br/>user_approval=authorized"]
        HALT --> HALT_RES["10 分钟处理<br/>结果只回写到 yard 页<br/>不推送·需回查"]
    end

    HALT_RES --> APPROVE
    subgraph ACT2["动作2 · 定向撤回（须先获批准）"]
        APPROVE["keisha_dialogue：<br/>展示确切撤回方案求批准"]
        APPROVE -->|"Keisha 认可"| RETRACT["notice_correction_desk<br/>recipient=1501 U only<br/>scope=targeted only<br/>user_approval=approved"]
        RETRACT --> RETRACT_RES["15 分钟处理<br/>结果回写 correction 页"]
        APPROVE -.->|"拿不到批准 / scope 错"| RETRACT_REJ["拒绝<br/>检查 scope 重试"]
    end

    RETRACT_RES --> SELECT
    subgraph ACT3["动作3 · 派发更正件"]
        SELECT["print_options 目录<br/>选 job442-corrected-manifest<br/>(非 GIS 重复/非 Shaw 爆发)"]
        SELECT --> DISPATCH["print_replace_desk<br/>entry=job442-corrected-manifest"]
        DISPATCH -->|"06:00 前提交"| DISP_OK["05:59 处理成功<br/>JOB442 随 06:00 车出厂"]
        DISPATCH -.->|"错过 06:00 / 选错"| DISP_REJ["选项过期<br/>无法再出更正版"]
    end

    DISP_OK --> VERIFY["print_replace_desk query<br/>确认 dispatch 状态<br/>(结果从不推送)"]
    VERIFY --> ANSWER["submit_answer<br/>conclusion=dispatched<br/>5 项 goal 各自引用证据<br/>如实说明：出厂 ≠ 送达门阶"]

    DISP_REJ --> ANSWER2["submit_answer<br/>conclusion=not_feasible"]

    style START fill:#e1f5ff
    style ANSWER fill:#c8f7c5
    style DISP_REJ fill:#ffd6d6
    style ANSWER2 fill:#ffd6d6
    style RETRACT_REJ fill:#fff3cd
```

## 二、Agent 实际路线（同一样式，✔ 成功 / ✘ 失误 / ⚠ 失败点）

```mermaid
flowchart TD
    S(["04:40 开始 · 80 步预算"]) --> OBS2["observe / recall_task<br/>✔ 认识任务面"]
    OBS2 --> SEARCH2["web_search → visit intro/contact/entry<br/>✔ 发现 keisha_dialogue<br/>crew_listings、print_halt_desk"]
    SEARCH2 --> ASK2["keisha_dialogue 问规则<br/>✔ 拿到四条规则<br/>(含：停印可自行授权)"]
    ASK2 --> CREWQ{"查 crew_listings<br/>(04:40，早于 04:55)"}
    CREWQ -->|"✘ 只见 pending：<br/>'确认中，稍后再查'"| HALT2

    HALT2["步14 · print_halt_desk 提交停印<br/>✔ 正确字段，submitted<br/>(结果10分钟后回写 yard 页)"]

    HALT2 --> WAIT2["步39 · wait_until 05:00<br/>(期间穿插查目录/发邮件)"]
    WAIT2 --> CREW2["步40 · crew_listings 复查<br/>✔ 04:55 已翻转：<br/>1400/1408/1410/1418，排除 1501 U"]
    CREW2 --> CATALOG2["步19 · print_options 查目录<br/>✔ 看到三条选项<br/>(job442 正确 / GIS重复 / Shaw爆发)<br/>但从未提交选择"]

    subgraph LOOP["⚠ 阶段 · 批准死循环（05:00-05:45）核心失败点"]
        APPROVEQ["keisha_dialogue 求批准<br/>(步24,28,32,41,47,50,52,53,60,62 共10次)"]
        APPROVEQ -->|"❗persona 只复述规则<br/>永不明确说 yes"| APPROVEQ
    end
    APPROVEQ -.->|"查阅陷阱文档 ✓<br/>找 Keisha 邮箱 ✘(不存在)<br/>向 Sam/Dana 发邮件 ×2<br/>(仅礼节性回执)"| APPROVEQ

    LOOP --> HALT3["步65 · 05:45 重交停印表单 ✔"]
    HALT3 --> RETRY1["步66 · 05:45 提交撤回表单<br/>✘ 被拒：recipient 写成<br/>'1501 U Street only'<br/>(期望精确 '1501 U Street')<br/>action 措辞不在白名单"]
    RETRY1 --> DEADLINE{"06:00 · 印刷车出厂"}

    DEADLINE -.->|"print_options 目录过期"| DEAD["步69/72 · 06:05/06:30 再查目录<br/>✘ 全部条目清空<br/>JOB442 永远无法派发"]
    DEADLINE --> RETRY2["步76 · 06:30 重交撤回表单<br/>(action 改为白名单措辞<br/>但 recipient 仍多 ' only')"]
    RETRY2 --> ANS["步80 · 07:00 submit_answer<br/>conclusion=not_feasible<br/>✘ 提交前未回查任何表单结果页<br/>可确认项也报成 unconfirmed"]

    style S fill:#e1f5ff
    style HALT2 fill:#c8f7c5
    style HALT3 fill:#c8f7c5
    style CREW2 fill:#c8f7c5
    style CATALOG2 fill:#c8f7c5
    style LOOP fill:#fff3cd
    style APPROVEQ fill:#fff3cd
    style RETRY1 fill:#ffd6d6
    style DEAD fill:#ffd6d6
    style ANS fill:#ffd6d6
```

另：全程 13 次模型输出非法 JSON（步 7/36/38/46/49/56/57/59/61/68/70/74/75），各浪费一步预算。

## 三、设计路径 vs Agent 实际对照

| 环节 | 参考策略（reference） | Agent 实际 | 结果 |
|---|---|---|---|
| 认识任务面 | visit contacts → 问 Keisha 规则 | web_search → intro → 问规则 | ✓ 等效 |
| crew 名单 | discover 后 advance 到 04:55 查 | 04:40 查到 pending，05:00 复查拿到 | ✓ 等效（多一轮） |
| 停印 JOB441 | 第一时间提交正确表单 | 04:40 提交过一次，05:45 才重交确认 | ✓ 达成 |
| Keisha 批准 | 展示确切方案一次，随后直接填 approved | 10 次求口头批准，始终不敢填 | ✗ 卡死 |
| 定向撤回 | 白名单措辞，精确 recipient | recipient 加" only"、action 自由发挥被拒 | ✗ |
| 选 JOB442 | print_options → 选 job442 | 看到过正确选项但从未提交 | ✗ |
| 派发 | 06:00 前提交 print_replace_desk | 06:00 后目录已清空 | ✗ |
| 回查结果 | advance 后 query 确认 dispatch | 提交答案前未回查任何表单结果页 | ✗ |

失败链因果：persona 永不说 yes → Agent 误以为口头批准是前置条件 → 10 次循环耗掉 05:00-05:45 → 撤回仓促提交被拒 → 拖过 06:00 目录过期 → 派发永久不可行 → 未回查即提交答案。

## 四、合法替代路径

任意顺序的「确认受众 → 停印 → 批准 → 撤回 → 派发」均可，只要每个 goal 的证据条件成立；只有 goal 证据参与评分。
