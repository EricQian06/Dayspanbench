# DaySpanBench: Benchmarking LLM Agents Across Long Calendar-Time Horizons

DaySpanBench 测量Agent在跨日、跨工作时段的沟通中获取信息、跟进内部流程、核验证据和处理截止时间的能力。

当前v0.3版本是**12个手写合成任务、41个人物的可运行种子环境**，参考历时覆盖**2–300天**。每个人物都有自己的角色配置、接收者模拟器、局部知识、工具权限、工作日历、消息队列和流程状态；每个请求独立运行状态机。任务从2026年11月开始，最长延续至2027年9月；机构、人员、事实及规则均为合成，不代表现实机构的承诺或规定。

直接查看：

- [自动运行真实模型测评：配置、完整循环与结果日志](docs/automatic-evaluation.md)
- [评分改进与LLM人物模拟器运行指南](docs/scoring-and-simulator.md)
- [测评流程中的文件使用指南：逐阶段、逐题、逐人物](/Users/weiwen/Documents/ChatGPT/DaySpanBench/docs/evaluation-file-guide.md)
- [12题总览与已验证历时](docs/task-catalog.md)
- [2–300天的分布与长期流程设计](docs/horizon-design.md)
- [完整任务卡示例：跨周末场地确认](docs/tasks/DSB-01.md)
- [完整任务卡示例：跨89天的学分转换](docs/tasks/DSB-03.md)
- [完整任务卡示例：300天内的分轮补件与未决放行](docs/tasks/DSB-12.md)
- [环境和评分协议](docs/environment-contract.md)
- [接收者与工具接入方式](docs/recipient-and-tools.md)

## 已实现

| 层 | 实现 |
|---|---|
| 人物配置 | 41个独立角色包，包含流程、接收者指令、白名单工具与本地事实 |
| 流程状态 | 缺材料、排队、处理中、内部等待、已回复和失败；补件可继续原事项 |
| 日历时间 | 午休、夜间、周末、关闭日期、角色不同工作日、跨时区、固定每周批次 |
| 内部流程 | 本地查询、文本证据签发、对外转介、内部转交、子事项返回和父事项继续 |
| 接收者 | 独立规则或LLM人物实例；请求理解、跨轮字段提取和受约束回复规划 |
| 联系工具 | 浏览器两级检索（搜索链接+访问页面）、发送邮件、拨打电话、读取收件箱、等待消息与提交答案 |
| 时间推进 | 虚拟时钟和事件队列，无需真实睡眠；不同人物可并行处理 |
| 评分 | 目标值归一化、证据属性与权限、必要业务能力；支持合法替代路径并保留有效期和材料门槛 |
| 验证 | 12条特权参考轨迹、多路径/等价答案与越权负例、HTTP接口替身测试、JSONL工具服务器 |
| 运行日志 | 可选每次episode独立保存配置、RPC、内部审计、LLM调用和评分；模拟器错误标记无效 |

每个人物有具体联络方式（`人名拼音@bench.example`邮箱、互不相同的电话）。email是异步渠道：只在对方工作时间段处理并带种子化随机延迟，不会秒回；电话是同步渠道：仅接听时段有人接听，口头答复不构成书面凭证。两级浏览器先搜索后访问，页面正文与联系人须访问链接才能取得。尚未接入真实平台、语音或浏览器界面。默认接收者用规则理解意图，不应拿默认规则的措辞敏感性直接解释为人类沟通能力。

## 运行

需要Python 3.11或更新版本，无第三方依赖。Windows若缺少IANA时区数据库，需另外安装`tzdata`；当前验证环境为macOS。

```bash
python3 scripts/validate.py
python3 scripts/replay.py
python3 -m unittest discover -s tests -v
```

`replay.py`执行作者参考策略，输出`artifacts/reference_runs/`。**参考策略可见私有目标，属于任务可行性见证，不是被测Agent，也不是LLM成绩。**

编辑手写来源后重新导出：

```bash
python3 scripts/author_tasks.py
python3 scripts/validate.py
python3 scripts/replay.py
python3 scripts/render_cards.py
```

`scripts/author_tasks.py`中的12题内容、人物关系、事实和等待时间均逐题手写；辅助函数只展开重复的数据结构。

## 给Agent的入口

自动测评全部12题（先按[运行说明](docs/automatic-evaluation.md)配置`.env`）：

