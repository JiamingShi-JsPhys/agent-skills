[English](README.md) · `中文说明`

# video-tracker

> **状态：实验性 / 不稳定。** 一个自包含的视频运动数据提取工具，面向物理
> 实验。用 OpenCV CSRT 追踪 `.mp4` / `.avi` / `.mov` 视频里的 1–2 个目标，
> 遮挡时用模板匹配重新捕获，对追踪坐标做 FFT 振幅谱分析，输出标准化的
> CSV / JSON / PNG，可直接喂给下游的量纲校验器。精度因目标而异——干净的单
> 目标素材追踪良好，但重度遮挡、形变或高速目标会让结果退化。在信任任何
> 数字之前，请对照已知参考值验证输出。

## 设计原则与核心特征

- **标准化、可机读的输出。** 每次运行在 `output/` 下写出一组固定产物——
  `<video>_tracking.csv`、`<video>_summary.json`、`<video>_fft.json`、
  `<video>_spectra.png`、`<video>_report.md`——让下游工具（如量纲校验器）
  有一个稳定的契约可消费。
- **可插拔追踪后端。** 每个声明的目标建一个追踪器实例；`tracker_type`
  选择后端：`auto` 在 4.x 构建上用 OpenCV CSRT，并在 5.x（CSRT 已移除）上
  自动回退至纯 `cv2.matchTemplate`（零外部权重）；`csrt` 强制 CSRT；
  `template` 强制模板后端（所有 OpenCV 版本可用）。
- **模板匹配重捕获。** 追踪器报告丢失时，可选的模板匹配重捕获触发：把目标
  ROI 模板与 CLAHE 增强灰度帧做归一化互相关，得分超过
  `template_match_threshold` 就把 ROI 重新定位并重新初始化追踪器。
- **FFT 振幅谱。** 追踪的 1-D 坐标序列送入归一化单边 DFT（`numpy.fft`）；
  提取主正频峰值、其周期与 Top-N 谐振，并配一张 matplotlib 图展示振幅谱与
  xy 轨迹。
- **物理一致性探针（纯 numpy）。** 一个可选的配套步骤检查追踪轨迹*是否
  服从牛顿力学*，而非只与某条参考路径比对——瞬移/平滑度、守恒量、运动方程
  拟合——并按物体写出 `<video>_physics.json`。无需参考视频。
- **非破坏性。** 原始视频绝不被修改，所有输出落在 `output/` 下。
- **参数化、无头运行。** ROI、FPS 与调参旋钮都在配置（`config.yaml` 或
  JSON）里声明；没有 `selectROI` / `input` / GUI。

## 下载与安装

获取本技能有**四种**标准方式：

**方式一：per-skill 安装器（推荐）**

**Releases** 页发布**每个技能一个安装器**。下载本技能的安装器并运行——会弹
出一个原生安装窗口（和标准安装程序一样）：顶部固定显示该技能的标题与描述，
随后勾选一个或多个目标 harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）并选择安装作用域（用户或项目），点「安装」
后，确定性进度条会逐个文件跟踪拷贝过程——和标准下载器一样，显示当前正在
拷贝哪个文件、还剩多少个。窗口打开时**不预设任何选择**。选择项目作用域时，
安装器会先扫描本机上的任务文件夹（依据 `.git`、`.workbuddy`、`.claude`、
`.codex`、`.dsh`、`.agents` 等标记识别），并在下拉框
中列出供你挑选：

- **Windows**：`video-tracker-installer.exe`（仅本技能）
- **macOS / Linux**：双击 `.app` / `.sh` **尚未提供**（计划中）。在此之前，
  用下方的源码包方式（方式二）或从仓库检出的 CLI。

无需命令行：该二进制只安装本技能。若要用 CLI 驱动同样逻辑：

```bash
python install.py --skill video-tracker --scope user
```

