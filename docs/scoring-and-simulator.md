# v0.3：按目标评分与LLM人物模拟器

本版本将评分从固定值/事实ID与指定人物链条，改为类型归一化、证据属性和必要业务能力。评分仍由程序执行。人物可以选择规则模式或实际调用LLM的模式；LLM不控制事实、时间和成绩。

**例外：LLM终审（judge，v0.4新增）。** 自LATCH_BENCH移植的任务（DSB-13起）除确定性评分外，还带作者撰写的语言性标准（`judge_criteria`，私有）。episode结束、模拟器交互全部完成后，由独立LLM评审官复核Agent的最终回复与Agent自己发出的信件，逐条给出通过与否、证据引用与理由（`dayspanbench/judge.py`）。评审结果只作为**独立指标**记录（`llm_judge`/`judge_passed`/`judge_total`），不改变`resolved_success`/`bounded_handling_success`，也不影响episode有效性；评审输出经结构校验与重试，仍失败则记pending。评审官只能看到Agent可见的证据与Agent发出的信件，看不到私有目标或评分配置。运行方式见`scripts/evaluate.py --judge simulator`（复用模拟器的StructuredClient；`--judge off`可关闭）。

## 评分规则

每项已确认结论必须引用本次实际送达、仍有效、对象和事实类型正确、由具备相应签发权限的角色产生的证据。权限与属性由可信环境配置和工具执行器赋予，Agent与人物LLM均不能提交或修改这些元数据。

| 变化 | 通过的例子 | 仍不通过 |
|---|---|---|
| 预设语义别名 | “尚无承诺日期”与“尚未承诺正式稳定版发布日期” | “下周一定发布” |
| 数量和单位归一化 | `92`厘米与`{"value":0.92,"unit":"m"}`；`"2,360 CNY"`与2360元 | 厘米与千克；把布尔true当数字1；错误数值 |
| 日期和时区 | `2026年12月9日`与`2026-12-09`；同一时刻的UTC与北京时间 | 不带时区的时间戳；错误日期 |
| 集合字段 | 同一材料清单换序 | 缺项、加项、重复项 |
| 证据匹配 | 相同对象/事实类型、授权来源、实际取得的另一份证据 | 猜中证据ID、未送达、过期、无签发权限、属于其他对象 |
| 动态文书标识 | DSB-12实际签发并取得的另一有效新版单证号 | 没有对应有效证据的任意编号 |
| 流程能力 | 直联合格代理或经过多级转交，真实进入技术复核 | 只有初审登记、缺材料、未真正受理或未等到截止 |

同义处理采用作者声明的有限别名，不是任意自由文本的语义理解。数量转换仅接受该字段声明的单位；文本做Unicode NFKC、空白和大小写归一化。公开观察中的`value_normalization`说明字段类型和单位，不包含会泄露答案的私有别名。

`unconfirmed`条目不附带`value`和`evidence_ids`，不能用未确认标签包裹“已放行”等实质断言。

`goals[].evidence_requirement`描述`subject`、`predicate`和授权签发能力；`facts[].attributes`描述事实对象和类型，证据签发时复制这些属性与发行人的权限。`accepted_facts`保留为作者参考策略的可行性见证，不再限制运行时评分只能接受那些事实ID。

一般目标使用`match: expected`，需要正确目标值与有效证据同时成立。DSB-12的登记号、新版单证和溯源编号使用`match: evidence`，答案必须与实际取得的合格证据一致，允许合规的编号变化。没有增加任意来源的宽松接受。

材料受理也使用证据属性与值匹配，避免评分接受替代凭证、入口却拒绝它。事项保存`admitted_at`和`admission_evidence`，后续检查凭证在受理时有效；最终答案引用的证据则需在提交时有效。

## DSB-12的两条真实路径

两条路径都需先取得初审登记号、有效新版单证和批次溯源材料：

1. 向单证联络人请求长期复核，由其内部转交境外代理。
2. 向单证联络人请求“转介境外代理直联”，通过同一材料核验后取得代理联系人，再直接发起长期复核。

