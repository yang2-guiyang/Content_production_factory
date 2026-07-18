# Content Production Factory

Content Production Factory 是一套面向 AI 和开发者的 Skill 文件包开发规范，统一约定 Skill 的架构、CLI 设计、编码风格、鉴权、打包、测试和文档格式。

本仓库当前提供开发规范，不是可直接运行的 Skill 成品。完整规则见 [SKILL 开发说明](./SKILL开发说明.md)。

## 核心架构

一个完整 Skill 由以下部分按需组成：

- `scripts/main.py`：默认执行层，负责实际功能
- `scripts/<name>.exe`：可选执行层，仅在用户明确要求打包时生成
- `SKILL.md`：路由层，通过 frontmatter 的 `description` 判断是否触发，并在正文中完成场景路由
- `references/CLI.md`：命令参考层，记录真实 CLI 命令、参数和示例
- `references/*.md`：SOP 操作层，一个具体需求对应一份操作手册

CLI 工具必须支持四步自发现：

```text
list-groups -> list-commands <group> -> <group> <command> --help -> execute
```

## 关键规范

- 功能正确和性能优先，代码使用直白、易读的实现
- Python 脚本必须在第三方库导入前将 stdout 强制设为 UTF-8
- 主 CLI 使用 Click 组织命令组，并提供 `list-groups` 和 `list-commands`
- 外部 API 密钥按需保存在 `scripts/.env`，不得提交到 Git
- 用户未明确要求时禁止自动打包；明确要求 Windows 免 Python 分发时，才使用 PyInstaller 生成单文件 exe
- CLI.md 必须根据真实帮助输出编写，每条命令完整包含用途、语法、参数表和可运行示例
- Skill 的触发条件只写在 `SKILL.md` frontmatter 的 `description` 中，正文不重复编写激活条件
- 开发过程逐步推进，每完成一个步骤后展示结果并确认，再进入下一步

## 推荐阅读顺序

1. 阅读“Skill 是什么”，理解执行层、路由层、参考层和操作层
2. 阅读“Click 命令组封装模式与 AI 四步自发现”
3. 按“新 Skill 开发流程”逐步实现和验证
4. 根据“文档编写标准”完成 SKILL.md、CLI.md 和 SOP 手册
5. 使用“验证清单”检查源码和中文输出；仅在用户明确要求打包或发布时检查 exe 和发布包

## 适用环境

规范以 Windows 11 为基准，路径和终端命令均按 Windows 环境编写。可选的 PyInstaller 流程也以 Windows 为基准；Linux 和 macOS 环境需要相应调整。

## 仓库文件

| 文件 | 说明 |
|---|---|
| [README.md](./README.md) | 仓库入口和规范摘要 |
| [SKILL开发说明.md](./SKILL开发说明.md) | 完整 Skill 开发规范、模板和检查清单 |
