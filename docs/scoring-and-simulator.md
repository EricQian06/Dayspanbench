# v0.5：LLM终审主评分与LLM人物模拟器

v0.5把评分范式从"结构化claims+证据编号引用的确定性核对"改为"**LLM评审官为主、确定性锚点为辅**"（`SCORING_VERSION 0.5.0`）：每题作者编写子部分标准`judge_criteria`，Agent提交`{conclusion, summary}`自然语言总结，LLM评审官逐条评阅；引擎另做一层确定性锚点核对（结论标签、表单办结、回执要素是否在总结中字面出现、截止受阻题的待处理状态）。人物可以选择规则模式或实际调用LLM的模式；LLM不控制事实、时间和进程，NPC措辞由LLM生成。

**LLM终审（judge）是主评分指标。** episode结束、模拟器交互全部完成后，独立LLM评审官（`dayspanbench/judge.py`）依据私有`judge_criteria`评阅：
- **输入**：各条标准（statement/pass_if/source）、Agent最终总结、Agent发出的信件，以及Agent可见的回执工件（receipts）、director已达成事实、审计轨迹摘要（工具调用、dialogue问答、表单办结结果）。看不到私有目标、隐藏事实或评分配置。
- **输出**：逐条`{criterion_id, passed, evidence, reason}`；主分数`score = subparts_passed / subparts_total`。输出经结构校验与重试，仍失败则该题标`judge_pending`，失败标准计`pending_criteria`，不计入通过率分母，也不影响episode有效性。
- **非确定性披露**：主分数由LLM给出，是非确定性指标。正式实验建议对同一episode多次评审取均值或多数，并报告pending比例；单次评审结果不应直接当作最终成绩。
- 无`judge_criteria`的题退化为`deterministic_only`口径（仅确定性锚点）。
- 运行方式见`scripts/evaluate.py --judge simulator`（默认，复用模拟器的StructuredClient；`--judge off`可关闭）。

## 评分规则

LLM评审官负责自然语言总结与信件的逐子部分评阅；确定性层只做进程锚点核对，二者合成最终分数：`complete := 全部子部分通过 AND deterministic_anchors_ok`。

确定性锚点（`dayspanbench/scoring.py`）核对：
- 答案对象结构（`{"conclusion": str, "summary": str}`）与结论标签合法性。
- 表单/选定是否按作者预期办结（审计轨迹）。
- 关键回执要素（受理号、票号、数量、金额、日期）是否在summary中字面或轻度归一化后出现。
- 截止受阻题（如DSB-12）的待处理事项状态。

类型归一化（数值/单位/日期/集合/预设别名）保留用于引擎内部的材料受理与事实登记核对，不再出现在Agent答案结构中。

材料受理仍按事实属性与值匹配：事项保存`admitted_at`和`admission_evidence`（director事实记录），后续检查凭证在受理时有效。引擎受理层拒绝凭空声称——引用回执中的编号、回执原文实质片段或正确转述凭证结论均可核对，但必须有引擎登记的、对Agent可见、未过期、属性匹配的事实作锚点。

## DSB-12的两条真实路径

两条路径都需先取得初审登记号、有效新版单证和批次溯源材料：

1. 向单证联络人请求长期复核，由其内部转交境外代理。
2. 向单证联络人请求“转介境外代理直联”，通过同一材料核验后取得代理联系人，再直接发起长期复核。

境外代理的技术复核工作流也检查凭证，直接联系不能绕过补件。评分检查已受理、具有`technical_review`能力且仍在处理的事项，其货件标识正确，受理凭证完备，并且已经到截止。它不绑定人物ID、工作流ID或中间转交层数。

作者默认参考路径仍是第一条，参考历时仍为300天。替代路径、多级转交和人物更名在测试中另行验证。

## LLM负责什么

`dayspanbench/simulator.py`中的`LLMSimulator`有三个真实API调用入口：

- `route`：读取当前角色、当前消息和该角色自己的历史，选择已声明工作流，逐字提取消息里的字段。显式结构化字段优先；抽取值必须有可核对的原文，仍要经过引擎的材料校验。路由不变，保持确定性校验。
- `render`（v0.5升级）：正式回复（`status: reply`）的正文由LLM在该人物的人设口吻下撰写，输入为引擎确定的canonical内容（事实、回执、联系人）、该人物与Agent的既往交互历史与director阶段提示；其他状态（needs_information/acknowledgement/referral/failed）仍用引擎的确定性canonical文本，受理语义不依赖模型。模型输出须**原样保留关键token**（数字、编号、带引号专名、联系人邮箱）：引擎做key-token校验，丢失即带反馈重试，仍失败则`SimulatorError`、episode记无效。模型不能增加、删除或改写事实内容，也不能改变消息送达时刻。
- `dialogue`（v0.5新增）：标注`dialogue_mode: llm`的委托人问答工具由LLM人格作答——输入persona、该委托人既往问答历史与阶段提示，引擎注入关键词匹配到的canonical答复作为事实约束；规则层校验答复不得与authored事实矛盾。

这不是任意自由生成的人物对话：事实、材料校验、内部转交、日历推进和消息时刻全部由状态引擎决定，LLM只负责措辞与上下文衔接。这样可以实际测量LLM意图理解、跨轮补件和信息组织，同时保持事实可复现。

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

人物模拟器拒绝、超时或输出越权（含render丢失关键token）时，返回终止错误，`valid_episode=false`，进程以状态2退出；不生成一个看似有效的Agent失败分数，也不让Agent在已损坏状态上继续。正式统计应报告无效episode比例，并预先固定重试规则。v0.5评分输出`scored_by`/`subparts_*`/`pending_criteria`/`deterministic_anchors_ok`（旧字段`resolved_success`/`bounded_handling_success`等为兼容别名），每项失败附可审查的`reasons`；judge评审失败的标准计pending、不判失败。

日志目录必须新建或为空，避免覆盖已有实验。日志包含私有提示词与内部信息，不能交给被测Agent。文件用于审计，不是可恢复的checkpoint。未提交就断开会记录`no_final_submission`；外层驱动器应进一步区分超预算、异常退出等原因。

## 验证和接口依据

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/replay.py
python3 scripts/render_cards.py
```

接口构造依据[OpenAI官方结构化输出文档](https://developers.openai.com/api/docs/guides/structured-outputs)。本地测试覆盖HTTP请求构造、Chat/Responses响应解析、重试、认证错误、拒绝、截断、字段伪造、人物隔离、回复越权及完整环境链路；使用替身HTTP响应，不代表已经验证某个真实服务商或模型的兼容性与角色质量。
