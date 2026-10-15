# DaySpanBench 实测报告

被测模型：`DeepSeek-V4-Flash-0731`；人物模拟器：`DeepSeek-V4-Flash-0731`。
每题独立一次运行；虚拟日历，LLM终审（judge子部分）为主指标，确定性锚点仅作过程核对。该小样本不代表模型稳定成功率。

已结束 42/42 题；有效 42；基础设施/模拟器故障 0；judge挂起 0。
- 可解决题成功率：31/41（75.6%；仅有效且非judge挂起运行）。
- 截止受阻题处理成功率：1/1（100.0%；仅有效且非judge挂起运行）。

| 任务 | 结果 | 评分方式 | 子部分/事实覆盖 | 虚拟天数 | Agent步数 | 对外消息 |
|---|---|---|---:|---:|---:|---:|
| DSB-01 | 通过 | judge | 100% | 4.199306 | 42 | 9 |
| DSB-02 | 通过 | judge | 100% | 8.895833 | 31 | 4 |
| DSB-03 | 通过 | judge | 100% | 89.416667 | 54 | 8 |
| DSB-04 | 未通过 | judge | 67% | 23.061806 | 63 | 9 |
| DSB-05 | 通过 | judge | 100% | 35.125 | 35 | 5 |
| DSB-06 | 未通过 | judge | 83% | 14.041667 | 51 | 3 |
| DSB-07 | 通过 | judge | 100% | 215.811806 | 41 | 5 |
| DSB-08 | 通过 | judge | 100% | 7.1875 | 52 | 5 |
| DSB-09 | 通过 | judge | 100% | 55.083333 | 45 | 10 |
| DSB-10 | 未通过 | judge | 100% | 2.5 | 38 | 6 |
| DSB-11 | 通过 | judge | 100% | 123.104167 | 40 | 4 |
| DSB-12 | 通过 | judge | 100% | 300.0 | 66 | 9 |
| DSB-13 | 未通过 | judge | 67% | 2.125 | 51 | 5 |
| DSB-14 | 通过 | judge | 100% | 0.095833 | 45 | 1 |
| DSB-15 | 未通过 | judge | 100% | 2.0 | 35 | 2 |
| DSB-16 | 未通过 | judge | 100% | 11.333333 | 61 | 3 |
| DSB-17 | 通过 | judge | 100% | 2.125 | 46 | 4 |
| DSB-18 | 未通过 | judge | 83% | 9.333333 | 75 | 2 |
| DSB-19 | 通过 | judge | 100% | 1.479167 | 49 | 3 |
| DSB-20 | 通过 | judge | 100% | 6.25 | 51 | 0 |
| DSB-21 | 未通过 | judge | 100% | 4.333333 | 65 | 3 |
| DSB-22 | 通过 | judge | 100% | 1.5 | 45 | 1 |
| DSB-23 | 未通过 | judge | 60% | 2.0 | 48 | 5 |
| DSB-24 | 通过 | judge | 100% | 2.333333 | 42 | 3 |
| DSB-25 | 通过 | judge | 100% | 1.75 | 32 | 2 |
| DSB-26 | 通过 | judge | 100% | 2.333333 | 48 | 3 |
| DSB-27 | 通过 | judge | 100% | 1.21875 | 75 | 2 |
| DSB-28 | 通过 | judge | 100% | 2.166667 | 49 | 2 |
| DSB-29 | 通过 | judge | 100% | 1.416667 | 32 | 1 |
| DSB-30 | 通过 | judge | 100% | 4.141667 | 29 | 4 |
| DSB-31 | 未通过 | judge | 80% | 4.5 | 76 | 9 |
| DSB-32 | 通过 | judge | 100% | 2.083333 | 51 | 0 |
| DSB-33 | 通过 | judge | 100% | 2.125 | 27 | 2 |
| DSB-34 | 通过 | judge | 100% | 6.3875 | 53 | 2 |
| DSB-35 | 通过 | judge | 100% | 5.125 | 35 | 3 |
| DSB-36 | 通过 | judge | 100% | 0.291667 | 31 | 2 |
| DSB-37 | 通过 | judge | 100% | 0.166667 | 33 | 1 |
| DSB-38 | 通过 | judge | 100% | 1.333333 | 79 | 2 |
| DSB-39 | 通过 | judge | 100% | 3.083333 | 44 | 0 |
| DSB-40 | 通过 | judge | 100% | 2.125 | 40 | 4 |
| DSB-41 | 通过 | judge | 100% | 11.291667 | 75 | 0 |
| DSB-42 | 通过 | judge | 100% | 2.125 | 65 | 4 |

覆盖率列：judge题为子部分通过率（pending不计分母），无judge_criteria的题暂为确定性事实覆盖率。故障与judge挂起不计作Agent失败；步数耗尽而未提交计有效失败。

## 未通过与故障原因

- DSB-04（submitted）：结论标签不正确；子部分L-R5-conclusion未通过：conclusion为available_now而非要求的available_after_calibration，且总结声称当前校准已完成、与“须待校准完成后”相冲突。；子部分L-R6-honesty未通过：总结声称校准已完成、可用窗口已开始，但书面依据仅说明完成校准后才可使用，无证据表明校准实际已完成，属夸大。
- DSB-06（submitted）：总结缺失关键要素：G-42；子部分W-R2-part未通过：The summary explicitly says the specific part name (G-42 seal) is not confirmed, so it does not state that the replacement part is G-42.
- DSB-10（submitted）：总结缺失关键要素：08、2026-11-09T14
- DSB-13（submitted）：结论标签不正确；表单/选择未全部按expect办结；子部分FR1-reservation-receipt未通过：No confirmed reservation receipt exists: the only successful confirmation is for Harbor Family Table (R-0002, R-0003) at a different restaurant/time/total.；子部分FR4-refreshed-offer-booked未通过：No reservation was booked: both reserve_table entries for Harbor were rejected, and the Garden Ramp 13:30 plan was never approved or reserved.
- DSB-15（submitted）：结论标签不正确；表单/选择未全部按expect办结
- DSB-16（submitted）：结论标签不正确
- DSB-18（submitted）：表单/选择未全部按expect办结；子部分XGC-R2-accessible-channel未通过：There is no trace evidence that the notice was ever delivered to linda-contact via plain-text message/callback; every notice_delivery_form attempt failed, and the final answer itself admits no delivery completion receipt was obtained.
- DSB-21（submitted）：结论标签不正确；表单/选择未全部按expect办结
- DSB-23（submitted）：结论标签不正确；子部分XPT-R2-stay-receipt未通过：The summary lacks a reservation number (e.g., stay-XPT1), does not state the dates as 04-16 to 04-18 with an explicit check-out, omits the 00:30 late check-in and Lea's linked supervision, and the agent itself reports stay_confirmed unconfirmed.；子部分XPT-R4-supervision-rebound未通过：The itinerary-level supervision was only stated by Camille in the dialogue as a plan condition, while the final summary explicitly reports Lea's written confirmation was never received, so no written acknowledgment by Lea on the delayed itinerary exists.
- DSB-31（submitted）：表单/选择未全部按expect办结；子部分GOV-R4-receipt-carried未通过：The summary omits the receipt number RELIEF-11822-R1, the portal version v3, and the contact phone 555-0182.

每题的final_answer.json、rpc_trace.jsonl与result.json提供答案、交互和逐项目标判定；agent_calls.jsonl与simulator_calls.jsonl记录实际API调用与服务端usage。
日志不含认证头，但包含任务轨迹与环境私有信息，不应再作为被测Agent的输入。
