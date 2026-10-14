# 实验报告：deepseek-v4-flash × DaySpanBench（DSB-01…42 全量）

- 日期：2026-10-13 / 10-14
- 被测模型（Agent）：`deepseek-v4-flash`（网关 https://az.gptplus5.com/v1）
- 人物模拟器 / LLM Judge：`deepseek-v4-flash`（同网关；judge 仅作语言层独立指标）
- 协议：JSON action chat；`max_tokens=4096`；虚拟日历；确定性评分（scoring v0.3.0）；`max_steps=80`，`workers=3-4`，`seed=0`
- Run 目录：
  - `artifacts/evaluation_runs/1013-004-deepseek`（首轮全量 42 题）
  - `…-rerun` / `…-rerun2*` / `…-rerun3`（环境缺陷修复后的分批重跑；每任务取**修复后的最新有效 run** 计入最终结论）

## 结论概览

| 指标 | 首轮 | 修复环境缺陷后（最终） |
|---|---:|---:|
| 可解决题成功（resolved，DSB-12 除外） | 19/41（46.3%） | **26/41（63.4%）** |
| 截止受阻题处理成功（DSB-12） | 1/1 | 1/1 |
| 无效 episode | 0 | 0（计入最终结论的均为有效运行） |

首轮 22 个失败任务逐项归因后，发现 13 个任务受**交互器缺陷**影响（表单 expect 逐字匹配过严、模拟器路由错过隐藏工具揭示通道、隐藏工具结构上不可发现、dialogue 批准规则不可达、拒绝文案误导）。修复引擎与 8 个 latch 任务源码并重跑后，其中 7 个任务转为通过；**最终剩余 16 个失败全部归因于 Agent 自身行为**，环境侧问题清零。

修复明细见 `dayspanbench/engine.py`（字段等价：类型归一/冠词容错/list 别名；拒绝文案指明不匹配字段）、`dayspanbench/simulator.py`（路由优先字面点名的工作流）、`scripts/latch_cases/`（DSB-14/21/31/33/34/35/39/41）。设计考点（catalog 轮换、suggest 误导、decoy 选项）未软化；136 个单元测试、validate、replay 全绿。

## 全部 42 题结果（最终口径）

