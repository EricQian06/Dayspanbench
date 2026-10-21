# DSB-43 可视化:Club recruitment — two app groups, staggered surveys, one interview clash

- **任务源码**: [scripts/club_cases/dsb43_club_recruitment.py](../../scripts/club_cases/dsb43_club_recruitment.py)
- **轨迹 run**: `artifacts/evaluation_runs/1025-043-paratera-deepseek/DSB-43`
- **Agent 模型**: DeepSeek-V4-Flash-0731 (paratera),52 步 / 0 action errors / 虚拟时长 9.0 天
- **时区**: 轨迹时刻为 UTC,任务展示时区 Asia/Shanghai(文中时刻已标注,UTC+8 换算后)
- **最终结果**: ✘ **未通过** — judge 6/6 subparts 全过,但 `deterministic_anchors_ok=false`(4 个 fact goals 只注册了 3 个:`pnc_confirmed_original` 从未注册)。conclusion=`resolved` 判定正确。
- **虚拟时间窗口**: 2026-09-11 20:00 → 09-23 18:00 (Asia/Shanghai)

---

## 一、任务推进流程(作者设计路径)

```mermaid
flowchart TD
    START(["开始 09-11 20:00<br/>周五校园节,扫码进两社团群"]):::startNode

    subgraph SG1["信息收集 / 进群阶段 (09-11 晚)"]
        WEB["web_search / visit_page<br/>找到两社团主页与调查页"] --> BWC_JOIN["bwc_group join<br/>✔ 即时入群"]
        WEB --> PNC_JOIN["pnc_group join<br/>⏳ 需管理员审核"]
        PNC_JOIN -.->|"错过容量窗口<br/>(09-13 20:00 ~ 09-14 09:00 满员)"| PNC_LOSE["钢琴群永远进不去<br/>pnc_survey 无法提交"]:::failNode
        PNC_JOIN -->|审核通过| PNC_OK["入群成功<br/>⏳ 群成员上限前通过即可"]
    end

    START --> SG1

    subgraph SG2["调查表阶段 (窗口不同)"]
        CONSULT["consult_user 询问 Alex<br/>可用晚:09-21/22/24/25<br/>周三 09-23 排练不可用<br/>羽毛球→竞赛部 / 钢琴→演奏部"]
        BWC_FORM["bwc_survey<br/>窗口 09-14 ~ 09-16"]
        PNC_FORM["pnc_survey<br/>窗口 09-15 ~ 09-17"]
        CONSULT --> BWC_FORM & PNC_FORM
    end
    SG1 --> SG2

    BWC_FORM -.->|"猜答案不问用户<br/>表单 expect 拒绝"| FORM_FAIL["form 被拒"]:::failNode

    subgraph SG3["面试安排公布 (时间点强制)"]
        BWC_POST["09-17 后读 bwc_group timeline<br/>羽毛球面试:周二 09-22 19:40-20:40<br/>Gym Court 2(一小时团体场)"]
        PNC_POST["09-19 后读 pnc_group timeline<br/>钢琴面试:周二 09-22 20:00-21:10<br/>Music Building A201"]
    end
    SG2 --> SG3

    CLASH{"发现冲突?<br/>周二晚两场重叠<br/>20:00-20:40"}:::decision
    SG3 --> CLASH
    CLASH -.->|"未察觉重叠"| MISS["保留原场次<br/>面试仍冲突"]:::failNode

    subgraph SG4["解决冲突 (关键路径)"]
        DIR1["lookup_directory<br/>→ Zhou Yanan (bwc_events_head)<br/>⚠ 勿找社长 Lin Zhiyuan"]
        EMAIL_BWC["邮件 Zhou Yanan<br/>要求改期 + 声明周三不可用"]
        BWC_MOVE["bwc_move_slot 节点<br/>提议周一 09-21 19:30-20:30"]
        CONFIRM["agent 确认某晚<br/>(bwc_slot_confirm 节点)"]
        SWAP{"bwc_swap_check:<br/>该晚学生是否换场?"}:::decision
        BWC_MOVE --> CONFIRM --> SWAP
        EMAIL_BWC --> BWC_MOVE
        SWAP -.->|"周一固定失败<br/>(周一学生均不能换)"| BWC_MOVE
        SWAP -->|"周三/周四/周五<br/>换场成功"| BWC_DONE["✔ 注册 fact:<br/>bwc_rescheduled_wednesday<br/>/ _thursday / _friday<br/>带书面回执,终态锁定"]
    end

    subgraph SG5["钢琴侧确认 (易遗漏!)"]
        DIR2["lookup_directory<br/>→ Wu Kexin (pnc_president)"]
        EMAIL_PNC["邮件 Wu Kexin<br/>明确表态保留原周二场次"]
        PNC_KEEP["pnc_keep_slot 节点<br/>keep_original=true →<br/>✔ 注册 pnc_confirmed_original<br/>回执确认周二 20:00-21:10"]
        EMAIL_PNC --> PNC_KEEP
    end

    CLASH -->|"改羽毛球场次<br/>(跨日,团体场)"| SG4
    CLASH -->|"钢琴保留原场次"| SG5

    SUBMIT(["submit_answer<br/>conclusion=resolved<br/>summary 覆盖:两表提交+冲突解决+<br/>新羽毛球时段+钢琴保留原时段"]):::goalNode
    BWC_DONE --> SUBMIT
    PNC_KEEP --> SUBMIT
    MISS --> SUBMIT2(["submit_answer<br/>conclusion ≠ resolved"]):::failNode

    classDef startNode fill:#cfe8ff,stroke:#5b9bd5,color:#000
    classDef failNode fill:#ffcccc,stroke:#cc0000,color:#000
    classDef goalNode fill:#c6efce,stroke:#006100,color:#000
    classDef decision fill:#fff2cc,stroke:#bf9000,color:#000
```

