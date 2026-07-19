# Content Production Factory CLI 命令清单

本清单基于 2026-07-19 当前源码、真实 `--help` 和实际 API 调用结果编写。目前包含 3 个独立命令组和 16 个子命令。

> 当前通过三个独立 Python 入口调用 CLI。工程没有 `scripts/main.py`，按现行开发流程不需要为了统一入口而主动创建；工程也没有打包产物，用户未明确要求首次打包时不创建 exe。

## 当前命令概览

| 命令组 | 子命令 | 用途 |
|---|---|---|
| 语音识别 | `recognize` | 识别本地短音频并返回情感标注 |
| 语音识别 | `recognize-context` | 使用上下文增强识别本地短音频 |
| 语音识别 | `transcribe-long` | 异步转写公网长音频并返回时间戳和情感 |
| 语音识别 | `transcribe-advanced` | 使用热词、说话人分离和敏感词过滤转写公网音频 |
| 语音识别 | `hotword-create` | 创建 Fun-ASR 热词表 |
| 语音识别 | `hotword-status` | 查询热词表状态 |
| 语音识别 | `hotword-list` | 列出热词表 |
| 语音识别 | `hotword-delete` | 删除热词表 |
| 视觉理解 | `analyze-images` | 分析单图或多图，完成问答、OCR、定位和文档解析等任务 |
| 视觉理解 | `ocr` | 使用 Qwen-OCR 提取图片文字、位置、表格、公式或结构化字段 |
| 视觉理解 | `ocr-pdf` | 使用 Qwen-OCR 直接解析公网 PDF 文档 |
| 视觉理解 | `analyze-video` | 分析本地或公网视频文件 |
| 视觉理解 | `analyze-frames` | 把至少四张连续图片作为视频帧分析 |
| 密钥管理 | `status` | 检查 API Key 是否已配置 |
| 密钥管理 | `set` | 新增或更新 API Key |
| 密钥管理 | `remove` | 删除 API Key |

## 查看帮助

```powershell
python scripts/commands/speech_recognition_commands.py --help
python scripts/commands/speech_recognition_commands.py <子命令> --help
python scripts/commands/visual_understanding_commands.py --help
python scripts/commands/visual_understanding_commands.py <子命令> --help
python scripts/commands/env_writer.py --help
python scripts/commands/env_writer.py <status|set|remove> --help
```

> 当前源码的部分命令简介仍包含尚不存在的 `python scripts/main.py ...` 示例。统一入口创建前，请以本清单中的独立脚本命令为准。

## 当前适用范围与已知限制

| 项目 | 当前行为 | 尚未通过 CLI 暴露的能力 |
|---|---|---|
| 本地短音频 | `recognize` 和 `recognize-context` 接受本地文件 | `recognize` 未主动检查 10 MB、5 分钟上限 |
| 长音频 | `transcribe-long` 和 `transcribe-advanced` 只接受公网 HTTP/HTTPS URL | 不能直接提交本地长音频，也没有 OSS 上传命令 |
| 语言与 ITN | 短音频自动识别语言；高级转写支持重复传入 `--language-hint` | `recognize` 和 `transcribe-long` 不能指定语言，`enable_itn` 固定为 `false` |
| 音频通道 | 长音频和高级转写固定处理 `channel_id=[0]` | 不能选择其他通道或执行多通道转写 |
| 上下文增强 | 支持一段不超过 400 字符的用户上下文 | 不支持多轮 `user` / `assistant` 上下文消息 |
| 热词 | 支持创建、查询、列表、删除和在转写时使用热词表 | 同一条创建命令中的全部热词共用一个权重和语言，不能逐词设置 |
| 流式与生产回调 | 当前使用同步响应或异步轮询 | 未封装流式输出、EventBridge 回调和批量任务调度 |
| 专用 OCR | 图片支持七种内置任务、旋转矫正、像素阈值和结构化结果；PDF 支持直接解析 | PDF 只接受公网 URL，不支持直接上传本地 PDF；未封装多轮 OCR 对话和 Batch API |
| Skill 路由 | 根 `SKILL.md` 根据语音或视觉任务选择命令 | 详细参数统一从本清单读取 |