境外代理的技术复核工作流也检查凭证，直接联系不能绕过补件。评分检查已受理、具有`technical_review`能力且仍在处理的事项，其货件标识正确，受理凭证完备，并且已经到截止。它不绑定人物ID、工作流ID或中间转交层数。

作者默认参考路径仍是第一条，参考历时仍为300天。替代路径、多级转交和人物更名在测试中另行验证。

## LLM负责什么

`dayspanbench/simulator.py`中的`LLMSimulator`有两个真实API调用入口：

- `route`：读取当前角色、当前消息和该角色自己的历史，选择已声明工作流，逐字提取消息里的字段。显式结构化字段优先；抽取值必须有可核对的原文，仍要经过引擎的材料校验。
- `render`：读取当前已取得证据，选择语气和证据呈现顺序；引擎据此渲染回复。模型不能增加、删除或改写事实段落，也不能改变消息送达时刻。

默认回复模式是**受约束的回复规划**：它不是任意自由生成的人物对话。语气来自预设选项，事实与澄清内容来自可信环境。这样可以实际测量LLM意图理解、跨轮补件和信息组织，同时保持事实评分可复现。若后续增加自由改写、谈判或情绪，需要另设模式并校准模拟器，不能把本模式描述成已经覆盖这些能力。

每个人物有独立实例与历史，底层可共用一个无会话状态的HTTP客户端。默认保留最近24条本人物消息，并在每次路由中提供自身事项的ID和状态；未实现LLM记忆摘要或进程重启恢复。内部转交使用已指定的工作流，不调用LLM猜测转交目的。

API调用只在交互或回复事件发生时执行。HTTP耗时只记入调用日志，不推进模拟日历；跨300天不会按天调用模型。

## 运行

Python 3.11+，标准库实现，无供应商SDK依赖。先通过安全方式将API密钥置于`DSB_SIMULATOR_API_KEY`环境变量，再设置模型名称。示例中的模型名称需替换为实际服务支持的模型，不在代码中默认选择供应商模型。

```bash
export DSB_SIMULATOR_MODEL='替换为你的模型名称'
python3 scripts/serve.py --task DSB-12 --simulator llm \
  --run-dir artifacts/evaluation_runs/llm-demo-001
```

地址以`--simulator-base-url`优先，其次为`DSB_SIMULATOR_BASE_URL`环境变量；当前工作区的`serve.py`默认地址为`https://az.gptplus5.com/v1`。Chat模式在地址后追加`/chat/completions`。如果要调用OpenAI官方服务，显式指定`--simulator-base-url https://api.openai.com/v1`；如果密钥已经在`OPENAI_API_KEY`，增加`--api-key-env OPENAI_API_KEY`。代码不会自动把其他密钥发给自定义服务。

OpenAI兼容服务：

```bash
python3 scripts/serve.py --task DSB-12 --simulator llm \
  --simulator-base-url https://your-provider.example/v1 \
  --simulator-model your-model \
  --run-dir artifacts/evaluation_runs/provider-demo-001
```

OpenAI Responses API：

```bash
python3 scripts/serve.py --task DSB-12 --simulator llm \
  --simulator-base-url https://api.openai.com/v1 \
  --simulator-api responses --api-key-env OPENAI_API_KEY \
  --run-dir artifacts/evaluation_runs/responses-demo-001
```

