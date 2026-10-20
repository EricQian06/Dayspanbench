# DSB-43 可视化 — Club recruitment: two app groups, staggered surveys, one interview clash

- 任务源码：`scripts/club_cases/dsb43_club_recruitment.py`（club_cases 管线，v0.5 范式）
- Agent 轨迹：`artifacts/evaluation_runs/1024-043-rerun2/DSB-43`（deepseek-v4-flash，45 步，action_errors 1 次）
- 最终结果：**judge 6/6 subparts，deterministic_anchors_ok = True，complete = True，conclusion = resolved**
- 时区说明：虚拟时钟为 UTC；任务 `display_timezone` 为 Asia/Shanghai（UTC+8），下文时刻均已换算为北京时间

---

## 一、任务推进流程（作者设计路径）

```mermaid
flowchart TD
    S(["开始 9.11 周五 20:00<br/>游园祭当晚开局"]) --> W1["web_search → festival 页<br/>拿到两个 t.me 群链接"]
    W1 --> J1["discover bwc_group → 即时入群<br/>读置顶公告：bwc_survey 9.14 开"]
    W1 --> J2["discover pnc_group → 审核 12h<br/>9.12 12:00 group_approved"]
    J2 -.->|9.13 20:00–9.14 09:00<br/>满员窗口·非致命| J2B["入群被拒 full<br/>等 9.14 早重试"]
    J2B -.-> J2

    subgraph ASK["问用户（consult_user，必做）"]
        A1["Alex 的本人答案：<br/>羽协可 9.21/22/24/25（排除周三 9.23）·Competition<br/>钢协两天都行 · 6 年琴龄 · Performance"]
    end
    J1 --> A1
    A1 --> F1["9.14 开表后提交 bwc_survey<br/>窗口 9.14–9.17"]
    A1 --> F2["9.15 开表后提交 pnc_survey<br/>窗口 9.15–9.18<br/>错值会被退回重交（限窗口内）"]
    F1 -.->|字段不符| F1R["退回 → 窗口内改对重交"]
    F2 -.->|字段不符| F2R["退回 → 窗口内改对重交"]
    F1 --> R1["9.14 18:00 处理完成<br/>R-receipt + fact bwc_survey_recorded"]
    F2 --> R2["9.15 18:00 处理完成<br/>R-receipt + fact pnc_survey_recorded"]

    R1 --> T1["9.17 18:00 群时间线：<br/>羽协面试 Group 3 · 周二 19:40–20:40"]
    R2 --> T2["9.19 18:00 群时间线：<br/>钢协面试 · 周二 20:00–21:10"]
    T1 --> C{"两时段均落 9.22 周二<br/>19:40–20:40 ∩ 20:00–21:10 冲突？"}
    C -- 是 --> D1["找对人：Events head 周亚楠<br/>（群成员表/directory）<br/>⚠ 会长林志远只做转介"]
    C -- 是 --> D2["找对人：钢协会长吴可信<br/>（管面试改动）<br/>⚠ Events head 陈默只做转介"]
    D1 --> E1["邮件需同时传达：<br/>要改期 + 周三 9.23 不可用<br/>（LLM extract 两字段全真才走正确分支）"]
    D2 --> E2["邮件传达保留原时段 + 周三不可用<br/>（keep_original=true, wednesday_free=false）"]

    E1 -.->|"漏说周三（Trap A）"| X1["分支：改到周三 19:30–20:30<br/>fact bwc_wednesday_booked ✘<br/>→ follow-up 开新 case 补救"]
    E2 -.->|"接受周三提议（Trap B）"| X2["分支：改到周三 20:00–20:10<br/>fact pnc_wednesday_booked ✘"]
    X1 --> E1B["follow-up 补上周三限制<br/>extract 全真 → fact bwc_rescheduled_monday<br/>周一 9.21 19:30–20:30 Gym Court 2"]
    E1 -->|正确| E1B
    E2 -->|正确| G2["fact pnc_confirmed_original<br/>保留周二 20:00–21:10"]

    E1B --> FIN(["提交答案：resolved<br/>summary 须含冲突、两表答案、<br/>排除 9.23、周一新时段、钢琴保留原时段"])
    G2 --> FIN
    style S fill:#cfe8ff
    style FIN fill:#c8f7c5
    style X1 fill:#ffd6d6
    style X2 fill:#ffd6d6
    style J2B fill:#fff3c4
```

设计要点：一周三小时群是独立 app 服务（浏览器不能入群）；问卷时间窗 9.14–9.17 / 9.15–9.18 在表单工具层强制执行；extract 受助人分支只匹配 LLM 提取的结构化字段，绝无关键词判定。

## 二、Agent 实际路线（1024-043-rerun2，45 步）

与第一节同款样式，✔ 成功绿底 / ⚠ 卡点黄底 / ✘ 失误红底，步号为 rpc_trace 步号：