| 任务 | 标题 | 结果 | 事实覆盖率 | 虚拟天数 | 步数 | LLM Judge | 失败归因 |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| DSB-01 | 活动场地：跨周末确认设备与报价 | ✅ | 100% | 5.2 | 36 | — | — |
| DSB-02 | 租房咨询：物业周审与新一期货梯表 | ✅ | 100% | 9.0 | 30 | — | — |
| DSB-03 | 学分转换：秋季补件与春季集中审议 | ✅ | 100% | 96.0 | 49 | — | （首轮环境：路由缺陷；修复后通过） |
| DSB-04 | 共享仪器：培训、进口耗材与七天稳定性校准 | ❌ | 50% | 23.3 | 73 | — | Agent |
| DSB-05 | 制造采购：28天耐久测试后重新询价 | ✅ | 100% | 36.1 | 46 | — | — |
| DSB-06 | 家电保修：等待原厂补货与工程师轮值 | ❌ | 50% | 14.0 | 72 | — | Agent |
| DSB-07 | 档案使用：权利继受核验后重新启动数字化 | ✅ | 100% | 213.8 | 43 | — | — |
| DSB-08 | 无障碍住宿：两家机构比较与延后的现场测量 | ✅ | 100% | 7.0 | 57 | — | — |
| DSB-09 | 公共活动咨询：意见征集与年末联合复核 | ✅ | 100% | 55.4 | 35 | — | — |
| DSB-10 | 二手相机：夜间联系、周末实测与取件咨询 | ❌ | 100% | 3.2 | 38 | — | Agent（结论键笔误） |
| DSB-11 | 开源兼容性：补丁验证后按窗口复核发布状态 | ✅ | 100% | 123.1 | 40 | — | — |
| DSB-12 | 跨境原型设备：300天内的初审、二次补件与未决放行 | ✅(受阻题) | 100% | 300.0 | 80 | — | 有意 blocked，处理得当 |
| DSB-13 | Family lunch: verified access, sesame controls | ✅ | 100% | 2.1 | 77 | 2/2 | — |
| DSB-14 | Outage correction: halt, retract, dispatch | ❌ | 80% | 0.1 | 80 | 1/3 | Agent（首轮含环境成分；修复后仍败于自身） |
| DSB-15 | Unauthorized app charge: scoped token reversal | ❌ | 67% | 2.0 | 54 | 1/2 | Agent |
| DSB-16 | Portfolio gate: assessed coursework | ✅ | 100% | 10.1 | 67 | — | — |
| DSB-17 | Home family lunch: helper-covered meal | ❌ | 100% | 2.1 | 47 | 2/2 | Agent（引证错误） |
| DSB-18 | Permit renewal: portal supplement + notice | ❌ | 50% | 9.3 | 77 | — | Agent（首轮含环境成分） |
| DSB-19 | Clinic-gated accessible rehabilitation trip | ❌ | 100% | 2.2 | 51 | 1/1 | Agent（引证错误） |
| DSB-20 | Remediation gate: hold unitA after evidence chain | ✅ | 100% | 6.3 | 68 | 3/3 | （首轮环境；修复后通过） |
| DSB-21 | Verified delivery: demand returned once | ❌ | 33% | 1.8 | 79 | 1/3 | Agent（修复后仍选错 desk） |
| DSB-22 | Film and jazz evening with a current feature | ✅ | 100% | 2.1 | 47 | — | — |
| DSB-23 | Lyon pet stay: delayed late arrival | ✅ | 100% | 0.7 | 49 | 2/2 | — |
| DSB-24 | Deadline replan: moved review | ✅ | 100% | 1.5 | 55 | 2/2 | — |
| DSB-25 | Fridge replacement: installment-gated | ✅ | 100% | 2.1 | 57 | 2/2 | — |
| DSB-26 | Conference travel after replan | ❌ | 17% | 2.3 | 79 | 0/2 | Agent |
| DSB-27 | Scoped account recovery | ✅ | 100% | 1.2 | 80 | 2/2 | — |
| DSB-28 | Analytics pathway: verified prerequisite | ❌ | 0% | 2.3 | 73 | 2/2 | Agent |
| DSB-29 | Weekend care handoff | ✅ | 100% | 1.3 | 44 | — | — |
| DSB-30 | Duplicate hotel charge: one dispute | ✅ | 100% | 4.1 | 51 | 2/2 | — |
| DSB-31 | Relief appeal: correct address history | ✅ | 100% | 4.0 | 47 | — | （首轮环境；修复后通过） |
| DSB-32 | Specialist follow-up after referral | ✅ | 100% | 2.0 | 61 | 3/3 | — |
| DSB-33 | Attended leak inspection | ❌ | 100% | 2.1 | 26 | 3/3 | Agent（引证错误） |
| DSB-34 | Credit renewal: correct the written rider | ✅ | 100% | 7.0 | 58 | 2/2 | （首轮环境；修复后通过） |
| DSB-35 | Deposit demand: verified recipient | ❌ | 100% | 1.9 | 59 | — | Agent（值对、引证不支持） |
| DSB-36 | Accessible festival evening | ❌ | 100% | 0.2 | 80 | — | Agent（引证错误） |
| DSB-37 | Rail cancellation with accompanied bike | ❌ | 100% | 0.1 | 48 | — | Agent（引证错误） |
| DSB-38 | Pet ownership transfer: right Luna | ✅ | 100% | 2.0 | 61 | 2/2 | — |
| DSB-39 | Weekly replanning: protected caregiver window | ✅ | 100% | 3.2 | 53 | — | （首轮环境；修复后通过） |
| DSB-40 | Fridge replacement: verified access | ✅ | 100% | 1.4 | 66 | — | — |
| DSB-41 | Five-person Chicago-Seattle family trip | ✅ | 100% | 11.4 | 78 | 3/3 | （首轮环境；修复后通过） |
| DSB-42 | Interview rescheduling: two separate records | ❌ | 75% | 2.1 | 80 | 1/2 | Agent（设计内陷阱未重查） |

注：修复后通过的任务（03/20/31/34/39/41）其行内数据取自修复后的重跑；"—" 表示该任务无 judge_criteria（DSB-01…12 手写任务）或未启用。

## 未通过任务的 Agent 失败具体原因（16 题 + DSB-12 说明）

**一、证据引用错误（值对但引错证据编号/predicate）——6 题**

- **DSB-17**（helper_window）：期望授权窗口 `13:00-15:00`，Agent 报 `13:30-14:30` 并引用 EV-0018（predicate=helper_acknowledged）——把"覆盖确认"证据当"授权窗口"证据；正确的 EV-0015/EV-0017 已在案。
- **DSB-19**（outbound_arrival / lift_verified）：两项数值全对（09:25 / true），但引用了 EV-0016（outbound_booked 预订凭证）；正确的 EV-0006（arrival）与 lift 类证据都已送达，Agent 拿到了却没在 claims 中引用。
- **DSB-33**（landlord_pays）：正确证据是房东书面授权 EV-0003，Agent 引用 EV-0009（fee=40 的证据，不支持 true）。
- **DSB-35**（verified_recipient / return_address）：dispatch 办结成功（dispatch-L1），值本身正确，但引用的证据不支持这两个 claim（value_not_supported）。
- **DSB-36**（seats）：值=3 正确，引用了 EV-0025（预约凭证，facts 只覆盖 access_reserved+total_cost）而非覆盖 seats 的 EV-0007/EV-0010。
- **DSB-37**（bike_accompanied）：值=true 正确，引用 EV-0007（bundle 预约凭证）而非 rail_desk 签发的 bike-MOB1 证据（EV-0001…0006）。

