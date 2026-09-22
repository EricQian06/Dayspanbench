# 自动测评完整流程

`scripts/evaluate.py`把真实被测模型、人物模拟器、环境状态引擎和规则评分接在一起。它不调用作者参考策略，不替Agent生成答案。`serve.py`仍用于外部Agent通过stdin/stdout接入；自动测评直接调度同一组`AgentTools`，无需再手动启动服务。

## 配置与运行

在项目根目录`.env`中配置`DSB_SIMULATOR_API_KEY`。可复制`.env.example`作为模板，Python按数据读取该文件，不执行shell代码。已有非空环境变量优先。若两模型使用相同base URL，被测模型可以复用该密钥；否则需要单独设置`DSB_AGENT_API_KEY`。

当前默认人物模型为`deepseek-v4-flash`，默认服务为用户配置的`https://az.gptplus5.com/v1`。被测模型必须通过参数显式指定。先运行基础聊天、人物路由、缺材料和回复规划的接口检查：

```bash
python3 scripts/evaluate.py \
  --agent-model deepseek-v4-flash-0731 \
  --simulator-model deepseek-v4-flash \
  --check-only \
  --run-dir artifacts/evaluation_runs/provider-check-001
```

检查通过后，运行全部12题：

```bash
python3 scripts/evaluate.py \
  --agent-model deepseek-v4-flash-0731 \
  --simulator-model deepseek-v4-flash \
  --workers 3 --max-steps 80 \
  --run-dir artifacts/evaluation_runs/deepseek-evaluation-001
```

日志目录必须是新目录或空目录。`--tasks DSB-01 DSB-12`可限定题目；`--simulator rule`可单独测规则人物环境，但与LLM人物环境是不同实验设置，不应混合汇报。重新运行使用新目录；当前不支持从中断事项恢复。

被测模型通过非流式Chat Completions返回`{"tool":"...","arguments":{...}}`。工具定义写入系统消息，不依赖服务商的原生function calling或JSON Schema支持。默认给Agent发送`max_tokens=4096`；可显式用`--agent-token-parameter max_completion_tokens`切换参数名，或`omit`不发送上限。`--agent-max-tokens`设置额度。人物模拟器默认输出预算为8192个token（`--simulator-max-tokens`），包含服务计入其中的推理token；仍默认使用严格`json_schema`；服务不支持时可显式选择`--simulator-format json_object`，不会自动换模式或换模型。

`--timeout`默认60秒，`--retries`默认1，仅对429/5xx和传输故障有限重试。并行度是独立题目数，各题的模型会话、环境与人物历史完全分开。`--max-steps`默认80，每次模型决策消耗一步，格式错误和工具参数错误也计入步数。消息预算另外由各题环境限制。

自动测评默认`--simulator-validation-retries 2`：人物LLM若生成不合格的字段抽取或回复计划，最多再请求两次，并告知同一角色校验要求。不会补充私有答案，不会降低证据标准，不会退回规则人物；重试仍失败则episode无效。每次实际请求及`validation_error`均保存，成本也纳入统计。这和HTTP故障重试是两种独立预算。已有显式字段的等值回显会忽略；值冲突仍拒绝。独立`serve.py`的人物校验重试仍默认0。

## 每题如何推进

1. 可信主进程加载私有题目、工具定义，创建人物实例和虚拟日历。
2. 被测模型只收到系统工具协议、公开`observe`结果与步数预算；不收到私有目标、参考动作、人物内部状态或评分。
3. 每轮调用被测模型，解析一个工具动作，校验公开参数Schema，调用白名单工具。
4. 发送消息和等待事件时可能调用人物LLM；事实内容、材料校验、内部转交和日历推进由状态引擎决定。真实API耗时不推进模拟日历。
5. 工具返回结果加入被测模型的完整交互历史。当前没有历史截断或自动摘要；人物模拟器的历史窗口独立配置，默认24条。
6. Agent自行调用`submit_answer`，主进程执行规则评分后停止该题。评分结果不会回传给模型试错。
7. 每题完成即更新总表与报告。所有题都结束后，报告也直接打印到终端。

Agent接口没有shell、文件读取、网络搜索等任意执行能力；模型只通过公开工具访问环境。隔离边界是发送给远程模型的请求内容；可信主进程本身仍可访问全部题目文件。

## 结果与故障口径