```bash
python3 scripts/evaluate.py --agent-model deepseek-v4-flash-0731 \
  --simulator-model deepseek-v4-flash --workers 3 --max-steps 80 \
  --run-dir artifacts/evaluation_runs/deepseek-evaluation-001
```

结束后直接打印实测报告，并保存`summary.json`、`report.md`及每题实际调用轨迹。每题由被测模型自行选工具并最终提交，不使用作者参考策略。以下为外部Agent自行接入的JSONL服务：

```bash
python3 scripts/serve.py --task DSB-01
```

该进程启动后等待输入：每行一个完整JSON对象（JSONL），并逐行返回JSON。空行会被忽略；不要将请求分成多行，也不要将Markdown代码围栏粘贴到终端。首个请求示例：

终端会显示“环境已就绪，正在等待stdin”提示；提示写入stderr，stdout仍保持纯JSONL。自动接入可用`--quiet`关闭提示。`--simulator-model`配置的是联系人模拟模型，服务本身不包含被测Agent的自动决策循环。

```json
{"id": 1, "tool": "observe", "arguments": {}}
```

发送邮件示例（收件人为邮箱地址，从联系人卡片取得）：

```json
{"id": 2, "tool": "send_email", "arguments": {"recipient": "chenzhi@bench.example", "text": "请提供活动场地的联系入口"}}
```

等待下一条对Agent可见的回复，或等到截止：

```json
{"id": 3, "tool": "wait_until", "arguments": {"until": "2026-11-10T18:00:00+08:00", "wake_on_message": true}}
```

`submit_answer`只允许调用一次。结构化答案示例见[协议](docs/environment-contract.md)。服务器默认使用规则接收者；显式指定`--simulator llm`后会调用所配置的LLM。详见[接入与命令示例](docs/scoring-and-simulator.md)。

## 文件组织与可见性

```text
dayspanbench/              日历、状态引擎、接收者接口和验证器
tasks/public/              被测Agent的公开任务
tasks/private/             环境完整事实、角色和目标（私有）
tasks/actors/DSB-xx/        每个人物的独立角色包（私有）
docs/tasks/                人类评审任务卡，含答案和内部时间线（私有）
docs/scoring-and-simulator.md 评分和LLM接入说明
scripts/author_tasks.py    手写内容来源（私有）
scripts/serve.py           白名单JSONL工具服务器
artifacts/reference_runs/ 特权参考回放与内部日志（私有）
artifacts/evaluation_runs/ 使用--run-dir指定的独立实验日志（私有，运行时生成）
tests/                    日历、状态、权限、证据和截止时间测试
```

运行正式实验时，应将私有环境置于独立进程/容器，只向Agent暴露工具RPC和公开观察。**不要给被测Agent本仓库的文件系统或Python对象访问权**；Python里的`AgentTools`封装本身不是安全沙箱。

## 当前版本的测量边界

- 11题预期能取得所需信息；第12题故意设为截止前受阻。`resolved_success`与`bounded_handling_success`分开统计。
- 参考历时为2、3、5、8、13、21、34、55、89、144、210、300天，采用近似对数间隔和四档均衡采样。这是模拟日历时间，不是模型运行的真实耗时，也不是最短可行耗时。
- 长期题包含分阶段查询、凭证更新与再次转交。DSB-12须完成初审、第二轮补件和长期复核受理，到300天截止时如实报告未确认；只等待到截止不能通过。
- 固定事实、确定性耗时与FIFO队列用于可复现的最小环境。LLM模式支持理解、逐字字段提取、语气选择和证据呈现顺序；事实正文受程序约束，尚无自由事实改写、随机失联、情绪、谈判或语音。
- 最终结论接受任务标签及其公开中文名称；结构化字段支持有限语义别名、数量/日期归一化与集合换序。任意自由文本仍需答案适配，评分不调用LLM。
- 已提供真实LLM HTTP调用代码；本次验证使用替身响应，未运行真实模型实验，尚无模型排名或真人校准数据。12题适合检查流程和做初步诊断，不足以支持稳健的总体能力排名。

## 设计参考

状态约束的模拟器借鉴[τ²-Bench](https://arxiv.org/abs/2506.07982)；角色互动可参考[SOTOPIA](https://arxiv.org/abs/2310.11667)；信息充分性与最终作答的区分可参考[MT-InfoSeek](https://arxiv.org/abs/2608.14808)。本任务集及时间规则为独立编写，未复制这些基准的任务。
