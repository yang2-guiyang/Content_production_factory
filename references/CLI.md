# Content Production Factory CLI 命令清单

本清单基于 2026-07-18 当前源码编写。目前包含 1 个命令组和 3 个子命令，均用于管理语音识别所需的 DashScope API Key。

> 当前仍处于语音识别 Step 2 之前，尚未创建语音识别 Click 命令、统一入口 `scripts/main.py` 或 exe。语音识别命令完成后，必须重新运行全部 `--help` 并更新本清单。

## 当前命令概览

| 命令组 | 子命令 | 用途 |
|---|---|---|
| 密钥管理 | `status` | 检查 API Key 是否已配置 |
| 密钥管理 | `set` | 新增或更新 API Key |
| 密钥管理 | `remove` | 删除 API Key |

## 查看帮助

```powershell
python scripts/commands/env_writer.py --help
python scripts/commands/env_writer.py status --help
python scripts/commands/env_writer.py set --help
python scripts/commands/env_writer.py remove --help
```

## 密钥管理

### `status`

**用途：** 检查 `scripts/.env` 中是否已配置 DashScope API Key，不显示密钥内容。

**完整语法：**

```powershell
python scripts/commands/env_writer.py status
```

**参数：** 无。

**示例：**

```powershell
python scripts/commands/env_writer.py status
```

**输出示例：**

```json
{
  "configured": true
}
```

### `set`

**用途：** 新增或更新 `scripts/.env` 中的 DashScope API Key，并保留其他配置项。

**完整语法：**

```powershell
python scripts/commands/env_writer.py set <API密钥>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<API密钥>` | 阿里云百炼 DashScope API Key | 是 | 无 |

**示例：**

```powershell
python scripts/commands/env_writer.py set sk-xxx
```

**输出示例：**

```json
{
  "configured": true
}
```

> 命令行参数可能进入终端历史。不要在聊天、日志或 Git 提交中暴露真实密钥。

### `remove`

**用途：** 从 `scripts/.env` 删除 DashScope API Key，并保留其他配置项。

**完整语法：**

```powershell
python scripts/commands/env_writer.py remove
```

**参数：** 无。

**示例：**

```powershell
python scripts/commands/env_writer.py remove
```

**输出示例：**

```json
{
  "configured": false
}
```

## 语音识别封装状态

| 项目 | 当前状态 |
|---|---|
| 固定模型 | `qwen3-asr-flash` |
| 最小 API 验证 | 已完成 |
| Click 命令 | 待 Step 2 创建 |
| 本地测试音频 | `FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3` |
| 统一入口 | 待 Step 4 创建 |
| Windows exe | 待 Step 5 创建 |

语音识别 Click 命令尚未实现，因此本清单不提前虚构命令名称、参数或示例。进入 Step 2 后，以实际源码和 `--help` 输出补充完整命令说明。