或用一条命令安装、无需下载（Windows PowerShell）——它直接从 GitHub 抓取安装
脚本、完成安装并自清理：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/JiamingShi-JsPhys/agent-skills/main/install-web.ps1))) -Skill video-tracker
```

该命令默认把本技能安装到 **Codex**（默认框架）的用户作用域。若要选择目标
harness 框架（全称清单：Claude Code、DeepSeek Harness、OpenAI Codex 与 WorkBuddy）或作用域，可追加 `-Frameworks`（`claude`、`codex`、`dsh`、`workbuddy`）或 `-Scope`（`user` 或 `project`）。Windows PowerShell 5.1+，无需
Python——完整参数集见根 `README.md`。

**方式二：源码包**

从 **Releases** 页（或「Generate ZIP / Generate Tarball」）下载源码包并解压
——无需安装器：

```bash
unzip agent-skills-<version>.zip        # 或：tar xzf agent-skills-<version>.tar.gz
cd agent-skills/skills/video-tracker    # 本技能是独立文件夹
pip install -r requirements.txt
```

**方式三：让 Agent 自行获取**

把下面这条指令复制给你的 Agent，它会自动定位本技能、从 **Releases** 页下载
安装器并为你安装：

> 请访问 https://github.com/JiamingShi-JsPhys/agent-skills/tree/main/skills/video-tracker，阅读该目录下的 README.md，并按其说明下载或安装此技能。

你只需告诉 Agent 技能名，其余由它处理。

**方式四：克隆仓库**

```bash
git clone https://github.com/JiamingShi-JsPhys/agent-skills.git
cd agent-skills/skills/video-tracker
pip install -r requirements.txt
```

环境要求：Python 3.10+。核心依赖：`numpy`、`opencv-contrib-python-headless`。
可选：`matplotlib`（PNG 频谱图）、`pyyaml`（YAML 配置）。

## 快速上手

```bash
cd video-tracker

# 0. 探测视频容器（不追踪）
python scripts/run.py probe --config config.yaml

# 1. 追踪 + 写 CSV / JSON 到 ./output
python scripts/run.py track --config config.yaml

# 2. FFT 频谱 + PNG 图
python scripts/run.py fft --config config.yaml

# 3. Markdown 报告
python scripts/run.py report --config config.yaml

# 4. 物理一致性探针（纯 numpy，基于已有轨迹）
python scripts/run.py physics --config config.yaml --family harmonic --fx 0.5

# 5. 内置合成演示（无需视频）
python scripts/run.py demo
```

### 输出形态

```
output/
  <video>_tracking.csv      # 每目标一组列
  <video>_summary.json      # fps, n_frames, 成功率, 丢失/重捕获帧
  <video>_fft.json          # 每信号频谱 + Top-N 峰
  <video>_spectra.png       # 振幅谱 + xy 轨迹
  <video>_report.md         # 汇总以上全部
  <video>_physics.json      # 每物体物理一致性探针
  batch_summary.json        # 多视频汇总
```

### 追踪器如何保持状态

- **丢失时重捕获。** 追踪器报告丢失目标时，可选的模板匹配重捕获
  （Thomas-Kr 方案）重新定位 ROI；密集 Farneback 光流
  （`use_optical_flow_fallback`）推进最后已知中心，而非冻结。可选的亚像素
  细化（`subpixel`）用局部模板匹配 + 抛物线峰值插值把中心推到亚像素精度。
- **事件窗口追踪。** 长视频或多事件视频里，有意思的运动通常只占一小段时间段。
  配置里声明 `frame_range: [start, end]`（含两端）就把追踪扫描限制在该窗口：
  直接 seek 到 `start`，追踪到 `end` 即停。CSV 里的帧号保留源视频绝对索引
  （可回溯原片），时间轴平移到窗口起点 `time_s = 0`。这是让 1080p 多分钟视频
  快速出结果的文档化做法——只追那几秒钟的事件段，而非全片。

## 边界（Limitations）

- **不稳定 / 实验性。** 本 skill 作为预研工具发布。追踪误差因目标而异，即便
  在干净基准上也可能达数像素（杂乱素材更差）；依赖结果前请先对照已知参考值
  验证。
- **仅 CPU。** OpenCV 追踪器无 GPU 路径；分辨率保持适中，或用 `max_dim` 自动
  降采样大帧以提升速度。
- **单相机、1–2 个目标。** 重度遮挡或形变目标即使有模板回退也可能丢。
- **FFT 分辨率**受视频长度限制（越长越精细）。
- **无光流信号的丢失目标**会冻结在最后已知 bbox 并记录 `confidence = 0`——
  但只在模板重捕获与光流回退都失败时。
- **YAML 配置需 PyYAML。** JSON 配置纯标准库即可；仅视频步骤需要 OpenCV。

## 测试与覆盖率

测试套件当前覆盖 124 个用例。运行方式：

```bash
python -m pytest -q
```

目标行覆盖率 ≥ 80%，与仓库质量基线一致。依赖 OpenCV 的用例在全栈未安装时
干净跳过；FFT / CSV / JSON / 报告路径是纯 numpy，始终可跑。

## 项目结构

```
video-tracker/
  SKILL.md                  # Agent 执行指南（MANDATORY WORKFLOW）
  README.md / README_zh.md  # 文档（本文件 + 中文版）
  config.yaml               # 配置模板
  scripts/
    __init__.py
    errors.py               # 异常类型
    config.py               # 配置加载 + 校验 + TrackerParams
    tracker.py              # CSRT 循环 + 模板重捕获
    fft_analyzer.py         # numpy FFT + 峰提取 + 图
    physics.py              # 纯 numpy 物理一致性探针
    data_export.py          # CSV / JSON 写出
    report.py               # Markdown 报告
    run.py                  # CLI 入口
  tests/                    # 单元 + 文档契约测试
  assets/example_output/    # 内置演示的输出
