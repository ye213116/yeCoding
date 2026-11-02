# yeCoding

yeCoding 是一个运行在终端里的 Python AI Agent：接入 OpenAI 兼容 LLM，通过 ReAct 工具循环读写文件、执行命令、检索代码、联网查询，并围绕 **Python 代码库理解**构建了 AST 符号解析、依赖感知检索和 token 预算上下文组装三层能力，配有可复现的对比评测。

核心路径有完整测试覆盖（`tests/`），不是演示项目。

## 模块总览

| 模块 | 位置 | 职责 |
| --- | --- | --- |
| 代码结构解析 | `src/yecoding/rag/parser.py` | 基于标准库 `ast` 抽取文件、类、函数、变量、import 依赖及调用/继承关系，输出符号与关系两类记录 |
| 符号索引与依赖检索 | `src/yecoding/rag/code_index.py` | SQLite 符号表 + 依赖边；`self.xxx` 调用沿基类链解析；符号命中排序检索，行级文本检索兜底 |
| 上下文组装 | `src/yecoding/rag/context_builder.py` | 固定 token 预算内按优先级（符号签名 > 调用链 > 源码摘录 > 文件摘要）装配 LLM 上下文块 |
| 会话上下文压缩 | `src/yecoding/context/manager.py` | 对话历史达到预算 80% 后压缩至 55%，CJK 感知 token 估算，保留近期轮次与完整工具调用对 |
| 智能体执行 | `src/yecoding/agent/` | ReAct / Plan-and-Execute / Multi-Agent 三种模式，统一流式事件协议 |
| 工具系统 | `src/yecoding/tools/` | 文件、shell、检索、记忆、技能、快照等内置工具 + MCP 动态工具；同批次工具调用按顺序处理写操作，相邻只读调用可并发 |
| LLM 接入 | `src/yecoding/llm/` | OpenAI 兼容流式客户端，DeepSeek/GLM 等模型档位与费用核算 |
| 对比评测 | `eval/` | 关键词摘录、直接输入文件、结构感知上下文的同任务对比（见下文） |

## 快速开始

要求 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://gitcode.com/javabetter/yeCoding.git
cd yeCoding
uv sync --extra dev
```

配置 API Key（写入 `.env` 或环境变量）：

```dotenv
YECODING_PROVIDER=deepseek
YECODING_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_key_here
```

也支持 `YECODING_API_KEY` 通用 Key，以及 `ZAI_API_KEY`/`GLM_API_KEY`、`KIMI_API_KEY`、`STEP_API_KEY` 等 provider 专属 Key；任何 OpenAI 兼容端点都可通过 `YECODING_PROVIDER=openai-compatible` + `YECODING_BASE_URL` 接入（含本地开源模型服务）。

运行：

```bash
uv run yecoding                          # 交互式 REPL
uv run yecoding -p "解释这个仓库"          # 单次查询
uv run yecoding --mode plan -p "先规划再执行"
uv run yecoding --mode team -p "并行审计核心模块"
uv run yecoding doctor --cwd .           # 环境自检
```

SDK 方式调用：

```python
from yecoding.sdk import create_default_engine

engine = create_default_engine(cwd=".")
result = engine.ask_complete("解释这个项目")
```

## 代码库理解（毕业设计核心链路）

```bash
/index                    # 对当前项目构建 AST 符号索引（.yecoding/code_index.sqlite3）
/search <query>           # 符号排序检索，行级匹配兜底
/context <query> [budget] # 一次性返回：符号签名 + 调用链 + 源码摘录 + 文件摘要
```

智能体侧对应两个工具：`search_code`（轻量检索）和 `get_context`（预算化上下文组装，探索代码库时优先使用）。索引构建约 0.2s / 千行级仓库，查询无需 LLM 参与即可复现。

## 上下文策略与三线实验

默认 `legacy` 保留原有窗口压缩行为；`evidence` 保留完整历史，为每次请求单独选择工具证据，
支持内容去重、文件版本失效检查、相关 Python 结构选择和带来源行段的日志摘录。
最近工具回合优先保留；16,000 token 是工具证据的估算软额度，不是供应商的精确输入计数。

```bash
YECODING_CONTEXT_STRATEGY=evidence uv run yecoding -p "解释并修复这个问题"
YECODING_TRACE_PATH=eval/results/session.jsonl uv run yecoding -p "检查这个仓库"
```

配置文件使用 `context.strategy`、`evidence_tokens`、`deduplicate`、`use_structure` 和
`trace_path`，CLI、SDK 与 Runtime 共用配置。轨迹默认关闭；开启后记录结构化模型请求、
工具结果、选择决策和 usage，并脱敏配置密钥及常见凭据字段。
策略只管理请求内容，不改变工具权限或执行顺序；已有 AST 索引仍是基础能力。

原版/改进版 yeCoding 与 mini-SWE-agent 的任务协议、独立环境安装及运行命令见
[评测说明](eval/README.md)和[现有实验报告](docs/mode-comparison.md)。
当前已完成策略实现和真实 CLI 链路验证；SWE-bench 开发集受任务镜像拉取超时阻塞，
尚无新策略的正式解决率或成本收益结论。

## 验证式多智能体修复

`repair` 在独立工作副本中执行 Python 修复，通过协调、修复、验证三个角色协作，
以 Docker 内真实执行的固定测试决定是否接受候选。失败证据支持有限重试，
成功后导出补丁与运行报告；原仓库不会被自动修改。

```bash
docker pull python:3.11-slim
uv run yecoding repair "修复指定缺陷" --cwd /path/to/project \
  --test "python -m unittest discover -s tests -v" --json