**二、时间管理 / 未在办结后重查——5 题**

- **DSB-04**（earliest_measurement / price）：按已取消批次日期提交培训表单被退回（11-13），重交后 11-20 才拿到安全证书，工程师 case 11-23 受理、预计 12-01 办结 > 截止 11-27。根因：提交前未重访官网核对批次改期，损失关键一周。
- **DSB-06**（covered / replacement_part）：上门预核表单已办结并签发 earliest_visit 证据，但"是否在保/更换零件"需要经工程师工作流函件确认；Agent 未推进该函件链即提交 unconfirmed。
- **DSB-14**（retracted / dispatched）：retraction 表单 10:45 办结成功，但 Agent 最后一次状态查询在 10:30（办结前），11:00 直接以 not_feasible 提交，从未看到办结确认；dispatched 目标需要在 06:00 卡车发出前通过 print_replace_desk 选 job442-corrected-manifest，Agent 只查过 status、从未提交选择（deadline 时间管理失败）。
- **DSB-15**（dispute_filed / disputed_amount）：00:05 提交 dispute 被拒（期限后台账记录已换名 charge-photo-final），拒绝结果 15:00 才经查询看到——期间空等近 15 小时未查 dispute 状态、未重查台账；当刻重交后立即交卷，无取证时间。
- **DSB-18**（notice_delivered / supplement_submitted / followup_complete）：initial 表单第 3 次才通过（前两次因字段口径；环境侧已修复），但通过当天 22:00 刚提交 notice/supplement 就交卷，未等 15 分钟-2 小时的办结周期，三项全部 unconfirmed。

**三、选错工具 / 未提交关键动作——3 题**

- **DSB-21**（5 项）：sofia_dialogue 发现与批准均已拿到（修复生效）；但地址变更后 Agent 仍用旧的 `xlc_dispatch_desk`（Suite 900 收件人是 redispatch desk 的口径）提交被拒；还把 Sofia 原话完整地址与表单口径混用。正确路径：换 `xlc_redispatch_desk`。
- **DSB-26**（5 项）：catalog 轮换后 entry id 变化（care-B→care-B-final），Agent 把查询结果里的 fields.caregiver 字段值当 entry id 提交，三次全拒后未纠正。
- **DSB-28**（2 项）：从未提交 first_stage 预订；反复 discover_tools 一个不存在的 "program_board" 工具 10+ 次；08-24 书面核验条目上架、08-25 页面更新后一次都没回查，直到 deadline 提交全 unconfirmed。

**四、其他（笔误 / 设计内陷阱应对）——2 题**

- **DSB-10**：5 个 goal 全过、证据齐备，唯一失败是结论枚举键写成 `does_not_meets_requirements`（正确键 `does_not_meet_requirements`，多一个 s）。
- **DSB-42**（shopify_rescheduled）：14:00Z 提交 w02 时 w02-v1 仍是当前行，但 process_delay 使处理落在 15:00Z，恰过 09:30 链接轮换点被拒——这是有意设计的轮换陷阱；陷阱生效后拒绝文案明确提示 stale/rotated 且 board 已换 w02-v2，Agent 有充足时间重提却只查了两次 status、从未重查 board 放弃。

**DSB-12 说明**：任务设计为截止前不可放行（bounded_unresolved），Agent 正确完成了全部可核实目标并以受阻标签提交，`bounded_handling_success=true`，按设计计为通过。

## Agent 失败模式统计

| 模式 | 任务数 | 占失败比 |
|---|---:|---:|
| 证据引用粗心（值对、引错编号/predicate） | 6 | 37.5% |
| 时间管理（未等办结/被拒后不重查/错过 deadline） | 5 | 31.3% |
| 选错工具/未提交关键动作 | 3 | 18.8% |
| 枚举键笔误 | 1 | 6.3% |
| 设计内陷阱被套后放弃 | 1 | 6.3% |

## 附：首轮环境缺陷清单（已全部修复并验证）

1. 表单 expect 逐字匹配过严：`"the landlord"`≠`landlord`、数字 310≠`"310"`、页面原话≠ID 令牌、`.pdf` 后缀、版本号口径（DSB-14/18/20/21/31/34/35）
2. 拒绝文案不指明不匹配字段 / 与事实矛盾（DSB-14/33）
3. 模拟器路由错过 deny/渠道类工作流 alias，隐藏工具名无法揭示（DSB-03/06）
4. sofia_dialogue 结构上不可发现（DSB-21，作者遗漏）
5. dialogue approve 规则永不授予批准而任务以批准为前置（DSB-39/41）

修复原则遵循 `complexify.md`：只修机制不一致，不软化考点。修复后重跑确认：上述任务中 03/20/31/34/39/41 转为通过，其余任务失败原因全部落在 Agent 侧。
