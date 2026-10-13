# DaySpanBench 复杂化设计备忘（complexify.md）

整理自 2026-10-13 的三轮迭代（引擎缺陷修复 → 陷阱引入 → 陷阱强化与口吻整改）。
适用范围：DSB-01…12（中文手写题，`scripts/author_tasks.py`）；DSB-13…42 为 LATCH 移植题，暂未按本标准做甄别性陷阱设计。

## 一、设计目标与边界

- **考查能力**：逻辑推理与耐心（跨日等待、轮询、内部转交、证据甄别、试错分辨），**不是时效拼手速**。
- **归因要求**：失败必须能干净归因到 agent；交互器端（引擎/模拟器/评分）不得存在机制性不公。
- **陷阱是有意设计**：现实中存在错误信息与误导引导，agent 必须试错、分辨。陷阱不软化为提示。

## 二、复杂化机制（v0.4.x 已落地）

### 1. 引擎机制（机制一致是底线）
- 隐藏表单/状态/记录工具（discover_tools 解锁）：分阶段办结；**所有官方确认渠道（重访页面、status 查询）在办结后均附书面凭证 evidence**——修前 `_hidden_status` 只给结论文本不给证据，是把 agent 引向死胡同的机制不一致（已于 1013-002 修复）。
- suggest 猜测性回复：canonical_text 必须完整送达（simulator render 曾丢弃带 contacts 的 suggest 正文，已修）；猜测可对可错，需逐一验证。
- consult 显式内部转交、deny 明示回绝、page_update 页面中途改写、catalog_update 库存变更。
- decoy 可选工具（leave_note/request_callback 等）：名字诱人但无法推进。
- 归一化：text 型 fact 的书面原文（长/短形、含/不含句尾标点）自动进入 aliases——逐字引用凭证原文不得判错。

### 2. 甄别类陷阱（核心考点）
- **越权证据**：`unauthorized_attestation=True` + `TRAP_PREDICATES`——页面挂出"看似匹配 subject/predicate"的参考文件，但 issuer 无签发权限，评分拒绝。trap fact 不得进入任何 actor 的 knowledge（validate 强制）。
- **陷阱值与真值不同且诱人**：更低价格 / 更高规格 / 更多学分 / 流程捷径（免复核、免实测）。同值陷阱甄别收益只剩证据权限，不采用。
- **时间差诱惑**：陷阱信息先到（开局即挂 / suggest 早期送达），正式真值渠道慢数天~数月。压力来自"正式渠道慢"，不来自"截止早"。
- **标签中性化**：陷阱文件标题去自曝字样（无"参考/摘编/抽样/转载"），仅留"（留存方整理）"轻线索；fetch_document 对正式/越权文件返回同格式中性 note，不替 agent 甄别。结构性线索只剩 issuer 权限。
- **口头误述口吻**：适度不确定的自然人类口吻（"我印象里大概是……不一定准"、"随口一说"）；**禁止**"错不了/肯定"式自信钓鱼。误述保留 hedge，但不自曝是错的。

### 3. 契约与信息公平（environment-contract.md）
- 口头与不确定性信息的证据地位：hedge 信息可能不正确，不足以作最终结论；签发人无权限的参考口径同理。
- **对人物回复的批判性判断**：对所有回复保持批判，"措辞本身不携带对错信号"——hedge 未必错、笃定未必对（两个方向都不暗示，防泄题）；判断责任在 agent，关键结论须结构化书面证据或交叉核实支撑。
- 官方渠道正反馈：仅在确实签发合法证据处给出"正式书面凭证已送达、编号可引用"类确认。

## 三、调参原则

| 维度 | 做法 |
|---|---|
| deadline | 宽松，削平"差 11 分钟全输"悬崖；不因时间差诱惑回收 |
| 真值渠道 delay | 可拉长数天制造时间差，但参考策略 replay 必须仍 PASS 且留余量 |
| 陷阱 vs 真值 | 真值永不变；陷阱值诱人且错误；两文件并存时仅凭 issuer 区分 |
| 队列陷阱 | 单工人 FIFO 自阻塞（如 DSB-06）保留为考点：并行多触达需谨慎 |
| 参考策略 | 走正式渠道，不受陷阱影响；任何改动后 12/12（现 42/42）PASS 是硬门槛 |

## 四、验证清单（每次改动后）

```bash
python scripts/author_tasks.py && python scripts/validate.py && python scripts/replay.py && python scripts/render_cards.py
# Windows 下单测需 sys.path 注入：
python -c "import sys,io,unittest; sys.path.insert(0,'.'); buf=io.StringIO(); unittest.TextTestRunner(stream=buf).run(unittest.TestLoader().discover('tests')); print(buf.getvalue()[-300:])"
```

- replay 全 PASS（golden times 变动需同步 tests/test_environment.py 断言）。
- 探针验证：每个 trap 证据 `looks_admissible=True` 且被评分拒绝；真证据仍通过。
- 陷阱文件正文/误述无自曝措辞（"仅供参考/错不了"清零检查）。

## 五、历史教训（1013-002/003 实测归因）

1. `_hidden_status` 不附 evidence → 4 题值对却失败（系统问题，已修）。
2. simulator render 丢弃 suggest 正文 → 全部口头误述陷阱未送达（已修）。修前陷阱"不起效"多为机制 bug，先查引擎再怪模型。
3. 归一化精确匹配缺书面原文 → 逐字引用凭证也挂（已修：aliases 自动收录）。
4. 陷阱可达性三要素缺一不可：**必经路径 + 时间差 + 值诱人**；挂在可选附件、贴免责标签、同值，三者任一即形同虚设。
5. fetch note 替 agent 甄别（"非正式参考口径"提示）= 辅导，甄别必须靠 agent 自己读 issuer。
