# Content Production Factory

Content Production Factory 是一套面向 AI 和开发者的 Skill 文件包开发规范，统一约定 Skill 的架构、CLI 设计、编码风格、鉴权、打包、测试和文档格式。

本仓库提供 Skill 开发规范，并包含可直接运行的语音识别、Qwen-Audio-TTS 声音复刻与非实时合成、视觉理解和 Qwen-OCR 独立 CLI。完整开发规则见 [SKILL 开发说明](./SKILL开发说明.md)，命令用法见 [CLI 命令清单](./references/CLI.md)。

## 核心架构

一个完整 Skill 由以下部分按需组成：

- `scripts/commands/*_commands.py`：默认执行层，单个能力先封装为独立 Click 命令组
- `scripts/main.py`：条件执行层；已有统一入口或用户明确要求时才创建、注册和更新
- `scripts/<name>.exe`：条件执行层；首次生成需用户明确要求，项目已有打包产物后随代码更新自动重建
- `SKILL.md`：路由层，通过 frontmatter 的 `description` 判断是否触发，并在正文中完成场景路由
- `references/CLI.md`：命令参考层，记录真实 CLI 命令、参数和示例
- `references/*.md`：SOP 操作层，一个具体需求对应一份操作手册

项目已有 `main.py` 时，统一入口必须支持四步自发现：

```text
list-groups -> list-commands <group> -> <group> <command> --help -> execute
```

## 关键规范

- 功能正确和性能优先，代码使用直白、易读的实现
- Python 脚本必须在第三方库导入前将 stdout 强制设为 UTF-8
- 独立 CLI 使用 Click 组织命令组；已有主入口时必须同步注册，并提供 `list-groups` 和 `list-commands`
- 外部 API 密钥按需保存在 `scripts/.env`，不得提交到 Git
- 工程首次打包必须由用户明确要求；已有 `.spec` 或历史 exe 后，每次代码变化必须重新打包并验证
- CLI.md 必须根据真实帮助输出编写，每条命令完整包含用途、语法、参数表和可运行示例
- Skill 的触发条件只写在 `SKILL.md` frontmatter 的 `description` 中，正文不重复编写激活条件
- 测试新能力时只写最小脚本并停止；用户要求 CLI 时自动执行适用的 2～7 更新循环
- SOP 默认不做，主要功能和 CLI 完成后仍需用户明确要求

## 当前 CLI

- `scripts/commands/speech_recognition_commands.py`：短音频、长音频、热词、上下文增强、说话人分离、敏感词、情感和时间戳
- `scripts/commands/speech_synthesis_commands.py`：Qwen-Audio-TTS 声音复刻、音色管理和非实时语音合成
- `scripts/commands/visual_understanding_commands.py`：单图、多图、视频文件、视频帧理解，以及 Qwen-OCR 图片和 PDF 解析
- `scripts/commands/env_writer.py`：DashScope API Key 状态、设置和删除

当前使用独立 Python 入口，没有 `scripts/main.py`。工程没有打包文件，用户未明确要求首次打包时不生成 exe。

## 推荐阅读顺序

1. 阅读“Skill 是什么”，理解执行层、路由层、参考层和操作层
2. 阅读“Click 命令组封装模式与 AI 四步自发现”
3. 按“新 Skill 开发流程”在最小验证和 CLI 更新之间循环推进
4. 根据“文档编写标准”完成 SKILL.md、CLI.md 和 SOP 手册
5. 使用“验证清单”检查源码和中文输出；项目已有打包产物时必须同时检查最新 exe

## 适用环境

规范以 Windows 11 为基准，路径和终端命令均按 Windows 环境编写。可选的 PyInstaller 流程也以 Windows 为基准；Linux 和 macOS 环境需要相应调整。

## 仓库文件

| 文件 | 说明 |
|---|---|
| [README.md](./README.md) | 仓库入口和规范摘要 |
| [SKILL开发说明.md](./SKILL开发说明.md) | 完整 Skill 开发规范、模板和检查清单 |
| [SKILL.md](./SKILL.md) | 语音识别与视觉理解意图路由 |
| [references/CLI.md](./references/CLI.md) | 完整 CLI 命令、参数、限制和真实示例 |