## 语音识别

### `recognize`

**用途：** 使用固定模型 `qwen3-asr-flash` 识别不超过 5 分钟、10 MB 的本地音频，同时返回文本、情感和语言标注。

**当前限制：** 模型自动判断语言，CLI 不能指定语言；ITN 固定关闭；代码尚未在提交前主动检查 10 MB 和 5 分钟限制，超限文件由接口返回错误。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py recognize <音频文件>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频文件>` | 本地音频文件路径 | 是 | 支持 `.aac`、`.flac`、`.m4a`、`.mp3`、`.ogg`、`.wav` |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py recognize "runtime/inputs/FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3"
```

**输出示例：**

```json
{
  "text": "你的年下如果和你的时下相合……",
  "annotations": [
    {
      "emotion": "neutral",
      "language": "zh",
      "type": "audio_info"
    }
  ],
  "model": "qwen3-asr-flash",
  "audio_file": "C:\\path\\to\\audio.mp3",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "seconds": 17,
    "total_tokens": 504
  }
}
```

### `recognize-context`

**用途：** 使用固定模型 `fun-asr-flash-2026-06-15` 和领域词汇或前文增强本地短音频识别准确率。

**当前限制：** 只支持一段 `user` 上下文文本，不支持多轮 `user` / `assistant` 上下文消息。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py recognize-context <音频文件> --context <上下文文本> --sample-rate <采样率Hz>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频文件>` | 本地音频文件路径 | 是 | 支持当前短音频格式 |
| `--context <上下文文本>` | 音频中可能出现的领域词汇或前文 | 是 | 最多 400 个字符 |
| `--sample-rate <采样率Hz>` | 音频真实采样率 | 是 | 不低于 8000，如 `16000`、`44100` |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py recognize-context "runtime/inputs/FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3" --context "年下 时下 财富 贫穷" --sample-rate 44100
```

**输出示例：**

```json
{
  "text": "你的年下如果和你的时下相合……",
  "context": "年下 时下 财富 贫穷",
  "model": "fun-asr-flash-2026-06-15",
  "audio_file": "C:\\path\\to\\audio.mp3",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "duration": 18
  }
}
```

### `transcribe-long`

**用途：** 使用固定模型 `qwen3-asr-flash-filetrans` 异步转写公网音频 URL，支持最长 12 小时、2 GB，并返回句级或字级时间戳和情感字段。