```

## 作为 Agent 技能使用

把目录丢进任何支持 Skill 规范的 Agent 框架。当请求命中范围（实验视频、物理
运动数据提取）时，Agent 读 `SKILL.md` 并遵循其 MANDATORY WORKFLOW：

1. 确认视频路径、FPS 以及目标物体的 ROI。
2. 读取配置（`config.yaml` 或 JSON）——声明 `videos`、`objects`、`fps`、
   可选 `scale_cm_per_px` 与 CSRT `params`，以及追踪旋钮
   `tracker_type` / `subpixel` / `use_optical_flow_fallback` / `max_dim` /
   `frame_step`。
3. 探测容器：`python scripts/run.py probe --config cfg` 打印 FPS、帧数、分辨率。
4. 追踪：`python scripts/run.py track --config cfg` 写出 `<video>_tracking.csv`
   与 `<video>_summary.json`。原始视频绝不被修改。
5. 频谱：`python scripts/run.py fft --config cfg` 写出 `<video>_fft.json` +
   `<video>_spectra.png`。
6. 报告：`python scripts/run.py report --config cfg` 写出 `<video>_report.md`。
7. 若追踪质量不佳，调整 `params`（降低 `psr_threshold`、提高 `patch_ratio`）
   或切换 `tracker_type`（`auto` / `csrt` / `template`）后重跑。

常见请求形态：

- "追踪这个视频里的单摆小球，给我 x(t)，单位 cm。"
- "这段振荡的主频是多少？"
- "球被架子挡住两秒——能重新捕获吗？"
- "批量处理这三段抛体视频并汇总结果。"

本技能自包含：不导入任何兄弟技能。

## 许可证

以 MIT License 发布，见 `LICENSE`。本技能自包含：派生所用的上游参考代码
（Theddeus / Thomas-Kr 的 CSRT 脚本）不随 skill 目录分发，也不从兄弟技能或
外部 references 目录导入任何内容。

## 问题反馈

首选：在仓库的 **Issues** 页开 issue。安全漏洞报告请用下方备用渠道。

备用渠道（仅限安全漏洞报告）：发邮件到 `jiamingshi_git@outlook.com`。

- **主题**：须包含前缀 `agent-skill_report`、具体技能名与简短描述。
  - 示例：`agent-skill_report video-tracker: 模板重捕获在高速目标上漂移，报告
    静默把丢失帧标记错`
- **正文**：须包含复现步骤、期望行为、实际行为与运行环境（操作系统、Python
  版本、相关依赖）。
- 涉及「文件丢失或损坏」等严重报告时，附上前后目录树（`tree` 输出）与生成的
  `verification_report.md`。
- 提交清晰、可复现的 issue 或 PR 的贡献者，将列入下一版发布说明的致谢。
