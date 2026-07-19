# Content Production Factory

Content Production Factory 是基于阿里云百炼的内容生产 Skill 和独立 CLI 工具集，覆盖文件上传与 URL 管理、语音识别、声音复刻、语音合成、视觉理解和 Qwen-OCR。

项目目前通过 `scripts/main.py` 统一提供 5 个命令组、25 个子命令，同时保留原有独立入口。所有模型命令默认使用当前已验证的最高质量参数；只有明确指定时才切换到 Flash、关闭思考或降低图像分辨率。

## 能力概览

| 能力 | 主要功能 | 默认模型 |
|---|---|---|
| 文件管理 | 多文件上传、签名 URL 获取、文件详情、分页列表和批量删除 | 百炼 Files API，默认 `file-extract` |
| 语音识别 | Qwen 上下文和语言增强、12 小时长音频、SRT、情感、时间戳、热词、说话人分离、敏感词过滤 | 按场景使用 `qwen3-asr-flash-2026-02-10`、`qwen3-asr-flash-filetrans`、`fun-asr` |
| 声音复刻 | 使用本地 WAV、MP3、M4A 或公网 URL 创建、查询、列出和删除自定义音色 | `qwen-audio-3.0-tts-plus` |
| 语音合成 | 使用系统音色或复刻音色生成 WAV、MP3、PCM，支持声音指令、情感和拟声标签 | `qwen-audio-3.0-tts-plus` |
| 视觉理解 | 单图、多图、视频、连续视频帧、视觉问答、物体定位和复杂推理 | `qwen3.7-plus` |
| Qwen-OCR | 文字定位、票据证照抽取、表格、文档、公式、多语言识别和 PDF 解析 | `qwen3.5-ocr` |

## 快速开始

### 1. 安装依赖

```powershell
python -m pip install -U click dashscope requests
```

### 2. 配置 API Key

```powershell
python scripts/main.py key set "sk-你的百炼API密钥"
python scripts/main.py key status
```

密钥保存在 `scripts/.env`，该文件已被 Git 忽略。CLI 不会在状态命令中显示密钥内容。

### 3. 查看命令

```powershell
python scripts/main.py --help
python scripts/main.py file --help
python scripts/main.py speech --help
python scripts/main.py tts --help
python scripts/main.py visual --help
python scripts/main.py key --help
```

完整参数、限制和真实输出见 [CLI 命令清单](./references/CLI.md)。

## 最高质量默认值

| 命令类型 | 默认配置 | 明确降档方式 |
|---|---|---|
| 短音频识别 | 最新快照 `qwen3-asr-flash-2026-02-10`，支持 System Context、语言和 ITN | 不提供本地模型降档 |
| 声音复刻与合成 | `qwen-audio-3.0-tts-plus`，复刻样本最多保留 20 秒 | `--model qwen-audio-3.0-tts-flash` |
| 图片理解 | `qwen3.7-plus`、思考模式、高分辨率、8192 Token | `--no-thinking`、`--standard-resolution` 或较小的 `--max-tokens` |
| 视频与帧理解 | `qwen3.7-plus`、思考模式、8192 Token | `--no-thinking` 或较小的 `--max-tokens` |
| OCR | `qwen3.5-ocr`、自动旋转矫正、8192 Token | `--no-rotate` 或较小的 `--max-tokens` |

语音识别中的 Flash 名称是官方专用模型名称，目前没有可直接替换的 Plus 档。时间戳粒度、热词、说话人分离、敏感词和 OCR 任务类型属于功能选择，不会因为最高质量策略而自动改写。

## 命令总览

### 文件管理

统一入口：`python scripts/main.py file`

| 命令 | 用途 |
|---|---|
| `upload` | 上传一个或多个本地文件，返回 `file_id` 和当前签名 URL |
| `get` | 查询文件属性并刷新签名 URL |
| `list` | 分页列举有效文件 |
| `delete` | 删除一个或多个文件并释放配额 |

### 语音识别

统一入口：`python scripts/main.py speech`

| 命令 | 用途 |
|---|---|
| `recognize` | 使用 Qwen 最新快照识别本地短音频，支持背景实体、语言和 ITN |
| `recognize-context` | 使用上下文增强识别准确率 |
| `transcribe-long` | 转写最长 12 小时的公网音频，支持语言、ITN、多音轨和 SRT |
| `transcribe-advanced` | 组合热词、说话人分离、语言提示和敏感词过滤 |
| `hotword-create` | 创建 Fun-ASR 热词表 |
| `hotword-status` | 查询热词表 |
| `hotword-list` | 列出热词表 |
| `hotword-delete` | 删除热词表 |

### 声音复刻与合成

统一入口：`python scripts/main.py tts`

| 命令 | 用途 |
|---|---|
| `voice-clone-create` | 从本地文件或公网 URL 创建复刻音色 |
| `voice-clone-list` | 列出复刻音色 |
| `voice-clone-status` | 查询音色详情和绑定模型 |
| `voice-clone-delete` | 删除音色并释放配额 |
| `synthesize` | 非实时语音合成并下载结果文件 |

