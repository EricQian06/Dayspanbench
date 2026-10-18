# DaySpanBench 手写任务集 v0.4

> 下表参考历时来自历史回放。2026-10-18的对话与排程修复后，尤其DSB-04、06、13、16、23的当前配置应以各任务JSON为准；历史回放未作为新模型成绩重新计分。

42个合成场景（12个中文原创场景 + 30个自LATCH_BENCH语料移植的英文场景）、96个独立角色。所有时间线由事件引擎回放验证。

参考历时采用近似对数间隔：**2、3、5、8、13、21、34、55、89、144、210、300天**。2–7天、8–30天、31–100天、101–300天四档各3题；这是测评采样设计，不代表现实办事时间的频率分布。详见[跨度设计](horizon-design.md)。

这些是作者参考轨迹的历时，不是任务的最短时间，也不是任何LLM的成绩。DSB-12评价截止前的受阻处理，不能并入已获取全部信息的成功率。

| 任务 | 场景 | 人物 | 参考历时 | 时间档 | 参考结束（北京时间） | 结果类型 |
|---|---|---:|---:|---|---|---|
| [DSB-01](tasks/DSB-01.md) | 活动场地：跨周末确认设备与报价 | 4 | 4.3125天 / 103.5小时 | 短期 | 2026-11-10 Tue 17:30 | resolved |
| [DSB-02](tasks/DSB-02.md) | 租房咨询：物业周审与新一期货梯表 | 3 | 8.625天 / 207小时 | 中短期 | 2026-11-12 Thu 10:30 | resolved |
| [DSB-03](tasks/DSB-03.md) | 学分转换：秋季补件与春季集中审议 | 4 | 89.8125天 / 2155.5小时 | 中长期 | 2027-02-03 Wed 09:30 | resolved |
| [DSB-04](tasks/DSB-04.md) | 共享仪器：培训、进口耗材与七天稳定性校准 | 4 | 21.0556天 / 505.33小时 | 中短期 | 2026-11-25 Wed 10:50 | resolved |
| [DSB-05](tasks/DSB-05.md) | 制造采购：28天耐久测试后重新询价 | 3 | 34.8542天 / 836.5小时 | 中长期 | 2026-12-08 Tue 10:30 | resolved |
| [DSB-06](tasks/DSB-06.md) | 家电保修：等待原厂补货与工程师轮值 | 3 | 13.6875天 / 328.5小时 | 中短期 | 2026-11-18 Wed 08:30 | resolved |
| [DSB-07](tasks/DSB-07.md) | 档案使用：权利继受核验后重新启动数字化 | 3 | 214.812天 / 5155.5小时 | 长期 | 2027-06-08 Tue 10:30 | resolved |
| [DSB-08](tasks/DSB-08.md) | 无障碍住宿：两家机构比较与延后的现场测量 | 4 | 6.00764天 / 144.18小时 | 短期 | 2026-11-12 Thu 13:41 | resolved |
| [DSB-09](tasks/DSB-09.md) | 公共活动咨询：意见征集与年末联合复核 | 3 | 55.0417天 / 1321小时 | 中长期 | 2026-12-28 Mon 16:00 | resolved |
| [DSB-10](tasks/DSB-10.md) | 二手相机：夜间联系、周末实测与取件咨询 | 3 | 3.04375天 / 73.05小时 | 短期 | 2026-11-09 Mon 11:03 | resolved |
| [DSB-11](tasks/DSB-11.md) | 开源兼容性：补丁验证后按窗口复核发布状态 | 4 | 111天 / 2664小时 | 长期 | 2027-02-26 Fri 20:30 | resolved |
| [DSB-12](tasks/DSB-12.md) | 跨境原型设备：300天内的初审、二次补件与未决放行 | 5 | 300天 / 7200小时 | 长期 | 2027-09-02 Thu 15:00 | bounded_unresolved |
| [DSB-13](tasks/DSB-13.md) | Family lunch: verified access, sesame controls and a changed offer | 2 | 1.20833天 / 29小时 | 短期 | 2027-07-11 Sun 02:00 | resolved |
| [DSB-14](tasks/DSB-14.md) | Outage correction: halt, retract, dispatch the right run | 2 | 0.059028天 / 1.42小时 | mid-short | 2027-06-11 Fri 18:05 | resolved |
| [DSB-15](tasks/DSB-15.md) | Unauthorized app charge: scoped token revocation and a deadline-gated dispute | 2 | 1.99861天 / 47.97小时 | 短期 | 2027-04-05 Mon 22:58 | resolved |
| [DSB-16](tasks/DSB-16.md) | Portfolio gate: assessed coursework before a truthful job application | 1 | 9.33333天 / 224小时 | mid-short | 2027-02-11 Thu 07:00 | resolved |
| [DSB-17](tasks/DSB-17.md) | Home family lunch: helper-covered meal after a delivery-time change | 3 | 1.33333天 / 32小时 | 短期 | 2027-07-11 Sun 05:00 | resolved |
| [DSB-18](tasks/DSB-18.md) | Permit renewal: portal supplement notice relayed in time | 1 | 8.04167天 / 193小时 | mid-short | 2027-09-21 Tue 23:00 | resolved |
| [DSB-19](tasks/DSB-19.md) | Clinic-gated accessible rehabilitation transport | 2 | 1.19444天 / 28.67小时 | 短期 | 2027-09-04 Sat 01:40 | resolved |
| [DSB-20](tasks/DSB-20.md) | Remediation gate: hold unitA only after the full evidence chain | 2 | 6天 / 144小时 | mid-short | 2027-08-24 Tue 22:00 | resolved |
| [DSB-21](tasks/DSB-21.md) | Verified delivery: demand returned once, correctly re-sent | 1 | 3.0625天 / 73.5小时 | mid-short | 2027-03-22 Mon 23:30 | resolved |
| [DSB-22](tasks/DSB-22.md) | Film and jazz evening with a current feasible return | 1 | 0.791667天 / 19小时 | 短期 | 2027-10-02 Sat 23:00 | resolved |
| [DSB-23](tasks/DSB-23.md) | Lyon pet stay: delayed late arrival, written pet acceptance and supervision | 3 | 0.875天 / 21小时 | 短期 | 2027-04-17 Sat 21:00 | resolved |
| [DSB-24](tasks/DSB-24.md) | Deadline replan: moved review, protected calendar, honest work-plan commitment | 1 | 1.33333天 / 32小时 | 短期 | 2027-10-06 Wed 06:00 | resolved |
| [DSB-25](tasks/DSB-25.md) | Fridge replacement: installment-gated order with a promo expiry | 2 | 1.25天 / 30小时 | 短期 | 2027-06-09 Wed 04:00 | resolved |
| [DSB-26](tasks/DSB-26.md) | Conference travel booked only after replacement care is confirmed | 2 | 2.32639天 / 55.83小时 | 短期 | 2027-09-04 Sat 05:50 | resolved |
| [DSB-27](tasks/DSB-27.md) | Scoped account recovery: official proof, one session revoked, partner share restored | 2 | 0.315972天 / 7.58小时 | 短期 | 2027-01-12 Tue 19:05 | resolved |
| [DSB-28](tasks/DSB-28.md) | Analytics pathway: verified prerequisites and one first-stage reservation | 1 | 2.08333天 / 50小时 | 短期 | 2027-08-26 Thu 00:00 | resolved |
| [DSB-29](tasks/DSB-29.md) | Weekend care handoff: scoped packets, revoked driver link, five acknowledgements | 2 | 1.14583天 / 27.5小时 | 短期 | 2027-09-18 Sat 03:30 | resolved |
| [DSB-30](tasks/DSB-30.md) | Duplicate hotel charge: one approved dispute and a corrected statement | 2 | 4.14444天 / 99.47小时 | 中短期 | 2027-07-15 Thu 01:28 | resolved |
| [DSB-31](tasks/DSB-31.md) | Relief appeal: correct address history, autofill refused | 2 | 3.16667天 / 76小时 | mid-short | 2027-11-05 Fri 03:00 | resolved |
| [DSB-32](tasks/DSB-32.md) | Specialist follow-up after referral review and a lost slot | 1 | 2.10417天 / 50.5小时 | 短期 | 2027-05-13 Thu 00:30 | resolved |
| [DSB-33](tasks/DSB-33.md) | Attended leak inspection: one approved slot, no repairs | 2 | 1.16667天 / 28小时 | 短期 | 2027-06-12 Sat 02:00 | resolved |
| [DSB-34](tasks/DSB-34.md) | Credit renewal: correct the written rider, then register the signed bundle | 1 | 6.29167天 / 151小时 | mid-short | 2027-09-15 Wed 04:00 | resolved |
| [DSB-35](tasks/DSB-35.md) | Deposit demand: verified recipient, private address kept out | 1 | 1.25天 / 30小时 | mid-short | 2027-03-20 Sat 04:00 | resolved |
| [DSB-36](tasks/DSB-36.md) | Accessible festival evening: the correct 21:00 set with step-free travel | 2 | 0.208333天 / 5小时 | 短期 | 2027-08-01 Sun 02:00 | resolved |
| [DSB-37](tasks/DSB-37.md) | Rail cancellation recovery with an accompanied folding bicycle | 1 | 0.1875天 / 4.5小时 | 短期 | 2027-10-08 Fri 02:00 | resolved |
| [DSB-38](tasks/DSB-38.md) | Pet ownership transfer: right Luna across registry, license and shelter release | 2 | 1.27083天 / 30.5小时 | 短期 | 2027-03-24 Wed 04:30 | resolved |
| [DSB-39](tasks/DSB-39.md) | Weekly replanning: protected caregiver week, unsent CEO reply, applied focus plan | 1 | 3.1875天 / 76.5小时 | 中短期 | 2027-05-11 Tue 02:30 | resolved |
| [DSB-40](tasks/DSB-40.md) | Fridge replacement: verified access and a changed delivery slot | 3 | 1.375天 / 33小时 | 短期 | 2027-06-09 Wed 07:00 | resolved |
| [DSB-41](tasks/DSB-41.md) | Five-person Chicago-Seattle family trip: recovered inventory and exact approval | 5 | 13.25天 / 318小时 | 中短期 | 2027-05-15 Sat 04:00 | resolved |
| [DSB-42](tasks/DSB-42.md) | Interview rescheduling: two separate recruiters, rotated link, no cross-employer disclosure | 2 | 2.14583天 / 51.5小时 | 短期 | 2027-09-16 Thu 01:30 | resolved |
