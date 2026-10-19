[English](README.md) · `中文说明`
# longitudinal-analysis

> 一个跨平台、零依赖、Agent-Native 的智能体 skill——核心是用一份可复现的 YAML 配置驱动 LMM、增长曲线、中介/SEM 多步分析，R 后端可选。

<!-- TOC depthFrom:2 -->

- [longitudinal-analysis](#longitudinal-analysis)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [流水线步骤](#流水线步骤)
  - [项目结构](#项目结构)
  - [运行测试](#运行测试)
  - [依赖](#依赖)
  - [开源协议](#开源协议)
  - [报告问题与反馈](#报告问题与反馈)

<!-- END_TOC -->


## 设计原则与核心特征

- **配置驱动**：一份 YAML 定义设计、时间点与分析步骤，同一份配置可复现运行。
- **混合方法友好**：LMM、增长曲线、中介 / SEM 各步骤并存，按需启用。
- **R 为可选后端**：混合线性模型经外部 `Rscript` 执行；没有 R 时相应步骤自动跳过。
- **线性混合模型（LMM）**：重复测量的固定 + 随机效应。
- **增长曲线建模**：轨迹项（截距、斜率……）。
- **中介 / 结构方程**：跨时间点路径模型，需 R `lavaan`。

## 下载与安装

获取本技能共有**四种**标准方式：

**方式一 —— per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents`、等标记识别），并在下拉框中列出供你挑选，无需手动输入：
- **Windows**：`longitudinal-analysis-installer.exe`（只装本技能）
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI。

无需命令行：该二进制只安装本技能。若要改用 CLI：

```bash
python install.py --skill longitudinal-analysis --scope user
```

或者用一行命令安装，无需下载（Windows PowerShell）——它直接从 GitHub 获取安装脚本，安装完成后自动清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill longitudinal-analysis
```

它会把**本技能**装进 **Codex**（默认框架）的用户作用域。要选择框架或作用域，加上 `-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）或 `-Scope`（`user` 或 `project`）。需要 Windows PowerShell 5.1+，无需 Python——完整参数说明见根目录的 `README.md`。

**方式二 —— 源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/longitudinal-analysis # 本技能就是顶层各自一个文件夹
pip install -e .
```

**方式三 —— 让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位本技能、从 **Releases** 页下载安装器并替你装好：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/longitudinal-analysis ，阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装本技能。

你只需要把技能名告诉 Agent，剩下的交给它。

**方式四 —— 克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/longitudinal-analysis
pip install -e .
```

环境要求：Python 3.10+。核心依赖：`pandas`、`numpy`、`scipy`、`statsmodels`、`openpyxl`。可选：R 及 `lme4`（LMM）、`lavaan`（SEM），用于 R 后端步骤；没有 R 时相应步骤自动跳过。

## 快速开始

```bash
pip install -e .
python -m src.cli run --config config/examples/behavior_2x2x2.yaml
```

步骤按序执行；加 `--step lmm`（或任一步骤名）只跑单步。需要 `Rscript` 的步骤在没有 R 时自动跳过。

## 流水线步骤

| 步骤 | 作用 |
|---|---|
| `lmm` | 对主要结局做线性混合模型 |
| `growth` | 增长曲线 / 轨迹分解 |
| `mediation` | 中介与 SEM 路径（需 R `lavaan`） |

## 项目结构

```
longitudinal-analysis/
├── SKILL.md                # Agent 执行指南（MANDATORY WORKFLOW）
├── README.md
├── README_zh.md            # 中文镜像
├── LICENSE                 # MIT
├── CHANGELOG.md
├── AUTHORS.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml          # 打包与工具配置
├── requirements.txt        # pandas、numpy、scipy、statsmodels、PyYAML
├── config/
│   ├── schema.yaml         # 配置模式
│   └── examples/
│       └── behavior_2x2x2.yaml   # 2×2×2 完整示例
├── R/
│   ├── lmm.R               # lme4 线性混合模型
│   └── mediation.R         # lavaan 中介 / SEM
├── src/
│   ├── __init__.py
│   ├── cli.py              # 入口
│   ├── config.py           # 配置加载（YAML / JSON）
│   ├── pipeline.py         # 步骤编排（无 R 时优雅降级）
│   ├── r_runner.py         # R 调用（经 stdin/stdout 传 JSON）
│   ├── audit.py            # 只追加的运行审计（输入/输出哈希）
│   └── steps/
│       ├── __init__.py
│       ├── descriptive.py  # 描述性统计（纯 pandas）
│       ├── manipulation.py # 操纵检验（Type II ANOVA）
│       ├── lmm.py          # 线性混合模型（R 后端）
│       ├── mediation.py    # 滞后中介 / SEM（R 后端）
│       └── sensitivity.py  # 随机效应 / 协方差敏感性
└── tests/
    ├── conftest.py
    ├── fixture_panel.csv   # 示例面板数据
    ├── test_cli.py
    ├── test_manipulation.py
    ├── test_pipeline.py
    ├── test_r_steps.py
    └── test_skill_docs.py  # 文档契约
```

## 运行测试

```bash
cd longitudinal-analysis
pytest tests
```

## 依赖

核心：`pandas`、`numpy`、`scipy`、`statsmodels`、`openpyxl`。
可选：R 及 `lme4`（LMM）、`lavaan`（SEM），用于 R 后端步骤。

## 开源协议

MIT License，详见 [LICENSE](LICENSE) 与 [CITATION.cff](CITATION.cff)。

请在主仓库提交 issue 与 pull request。

## 报告问题与反馈

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report longitudinal-analysis: R-runner 步骤会执行配置文件里未经校验的 shell 命令`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 命令输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