### 视觉理解与 OCR

统一入口：`python scripts/main.py visual`

| 命令 | 用途 |
|---|---|
| `analyze-images` | 单图、多图、视觉问答、定位和复杂推理 |
| `analyze-video` | 视频摘要、动作分析和事件定位 |
| `analyze-frames` | 把至少四张连续图片作为视频帧分析 |
| `ocr` | 图片文字、位置、表格、文档、公式和结构化字段提取 |
| `ocr-pdf` | 直接解析不超过 50 页、100 MB 的公网 PDF |

### 密钥管理

统一入口：`python scripts/main.py key`

| 命令 | 用途 |
|---|---|
| `status` | 检查 API Key 是否已配置 |
| `set` | 写入或更新 API Key |
| `remove` | 删除 API Key |

## 常用示例

### 多文件上传并取得 URL

```powershell
python scripts/main.py file upload "runtime/inputs/audio.mp3" "runtime/inputs/image.jpg" --description "内容生产素材"
```

默认使用 `file-extract`。命令会为每个成功上传的文件返回 `file_id` 和签名 URL；长期复用时保存 `file_id`，任务开始前使用 `file get <文件ID>` 获取当前 URL。

### 使用背景实体增强本地音频识别

```powershell
python scripts/main.py speech recognize "runtime/inputs/audio.mp3" --language zh --context "背景和实体词：年下、时下、财富、贫穷、贯穿一生。"
```

### 获取长音频字级时间戳

```powershell
python scripts/main.py speech transcribe-long "https://example.com/audio.mp3" --language zh --timestamp-level word --output-srt "runtime/outputs/audio.srt"
```

### 创建最高质量复刻音色

```powershell
python scripts/main.py tts voice-clone-create "runtime/inputs/voice.mp3" --prefix myvoice --language-hint zh
```

命令默认绑定 `qwen-audio-3.0-tts-plus`，返回的 `voice_id` 用于后续合成。

### 使用复刻音色生成 MP3

```powershell
python scripts/main.py tts synthesize --text "每一个好内容，都值得被认真听见。" --voice "qwen-audio-3.0-tts-plus-myvoice-音色ID" --output "runtime/outputs/narration.mp3" --format mp3
```

### 使用最高质量视觉理解

```powershell
python scripts/main.py visual analyze-images --image "runtime/inputs/image.jpg" --prompt "准确描述图片中的人物、物体和场景。"
```

默认开启思考和高分辨率。需要降低成本时显式使用 `--no-thinking --standard-resolution`。

### 票据结构化信息抽取

```powershell
python scripts/main.py visual ocr --image "runtime/inputs/ticket.jpg" --task key_information_extraction --schema-file "runtime/inputs/ticket-schema.json"
```

### PDF 文档解析

```powershell
python scripts/main.py visual ocr-pdf --pdf-url "https://example.com/document.pdf"
```

## 运行目录

```text
runtime/
├── inputs/      # 本地音频、图片、视频和 Schema 输入
└── outputs/     # 合成音频和其他运行结果
```

`runtime/` 用于本地测试与产物，不提交到 Git。

## 当前限制

- 长音频识别和云端 SRT 仍只接受 HTTP/HTTPS URL；本地文件先通过 `file upload` 上传，再把返回 URL 传给识别命令。
- 工程不再提供本地 Whisper/VAD；本地短音频由 Qwen 在线识别，字幕由 Filetrans 的云端时间戳生成。
- `ocr-pdf` 只接受 URL；本地 PDF 可先使用 `file upload` 取得签名 URL。
- 百炼文件管理目前仅在北京 Region 开放；签名 URL 不是永久地址，应保存 `file_id` 并在使用前重新查询。
- Qwen-Audio-TTS 当前封装已实测的非流式输出；SSE 流式输出需要 Workspace ID，尚未封装。
- `scripts/main.py` 是统一入口；`scripts/commands/` 下的独立入口继续保留，用于兼容和开发调试。
- 首次打包只有在用户明确要求时执行。

## 项目结构

```text
Content_production_factory/
├── README.md
├── SKILL.md
├── SKILL开发说明.md
├── references/
│   └── CLI.md
└── scripts/
    ├── main.py
    └── commands/
        ├── env_reader.py
        ├── env_writer.py
        ├── file_management_commands.py
        ├── speech_recognition_commands.py
        ├── speech_synthesis_commands.py
        └── visual_understanding_commands.py
```

## 文档

- [完整 CLI 命令、参数和验证结果](./references/CLI.md)
- [Codex Skill 路由](./SKILL.md)
- [Skill 开发说明](./SKILL开发说明.md)

## 开发约定

- 新接口或脚本测试先写最小可运行版本，不自动进入 CLI、文档或打包阶段。
- 用户明确要求封装 CLI 时，完成 Click 命令、鉴权、现有入口和 `SKILL.md`/`CLI.md` 更新。
- SOP 只在用户明确要求时编写。
- 工程没有打包文件时，不自动首次打包；已有打包产物后，代码更新需要重新打包验证。
