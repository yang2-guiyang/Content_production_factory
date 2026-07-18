# Content Production Factory CLI 命令清单

本清单基于 2026-07-18 当前源码实际运行 `--help` 的结果编写，包含 2 个命令组和 4 个子命令。命令参数、默认值和示例均以当前源码为准。

> 当前处于 Step 4 之前的源码阶段，尚未创建统一入口 `scripts/main.py` 和 exe。本清单先记录已经封装完成的命令模块；统一入口完成后需要重新运行全部 `--help` 并更新运行方式。

## AI 自发现流程（当前源码阶段）

当前没有 `list-groups` 和 `list-commands`，分别通过两个命令模块查询能力：

```text
Step 1：查看声音复刻命令组
  python scripts/commands/voice_commands.py --help

Step 2：查看声音复刻子命令
  python scripts/commands/voice_commands.py create --help

Step 3：查看密钥管理命令组
  python scripts/commands/env_writer.py --help

Step 4：查看具体密钥命令
  python scripts/commands/env_writer.py <status|set|remove> --help
```

完成 Step 4 后，自发现入口将统一为：

```text
python scripts/main.py list-groups
python scripts/main.py list-commands <命令组>
python scripts/main.py <命令组> <子命令> --help
python scripts/main.py <命令组> <子命令> [参数]
```

## 通用语法

| 写法 | 说明 | 示例 |
|---|---|---|
| `python scripts/commands/voice_commands.py <命令> [参数]` | 运行声音复刻命令 | `python scripts/commands/voice_commands.py create https://example.com/voice.wav` |
| `python scripts/commands/env_writer.py <命令> [参数]` | 运行密钥管理命令 | `python scripts/commands/env_writer.py status` |
| `<必填参数>` | 必须提供的参数 | `<音频URL>` |
| `[可选参数]` | 可省略并使用默认值 | `[--prefix narrator1]` |

## 声音复刻

### `create`

**用途：** 使用公网音频创建 Qwen-Audio-TTS 自定义音色。

**完整语法：**

```powershell
python scripts/commands/voice_commands.py create <音频URL> [--target-model <模型名称>] [--prefix <音色前缀>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频URL>` | 公网可下载的 WAV、MP3 或 M4A 音频 URL，建议使用 10～20 秒清晰人声 | 是 | — |
| `--target-model <模型名称>` | 音色绑定的 Qwen-Audio-TTS 模型；创建后不能跨模型使用 | 否 | 默认：`qwen-audio-3.0-tts-flash`<br>可选：`qwen-audio-3.0-tts-flash`、`qwen-audio-3.0-tts-plus` |
| `--prefix <音色前缀>` | 音色 ID 前缀，仅使用英文字母和数字 | 否 | 默认：`myvoice` |

**示例：**

```powershell
python scripts/commands/voice_commands.py create "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/sensevoice/rich_text_example_1.wav" --target-model qwen-audio-3.0-tts-flash --prefix narrator1
```

**输出示例：**

```json
{
  "voice_id": "qwen-audio-3.0-tts-flash-narrator1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "target_model": "qwen-audio-3.0-tts-flash",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "count": 1
  }
}
```

---

## 密钥管理

### `status`

**用途：** 查看 `scripts/.env` 中是否已经配置 DashScope API Key，不显示密钥内容。

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

---

### `set`

**用途：** 新增或更新 `scripts/.env` 中的 DashScope API Key，并保留其他配置项。

**完整语法：**

```powershell
python scripts/commands/env_writer.py set <API密钥>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<API密钥>` | 阿里云百炼 DashScope API Key | 是 | — |

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

> 命令行参数可能进入终端历史。共享设备上优先直接编辑 `scripts/.env`，不要在聊天、日志或 Git 提交中暴露真实密钥。

---

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

---

## 当前未封装能力

- 语音识别：最小 API 已验证，但 Click 命令尚未创建
- 统一入口：`scripts/main.py` 尚未创建
- AI 四步自发现：`list-groups` 和 `list-commands` 尚未创建
- Windows exe：尚未打包
