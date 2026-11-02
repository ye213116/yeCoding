# T6：工程代码上下文对比实验

## 原版 / 改进版 / mini 三线端到端实验

`context_benchmark.py` 固定 SWE-bench Lite 数据修订
`6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`、原版 yeCoding
`7a1783bc723d358090a3c9f318d7bf795903138e`、mini-SWE-agent v2.4.6
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8` 和经典格式验收器 swebench 4.1.0。
完整 Python 3.12 依赖及包哈希见 `context-requirements.lock`；不改变产品依赖或 uv.lock。

先运行不调用模型的镜像与仓库预检，再运行开发集。两版 yeCoding 使用同一受限工具适配、
模型、固定动态字段及环境；原版从 Git 归档加载。mini 使用原生 Agent、模型动作解析及
官方 SWE-bench 提示词/观察模板，仅统一模型参数、预算与执行环境。
三组均在任务容器内以宿主 UID 执行命令，通过 conda run 激活 testbed 环境，并绑定独立工作副本。
参考补丁和测试补丁只由外部验收器读取，不传入 Agent，也不挂载到任务容器。

```bash
# 工具与快照放在 .git，避免被现有仓库自索引当成待分析源码。
uv venv --python 3.12 .git/context-tools/context-venv
git clone --depth 1 --branch v2.4.6 https://github.com/SWE-agent/mini-swe-agent.git \
  .git/context-tools/mini-swe-agent
uv pip install --python .git/context-tools/context-venv/bin/python \
  --require-hashes -r eval/context-requirements.lock

PYTHONPATH=src:. .git/context-tools/context-venv/bin/python -m eval.context_benchmark prepare \
  --out .git/context-experiments/three-line-001
PYTHONPATH=src:. .git/context-tools/context-venv/bin/python -m eval.context_benchmark run \
  --out .git/context-experiments/three-line-001 --split dev
# 开发闭环通过后：一次执行主实验及两组消融，共 300 次。
PYTHONPATH=src:. .git/context-tools/context-venv/bin/python -m eval.context_benchmark run \
  --out .git/context-experiments/three-line-001 --split test --ablations
PYTHONPATH=src:. .git/context-tools/context-venv/bin/python -m eval.context_benchmark report \
  --out .git/context-experiments/three-line-001 --split test
