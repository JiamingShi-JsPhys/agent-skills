[English](README.md) · `中文说明`
# document-evolution-tracker

> 一个跨平台、零依赖、Agent-Native 的智能体 skill——核心是把每一处文字改动追溯到来源，让报告读起来是"变化的故事"而非裸 diff。

<!-- TOC depthFrom:2 -->

- [document-evolution-tracker](#document-evolution-tracker)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [对比粒度](#对比粒度)
  - [项目结构](#项目结构)
  - [运行测试](#运行测试)
  - [开源协议](#开源协议)
  - [报告问题与反馈](#报告问题与反馈)

<!-- END_TOC -->


## 设计原则与核心特征

- **谱系优先**：每处改动都能追溯到文字来源，报告读起来是"变化的故事"而非裸 diff。
- **多粒度对比**：按行 / 段 / 句不同粒度追踪编辑。
- **可复现报告**：每次运行按 tracking id 版本化，结果可审计。
- **版本化快照**：每个修订都有稳定的 tracking id。
- **谱系追踪**：展示某段落来源、以及它在各版本间的流转。
- **可导出报告**：每次运行输出 Markdown + JSON，JSON 为机器可读契约。

## 下载与安装

获取本技能共有**四种**标准方式：

**方式一 —— per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents`、等标记识别），并在下拉框中列出供你挑选，无需手动输入：
- **Windows**：`document-evolution-tracker-installer.exe`（只装本技能）
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI。

无需命令行：该二进制只安装本技能。若要改用 CLI：

```bash
python install.py --skill document-evolution-tracker --scope user
```

或者用一行命令安装，无需下载（Windows PowerShell）——它直接从 GitHub 获取安装脚本，安装完成后自动清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill document-evolution-tracker
```

它会把**本技能**装进 **Codex**（默认框架）的用户作用域。要选择框架或作用域，加上 `-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）或 `-Scope`（`user` 或 `project`）。需要 Windows PowerShell 5.1+，无需 Python——完整参数说明见根目录的 `README.md`。

**方式二 —— 源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/document-evolution-tracker # 本技能就是顶层各自一个文件夹
pip install -e .
```

**方式三 —— 让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位本技能、从 **Releases** 页下载安装器并替你装好：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/document-evolution-tracker ，阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装本技能。

你只需要把技能名告诉 Agent，剩下的交给它。

**方式四 —— 克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/document-evolution-tracker
pip install -e .
```

环境要求：Python 3.10+。

## 快速开始

```bash
pip install -e .
python -m src.cli run --config config/examples/family.json --concepts "Alpha,Beta"
```

报告输出到 `./evolution/evolution_<tracking_id>.{md,json}`。

## 对比粒度

| 层级 | 适用 |
|---|---|
| `line` | 粗粒度变更概览 |
| `paragraph` | 跟踪某段落在版本间的改写 |
| `sentence` | 句级精确编辑 |

## 项目结构

```
document-evolution-tracker/
├── SKILL.md                # Agent 执行指南（MANDATORY WORKFLOW）
├── README.md
├── README_zh.md            # 中文镜像
├── LICENSE                 # MIT
├── CHANGELOG.md
├── AUTHORS.md
├── CITATION.cff
├── .gitignore
├── pyproject.toml          # 打包与工具配置
├── requirements.txt        # PyYAML（可选）+ pytest
├── config/
│   ├── schema.yaml         # 配置模式
│   └── examples/
│       ├── family.json      # 示例配置
│       └── family/          # 示例文档各版本
│           ├── v1.md
│           └── v2.md
├── src/
│   ├── __init__.py
│   ├── cli.py               # 入口
│   ├── config.py            # 版本族 + 粒度 + 输出配置
│   ├── tracker.py           # 串联各模块的统一入口
│   ├── align.py             # 版本间段落对齐
│   ├── diff_blocks.py       # 块级结构 diff
│   ├── lineage.py           # 概念谱系图
│   ├── versioning.py        # 版本解析（两种命名方案）
│   └── report.py            # Markdown / JSON 报告
└── tests/                   # pytest 测试
    ├── test_core.py
    ├── test_skill_docs.py   # 文档契约
    └── test_tracker_cli.py
```

## 运行测试

```bash
cd document-evolution-tracker
pytest tests
```

## 开源协议

MIT License，详见 [LICENSE](LICENSE) 与 [CITATION.cff](CITATION.cff)。

请在主仓库提交 issue 与 pull request。

## 报告问题与反馈

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report document-evolution-tracker: 演化报告写文件时跟随符号链接，可覆盖工作区之外的文件`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 命令输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