**要点**:
- 羽毛球改期链:`bwc_move_slot` → `bwc_slot_confirm` → `bwc_swap_check`,任一晚的确认单封邮件即可同时驱动两个节点(engine 的 derive 机制);换场成功分支为 terminal,锁定后只能收到 authored 道歉信。
- 周三 09-23 是用户排练日(failure mode:向 Events head 声称周三可用 → 被安排到不可去的场次)。
- 钢琴侧无需改期,但**必须**给社长发信表态,`pnc_confirmed_original` 才会注册 —— 不发信,面试"事实上"保留但 goal 不成立。

## 二、Agent 实际路线(同一布局对照)

```mermaid
flowchart TD
    START(["步1 observe<br/>09-11 20:00 (UTC 12:00)"]):::startNode

    subgraph SG1["信息收集 / 进群 (步2-16) ✔"]
        WEB["步2-7 web_search+visit_page×5<br/>两社团主页/调查页 ✔"]
        BWC_JOIN["步10 bwc_group join<br/>✔ 即时入群"]
        PNC_JOIN["步11 pnc_group join<br/>✔ 09-12 12:00 审核通过<br/>(赶在容量窗口前)"]
        WEB --> BWC_JOIN & PNC_JOIN
        STEP16["步16 pnc_group query pinned<br/>09-12 12:00 看到欢迎帖"]
        PNC_JOIN --> STEP16
    end
    START --> SG1

    subgraph SG2["调查表 (步14-22) ✔"]
        CONSULT["步14 consult_user<br/>✔ 正确获得 Alex 可用晚/部门<br/>周三 09-23 排练排除"]
        BWC_FORM["步20 bwc_survey 提交<br/>09-14 00:00 ✔ 接受"]
        PNC_FORM["步22 pnc_survey 提交<br/>09-15 00:00 ✔ 接受<br/>(步21等到窗口开放)"]
        CONSULT --> BWC_FORM & PNC_FORM
    end
    SG1 --> SG2

    subgraph SG3["读公告 (步25-35) ✔"]
        WAIT18_19["步18/19/25/27/29 wait_until 循环<br/>⏳ 等待 09-17 公布"]
        BWC_POST["步30 bwc_group query all<br/>09-17 22:00 ✔ 看到羽毛球面试<br/>周二 19:40-20:40"]
        PNC_POST["步34 pnc_group query all<br/>09-19 20:00 ✔ 看到钢琴面试<br/>周二 20:00-21:10"]
        DIR2["步35 lookup_directory Wu Kexin<br/>✔ 查到钢琴社长联系方式"]
    end
    SG2 --> SG3

    CLASH{"步35 前后察觉冲突<br/>✔ 重叠 20:00-20:40"}:::decision
    SG3 --> CLASH

    subgraph SG4["羽毛球改期 (步36-50) ✔"]
        DIR1["步32 lookup_directory<br/>✔ 直找 Events head Zhou Yanan"]
        EMAIL_BWC["步36 邮件:改期+周三不可用<br/>→ 提议周一"]
        R38["步38 拒周一?否——声明周一可用<br/>→ 周一换场检查"]
        SWAPFAIL["步44 周一学生换场失败<br/>→ 提议周四"]
        R45["步45 确认周四 09-24 19:30-20:30"]
        SWAP["步49 ✔ 周四换场成功锁定<br/>注册 bwc_rescheduled_thursday<br/>回执确认(终态)"]
        EMAIL_BWC --> R38 --> SWAPFAIL --> R45 --> SWAP
    end
    CLASH --> SG4

    subgraph SG5["钢琴侧确认 ✘ — 完全缺失"]
        NOTHING["步34/51 仅 pnc_group query all<br/>看群消息,未发任何邮件<br/>给 Wu Kexin"]
        NOFACT["✘ pnc_confirmed_original<br/>从未注册<br/>goal_facts_established=false"]:::failNode
        NOTHING --> NOFACT
    end
    CLASH -.->|"⚠ 查了社长联系方式(步35)<br/>却从未使用"| SG5

    SUBMIT(["步52 submit_answer<br/>conclusion=resolved ✔<br/>summary 写'钢琴按原场次进行'"]):::goalNode
    SWAP --> SUBMIT
    NOFACT -.->|"judge 被 summary 说服 6/6,<br/>graph fact 门控拦截"| FINAL(["✘ complete=false<br/>resolved_success=false"]):::failNode

    classDef startNode fill:#cfe8ff,stroke:#5b9bd5,color:#000
    classDef failNode fill:#ffcccc,stroke:#cc0000,color:#000
    classDef goalNode fill:#c6efce,stroke:#006100,color:#000
    classDef decision fill:#fff2cc,stroke:#bf9000,color:#000
```