- 11道`resolved`题报告`resolved_success`成功率。
- DSB-12单独报告`bounded_handling_success`，不是放行成功率。
- `required_fact_coverage`反映实际取得证据，区别于最终答对。DSB-12只对四个可核实目标计算覆盖率。
- 步数耗尽、动作格式错误或错误作答属于模型行为；步数耗尽按有效失败计，`submitted=false`，主进程仅用空答案计算终局诊断，不替模型作答。
- 人物模拟器错误、Agent API传输/响应封装错误、主进程错误使episode无效，单列并排除成功率分母。不能把故障当成模型答错，也不能把仅存活样本的比例当成全12题无条件成功率。
- 默认每题一次，报告一次真实运行结果，不提供跨随机重复的稳定性估计。接口检查结果与本地测试不能计作模型测评成绩。

## 日志文件在何时使用

| 文件 | 写入时机 | 用途与读取者 |
|---|---|---|
| `.env` | 用户配置阶段 | 仅可信主进程读取认证配置，不进入模型消息或日志 |
| `.env.example` | 开发阶段 | 无密钥的配置模板 |
| `scripts/evaluate.py` | 启动实验 | 读取配置、选择题目、分配并行任务、汇总报告 |
| `dayspanbench/evaluation.py` | 每轮交互和终局 | Agent客户端、动作校验、完整循环、日志和汇总实现 |
| `manifest.json`（总目录） | 正式实验开始 | 固定模型、预算、并行度、代码与工具Schema哈希 |
| `DSB-xx/manifest.json` | 单题开始 | 单题配置、任务内容哈希和Agent系统提示哈希 |
| `DSB-xx/agent_calls.jsonl` | 每轮/故障退出 | 实际Agent请求与响应、返回模型标识、usage和HTTP尝试数 |
| `DSB-xx/rpc_trace.jsonl` | 每个工具动作后 | 主进程执行的动作、返回结果和参数错误 |
| `DSB-xx/simulator_calls.jsonl` | 每轮/故障退出 | 人物LLM调用、上下文、输出与usage，仅环境审计可读 |
| `DSB-xx/private_audit.jsonl` | 每轮/故障退出 | 内部流程、证据和转交记录，仅环境审计可读 |
| `DSB-xx/final_answer.json` | Agent最终提交后 | 真实模型答案，未提交时不存在 |
| `DSB-xx/result.json` | 单题结束 | 有效性、终止原因、逐项目标评分与成本指标 |
| `summary.json`、`report.md` | 每题结束和整批结束 | 机器可读总表与人类可读报告，进行中时题数可能未齐 |
| `preflight.json` | `--check-only`结束 | 接口检测状态，不是测评分数 |

日志不含认证头，但包含场景答案和私有状态，因此整个`artifacts/evaluation_runs/`默认忽略版本控制；不要把这些日志返回给被测Agent。

## 本地实测与评分勘误

2026-09-21的本地实测使用被测模型`deepseek-v4-flash-0731`、人物模型`deepseek-v4-flash`，12题均已尝试。原始成绩及故障见[原始报告](../artifacts/evaluation_runs/deepseek-dual-20260921-002/report.md)，事后规则修正见[复评分报告](../artifacts/evaluation_runs/deepseek-dual-20260921-002/regraded/report.md)。6题有效、6题因模拟器故障无效；原始有效题成功率1/6，补充明确同义表达后为2/6。不能将该比例当成完整12题的无条件能力成绩。

勘误[DSB11-alias-20260921](scoring-errata/DSB11-alias-20260921.json)补充“暂无承诺日期”与“尚无承诺日期”等价，作者来源及任务定义已同步。评分仍为规则执行；该规则是在观察本次输出后添加的，必须与原始成绩并列披露。日期承诺、凭证权限、证据有效期、业务路径条件均未改变。

`scripts/regrade.py`不发起API调用。它使用该轮保存的原始题目、Agent工具动作和人物输出，先逐条核对工具结果并复现原始评分，再应用声明的勘误，不调用作者参考策略，也不替换模型答案。复现时指定一个新的输出目录：

```bash
python3 scripts/regrade.py artifacts/evaluation_runs/deepseek-dual-20260921-002 \
  --output-dir artifacts/evaluation_runs/deepseek-dual-20260921-002/regraded-check
```

`task_snapshot/`保存勘误前的12题定义；`regraded/`保存修正结果、勘误说明与复评分记录。原始`result.json`、`summary.json`和报告保持不变。
