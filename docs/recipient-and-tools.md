# 人物接收者与工具接入

v0.3提供规则接收者与实际调用LLM的受约束人物模拟器。配置与完整CLI示例见[评分与LLM模拟器指南](scoring-and-simulator.md)。

## 配置与独立状态

每个人物包`tasks/actors/DSB-xx/<actor>.json`包含角色、工作流、接收者指令、白名单工具、局部事实、签发权限与完整日历。当前环境从私有任务JSON的内嵌配置加载人物，人物包用于一致性检查和人工审查。

每次运行给各人物分别创建独立`ActorState`、日历、队列、收件箱、发件箱、事项集合和对话历史。所有人物共享引擎实现；每个请求独立运行状态机。选择LLM模式时，角色有各自的`LLMSimulator`实例，可共享无会话状态的HTTP客户端。

## 三种接收者接口

| 类 | 功能 | 使用方式 |
|---|---|---|
| `RuleRecipient` | 按角色自身别名选择工作流 | 服务器默认；适合确定性回归 |
| `LLMRecipient` | 保留旧的`callback(view) -> {workflow_id}`路由接口 | 主进程自行注入；不负责字段抽取与回复规划 |
| `LLMSimulator` | 实际结构化LLM调用，支持路由、字段抽取、跨轮补件和受约束回复规划 | `serve.py --simulator llm`或主进程显式注入 |

接收者清单中的adapter字符串是说明元数据，不会自动动态导入执行；实际类型由主进程或CLI选择。

## Python接入示例

下面会在人物交互发生时真实调用所配置模型。先设置`DSB_SIMULATOR_MODEL`和`DSB_SIMULATOR_API_KEY`，不要将密钥写入任务JSON。

```python
import json
import os
from pathlib import Path
from dayspanbench.engine import Environment
from dayspanbench.llm import LLMConfig, StructuredClient
from dayspanbench.simulator import LLMSimulator

task = json.loads(Path("tasks/private/DSB-12.json").read_text())
client = StructuredClient(LLMConfig(
    model=os.environ["DSB_SIMULATOR_MODEL"],
    api_key=os.environ["DSB_SIMULATOR_API_KEY"],
    base_url=os.getenv("DSB_SIMULATOR_BASE_URL", "https://api.openai.com/v1"),
))
people = {a["id"]: LLMSimulator(client, a["id"]) for a in task["actors"]}
env = Environment(task, recipient=people)
tools = env.tools()  # 仅可信主进程持有对象；被测Agent只经RPC使用公开方法。
tools.send_email("luosen@bench.example", "查询货件PK-608的入库记录", {"tracking": "PK-608"})
```

每个人物的路由输入只有自己的角色与指令、当前请求、显式字段、自身历史和事项状态，以及自身工作流标签、别名和必需字段。没有全局事实、评分目标、其他人物历史或未来事件队列。抽取字段必须有Agent消息原文支持，且不能覆盖显式字段或代替实际取得凭证。

回复调用只取得已完成步骤产生的回执与当前可返回内容。v0.5起，正式回复（`reply`状态）的正文由LLM在该人物人设口吻下依据canonical内容（事实、回执、联系人）与既往交互撰写，其他状态仍由程序渲染确定性文本；canonical中的数字、编号、专名与联系人邮箱必须原样保留（key-token校验），不允许添加或遗漏事实。这个模式尚不支持自由事实改写、谈判或情绪模拟。

内部转交已经指定目标工作流，直接由状态引擎受理。缺材料会失败或要求补件；LLM不能让材料门槛失效。

## 工具与评分边界

`Environment.execute_tool`只执行当前人物声明的查询、回执签发、转介、内部转交和回复。回执登记到director的已达成事实并附带对象、事实类型和签发权限，保留真实来源。材料受理使用这些属性，不能仅靠猜中编号获得分数。

人物LLM只选择和组织，不直接执行工具、不修改日历或状态。模型输出越权、API拒绝或网络失败属于`SimulatorError`，episode终止并标记无效，不静默更换规则角色。CLI可保存调用输入、输出、用量和耗时；这些日志留在可信主进程。

新人物应在作者脚本定义角色、权限、工作流、日历和必要能力。新增工具种类还需修改执行器、验证器及测试；新增评分目标应给出回执要素、归一化类型与必要业务约束。被测Agent始终仅使用公开工具（通用工具及本题启用的可选/隐藏工具）。
