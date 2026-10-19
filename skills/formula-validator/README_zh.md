[English](README.md) · `中文说明`
# formula-validator

> 一个跨平台、零依赖、Agent-Native 的智能体 skill——核心是用五道确定性的计算机代数检查，把一条你拿不准的公式变成「通过 / 失败 / 未知」的判定，让 AI 在不自己重推的情况下核验它不信任的推导。

<!-- TOC depthFrom:2 -->

- [formula-validator](#formula-validator)
  - [设计原则与核心特征](#设计原则与核心特征)
  - [下载与安装](#下载与安装)
  - [快速开始](#快速开始)
  - [已知局限](#已知局限)
  - [测试与覆盖率](#测试与覆盖率)
  - [项目结构](#项目结构)
  - [作为 Agent 技能挂载使用](#作为-agent-技能挂载使用)
  - [开源协议](#开源协议)
  - [报告问题与反馈](#报告问题与反馈)

<!-- END_TOC -->

formula-validator 把一条你没把握的公式变成 pass / fail / unknown 的判定。它解析输入、传播 SI 量纲、枚举极限情形、在一万组采样点上比较两侧、并试图从符号上证明恒等式——每一步都走 SymPy / NumPy / mpmath，绝不靠生成。

大模型只负责提取公式和解读报告，全部计算交给本地数学库；工具只往屏幕打印一行紧凑的 JSON 摘要，把高亮的失败点写进 Markdown 报告，这样核验不会刷屏。

## 设计原则与核心特征

- **确定性，不靠生成**：每道检查都走 SymPy / NumPy / mpmath；模型绝不自己“重推代数”。
- **触发即执行**：公式 / 推导 / 矩阵进入对话，且用户正在检查、验证、调试或准备依赖它时整套触发——不看公式怎么来的、也不看它有几行。把表达式（和可能带的单位）交给工具，不要自己重推；用 `validate` / `check` / `derive` / `matrix` 对上请求，用 Bash 运行，汇报判定而不重算。会话中再出现新公式就再跑一次对应子命令。
- **紧凑判定**：一行 JSON + 一份高亮 Markdown 报告，核验不刷屏。
- **分层校验**：五道独立检查（D1–D5），各自汇报状态，失败可定位到具体层。
- **解析 + 量纲分析**：物理感知的命名空间（`E` 始终是能量而非欧拉数），并在七个 SI 基本量纲上传播量纲向量。
- **极限枚举**：每个自由变量分别对 0、正无穷、负无穷枚举，比较两侧的行为而不只孤立地判一个发散。
- **数值蒙特卡洛采样**：一万组跨数量级的对数均匀采样，并报告最不一致的那组参数。
- **符号恒等式证明**：`左 - 右 == 0`，化简器放弃时用 40 位高精度算术交叉验证。
- **多步断点定位**：`derive` 找到第一行开始错的步骤，把“漏了量纲因子”和“系数错”“函数形式错”分开。
- **矩阵性质检查**：厄米、幺正、反厄米、正交、无迹、幂等、实谱——用于群论与量子力学。
- **双语、面向 Agent 的输出**：对话里一行 JSON 摘要，磁盘上一份高亮 Markdown 报告，输入同时支持 SymPy 与 LaTeX。

```
输入："E = m*c**2"  +  单位
        |
        v
   +---------+   D1 解析          D2 量纲
   | validate|--> D3 极限枚举      D4 数值（一万组蒙特卡洛）
   |  /check |--> D5 符号恒等式
   +---------+
        |
        v
   一行紧凑 JSON 摘要  +  _reports/latest.md（高亮失败点）
```

### 五层校验（D1–D5）——每一层查什么

一条公式由五道互相独立的检查判定。每一道都可以返回 `pass` / `fail` / `unknown` / `conflict`；整体判定取“非放弃结果里最差的那一档”。

| | 检查 | 失败意味着 |
|---|---|---|
| D1 | 解析 | 公式没读懂。此时会明确放弃，不会猜一个意思继续。 |
| D2 | 量纲 | 两侧量纲不同，或者一个加法混了不同量纲的量。 |
| D3 | 极限 | 某个变量趋于 0 或无穷时，两侧行为不一致。 |
| D4 | 数值 | 一万组蒙特卡洛随机参数下两侧不相等，并给出最差的那组参数。 |
| D5 | 符号 | `左 - 右` 化简不到 0；在双重根附近用 40 位高精度算术复核。 |

定义式 `E = m*c**2` 左边是裸符号，随机采样必然不等，所以它只做量纲检查，并告诉你想要完整检查该改写成什么形式。

**保证：**

- **不猜单位。** 单位推断默认关闭。猜错一个单位会制造一次假报错，这比承认不知道更伤信任。要用就加 `--infer`，且推断出来的单位会逐条列给你复核。
- **不把浮点噪声当错误。** 在双重根附近，两个数学上恒等的式子可以差很多个 ulp。此时会用 40 位高精度算术在最差点复核：吻合就判通过并注明原因。
- **区分「证伪」和「证不出来」。** 符号化简器化简不掉，只说明化简器能力到顶了，不代表公式错，会单独报成 `unresolved`。
- **量纲与数值打架时报 `conflict`。** 这通常是单位声明写错了，而不是公式错，所以单独成一类，提醒你先看单位。
- **解析失败就用解析器自己的提示报出来**，绝不用猜的意思去修补。

**报告怎么读：** 紧凑的 JSON 摘要给出判定、失败的 checks、以及第一个错误。完整的 Markdown 报告（`_reports/latest.md`）高亮每一处失败点；只有一行摘要看不明白时才需要打开它。

### 常见请求形状

当“检查一条公式”和“让推理可信”同时出现时，本 skill 整套触发——**即使一个字都没提“验证”**。典型请求形状：「这对吗」「看着不对」「量纲对吗」「哪一步开始错的」「这个矩阵幺正吗」。注意：触发不看任务有几步，也不依赖具体措辞——任何“正确性很重要”的符号断言都会触发它。标准动作链：

1. **把子命令对上请求。** 要确认恒等式 → `validate`；查单个量 → `check`；一条链 → `derive`；矩阵性质 → `matrix`。
2. **在要紧处补单位。** 量纲分析只有在声明了单位时才会跑；没单位，量纲检查会主动放弃。
3. **读报告。** 汇报判定；失败时给出最差点与错误类型。
4. **多步链用 `derive`** 定位断点，把“漏了一个量纲因子”和“系数错”“函数形式错”区分开。

---

---

## 下载与安装

获取本技能共有**四种**标准方式：

**方式一 —— per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、`.codex`、`.dsh`、`.agents`、等标记识别），并在下拉框中列出供你挑选，无需手动输入：
- **Windows**：`formula-validator-installer.exe`（只装本技能）
- **macOS / Linux**：双击即用的 `.app` **暂未提供**（计划中）。在此之前，请走下面的源码包方式（方式二），或从仓库检出后用 CLI。

无需命令行：该二进制只安装本技能。若要改用 CLI：

```bash
python install.py --skill formula-validator --scope user
```

或者用一行命令安装，无需下载（Windows PowerShell）——它直接从 GitHub 获取安装脚本，安装完成后自动清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill formula-validator
```

它会把**本技能**装进 **Codex**（默认框架）的用户作用域。要选择框架或作用域，加上 `-Frameworks`（`workbuddy`、`claude`、`codex`、`dsh`）或 `-Scope`（`user` 或 `project`）。需要 Windows PowerShell 5.1+，无需 Python——完整参数说明见根目录的 `README.md`。

**方式二 —— 源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包，解压即用，无需安装器：

```bash
unzip js_agent_skills-<version>.zip        # 或: tar xzf js_agent_skills-<version>.tar.gz
cd js_agent_skills/formula-validator    # 本技能就是顶层各自一个文件夹
pip install -r requirements.txt
```

**方式三 —— 让 Agent 自行获取**

把下面这段指令复制给 Agent，它会自动定位本技能、从 **Releases** 页下载安装器并替你装好：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/formula-validator ，阅读该文件夹下的 `README.md`，并按照其中的说明下载或安装本技能。

你只需要把技能名告诉 Agent，剩下的交给它。

**方式四 —— 克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/formula-validator
pip install -r requirements.txt
```

环境要求：Python 3.10+。`sympy` `numpy` `scipy` `mpmath` 均为必需依赖（均不属于标准库）。`scipy` 仅在遇到 NumPy 不支持的特殊函数（`erf`、`gamma`、`besselj`、`zeta`）时按需导入。也可挂成 MCP 服务器，见 `mcp_server/README.md`，不需要额外装 `mcp` 包。

---

## 快速开始

```bash
cd agent-skills/skills/formula-validator

# 0. （可选）验证一条恒等式
python scripts/cli.py validate --expr "1/(x*(1+x)) = 1/x - 1/(1+x)"

# 1. 带单位核验（量纲检查会跑）
python scripts/cli.py validate --expr "E = m*c**2" --units E=J --units m=kg --units c=m/s

# 2. 只检查单个结果
python scripts/cli.py check --expr "hbar**2*k**2/(2*m)" --units hbar=J*s --units k=1/m

# 3. 定位多步推导的第一处断点
python scripts/cli.py derive --steps "1/(1-x**2)" --steps "1/((1-x)*(1+x))" --steps "1/(1-x)"

# 4. 确认矩阵性质（厄米、幺正……）
python scripts/cli.py matrix --matrix "Matrix([[0, -I], [I, 0]])"
```

其他命令：

```bash
python scripts/cli.py validate --expr "x**2 = 2*x" --units x=m --infer
python scripts/cli.py check    --expr "p*c" --expect-zero --units p=kg*m/s --units c=m/s
python scripts/cli.py derive   --steps-file steps.txt
python scripts/cli.py matrix   --matrix-file M.txt --props hermitian,unitary,traceless
python scripts/cli.py validate --expr "f(x) = x**2" --report out.md --stdout-report
```

### 输出形态

CLI 默认只打印一行紧凑的 JSON（完整高亮报告写到 `_reports/latest.md`，可用 `--report` 改路径）：

```json
{"verdict": "fail", "failed_checks": ["dimension"],
 "first_error": "a sum mixes incompatible dimensions", ...}
```

看到 `verdict: pass` 说明公式扛住了每一道适用的检查；看到 `verdict: fail` 或 `conflict`，打开 `_reports/latest.md` 看最差点与错误类型。

### 作为 Python 库调用

```python
from scripts.core import pipeline

res = pipeline.validate_equation(
    "E = m*c**2",
    units={"E": "J", "m": "kg", "c": "m/s"},
)
print(res["verdict"], res.get("failed_checks"))
```


## 已知局限

- 数值吻合是证据，不是证明。一万组点、跨四个数量级已经是很强的证据，但错误若恰好落在未采样区域仍会漏过。
- 不声明单位时，量纲检查会主动放弃，因此一个量纲错误的公式可能通过其余检查。
- 极限检查是对比式的：两侧同样发散且比值趋于 1 的情形不会被判为错误。
- 符号证明受表达式规模限制，返回 `unresolved` 只说明化简器能力，不代表公式有误。
- LaTeX 的 `\int`、`\sum`、`\prod` 需要无歧义的积分/求和体，否则会要求改用 SymPy 语法，而不是猜一个积分域。
- 技能是否加载取决于 Agent 对适用范围的识别，不保证每次对话都触发。

---

---

## 测试与覆盖率

```bash
pytest                                            # 运行全部测试
pytest --cov=scripts --cov-report=term-missing    # 带覆盖率报告
```

当前测试套件共 246 个用例，行覆盖率约 84%（目标 >= 80%）。

---

## 项目结构

```
formula-validator/
+---- SKILL.md              # 技能入口（YAML 元数据 + 执行指南）
+---- README.md
+---- README_zh.md         # 中文镜像
+---- LICENSE               # MIT
+---- CHANGELOG.md
+---- CONTRIBUTING.md
+---- .gitignore
+---- requirements.txt      # sympy, numpy, scipy, mpmath
+---- scripts/
|   +---- __init__.py       # __version__
|   +---- cli.py            # CLI（validate / check / derive / matrix）
|   `---- core/
|       +---- __init__.py   # 核心校验引擎（不经过语言模型）
|       +---- pipeline.py   # D1-D5 编排 + 报告
|       +---- parsing.py    # SymPy + LaTeX 回退解析
|       +---- dimensions.py # 量纲分析
|       +---- limits.py     # 极限枚举
|       +---- numeric.py    # 一万组蒙特卡洛比较
|       +---- symbolic.py   # 恒等式证明 + 高精度复核
|       +---- breakpoint.py # 多步推导断点定位
|       +---- errors.py     # 判定（verdict）与故障（fault）两类异常
|       +---- matrixprops.py# 矩阵性质检查（厄米、幺正……）
|       +---- report.py     # Markdown + JSON 报告
|       `---- registry.py   # 检查注册表
+---- mcp_server/
|   +---- server.py         # 零依赖 MCP 服务器
|   +---- mcp_config.example.json
|   `---- README.md
`---- tests/
    +---- conftest.py
    +---- test_skill_docs.py   # 文档契约
    +---- test_cli_inprocess.py
    +---- test_core_direct.py
    +---- test_coverage_extra.py
    +---- test_parsing.py
    +---- test_dimensions.py
    +---- test_limits.py
    +---- test_numeric.py
    +---- test_symbolic.py
    +---- test_mcp.py
    `---- test_end_to_end.py
```

---

## 作为 Agent 技能挂载使用

本项目是一个自包含的 Agent Skill 包。`SKILL.md` 包含 YAML 元数据（`name` / `description` / `version` / `author` / `license` / `allowed-tools`），并附带 “Execution steps” 执行指南。只需将本文件夹指向任何 AI Agent Harness。当用户的需求命中本技能适用范围时，Agent 会读取 `SKILL.md` 中的执行步骤并调用底层脚本（技能的加载取决于 Agent 对适用范围的识别，并不保证每次对话都会触发）。

你也可以直接在 Python 中调用这些模块：

```python
from scripts.core import pipeline

res = pipeline.validate_equation("x = 2*x", units={"x": "m"})
print(res["verdict"])
```

或者把它跑成零依赖的 MCP 服务器：

```bash
python mcp_server/server.py
```

通信协议见 `mcp_server/README.md`。

---

## 开源协议

MIT License，详见 [LICENSE](LICENSE)。

---

## 报告问题与反馈

首选：在本仓库的 **Issues** 页面提交问题（对于安全漏洞问题的报告，使用备选方案）。

备选（仅供报告安全漏洞问题）：发送邮件至 `jiamingshi_git@outlook.com`

- **邮件主题**：必须包含前缀 `agent-skill_report`，并注明具体技能与简要问题。
  - 示例：`agent-skill_report formula-validator: 符号证明层对未加沙箱的用户可控表达式求值`
- **邮件正文**：必须包含复现步骤、预期行为、实际行为以及运行环境（操作系统、Python 版本、相关依赖安装状态）。
- 针对「文件丢失或损坏」的严重报告，请附带前后目录树结构（`tree` 命令输出）与生成的 `verification_report.md`。
- 提交清晰、可复现 Issue 或 Pull Request 的贡献者，将被列入下个版本发布说明的致谢名单。