默认要求服务支持`json_schema`结构化输出。不支持时可显式添加`--simulator-format json_object`：完整输出Schema会写入system消息，本地仍会验证路由和回复计划。JSON模式只要求合法JSON，不能替代Schema校验，见[OpenAI官方说明](https://developers.openai.com/api/docs/guides/structured-outputs#json-mode)。兼容性取决于服务是否支持相应端点、`response_format`、`max_completion_tokens`等参数。不会在接口不支持时静默切换模式。

Chat模式使用标准库发送HTTP请求，与`OpenAI(base_url=...).chat.completions.create(...)`使用相同端点和Bearer认证，显式设置`stream=False`，读取`choices[0].message.content`。但普通`Hello!`调用只验证基础聊天；它不验证本环境额外使用的结构化输出和token上限参数，也不验证模型是否能遵守人物路由/回复约束。`print(completion.choices[0].message)`会打印消息对象，单独查看正文应使用`.message.content`。Python参数名应为`api_key`、`base_url`，不应带Markdown转义反斜杠。

可配置`--simulator-timeout 30`、`--simulator-retries 2`、`--simulator-max-tokens 2048`、`--history-limit 24`。HTTP 429、5xx和网络超时有限重试，认证错误、拒绝、截断、非法输出不静默退回规则角色。

服务启动后保持同一进程，向stdin逐行发送请求；每个请求必须是单行完整JSON，stdout每行返回JSON。空行会被忽略；不要粘贴Markdown代码围栏或跨行格式化JSON。它是等待外部请求的环境服务，不会启动后自动完成任务。下面第一条不调用LLM，第二条会触发人物路由：

启动时会在stderr显示就绪与等待输入提示，LLM模式处理消息/等待工具时也会提示当前阶段；`--quiet`可关闭这些提示，不影响stdout的JSONL协议。若终端只有shell的续行提示，说明命令还没提交：请检查反斜杠续行和复制格式。URL应是普通`https://…/v1`字符串，不能带Markdown的`[文字](链接)`包装。

```json
{"id":1,"tool":"observe","arguments":{}}
{"id":2,"tool":"send_email","arguments":{"recipient":"luosen@bench.example","text":"请核查货件PK-608的历史入库记录和后续联系入口。","fields":{"tracking":"PK-608"}}}
{"id":3,"tool":"wait_until","arguments":{"until":"2027-09-02T15:00:00+08:00"}}
```

规则模式：

```bash
python3 scripts/serve.py --task DSB-12 --simulator rule
```

通用Agent工具不变（v0.4起每题另有可选工具与隐藏工具，以`observe()`为准）；新增的是可信环境端人物模拟器，不是被测模型的自动运行器。

## 日志与无效episode

指定`--run-dir`后保存：

| 文件 | 内容 |
|---|---|
| `manifest.json` | 任务版本与哈希、评分版本、模拟模型、服务地址、参数和时间模式；不记录密钥 |
| `rpc_trace.jsonl` | 该次Agent工具请求与公开响应 |
| `private_audit.jsonl` | 状态迁移、工具、内部转交和模拟器错误 |
| `simulator_calls.jsonl` | 人物LLM输入、结构化输出、调用次数、用量、耗时和错误；私有 |
| `final_answer.json` | 有最终提交时保存Agent实际答案 |
| `result.json` | 本次评分，或没有最终提交/模拟器故障的终止原因 |

人物模拟器拒绝、超时或输出越权时，返回终止错误，`valid_episode=false`，进程以状态2退出；不生成一个看似有效的Agent失败分数，也不让Agent在已损坏状态上继续。正式统计应报告无效episode比例，并预先固定重试规则。正常规则评分保留`resolved_success`与`bounded_handling_success`的区分，每项失败新增可审查的`reasons`。

日志目录必须新建或为空，避免覆盖已有实验。日志包含私有提示词与内部信息，不能交给被测Agent。文件用于审计，不是可恢复的checkpoint。未提交就断开会记录`no_final_submission`；外层驱动器应进一步区分超预算、异常退出等原因。

## 验证和接口依据

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/replay.py
python3 scripts/render_cards.py
```

接口构造依据[OpenAI官方结构化输出文档](https://developers.openai.com/api/docs/guides/structured-outputs)。本地测试覆盖HTTP请求构造、Chat/Responses响应解析、重试、认证错误、拒绝、截断、字段伪造、人物隔离、回复越权及完整环境链路；使用替身HTTP响应，不代表已经验证某个真实服务商或模型的兼容性与角色质量。
