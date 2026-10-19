[English](README.md) · `中文说明`
# task-organizer

> 一个跨平台、零依赖、Agent-Native 的智能体 skill——核心是 **文件夹整理** 与 **全局统筹**。

<!-- TOC depthFrom:2 -->

- [task-organizer](#task-organizer)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [测试与覆盖率](#测试与覆盖率)
  - [项目结构](#项目结构)
  - [作为 Agent 技能挂载使用](#作为-agent-技能挂载使用)
  - [开源协议](#开源协议)
  - [报告问题与反馈](#报告问题与反馈)

<!-- END_TOC -->

task-organizer 帮你把杂乱的任务/项目文件夹整理成统一的标准三段式结构，并统筹整个任务的文件生命周期：任务一开始就建好全部结构、全程登记文件来源、用广播中心给出整个文件夹的只读地图、最终交付前再整理一次并重建索引。这样既能让文件夹在任务进行中始终保持整齐，也能在长任务里保护上下文窗口。

整理前后会做完整的目录快照，并强制执行 8 项一致性检查（C1–C8）；任何一项失败都 **自动回滚** 到整理前状态——通常可以避免出现“整理了一半且无法证明无损”的文件夹。

```
task_folder/
+---- _broadcast/            # 只读的上下文压缩索引
|   +---- INDEX.md           #   每个文件一行：摘要 + 关键词 + 分类
|   `---- index.json         #   同一份索引，机器可读
+---- material/
|   +---- initial/           # 你自己的材料——原样保留，绝不改名
|   +---- downloaded/        #   本次对话中由 AI 下载的文件
|   +---- duplicates/        #   查重模式隔离出的完全重复文件
|   +---- Index.md           #   自动生成的 Markdown 索引
|   `---- Index.xlsx         #   自动生成的 Excel 索引（含 Statistics 统计页）
+---- process/               # AI 产出 + 快照 + 日志 + 历史记录
|   +---- YYYYMMDD_HHMMSS_before.json
|   +---- YYYYMMDD_HHMMSS_after.json
|   +---- YYYYMMDD_HHMMSS_OrganizeLog.md
|   +---- sources.json       #   来源清单（用户 / 下载）
|   +---- verification_report.md        # C1-C8 校验结果
|   +---- history/           #   操作历史 + undo / redo
|   `---- logs/              #   按天记录的活动日志
`---- results/               # 最终交付物（文件名含 final / deliverable / 报告 / 综述）
```

**唯一需要记住的规则：`material/initial/` 只属于你。** 工具从不会把自己产生的任何文件写进这个目录，所以它永远不可能和你的文件撞名。你只需要：建好文件夹 → 把材料放进去 → 运行 `init`。你的材料始终原样保留，不会被改名或修改。

---

## 设计原则与核心特征

- **触发即执行**：命中工作空间（任务 / 项目 / 研究文件夹）即整套触发，先只读 `doctor`，按需 `init` / `organize`；只说明不执行视为失败。
- **干净的标准结构**：固定三层布局（`material/` + `process/` + `results/`），外加只读的 `_broadcast/` 索引；任何任务文件夹读起来都一样。
- **全生命周期协调**：任务开始即建好全部结构，全程登记来源；AI 下载文件立刻 `mark-downloaded` 声明，交付前 `organize` + `broadcast` 重建索引。
- **保护上下文窗口**：`_broadcast/` 是只读压缩索引，只写 `INDEX.md` + `index.json`，支持常见格式，默认本地摘要，AI 可选；后续会话先读目录，再打开原文。
- **无损与安全**：前后 SHA-256 快照 + C1–C8 校验，失败自动回滚；支持 `undo` / `redo`、`--mode` 分档、`--keep N` 轮转。
- **可选增强**：查重、YAML 规则、双格式索引、AI 摘要、中文交付关键词、按天日志。

### 触发后必须执行的工作流

本技能是一条“去执行”的指令，不是一份供总结的文档：命中触发条件就**必须运行工具**并报告它做了什么——用对这个技能的描述（特性、命令列表、架构）来作答是一种**任务失败**，不是结果。完整步骤以 `SKILL.md` 的 MANDATORY WORKFLOW 为准，要点如下：

1. **会话开局结构检查**：工作空间文件夹一确定，先跑只读的 `doctor <root>`（它不写、不搬、不读内容，只做一次 stat 遍历，因此跑在任何确认之前，永远安全）。报告结构缺失时再走**文件夹信号检测**：明确要求整理 / 搭建，或“产出成果物 + 保持文件夹整齐”的复合意图 → 直接 `init <root>` 并**跳过提议**；只是附带 / 引用文件夹 → **先提议，再动手**，只提议一次然后停下，**用户确认前不运行任何会改动文件夹的命令**（每个文件夹最多提议一次）。
2. **解析路径，选入口**：没给路径就问，并给一个具体默认值；从零创建 / 空文件夹走 `init`，整理已有内容走 `organize`。
3. **交付前闭环**：交付物写完后跑 `organize <root>` 再 `broadcast <root>` **重建广播索引**；文件名含 `final` / `deliverable` / `report` / `review` / `summary` 或中文关键词 **定稿 / 最终版 / 终稿 / 综述 / 报告 / 总结 / 小结** 才会落入 `results/`。
4. **下载即登记**：会话里往任务文件夹下载 / 抓取文件，立刻 `mark-downloaded <root> <file> --url <来源>`——这是让 `downloaded/` 真正表示“AI 下载的文件”的唯一办法。
5. **广播中心是强制的、不是可选项**：`_broadcast/` 是一份分类的**只读**摘要（只写 `INDEX.md` + `index.json`），最终交付前必须重建，让后续会话先读目录、再打开原文，而不是重读每一个原始文档。

---

## 下载与安装

获取本技能共有**四种**标准方式：

**方式一 —— per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents`、`.task-organizer.yml` 等标记识别），并在下拉框中列出供你挑选，无需手动输入：
- **Windows**：`task-organizer-installer.exe`（只装本技能）
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI。

无需命令行：该二进制只安装本技能。若要改用 CLI：

```bash
python install.py --skill task-organizer --scope user
```

或者用一行命令安装，无需下载（Windows PowerShell）——它直接从 GitHub 获取安装脚本，安装完成后自动清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill task-organizer
```

它会把**本技能**装进 **Codex**（默认框架）的用户作用域。要选择框架或作用域，加上 `-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）或 `-Scope`（`user` 或 `project`）。需要 Windows PowerShell 5.1+，无需 Python——完整参数说明见根目录的 `README.md`。

**方式二 —— 源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/task-organizer       # 本技能就是顶层各自一个文件夹
```

**方式三 —— 让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位本技能、从 **Releases** 页下载安装器并替你装好：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/task-organizer ，阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装本技能。

你只需要把技能名告诉 Agent，剩下的交给它。

**方式四 —— 克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/task-organizer
```

环境要求：Python 3.10+。openpyxl 为可选依赖（仅用于生成 Excel 索引；不安装也能正常生成 Markdown 索引）。除 openpyxl 外的所有特性均仅使用标准库实现，不引入新依赖。

---

## 快速开始

```bash
cd agent-skills/skills/task-organizer

# 0. （可选）只读诊断：结构 / 散落文件 / 广播新鲜度
python -m scripts.run doctor /path/to/task_folder

# 1. 先建好任务文件夹，把自己的材料放进去（手动）。
# 2. 轻量 init：搭骨架 + 把你的材料原样搬进 material/initial/。
python -m scripts.run init /path/to/task_folder

# 3. 完整整理 + 校验（失败自动回滚）。
python -m scripts.run organize /path/to/task_folder

# 4. AI 下载了文件 -> 先声明来源，再整理。
python -m scripts.run mark-downloaded /path/to/task_folder fetched.pdf --url https://...
python -m scripts.run organize /path/to/task_folder --mode quick
```

其他命令：

```bash
python -m scripts.run organize /path/to/task_folder --mode incremental --keep 5
python -m scripts.run organize /path/to/task_folder --profile pharma --config rules.yml
python -m scripts.run index    /path/to/task_folder        # 只重新生成索引
python -m scripts.run snapshot /path/to/task_folder        # 危险操作前的安全气囊
python -m scripts.run undo     /path/to/task_folder/process/history/<file>.json
python -m scripts.run redo     /path/to/task_folder/process/history/<file>.json
python -m scripts.run dedupe   /path/to/task_folder --action report
python -m scripts.run doctor   /path/to/task_folder        # 只读诊断：结构/散落文件/广播新鲜度
python -m scripts.run broadcast /path/to/task_folder --ai   # AI 摘要（默认本地模式）
```

输出示例：

```
Root: /path/to/task_folder
mode: full
organize: done
verification: passed
history: wrote 20261012_191444_history.json
```

看到 `verification: passed` 时，三层结构已经可以安全使用；出现 `verification: failed` 时系统已自动回滚，修复问题后重试。

### 稳定状态下的文件流向

```
你建好文件夹，把材料放进去
        |
        v
   +---------+      +-------------------------------------------+
   |  init   |----->| material/initial/<你的文件，原封不动>      |
   +---------+      +-------------------------------------------+
        |
        v  （之后随着工作推进）
   organize --mode=quick|incremental|full
        |
        +--> AI 自己的产出 .................... process/
        +--> 含 final / deliverable ............ results/
        +--> mark-downloaded 后再整理 ......... material/downloaded/
        |
        v
   index     （需要交接报告时）
   snapshot  （任何危险操作之前）
```

目标是让文件夹在整个任务里尽量保持整齐，而不是等到最后才整理一次：骨架只建一次，之后随手把东西放对位置。

### 分步调用（作为 Python 库使用）

```python
from pathlib import Path
from scripts import snapshot, organize, verify, index_md, index_xlsx, rollback, utils

root = Path("/path/to/task_folder").resolve()

before = snapshot.make_snapshot(root, phase="before")
session = utils.OrganizeSession(root=root)
organize.organize_folder(root, session=session)

after = snapshot.make_snapshot(root, phase="after")
vres = verify.verify(root, session=session, before=before, after=after)

if not vres.passed:
    rollback.rollback(root, session=session)   # 校验失败 -> 回滚
else:
    index_md.write_index_md(root)
    index_xlsx.write_index_xlsx(root)
```

---

## 测试与覆盖率

```bash
pytest                                            # 运行全部测试
pytest --cov=scripts --cov-report=term-missing    # 带覆盖率报告
```

当前测试套件共 340 个用例，覆盖率约 88%（目标 >= 80%）。

---

## 项目结构

```
task-organizer/
+---- SKILL.md              # 技能入口（YAML 元数据 + 执行指南）
+---- README.md
+---- README_zh.md          # 中文镜像
+---- LICENSE               # MIT
+---- CHANGELOG.md
+---- CONTRIBUTING.md
+---- AUTHORS.md
+---- CITATION.cff
+---- .gitignore
+---- .task-organizer.yml.example   # YAML 配置示例（含 pharma 领域档案）
+---- pyproject.toml        # 打包与工具配置
+---- requirements.txt      # openpyxl, pytest, pytest-cov
+---- scripts/
|   +---- __init__.py
|   +---- run.py            # 流水线编排 + CLI（init/material/index/snapshot/undo/redo/dedupe/mark-*）
|   +---- scan.py           # 递归扫描与条目分类
|   +---- snapshot.py       # 前后快照（可选复用哈希缓存）
|   +---- organize.py       # 三层结构 + 基于来源的放置
|   +---- verify.py         # 强制 8 项一致性校验（C1-C8）
|   +---- rollback.py       # 基于日志的回滚
|   +---- dedupe.py         # 精确 + 相似查重
|   +---- history.py        # 操作历史 + Undo/Redo
|   +---- rules.py          # YAML 规则配置 + 领域档案
|   +---- init.py           # 轻量骨架 + 内容搬移
|   +---- sources.py        # 来源清单
|   +---- hashcache.py      # 增量哈希缓存
|   +---- rotate.py         # 产物轮转
|   +---- text_extract.py   # 多格式文本抽取（docx/pdf/pptx/xlsx）
|   +---- broadcast.py      # 广播中心：上下文压缩索引（_broadcast/）
|   +---- doctor.py         # 只读诊断：结构完整性 / 散落文件 / 广播新鲜度
|   +---- index_md.py       # Markdown 索引
|   +---- index_xlsx.py     # Excel 索引 (openpyxl)
|   `---- utils/            # 通用工具（路径/日志/快照/AI摘要/结构）
|       +---- __init__.py
|       `---- logger.py     # 标准库日志
+---- assets/
|   +---- index-template.md
|   `---- verification-report-template.md
`---- tests/
    +---- __init__.py
    +---- conftest.py
    +---- test_scan.py
    +---- test_snapshot.py
    +---- test_organize.py
    +---- test_verify.py
    +---- test_rollback.py
    +---- test_index.py
    +---- test_run.py
    +---- test_dedupe.py
    +---- test_history.py
    +---- test_rules.py
    +---- test_logger.py
    +---- test_init.py
    +---- test_sources.py
    +---- test_hashcache.py
    +---- test_rotate.py
    +---- test_doctor.py        # 只读诊断
    +---- test_skill_docs.py    # 文档契约
    `---- test_broadcast.py     # 广播中心：抽取、只读、幂等
```

---

## 作为 Agent 技能挂载使用

本项目是一个自包含的 Agent Skill 包。`SKILL.md` 包含 YAML 元数据（`name` / `description` / `version` / `author` / `license` / `allowed-tools`），并附带 “Execution steps” 执行指南。只需将本文件夹指向任何 AI Agent Harness。当用户的需求命中本技能适用范围时，Agent 会读取 `SKILL.md` 中的执行步骤并调用底层脚本（技能的加载取决于 Agent 对适用范围的识别，并不保证每次对话都会触发）。

给 Agent 的一条重要约定：只要在本次对话中往任务文件夹里下载或抓取了文件，就立刻调用 `mark-downloaded`（附上来源 URL）。这才是让 `downloaded/` 真正表示“AI 下载的文件”、而不是“文件名里刚好带 download 的文件”的唯一办法。

你也可以直接在 Python 中调用这些模块：

```python
from pathlib import Path
from scripts import run
result = run.run(Path("/path/to/task_folder"))
print(result.summary_lines())
```

---

## 开源协议

MIT License，详见 [LICENSE](LICENSE)。

---

## 报告问题与反馈

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report task-organizer: dedupe move 的路径穿越可读取任务文件夹之外的路径`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 命令输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