```

准备输出目录必须不存在。冻结实际源码、模型控制配置、价格快照、镜像 digest、数据集和验收器版本；
原版、改进版与评测器代码均保存独立快照，worker 从快照加载，每个任务开始前检查文件指纹。
实现或配置变化拒绝继续。已有尝试不覆盖、不自动续跑；接口或验收基础设施异常时保留尝试和用量并停止。
worker 超时会按任务标签回收容器，保存已收到的 usage，缺失账目明确标记为未知。
空补丁计为未解决，不误记为 Docker 故障。官方验收使用每次唯一 run_id，避免读取旧补丁的缓存结果。
补丁在任务容器内相对固定 base_commit 导出。宿主文件工具和快照先验证工作树；
链接、特殊文件和超过既有 20,000 项扫描限制的工作树拒绝处理，初始化失败单列为环境错误。

开发集 5 题各三线运行一次；正式集 20 题，各线重复 3 次。默认每任务 120,000 累计 token、
64 次请求、900 秒，单次输出 8,192；Memory、Skill 和 MCP 关闭。
`no_structure`、`no_dedup` 分别关闭新策略的结构选择和去重，额度相同。
主实验为 180 次，加消融为 300 次，不包含开发运行；只运行主实验时省略 `--ablations`。
不要在已跑主实验的同一目录追加完整消融排程。

原始轨迹保存逐请求消息/工具/系统上下文、原始工具结果、文件版本、保留或省略的输出行段，
以及模型 usage、缓存、耗时、终止原因和补丁。字符估算与模型返回 token 分开。
报告保留失败运行，另列双方均解决的配对消耗；按任务聚合重复运行并重采样，
不把重复运行数当作独立任务数。价格来自带日期的配置快照，费用为估算，不声称等于实际账单。

2026-10-30：普通隔离容器读写和真实 evidence CLI 已通过；首个任务
`pylint-dev__astroid-1978` 镜像拉取 1,200 秒超时，预检保存为 environment_error。
尚未运行三线开发集、官方补丁验收或正式实验。详细状态继续维护在原有
[模式对照报告](../docs/mode-comparison.md)。下文原检索实验保留其独立指标与历史口径。

新增代码修复实验独立于下述检索实验：`run_repair_eval.py` 使用固定 python-dotenv 源码，
构造 2 个开发、8 个保留评测的人工注入缺陷任务，对比 `single/team/verified` 三种反馈策略。
不加 `--live` 只运行真实 Docker 测试验证任务有效性；加 `--live` 才实际调用模型。
每组独立启动且关闭跨任务记忆，额外测试在模型结束后加入，用于检查错误验收。
这些任务不是历史上游 issue 或 SWE-bench。运行方式与解释见
[修复流程](../docs/repair-workflow.md)，任务定义见 [repair_tasks.json](repair_tasks.json)。

本目录比较三种上下文构造策略。检索指标无需模型；生成结果有用性需要有效的模型密钥，
没有密钥时结果明确记为 `skipped`，不能在论文中当作已完成的量化结果。

## 对比策略

| 策略 | 实现 | 输入给模型的代码 |
| --- | --- | --- |
| `grep` 关键词检索 | `grep_retrieve` | 对每个英文查询词搜索，命中行扩展前后各 3 行，按预算放入摘录 |
| `file` 直接输入文件 | `file_retrieve` | 按查询词在文件名、文件内容的命中排序，依次从文件开头放入原始代码；超预算时在行边界截断 |
| `symbol` 结构感知 | `symbol_retrieve` → `ContextBuilder.build` | 索引中的符号签名、调用链、源码摘录、文件摘要按优先级组装 |

三者使用同一 `tasks.json`、同一预算和同一 token 估算器。`grep` 与 `file` 使用任务中的
`en_terms`；`symbol` 使用原始问题加同一组 `en_terms`。`en_terms` 是预先写定的英文检索词，
不由测试时的模型临时生成。`file` 排序不读取任务的 `primary_symbols`、`dep_symbols` 或
`relevant_files` 真值。`file` 的工具次数记为一次文件选择加每个实际读取的文件一次；
此数值只是估计，不代表真实模型的工具往返。

## 任务与真值

- 10 个自建任务，目标是本仓库的 Python 代码，涉及 context、memory、agent、rag、
  tools、snapshot、skill 和 llm 模块。
- 每个任务有自然语言问题、固定英文检索词、核心符号、必要依赖符号和相关文件。
- 真值由源码阅读标注；`tests/test_eval_harness.py` 校验标注符号存在于 AST 索引。
- 该任务集与系统同源，不能据此推断对其他仓库或 Verilog/VHDL 的效果。

## 指标与统计口径

| 指标 | 计算方式 |
| --- | --- |
| 上下文长度 | `estimate_text_tokens(context)`；这是统一的 CJK/代码近似估算，不是供应商的精确 tokenizer 计数 |
| 核心符号召回率 | 返回的源码行集合与核心符号定义行及其后 3 行相交即记命中，除以核心符号总数 |
| 总符号召回率 | 同上，分母包含核心符号和必要依赖符号 |
| 文件召回率 | 出现的真值文件数 / 真值文件总数 |
| 生成结果有用性 | 三种上下文分别交给同一模型、同一问答提示词生成中文回答，再由同一模型按 1–5 分评分 |

生成与评委调用采用相同的模型和 `temperature=0`。DeepSeek 评测显式关闭思考模式
（见[官方说明](https://api-docs.deepseek.com/guides/thinking_mode/)），两类调用最多输出
1024 token；其他兼容模型的生成上限为 1024、评委上限为 4096 token。
每项汇总为 10 个任务的均值±样本标准差。有用性仅汇总实际评分的任务并显示 `n`；
原始回答和逐任务评分逐步写入 `results.json`，中断后使用同一路径可从已完成结果续跑。
模型兼任生成器和评委会带来
评价偏差，论文应报告这一限制，并抽样人工复核。预算限制只作用于检索到的代码上下文，
统一的问答提示词不计入预算。

## 运行与留存

```bash
uv run python eval/run_eval.py --budget 4000 --skip-llm
uv run python eval/run_eval.py --budget 2000 --skip-llm
# 配好 .env 中的真实模型密钥后，再运行包含有用性评分的实验：
uv run python eval/run_eval.py --budget 4000
```

结果默认写入 `eval/results/results.json`，该目录被 Git 忽略。保存论文证据时应另行归档
`tasks.json`、运行命令、预算、模型和版本、生成时间、逐任务结果、评分输出及仓库提交号。
每个预算使用不同的 `--out` 路径，以免覆盖前一次实验。论文中的数值以归档的原始结果为准。

## 独立任务与依赖扩展消融

`tasks-python-dotenv.json` 包含 12 个从上游源码阅读标注的代码理解任务，覆盖加载、搜索路径、
插值、解析、错误恢复和文件改写。上游固定为 v1.1.1，commit
`16e660d384b942b11879b44500afbbe021650448`；8 个 Python 生产源码文件原样保存在
`fixtures/python-dotenv-v1.1.1.zip`，附许可证和逐文件哈希。fixture 不含测试，
准备过程不安装依赖、不执行上游代码、无需网络：

```bash
uv run python eval/prepare_external.py
uv run python eval/run_eval.py --repo /tmp/yecoding-eval-python-dotenv-v1.1.1/src \
  --tasks eval/tasks-python-dotenv.json --budget 2000 --ablation --skip-llm \
  --out eval/results/dotenv-2000-retrieval.json