- ✔ 绿:进群、问用户、两表提交、读两组公告、找对 Events head、改期全链走通(含周一失败→周四成功的迂回)。
- ⚠ 黄:wait_until 循环 5 次(步18/19/25/27/29)属正常等窗口;真正的卡点是步35 查到钢琴社长联系方式后**没有任何后续动作**。
- ✘ 红:钢琴侧确认链完全缺失 → `pnc_confirmed_original` 未注册 → deterministic anchors 拦截。
- action_errors:0;52 步全部为合法调用。

## 三、设计路径 vs Agent 实际对照

| 环节 | 参考策略 (reference) | Agent 实际 | 结果 |
|---|---|---|---|
| 找到两社团入口 | web_search → 官网/频道页 → 群工具 | 同路径,步2-9 discover_tools×4 | ✓ |
| 进羽毛球群 | bwc_group join(即时) | 步10,即时成功 | ✓ |
| 进钢琴群 | pnc_group join,须赶在 09-13/14 容量窗口前通过审核 | 步11 提交,09-12 通过 | ✓ |
| 获取用户真实答案 | consult_user(可用晚/部门/周三限制) | 步14 一次性问全 | ✓ |
| 提交两份调查表 | 各自窗口内提交,字段为用户自己的答案 | 步20(09-14)、步22(09-15),均接受 | ✓ |
| 读到两场面试安排 | 09-17 后读 bwc timeline;09-19 后读 pnc timeline | 步30(09-17)、步34(09-19) | ✓ |
| 察觉周二晚冲突 | 对照 19:40-20:40 与 20:00-21:10 重叠 | 察觉并在 summary 说明 | ✓ |
| 联系羽毛球 Events head | lookup_directory → Zhou Yanan(非社长) | 步32 直找 Zhou Yanan | ✓ |
| 声明周三不可用 + 请求改期 | 首信含两项,防被排到排练日 | 步36 首信即声明周三不可用 | ✓ |
| 确认提议晚 + 学生换场 | 确认→swap 检查;周一固定失败则转下一晚 | 步38 确认周一→失败(步44)→步45 确认周四→步49 锁定 | ✓ |
| **给钢琴社长发信表态** | **邮件 Wu Kexin:保留原场次 → 注册 pnc_confirmed_original** | **只查了联系方式(步35),从未发信** | ✗ |
| 提交答案 | conclusion=resolved,summary 覆盖全部四 goal | conclusion ✔,summary 内容与事实相符(除钢琴侧未经确认) | △ |

**失败链**:步35 查到 Wu Kexin 联系方式 → 误以为"钢琴无需动作,保持原样即可" → 从未触发 `pnc_keep_slot` 节点 → `pnc_confirmed_original` 未注册 → `goal_facts_established=false` → `deterministic_anchors_ok=false` → **complete=false**。judge 层 6/6 全过(被 summary 中"钢琴面试按原安排进行"的说法说服),是 v0.6 graph fact 门控把"summary 说得对但路径没走"拦下的典型案例。

## 四、合法替代路径

来自任务 `alternate_paths`:

> 任意合法顺序的进群、提交调查、读公告与负责人邮件均被接受,只要每个 goal 的证据条件成立;两个社团可任意先后处理;羽毛球面试可改到用户实际空闲的**任一**晚上 —— 参考策略的周一场次只是一种合法结果,不是唯一解(本 run 中 agent 走的周四路径同样合法)。

另从 `judge_criteria`/graph 结构:钢琴侧的三个分支(keep original / move Wednesday / default keep)中前两个均注册合法 fact,但 `move Wednesday` 会与用户排练约束冲突(且用户需在信中声明周三可用才触发,如实声明则不会走到);`pnc_wednesday_booked` 不是 `piano_interview_kept` goal 的接受 fact。