**当前限制：** 只接受公网 URL，不能直接传入本地长音频；固定处理通道 `0`，ITN 固定关闭，不能通过 CLI 指定语言。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py transcribe-long <音频URL> [--timestamp-level <sentence|word>] [--timeout <秒>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频URL>` | 公网可下载的音频 URL | 是 | 必须以 `http://` 或 `https://` 开头 |
| `--timestamp-level <sentence|word>` | 时间戳级别 | 否 | 默认 `sentence`；可选 `sentence`、`word` |
| `--timeout <秒>` | 等待异步任务完成的最长时间 | 否 | 默认 `1800`，最小 `60` |

**句级时间戳示例：**

```powershell
python scripts/commands/speech_recognition_commands.py transcribe-long "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3" --timestamp-level sentence --timeout 120
```

**字级时间戳示例：**

```powershell
python scripts/commands/speech_recognition_commands.py transcribe-long "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3" --timestamp-level word --timeout 120
```

**输出示例：**

```json
{
  "model": "qwen3-asr-flash-filetrans",
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "timestamp_level": "word",
  "usage": {
    "seconds": 1
  },
  "transcription": {
    "transcripts": [
      {
        "text": "欢迎使用阿里云。",
        "sentences": [
          {
            "begin_time": 0,
            "end_time": 1440,
            "emotion": "neutral",
            "words": [
              {
                "begin_time": 0,
                "end_time": 160,
                "text": "欢"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### `hotword-create`

**用途：** 创建固定绑定 `fun-asr` 的热词表，供 `transcribe-advanced --vocabulary-id` 使用。

**当前限制：** 一次命令中的全部 `--word` 共用同一个 `--weight` 和 `--language`，不能为每个热词分别设置权重或语言。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-create <前缀> --word <热词> [--word <热词> ...] [--weight <1-5>] [--language <语言代码>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<前缀>` | 热词表 ID 前缀 | 是 | 不超过 10 个字符 |
| `--word <热词>` | 加入热词，可重复传入 | 是 | 每个表最多 500 个热词 |
| `--weight <1-5>` | 全部热词使用的权重 | 否 | 默认 `4`；范围 `1`～`5` |
| `--language <语言代码>` | 热词语言代码 | 否 | 默认 `zh` |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-create codexadv --word "语音实验室" --word "阿里云百炼" --weight 4 --language zh
```

**输出示例：**

```json
{
  "vocabulary_id": "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "target_model": "fun-asr",
  "status": "OK",
  "vocabulary": [
    {
      "text": "语音实验室",
      "weight": 4,
      "lang": "zh"
    }
  ]
}
```

### `hotword-status`

**用途：** 查询一个热词表的状态和内容。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-status <热词表ID>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<热词表ID>` | `hotword-create` 返回的 ID | 是 | 无 |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-status "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**输出示例：**

```json
{
  "vocabulary_id": "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "OK",
  "target_model": "fun-asr"
}
```

### `hotword-list`

**用途：** 列出当前 API Key 账号中的热词表，可按前缀过滤。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-list [--prefix <前缀>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--prefix <前缀>` | 只列出指定前缀的热词表 | 否 | 默认列出全部 |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-list --prefix codexadv
```

**输出示例：**

```json
{
  "count": 0,
  "items": []
}
```

### `hotword-delete`

**用途：** 删除不再使用的热词表，释放账号热词表配额。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-delete <热词表ID>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<热词表ID>` | 要删除的热词表 ID | 是 | 无 |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py hotword-delete "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**输出示例：**

```json
{
  "vocabulary_id": "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "deleted": true
}
```

### `transcribe-advanced`

**用途：** 使用固定模型 `fun-asr` 对公网音频执行异步转写，可组合使用热词、说话人分离、敏感词替换或移除、语言提示。完整结果固定包含 Fun-ASR 的句级和词级时间戳。

**当前限制：** 只接受公网 URL 并固定处理通道 `0`；Fun-ASR 不支持情感识别，情感字段应使用 `recognize` 或 `transcribe-long` 获取。

**完整语法：**

```powershell
python scripts/commands/speech_recognition_commands.py transcribe-advanced <音频URL> [--vocabulary-id <热词表ID>] [--diarization|--no-diarization] [--filter-signed <敏感词>] [--filter-empty <敏感词>] [--system-sensitive-filter|--no-system-sensitive-filter] [--language-hint <语言代码>] [--timeout <秒>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频URL>` | 公网可下载的音频 URL | 是 | 必须以 `http://` 或 `https://` 开头 |
| `--vocabulary-id <热词表ID>` | 使用指定 Fun-ASR 热词表 | 否 | 默认不使用热词，可由 `hotword-create` 创建 |
| `--diarization` / `--no-diarization` | 是否启用说话人分离 | 否 | 默认 `--no-diarization` |
| `--filter-signed <敏感词>` | 替换为等长星号，可重复传入 | 否 | 默认无自定义替换词 |
| `--filter-empty <敏感词>` | 从结果中移除，可重复传入 | 否 | 默认无自定义移除词 |
| `--system-sensitive-filter` / `--no-system-sensitive-filter` | 是否使用系统预置敏感词表 | 否 | 默认启用 |
| `--language-hint <语言代码>` | 指定音频语种，可重复传入 | 否 | 默认由模型判断 |
| `--timeout <秒>` | 等待异步任务完成的最长时间 | 否 | 默认 `1800`，最小 `60` |

**示例：**

```powershell
python scripts/commands/speech_recognition_commands.py transcribe-advanced "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav" --vocabulary-id "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" --diarization --filter-signed "阿里巴巴" --no-system-sensitive-filter --language-hint zh --language-hint en --timeout 120
```

**输出示例：**

```json
{
  "model": "fun-asr",
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "options": {
    "vocabulary_id": "vocab-codexadv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "diarization": true,
    "filter_signed": ["阿里巴巴"],
    "system_sensitive_filter": false,
    "language_hints": ["zh", "en"]
  },
  "transcription": {
    "transcripts": [
      {
        "text": "Hello world，这里是****语音实验室。",
        "sentences": [
          {
            "speaker_id": 0,
            "begin_time": 760,
            "end_time": 3520,
            "text": "Hello world，这里是****语音实验室。",
            "words": [
              {
                "begin_time": 760,
                "end_time": 1040,
                "text": "Hello"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

## 视觉理解

通用视觉理解使用默认模型 `qwen3.7-plus`；专用文字提取使用默认模型 `qwen3.5-ocr`。普通描述、问答、定位和视频任务使用 `analyze-*` 命令，需要文字位置、结构化字段、表格、公式、多语言文字或 PDF 布局时优先使用 `ocr` 或 `ocr-pdf`。

### `analyze-images`

**用途：** 分析一张或多张本地图片、Data URL 或公网图片 URL。

**完整语法：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image <图片路径或URL> [--image <图片路径或URL> ...] --prompt <问题或任务> [--model <模型名称>] [--thinking|--no-thinking] [--thinking-budget <Token数>] [--high-resolution|--standard-resolution] [--min-pixels <像素数>] [--max-pixels <像素数>] [--max-tokens <Token数>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--image <图片路径或URL>` | 输入图片，可重复传入多张 | 是 | 本地文件、Data URL、HTTP/HTTPS URL |
| `--prompt <问题或任务>` | 描述模型需要完成的视觉任务 | 是 | 任意文本 |
| `--model <模型名称>` | 使用的百炼视觉模型 | 否 | 默认 `qwen3.7-plus` |
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认 `--no-thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--high-resolution` / `--standard-resolution` | 是否启用高分辨率图像模式 | 否 | 默认标准分辨率 |
| `--min-pixels <像素数>` | 每张图片的最小像素阈值 | 否 | 正整数 |
| `--max-pixels <像素数>` | 标准分辨率模式的最大像素阈值 | 否 | 正整数；不能与 `--high-resolution` 同时使用 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `2048` |

**支持的本地图像格式：** BMP、HEIC、JPEG、PNG、TIFF、WEBP。本地图片不能超过 10 MB。

**单图描述示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/visual-dog-and-girl.jpeg" --prompt "请只用一句中文描述图片。"
```

**多图比较示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/a.jpg" --image "runtime/inputs/b.jpg" --prompt "分别描述两张图片并说明主要区别。"
```

**OCR 和信息抽取示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/invoice.png" --prompt "提取发票代码、发票号码和金额，以 JSON 输出。" --high-resolution
```

**物体定位示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/food.jpg" --prompt "检测所有食物，以 JSON 输出 label 和 bbox 坐标。"
```

**文档解析示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/document.png" --prompt "qwenvl markdown"
```

**思考模式示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-images --image "runtime/inputs/question.png" --prompt "分步骤解答图片中的题目。" --thinking --thinking-budget 4096
```

**输出示例：**

```json
{
  "text": "在夕阳金色的海滩上，一位年轻女子微笑着与她的拉布拉多犬握手互动。",
  "reasoning_content": "",
  "model": "qwen3.7-plus",
  "thinking": false,
  "high_resolution": false,
  "finish_reason": "stop",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "input_tokens": 2526,
    "output_tokens": 25,
    "image_tokens": 2503
  },
  "input_type": "images",
  "inputs": [
    "file://C:/path/to/image.jpeg"
  ],
  "prompt": "请只用一句中文描述图片。"
}
```

### `ocr`

**用途：** 使用 Qwen-OCR 识别一张或多张本地图片、Data URL 或公网图片 URL，并保留专用的 `ocr_result` 结构化结果。

**完整语法：**

```powershell
python scripts/commands/visual_understanding_commands.py ocr --image <图片路径或URL> [--image <图片路径或URL> ...] [--task <任务>] [--prompt <补充要求>] [--schema <JSON对象>|--schema-file <JSON文件>] [--rotate|--no-rotate] [--min-pixels <像素数>] [--max-pixels <像素数>] [--model <模型名称>] [--max-tokens <Token数>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--image <图片路径或URL>` | 输入图片，可重复传入多张 | 是 | 本地文件、Data URL、HTTP/HTTPS URL |
| `--task <任务>` | 使用 Qwen-OCR 内置任务 | 否 | 默认 `text_recognition`；见下表 |
| `--prompt <补充要求>` | 在内置任务之外增加用户要求 | 否 | 任意文本 |
| `--schema <JSON对象>` | 直接传入信息抽取字段模板 | 否 | 仅限 `key_information_extraction` |
| `--schema-file <JSON文件>` | 从 UTF-8 JSON 文件读取字段模板 | 否 | 仅限 `key_information_extraction`；不能与 `--schema` 同时使用 |
| `--rotate` / `--no-rotate` | 是否自动矫正倾斜或旋转图像 | 否 | 默认 `--no-rotate` |
| `--min-pixels <像素数>` | 小图放大后的最小像素阈值 | 否 | 正整数 |
| `--max-pixels <像素数>` | 大图缩小后的最大像素阈值 | 否 | 正整数 |
| `--model <模型名称>` | 使用的 Qwen-OCR 模型 | 否 | 默认 `qwen3.5-ocr` |
| `--max-tokens <Token数>` | 回复最大 Token 数 | 否 | 默认 `8192` |

**内置任务：**

| 任务值 | 能力 | 主要输出 |
|---|---|---|
| `advanced_recognition` | 高精文字识别和文字行定位 | `ocr_result.words_info`，含文本、四点坐标和旋转矩形 |
| `key_information_extraction` | 票据、证照、表单结构化信息抽取 | `ocr_result.kv_result`；Schema 最多三层嵌套 |
| `table_parsing` | 表格解析 | HTML 表格文本 |
| `document_parsing` | 扫描文档版面解析 | LaTeX 文本或结构化布局 |
| `formula_recognition` | 数学公式识别 | LaTeX 公式 |
| `text_recognition` | 中英文通用文字识别 | 纯文本 |
| `multi_lan` | 小语种文字识别 | 纯文本；支持阿、法、德、意、日、韩、葡、俄、西、越等语言 |

**结构化票据抽取示例：**

```powershell
python scripts/commands/visual_understanding_commands.py ocr --image "runtime/inputs/ticket.jpg" --task key_information_extraction --schema-file "runtime/inputs/ticket-schema.json" --rotate
```

`ticket-schema.json` 示例：

```json
{
  "乘车日期": "年-月-日",
  "车次": "车次编号",
  "票价": "含货币符号的金额"
}
```

**其他任务示例：**

```powershell
python scripts/commands/visual_understanding_commands.py ocr --image "runtime/inputs/page.png" --task advanced_recognition --rotate
python scripts/commands/visual_understanding_commands.py ocr --image "runtime/inputs/table.png" --task table_parsing
python scripts/commands/visual_understanding_commands.py ocr --image "runtime/inputs/formula.png" --task formula_recognition
python scripts/commands/visual_understanding_commands.py ocr --image "runtime/inputs/multilingual.png" --task multi_lan
```

**真实输出结构：**

```json
{
  "text": "```json\n{\"车次\": \"G1948\", \"票价\": \"337.50\"}\n```",
  "ocr_result": {
    "kv_result": {
      "车次": "G1948",
      "票价": "337.50"
    }
  },
  "model": "qwen3.5-ocr",
  "task": "key_information_extraction",
  "finish_reason": "stop",
  "rotate": true
}
```

**图像限制：** 本地或公网单图使用 `qwen3.5-ocr` 时不能超过 20 MB；Data URL 编码后不能超过 10 MB。宽和高均须大于 10 像素，宽高比不能超过 200:1，建议总像素不超过 1568 万。4K 以下支持 BMP、HEIC、JPEG、PNG、TIFF、WEBP；4K 到 8K 仅支持 JPEG、JPG、PNG。

### `ocr-pdf`

**用途：** 通过 Responses API 把公网 PDF 直接交给 `qwen3.5-ocr` 做文档解析，无需手工拆页，并返回文本和 `ocr_result.layouts`。

**完整语法：**

```powershell
python scripts/commands/visual_understanding_commands.py ocr-pdf --pdf-url <公网PDF URL> [--model <模型名称>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--pdf-url <公网PDF URL>` | 可由百炼服务访问的 PDF URL | 是 | `http://` 或 `https://`；最大 50 页且不超过 100 MB |
| `--model <模型名称>` | 支持 Responses API 的 Qwen-OCR 模型 | 否 | 默认 `qwen3.5-ocr` |

**示例：**

```powershell
python scripts/commands/visual_understanding_commands.py ocr-pdf --pdf-url "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
```

**真实输出结构：**

```json
{
  "text": "# Dummy PDF file",
  "ocr_result": {
    "layouts": [
      {
        "pageNum": 0,
        "type": "title",
        "text": "Dummy PDF file",
        "pos": [
          {"x": 128, "y": 159},
          {"x": 413, "y": 159}
        ]
      }
    ]
  },
  "model": "qwen3.5-ocr",
  "task": "document_parsing",
  "status": "completed"
}
```

> 当前 `ocr-pdf` 只接受公网 URL，不负责把本地 PDF 上传到 OSS。PDF 直接解析仅适用于 `qwen3.5-ocr` 及之后支持 Responses API 的模型。

### `analyze-video`

**用途：** 分析一个本地或公网视频文件，生成摘要、动作描述、事件定位或提示词要求的时间戳结果。模型只理解视频画面，不理解视频音轨。

**完整语法：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-video --video <视频路径或URL> --prompt <问题或任务> [--fps <0.1-10>] [--max-frames <帧数>] [--model <模型名称>] [--thinking|--no-thinking] [--thinking-budget <Token数>] [--max-tokens <Token数>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--video <视频路径或URL>` | 输入一个视频文件 | 是 | 本地文件、Data URL、HTTP/HTTPS URL |
| `--prompt <问题或任务>` | 视频分析要求 | 是 | 任意文本 |
| `--fps <0.1-10>` | 每秒抽取的视频帧数 | 否 | 默认 `2.0` |
| `--max-frames <帧数>` | 视频最多抽取帧数 | 否 | 正整数 |
| `--model <模型名称>` | 使用的百炼视觉模型 | 否 | 默认 `qwen3.7-plus` |
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认 `--no-thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `2048` |

**支持的本地视频格式：** AVI、FLV、MKV、MOV、MP4、WMV。本地视频不能超过 100 MB。

**视频摘要示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-video --video "runtime/inputs/video.mp4" --prompt "用三句话概括视频内容。" --fps 1 --max-frames 120
```

**事件时间戳示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-video --video "runtime/inputs/video.mp4" --prompt "以 JSON 输出人物动作的 start_time、end_time 和 event，时间使用 HH:mm:ss。" --fps 2
```

**输出示例：**

```json
{
  "text": "视频中的人物先面对镜头微笑，随后开心地大笑。",
  "model": "qwen3.7-plus",
  "input_type": "video",
  "inputs": [
    "https://example.com/video.mp4"
  ],
  "fps": 1.0,
  "max_frames": 20,
  "finish_reason": "stop"
}
```

### `analyze-frames`

**用途：** 把已经按时间顺序抽取的至少四张图片作为视频帧输入，分析事件顺序和动作变化。

**完整语法：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-frames --frame <帧图片路径或URL> --frame <帧图片路径或URL> --frame <帧图片路径或URL> --frame <帧图片路径或URL> [--frame <帧图片路径或URL> ...] --prompt <问题或任务> [--fps <0.1-10>] [--model <模型名称>] [--thinking|--no-thinking] [--thinking-budget <Token数>] [--max-tokens <Token数>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--frame <帧图片路径或URL>` | 按时间顺序输入视频帧 | 是 | 至少重复四次 |
| `--prompt <问题或任务>` | 帧序列分析要求 | 是 | 任意文本 |
| `--fps <0.1-10>` | 帧序列从原视频抽取时的帧率 | 否 | 默认 `2.0` |
| `--model <模型名称>` | 使用的百炼视觉模型 | 否 | 默认 `qwen3.7-plus` |
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认 `--no-thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `2048` |

**示例：**

```powershell
python scripts/commands/visual_understanding_commands.py analyze-frames --frame "runtime/inputs/frame-001.jpg" --frame "runtime/inputs/frame-002.jpg" --frame "runtime/inputs/frame-003.jpg" --frame "runtime/inputs/frame-004.jpg" --prompt "按时间顺序描述画面中发生的事件。" --fps 2
```

**输出示例：**

```json
{
  "text": "守门员准备防守，随后向左侧扑救，但足球最终进入球门。",
  "model": "qwen3.7-plus",
  "input_type": "video_frames",
  "inputs": [
    "file://C:/path/to/frame-001.jpg",
    "file://C:/path/to/frame-002.jpg",
    "file://C:/path/to/frame-003.jpg",
    "file://C:/path/to/frame-004.jpg"
  ],
  "fps": 2.0,
  "finish_reason": "stop"
}
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

## 当前封装状态

| 项目 | 当前状态 | 2026-07-19 本轮检查 |
|---|---|---|
| 短音频文本、情感和语言 | 已封装 | 真实 CLI 通过，返回 `emotion=neutral`、`language=zh` |
| 上下文增强 | 已封装单轮文本上下文 | 真实 CLI 通过 |
| 长音频异步转写 | 已封装公网 URL | 真实 CLI 通过；历史已使用超过 5 分钟人声音频验证 |
| 句级和字级时间戳 | 已封装 | 字级时间戳真实 CLI 通过 |
| 热词创建、查询、列表和删除 | 已封装 | 本轮只执行无写操作的列表查询；创建和删除沿用历史实测结果 |
| 说话人分离 | 已封装 | 真实 CLI 通过并返回 `speaker_id` |
| 敏感词替换和移除 | 已封装 | `阿里巴巴` 替换为 `****`，`实验室` 成功移除 |
| 单图和多图理解 | 已封装 | 公网图片、本地图片上传和多图比较真实 CLI 通过 |
| 视频文件理解 | 已封装 | 公网视频真实 CLI 通过，支持 `fps` 和 `max_frames` |
| 视频帧序列理解 | 已封装 | 四张连续帧真实 CLI 通过 |
| 视觉思考模式 | 已封装 | `reasoning_content` 和最终回复真实 CLI 通过 |
| Qwen-OCR 七种图片任务 | 已封装 | `key_information_extraction` 真实 CLI 通过并返回 `ocr_result.kv_result`；其余任务完成参数和响应行为检查 |
| Qwen-OCR PDF 解析 | 已封装公网 URL | 真实 CLI 通过并返回文本与 `ocr_result.layouts` |
| 统一入口 | 未创建，当前不强制 | 使用三个独立 Python 入口 |
| 根 `SKILL.md` | 已创建 | 可按语音和视觉意图路由到本清单 |
| Windows exe | 未创建，当前不进入打包阶段 | 工程无打包文件，用户未要求首次打包 |