uv run python eval/run_eval.py --repo /tmp/yecoding-eval-python-dotenv-v1.1.1/src \
  --tasks eval/tasks-python-dotenv.json --budget 4000 --ablation --skip-llm \
  --out eval/results/dotenv-4000-retrieval.json
# 模型配置从本项目读取，分析对象仍为独立仓库：
uv run python eval/run_eval.py --repo /tmp/yecoding-eval-python-dotenv-v1.1.1/src \
  --tasks eval/tasks-python-dotenv.json --config-root . --budget 4000 --ablation \
  --out eval/results/dotenv-4000-live.json
```

默认解压到系统临时目录，避免上游源码污染本项目的自建任务检索。
准备目标已存在时会报错，保护已有源码；已有准备结果可以直接用于评测。
评测开始前检查所有真值符号唯一存在、相关文件包含对应定义，并校验独立任务的固定源码
manifest。预算必须至少为 128。英文检索词在运行前固定，`reference_facts` 仅供复核，
不参与任何检索或模型问答；词汇来自接口阅读，不能代表完全未知 API 名称的自然查询。

`--ablation` 增加 `symbol_no_deps`：与完整结构方法使用相同排名和组装配置，
关闭调用者/被调用者关系阶段，剩余预算仍可供源码和摘要使用。

新增 `overall_line_coverage` 是核心及依赖符号定义区间的已覆盖行比例，先按符号计算，
再取任务内平均。签名对应一个定义行，按一行计入覆盖；不是精确的原始代码字符覆盖率。
嵌套定义区间可能重叠，因此不应当作整个仓库的独立行覆盖率。该指标辅助区分
“存在符号签名”和“具有足够函数体代码”。

新版报告还保存完整代码上下文、原始模型回答、评委文本、输入与实现源码哈希，
支持相同参数和上下文的断点恢复。温度 0 不保证跨时段模型输出完全相同。
本轮已归档结果见 [evidence/README.md](evidence/README.md)，分析见
[实验工作稿](../docs/thesis-experiments.md)。

## 学生/导师复核

```bash
uv run python eval/export_review.py --report eval/evidence/dotenv-4000-live.json \
  --tasks eval/tasks-python-dotenv.json --out eval/results/review-dotenv-4000
```

复核 `review.csv`，先不看 `review-key.json` 和模型分数。结合固定源码和
`reference_facts`，分别填写正确性、完整性、依据及总体有用性，均为 1–5 分，并记录错误。
1 表示严重错误或无有效依据，3 表示部分正确但有关键遗漏，5 表示准确、完整且有依据。
评分参考事实仍需学生/导师检查，不是独立专家已经确认的真值。
正文风格可能透露策略，隐藏列和打乱顺序只能减轻先入为主，不能保证完全盲评。
导出目录已存在时拒绝覆盖，避免丢失人工评分。

## 实验限制

- `grep` 是确定性模拟检索，不包含模型反复改写查询的行为。
- `file` 使用关键词选择文件，模拟“找到文件后整段输入”；其前缀截断策略可能遗漏文件后部。
- 符号检索与真值都围绕 Python AST；其他工程语言目前只有文本索引，不能宣称已实现
  Verilog/VHDL 的结构解析。
- 10 个任务只来自本仓库，样本数小。若论文要求外部泛化，应增加公开小型 Python 仓库任务。