```mermaid
flowchart TD
    S(["步1-2 observe / recall_task<br/>9.11 20:00"]) --> W1["✔ 步3-8 web_search + 5 页浏览<br/>festival 页拿双群链接<br/>9.11 20:0x"]
    W1 --> J1["✔ 步9,11 bwc_group 即时入群<br/>步13 读置顶：survey 9.14 开"]
    W1 --> J2["✔ 步10,12 pnc_group 提交申请 pending<br/>9.12 12:00 自动批准（audit）"]
    J1 --> A1["✔ 步14 consult_user 一次问全 4 项<br/>user_reply 9.11 22:54：<br/>排除 9.23 周三 · Competition · 6年 · both · Performance"]
    A1 --> F1["✔ 步17,19,22 等 9.14 08:00 开表<br/>bwc_survey 一次通过<br/>9.14 18:00 R-0001 + bwc_survey_recorded"]
    A1 --> F2["✔ 步23,24 等 9.15 08:05<br/>pnc_survey 一次通过<br/>9.15 18:00 R + pnc_survey_recorded"]
    F1 --> T1["✔ 步28-32 等 9.17 群时间线<br/>羽协 Group 3 · 周二 19:40–20:40"]
    F2 --> T2["✔ 步35,36 等 9.19 18:00 后读 pnc 群<br/>钢协 · 周二 20:00–21:10"]
    T1 --> C{"步 33-34 冲突识别 ✔<br/>查成员表 + directory 找周亚楠"}
    C -- 冲突 --> E1["✘ 步38 首封邮件给周亚楠（CASE-0001）<br/>只说要改期，漏说周三限制<br/>extract {wants_move:T, wednesday_unavailable:F}<br/>→ Trap A 触发：R-0003 改到周三 19:30–20:30<br/>fact bwc_wednesday_booked"]
    C -- 冲突 --> E2["✔ 步39,42 查 directory 找吴可信<br/>邮件表达保留原时段（CASE-0003）<br/>extract {keep_original:T, wednesday_free:F}<br/>9.19 20:26 回信确认周二 20:00–21:10<br/>fact pnc_confirmed_original"]
    E1 --> E1B["✔ 步40 读到回信发现周三档<br/>步41 follow-up 开新 case（CASE-0002）补周三限制<br/>extract 全真 → 9.19 20:17 回信<br/>周一 9.21 19:30–20:30 Gym Court 2<br/>fact bwc_rescheduled_monday"]
    E1B --> FIN(["✔ 步45 submit_answer<br/>conclusion resolved · 6/6"])
    E2 --> FIN
    style S fill:#cfe8ff
    style FIN fill:#c8f7c5
    style E1 fill:#ffd6d6
    style E1B fill:#c8f7c5
    style E2 fill:#c8f7c5
```

- **action_errors：1 次**（步 37，非法 JSON，下一个动作步 38 正常恢复）
- 群容量满员窗口（9.13 20:00–9.14 09:00）本 run 未被踩中（agent 9.11 已入群）
- 与上一轮（1024-043-deepseek 修复版）相比：本轮 agent 在 9.15 当天即正确提交钢协问卷，未触发退回路径；但 Trap A 真实触发并经 follow-up 恢复，验证了陷阱分支 + follow-up 新 case 二次 extract 的完整链路

## 三、设计路径 vs Agent 实际对照

| 环节 | 参考策略（reference） | Agent 实际 | 结果 |
|---|---|---|---|
| 入口信息 | festival 页拿双群链接 | 步 3–8 同路径 | ✓ |
| 入群 | bwc 即时 / pnc 审核 12h | 步 9–12，9.12 12:00 批准 | ✓ |
| 问用户 | consult_user 两次（问卷前 + 冲突后） | 步 14 一次问全，冲突后未再问（已有答案，可接受） | ✓ |
| bwc 问卷 | 9.14 开表提交，排除周三 | 步 22 一次通过，R-0001 | ✓ |
| pnc 问卷 | 9.15 开表提交 both/6 年/Performance | 步 24 一次通过（上轮曾退回重交，本轮无） | ✓ |
| 排班读取 | 9.17 / 9.19 后读群时间线 | 步 28–32 / 35–36 | ✓ |
| 找对人 | 周亚楠（改期）/ 吴可信（确认）；避开会长转介 | 群成员表 + directory，未踩转介陷阱 | ✓ |
| 羽协改期邮件 | 一次传达 wants_move + 周三限制 | 步 38 漏周三 → Trap A（R-0003 周三档）；步 41 follow-up 补救 | ⚠→✓ |
| 钢协确认 | 保留原时段、拒绝周三提议 | 步 42 一次到位，pnc_confirmed_original | ✓ |
| 提交答案 | resolved + 完整 summary | 步 45，judge 6/6 | ✓ |

失败链（本 run 唯一失误）：首封羽协邮件漏传达周三限制 → extract 走陷阱分支 → `bwc_wednesday_booked`（周三 19:30–20:30 面试）→ agent 读回信发现与排练冲突 → follow-up 开新 case 补充限制 → 二次 extract 命中正确分支 → `bwc_rescheduled_monday`。**失误被 follow-up 路由机制兜住，未影响最终判定。**

## 四、合法替代路径

摘自 `alternate_paths`：任意合法顺序的入群、问卷提交、时间线读取与负责人邮件均被接受，只要每个 goal 的证据条件成立；两个俱乐部可任意先后处理；冲突也可以通过把羽协面试改到用户实际有空的其他晚上解决——参考策略的周一时段只是其中一个合法结果，不是唯一解。
