[English](README.md) · `中文说明`
# multi-dim-manager

> 一个跨平台、零依赖、Agent-Native 的智能体 skill——自包含的多维度计算实验状态管理器：把参数网格在几百轮里迭代，每轮对声明的关键路径做快照，审计每一轮，并能非破坏性地回滚到任意一轮。算力由你的计算插件提供，本技能只负责管理它周边的状态。

<!-- TOC depthFrom:2 -->

- [multi-dim-manager](#multi-dim-manager)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [常见请求形状](#常见请求形状)
  - [已知局限](#已知局限)
  - [测试与覆盖率](#测试与覆盖率)
  - [项目结构](#项目结构)
  - [作为 Agent 技能挂载使用](#作为-agent-技能挂载使用)
  - [开源协议](#开源协议)
  - [报告问题与反馈](#报告问题与反馈)

<!-- END_TOC -->

---

## 设计原则与核心特征

- **关注点分离**：你的计算插件负责算，本技能只管它周边的状态（快照、审计、回滚）。
- **触发即执行**：用户要求运行 / 检查 / 恢复多维度实验时，读取配置并确认参数空间、关键路径、插件命令就绪；先报告总轮数，优先 dry-run 让用户看到完整计划，再执行。每轮先快照关键路径、再调用插件、再快照并追加审计；某轮失败记录状态，开启 `auto_rollback` 时恢复上一轮稳定状态（记入审计），不中断整个扫描。
- **非破坏性回滚**：默认落到新目录（`<workdir>.rollback_NNNN`），只有显式 `--force` 才覆盖当前工作目录；无论哪种动作都写入审计。
- **可审计**：每轮向 `audit_log.jsonl` 追加一行 JSON，记录参数组合、输入哈希、输出哈希、时间戳、插件退出码，以及前后两次快照（pre/post）；回滚动作同样入审计，事后可完整复现。
- **快照内容寻址**：只快照 `critical_paths` 声明的文件，按 SHA-256 内容寻址只存一份，跨轮不变的文件不额外占空间；一次快照即一份「相对路径 → 内容哈希」清单。
- **汇总产出**：写出 `results_summary.csv/.md`、`report_draft.md`、`run_metadata.json`；按需用 `rollback` 恢复（默认新建目录，`--force` 才覆盖）。
- **插件契约**：一条 shell 命令 + JSON 输入输出 + 退出码 0/1/2。
- **纯标准库**：默认零第三方依赖；JSON 配置即可用，YAML 配置需 `pyyaml`。

---

## 下载与安装

获取本技能共有**四种**标准方式：

**方式一 —— per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents` 及其他项目标记识别），并在下拉框中列出供你挑选，无需手动输入：
- **Windows**：`multi-dim-manager-installer.exe`（只装本技能）
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI。

无需命令行：该二进制只安装本技能。若要改用 CLI：

```bash
python install.py --skill multi-dim-manager --scope user
```

或者用一行命令安装，无需下载（Windows PowerShell）——它直接从 GitHub 获取安装脚本，安装完成后自动清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill multi-dim-manager
```

它会把**本技能**装进 **Codex**（默认框架）的用户作用域。要选择框架或作用域，加上 `-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）或 `-Scope`（`user` 或 `project`）。需要 Windows PowerShell 5.1+，无需 Python——完整参数说明见根目录的 `README.md`。

**方式二 —— 源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/multi-dim-manager    # 本技能就是顶层各自一个文件夹
pip install -r requirements.txt
```

**方式三 —— 让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位本技能、从 **Releases** 页下载安装器并替你装好：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/multi-dim-manager ，阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装本技能。

你只需要把技能名告诉 Agent，剩下的交给它。

**方式四 —— 克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/multi-dim-manager
pip install -r requirements.txt
```

环境要求：Python 3.10+。使用 JSON 配置时无需任何第三方包；YAML 配置需要
`pyyaml`（`pip install pyyaml`）。其余均只用 Python 标准库。

---

## 快速开始

```bash
cd agent-skills/skills/multi-dim-manager

# 0. （可选）先看完整计划，不真正执行
python scripts/run.py dryrun --config config.example.yaml

# 1. 运行扫描（在 ./output 下写出审计、快照、汇总）
python scripts/run.py run --config config.example.yaml

# 2. 把某一轮恢复到新目录
python scripts/run.py rollback --config config.example.yaml --round 12

# 3. 从审计日志重新生成汇总
python scripts/run.py summary --config config.example.yaml

# 4. 检查某一轮的插件契约结果
python scripts/run.py verify --config config.example.yaml --round 12
```

### 输出结构

```
output/
  audit_log.jsonl      # 每轮一行 JSON（含回滚）
  snapshots/store/     # 内容寻址的关键文件存储
  results_summary.csv  # 扁平、可筛选的表格
  results_summary.md   # 同一张表的 Markdown 版
  report_draft.md      # 叙述性草稿
  run_metadata.json    # 参数空间、插件、计时
```


## 常见请求形状

- “把这个 2×2×2 网格、200 轮跑完，告诉我哪些组合通过了。”
- “第 47 轮崩了——把它的状态恢复出来，我想检查当时的输入。”
- “全部回滚到第 150 轮，换组参数从那里重跑。”
- “把最近 10 轮的审计轨迹给我看。”

---

## 已知局限

- **确定性只保证在编排层**。技能记录哈希、对相同输入重放相同计划，但无法让一个本身不确定的插件变确定。若插件触网、用随机种子、或读取系统时钟，相同输入可能产生不同输出。这类不确定性请在插件里自行声明。
- **关键路径必须提前声明**。未列入 `critical_paths` 的文件不会被快照，因此也无法回滚。
- **黄金输出校验留到 v0.2**。当前校验器只检查插件契约（退出码 0 + 有结果文件）。与已知预期输出的比对尚未实现。
- **YAML 配置需要 PyYAML**。JSON 配置仅靠标准库即可。

---

---

## 测试与覆盖率

测试套件当前覆盖 87 个用例。运行方式：

```bash
python -m pytest -q
```

目标行覆盖率 >= 80%，与仓库的质量基线一致。两个 YAML 配置测试在未安装 PyYAML 时会自动跳过；JSON 配置测试始终运行。

---

## 项目结构

```
multi-dim-manager/
  SKILL.md                 # Agent 执行指南（MANDATORY WORKFLOW）
  README.md                # 文档（本文件）
  README_zh.md             # 中文镜像
  LICENSE                  # MIT
  CHANGELOG.md
  AUTHORS.md
  CITATION.cff
  .gitignore
  config.example.yaml      # 配置模板
  pyproject.toml           # 打包与工具配置
  requirements.txt         # pyyaml（可选；JSON 配置无需任何依赖）
  sample_plugin.py         # 示例计算插件（契约演示）
  scripts/
    __init__.py
    param_space.py         # 参数空间解析与展开
    config.py              # 实验配置加载
    executor.py            # 插件调用（shell + JSON + 退出码 0/1/2）
    snapshot.py            # 内容寻址的关键路径快照
    audit.py               # 只追加的 JSONL 审计日志
    rollback.py            # 非破坏性回滚
    aggregator.py          # 结果表汇总
    report.py              # Markdown 汇总 / 草稿
    verify.py              # 插件契约校验（黄金比对：v0.2）
    run.py                 # CLI 入口
    common.py              # 各核心模块共用的通用工具
    errors.py              # 领域专属错误类型
  tests/                   # 单元测试 + 文档契约测试
    conftest.py
    test_aggregator.py
    test_audit.py
    test_config.py
    test_executor.py
    test_param_space.py
    test_report.py
    test_rollback.py
    test_run_cli.py
    test_skill_docs.py     # 文档契约
    test_snapshot.py
    test_verify.py
```

---

## 作为 Agent 技能挂载使用

把整个文件夹放进任何支持 Skill 规范的 Agent 环境。当请求命中适用范围（多轮、多维、需要
跟踪状态的实验）时，Agent 读取 `SKILL.md` 并按其 MANDATORY WORKFLOW 执行。本技能自包含：
不 import 任何兄弟技能。

---

## 开源协议

基于 MIT 协议发布，详见 `LICENSE`。

---

## 报告问题与反馈

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report multi-dim-manager: 回滚命令可把快照文件恢复到任意绝对路径`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 命令输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