```

执行镜像须预装项目依赖。`--test` 可重复；三个内置修复 Skill 与项目作用域 Memory
复用现有系统。CLI、SDK、REPL `/repair` 和 Runtime `mode=repair` 共用实现。
**容器隔离只适用于修复路径**，普通 ReAct/Plan/Team 保持原有执行方式。
配置、演示、预算语义和边界见[修复流程](docs/repair-workflow.md)。

## 评测

`eval/run_eval.py` 在相同任务集、相同 token 预算、相同模型下对比三种策略：关键词检索摘录、直接输入文件、符号索引上下文组装。任务集为 10 个自建任务（对本仓库自身提问），真值符号经程序化校验；口径与统计方法见 [eval/README.md](eval/README.md)。

```bash
uv run python eval/run_eval.py --budget 4000 --skip-llm # 仅检索维度
uv run python eval/run_eval.py --budget 4000            # 含同模型生成与有用性评分
```

另有固定版本 python-dotenv v1.1.1 的 12 个独立任务、离线源码 fixture 和
`--ablation` 依赖扩展消融。运行方式见 [eval/README.md](eval/README.md)，
原始上下文、回答和评委输出归档在 [eval/evidence/](eval/evidence/README.md)。

独立任务实测（budget=4000，12 任务，均值±样本标准差）：

| 维度 | 直接文件 | 关键词摘录 | 结构感知 | 关闭依赖扩展 |
| --- | --- | --- | --- | --- |
| 上下文长度，估算 tokens | 3617±877 | 1550±883 | 1243±292 | 926±224 |
| 核心+依赖符号召回率 | 85.4%±22.5% | 75.4%±23.9% | 88.3%±18.4% | 64.4%±26.8% |
| 模型有用性评分，满分 5 | 4.75±0.87 | 4.58±0.90 | 4.75±0.45 | 4.75±0.45 |

该轮使用配置模型 `deepseek-v4-flash` 生成及评分，温度为 0。核心符号召回四者均为 100%；
这按定义附近行命中计算，不代表完整函数体覆盖。模型评分已有明确错判，不能据此宣布
依赖扩展提升生成质量；人工复核尚待完成。两档预算、源码覆盖指标和失败分析见
[实验工作稿](docs/thesis-experiments.md)，实现说明见[方法工作稿](docs/thesis-method.md)。

## 交互命令

REPL 内可用 `/help` 查看全部命令，常用的有：

```text
/index [path]      构建符号索引            /search <query>      代码检索
/context <q> [n]   预算化上下文            /plan <task>         计划-执行模式
/team <task>       多智能体模式            /model               模型选择器
/memory ...        长期记忆管理            /skill ...           技能管理
/mcp               MCP 服务器管理          /task ...            后台任务
/snapshot /restore 快照与恢复              /usage               Token 用量
```

## 配置与数据位置

配置优先级：内置默认 → `~/.yecoding/config.json` → 项目 `.yecoding/config.json` → `.env` → CLI 参数 → 进程环境变量。

| 路径 | 用途 |
| --- | --- |
| `~/.yecoding/config.json` | 全局配置（含 API Key，建议用环境变量代替） |
| `.yecoding/` | 项目级配置、技能、MCP 配置、代码索引 |
| `~/.yecoding/snapshots/` | Agent run 前后自动快照，可 `/restore` 回滚 |
| `~/.yecoding/skills/` | 用户级技能（`builtin → user → project` 三层加载） |
| `AGENTS.md` | 项目级静态记忆与工程约定（人工维护、可版本控制） |

## 安全

写文件、执行命令、恢复快照等危险动作经过 policy 守卫、HITL 人工确认和 JSONL 审计日志；`save_skill` 强制人工确认；`web_fetch` 拒绝 `file://`、loopback 与内网地址。交互模式 `Shift+Tab` 可临时切换会话权限模式。

## 开发

```bash
uv run --extra dev python -m pytest      # 全量测试
uv run --extra dev ruff check .          # lint
uv run --extra dev ruff format --check . # 格式
```

更多设计决策与模块细节见 [AGENTS.md](AGENTS.md)；毕设的[文献与技术路线](docs/literature-review.md)、[任务核对](docs/thesis-readiness.md)和对外能力[对齐记录](docs/parity.md)分别记录研究背景、完成状态与产品边界。

## License

MIT. See [LICENSE](LICENSE).
