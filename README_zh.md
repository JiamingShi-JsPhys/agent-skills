[English](README.md) · `中文说明`
# agent-skills

> `agent-skills` 是 **Jiaming Shi（施嘉名）** 开发并维护的 Agent 技能集合。它为各类 AI Agent
> 工具提供标准化、可审计、可靠的本地执行能力。仓库中的每个技能都是独立、自包含的包——运行
> 技能无需复杂的安装或构建步骤，只要环境支持 Skill 规范即可直接挂载使用。

<!-- TOC depthFrom:2 -->

- [agent-skills](#agent-skills)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [七个技能](#七个技能)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [仓库布局](#仓库布局)
  - [开发与贡献](#开发与贡献)
  - [开源协议](#开源协议)
  - [报告问题](#报告问题)

<!-- END_TOC -->

## 设计原则与核心特征

1. **Agent 原生**：每个技能都附带一份带标准元数据的 `SKILL.md`。Agent 可以自行读取该文件、理解技能适用范围与执行步骤，并自主调用底层脚本。
2. **零依赖部署**：技能尽量只用 Python 标准库，避免复杂的依赖链，保证跨平台即插即用（Windows / macOS / Linux）。
3. **确定性安全**：为防止 AI 执行幻觉，每个技能都强制可验证、可回滚的操作与完整的审计日志。
4. **触发即执行**：每个技能的 `SKILL.md` 以强制工作流开篇——命中适用范围的请求会让 Agent 直接运行工具并汇报结果，而不是只描述这个工具能做什么。

## 七个技能

目前有 7 个可安装技能，按功能分组如下。每一行链接到该技能的 `README.md`（本表是唯一总览；点进去是各技能的详细文档）。

| | 功能类别 | 技能 | 一句话说明 | 依赖库 |
| :--- | :--- | :---: | :--- | :--- |
| | **文件与项目管理** | [`task-organizer`](skills/task-organizer/README_zh.md) v1.0.1 | 把杂乱的任务文件夹整理成三段式结构，提供广播中心作为上下文压缩索引 | 标准库 |
| | | [`document-evolution-tracker`](skills/document-evolution-tracker/README_zh.md) v1.0.0 | 追踪文档家族的版本对齐与概念谱系，自动发现版本、做块级 diff 并渲染时间线 | 标准库 |
| | **实验运行与调度** | [`multi-dim-manager`](skills/multi-dim-manager/README_zh.md) v1.0.1 | 把参数空间笛卡尔展开成多轮独立任务，用于多个同类型任务的自动运行 | 标准库 + PyYAML（可选，用于 YAML 配置） |
| | **数据分析与提取** | [`longitudinal-analysis`](skills/longitudinal-analysis/README_zh.md) v1.0.0 | 纵向统计分析流水线：描述性统计、操纵检验、线性混合模型、滞后中介与敏感性分析 | `pandas`、`numpy`、`scipy`、`statsmodels`、`openpyxl`；可选 `Rscript` + `lme4`/`lavaan` |
| | | [`video-tracker`](skills/video-tracker/README_zh.md) v0.0.0 (beta) | 逐帧追踪实验视频中的运动目标，输出标准化运动数据：OpenCV 追踪、FFT 频谱、物理一致性探针 | `numpy`、`opencv`（headless）；可选 `matplotlib`、`pyyaml` |
| | **质量验证与检测** | [`formula-validator`](skills/formula-validator/README_zh.md) v1.0.1 | 物理 / 数学公式的确定性校验器，对多层独立检查并输出报告 | 标准库 |
| | | [`conflict-detector`](skills/conflict-detector/README_zh.md) v1.0.0 | 跨文档冲突检测器，提取数值 / 布尔断言与条款做分类，输出冲突报告 | 标准库 |

## 下载与安装

获取技能共有**四种**标准方式。

**方式一：跨平台安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**（本发版共 7 个）。下载你要的那个技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后确定性进度条会逐个文件跟踪拷贝过程。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents`、`.task-organizer.yml` 等标记识别），并在下拉框中列出供你挑选：

- **Windows**：`<skill>-installer.exe`（每个技能一个，例如 `task-organizer-installer.exe`）。每个二进制各自捆绑它的那个技能，双击只安装那一个。
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI 入口。

若要改用 CLI（从仓库检出，或用二进制）驱动同一逻辑：

```bash
# 列出可安装的技能。
python install.py --list

# 把所有技能装到四个框架的用户作用域。
python install.py --platform all --scope user

# 只装一个技能到项目作用域（相对当前目录）。
python install.py --skill task-organizer --scope project

# 强制覆盖已存在的安装。
python install.py --platform workbuddy --scope user --force
```

对应入口还有 `uninstall.py`（移除已安装技能）与 `verify.py`（校验安装完整性）。偏好 shell 的用户可用 `install.sh` / `install.ps1` 转发脚本。Windows 安装器由 `installer/installer_gui.py`（自包含、纯标准库的 tkinter 前端）按每个技能各构建一份；构建工具链放在本仓库之外（维护者的本地构建工作区），**不属于**安装路径——预构建的安装器挂在 Releases 页上。

#### 一行安装 —— 无需下载（Windows PowerShell）

不想下载任何文件？在 PowerShell 里跑这一条命令即可——它从 GitHub 直接取安装脚本、完成安装并自行清理临时文件：

```powershell
irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1 | iex
```

默认把**所有技能**装到用户作用域的 **Codex**（默认框架）。要指定技能、框架或作用域，用 scriptblock 形式传参（`| iex` 形式无法带参数）：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill task-organizer -Frameworks workbuddy,claude -Scope user
```

参数：`-Skill`（技能名、逗号分隔多个，或 `*` 全部）、`-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）、`-Scope`（`user` 或 `project`）、`-Dir`（项目作用域的任务文件夹）、`-Repo` / `-Branch`（默认本仓库、`main`）、`-Force`（覆盖已存在的安装）。需要 Windows PowerShell 5.1+，无需 Python。

**方式二：源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills   # 每个技能就是顶层各自一个文件夹
```

**方式三：让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位对应技能并替你装好：

> 请访问仓库 https://github.com/JiamingShi-JsPhys/agent-skills ，找到我需要的技能文件夹（注明技能名字或功能），阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装该技能。

你只需要告诉 Agent 技能名，剩下的交给它。

**方式四：克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills   # 每个技能就是顶层各自一个文件夹
```

## 快速开始

每个技能均提供基于 Python 的命令行接口。以 `task-organizer` 为例：

```bash
cd agent-skills/skills/task-organizer
python -m scripts.run /path/to/task_folder
```

以 `conflict-detector` 为例：

```bash
cd agent-skills/skills/conflict-detector
python -m src.cli --help
```

或在 Python 里直接调用模块：

```python
from pathlib import Path
from scripts import run   # 具体模块名请参考技能内的实际实现

result = run.organize(Path("/path/to/task_folder"))
print(result.summary_lines())
```

> 以上为示例，实际接口以技能目录内的文档为准。

## 仓库布局

所有已发布技能统一放在顶层的 **`skills/`** 目录下，各自独立成文件夹。下方的树与磁盘实际布局一一对应：先目录后文件，各组内按**字母序**排列。各技能的内部结构见其自带 README。

```
agent-skills/
├── skills/
│   ├── conflict-detector/                 # 跨文档冲突检测器
│   ├── document-evolution-tracker/        # 版本对齐 + 概念谱系
│   ├── formula-validator/                 # 物理 / 数学公式确定性校验器
│   ├── longitudinal-analysis/             # 纵向统计分析流水线
│   ├── multi-dim-manager/                 # 多维度实验状态管理器
│   ├── task-organizer/                    # 任务文件夹整理 + 广播中心
│   └── video-tracker/                     # 实验视频运动数据提取器（实验性）
├── installer/                                # 跨平台安装器（原生 tkinter 窗口 + 内核）
│   ├── __init__.py
│   ├── assets/
│   │   └── README.md                         #   图标资产（打包前放入各平台图标）
│   ├── installer_core.py                     #   与 GUI 解耦的安装/卸载/校验逻辑
│   ├── installer_gui.py                      #   双击目标（用 PyInstaller 打包成 .exe/.app）
│   ├── platform_paths.py                     #   (平台, 作用域) -> 目标目录
│   ├── requirements.txt
│   └── skill_loader.py                       #   自适应技能发现
├── tests/                                    # 安装器单元测试
├── .gitignore
├── AUTHORS.md
├── CITATION.cff
├── install-web.ps1                           # 一行式网络安装器（PowerShell）
├── LICENSE
├── README.md
├── README_zh.md
├── VERSION
├── conftest.py
├── install.ps1
├── install.py
├── install.sh
├── uninstall.py
└── verify.py
```

一个技能即一个含 `SKILL.md` 的目录，其 frontmatter 携带版本、名称、描述等元数据。每个已发布技能至少携带 `SKILL.md`、中英双语文档、`LICENSE`、`CHANGELOG.md`、`requirements.txt` 与 `tests/` 测试目录；多数还携带 `pyproject.toml`、`CITATION.cff` 与 `AUTHORS.md`（公式校验器除外），以及各技能特有的 `CONTRIBUTING.md`、配置示例或 `src/` / `scripts/` 代码树。

## 开发与贡献

本仓库遵循严格的开源工程标准。如果你希望提交新的技能或修复现有问题：

1. **独立性原则**：每个 Skill 必须位于独立文件夹中，且包含完整的 `LICENSE`、`README.md` 以及标准的 `SKILL.md` 文件。
2. **质量底线**：提交的 Python 代码必须包含类型提示（Type hints）与 Docstrings，并附带覆盖核心逻辑的单元测试（目标覆盖率 >= 80%）。
3. **版本控制**：遵循 [Semantic Versioning](https://semver.org/) 与 [Keep a Changelog](https://keepachangelog.com/) 规范记录变更。
4. **代码风格**：遵循 PEP 8 规范（建议行宽 <= 88），核心流程要求异常捕获与优雅降级，尽量避免在预期 I/O 错误下直接崩溃。

## 开源协议

本仓库整体采用 [MIT License](LICENSE) 发布，详见根目录下的 `LICENSE` 文件。

每个技能包内均携带独立的 `LICENSE` 文件，以该技能目录下的声明为准。

## 报告问题

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report task-organizer: path traversal 可读取任务文件夹之外的路径`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
