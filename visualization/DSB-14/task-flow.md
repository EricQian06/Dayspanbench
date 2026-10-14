# DSB-14 任务推进流程思维导图（作者视角 / 设计流程）

来源：`scripts/latch_cases/dsb14_outage_correction.py`
背景：Keisha Brown（通讯负责人）的更正流程——JOB441 昨晚把错误的停水通知投到了 1501 U Street；正确的双语门挂通知必须在 06:00 随印刷车出厂。

## 总览（mindmap）

```mermaid
mindmap
  root((DSB-14<br/>停水通知更正))
    背景
      JOB441 误投 1501 U Street
      06:00 印刷车出厂 = 硬截止
      2019 GIS 名单已过期
    信息收集
      crew_listings 隐藏目录
        04:55 前显示 pending
        04:55 后翻转：1400/1408/1410/1418 14th St
      keisha_dialogue 隐藏对话
        授权规则只通过对话浮出
      文档证据
        template-outage-C.pdf 唯一批准模板
        b1400-profile.pdf 双语依据
        gis-2019.pdf 陷阱·过期名单
        shaw-blast.pdf 陷阱·全 Shaw 草稿
        reviewer-schedule.pdf 陷阱·08:30 审校在截止后
    三大动作
      1. 停印 JOB441
        print_halt_desk 表单
        无需 Keisha 预先批准
        隔离剩余库存
      2. 定向撤回
        notice_correction_desk 表单
        仅发 1501 U Street
        必须先获 Keisha 批准
      3. 派发 JOB442
        print_options 目录选 job442
        print_replace_desk 提交
        06:00 准时处理·过期作废
    评分目标
      audience 受众正确
      bilingual 1400 双语
      retracted 定向撤回
      halted 停印+隔离
      dispatched 按时出厂
    陷阱（有意设计）
      沿用过期 GIS 受众
      发全 Shaw 爆发草稿
      等 08:30 西语审校
      全域撤回而非定向
      跳过停印
      谎称已送达门阶
```

## 推进流程（flowchart，含时间与分支）

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

## 时间线要点

| 虚拟时刻 | 事件 |
|---|---|
| 06-11 04:40 | 任务开始（UTC 08:40） |
| 04:55 | crew_listings 翻转：pending → 确认名单 |
| 05:59 | print_replace_desk 处理选中的 manifest |
| 06:00 | 印刷车出厂；print_options 全部条目过期（截止由目录过期而非任务 deadline 强制） |
| 08:30 | 西语审校返回（已在截止后，是干扰项） |
| 06-13 06:05 | 任务 deadline（case 原生边界，宽松） |

## 合法替代路径

任意顺序的「确认受众 → 停印 → 批准 → 撤回 → 派发」均可，只要每个 goal 的证据条件成立；只有 goal 证据参与评分。
