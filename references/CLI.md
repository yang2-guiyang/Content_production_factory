# Content Production Factory CLI 命令清单

本清单基于 2026-07-21 当前源码、真实 `--help` 和实际 API 调用结果编写。目前统一入口包含 7 个命令组和 31 个子命令。

> 首选入口是 `python scripts/main.py <命令组> <子命令>`。`scripts/commands/` 下的六个独立 Python 入口继续保留，用于兼容已有调用和开发调试。工程没有打包产物，用户未明确要求首次打包时不创建 exe。

## 全局默认质量策略

除非用户明确要求降低成本、缩短延迟或指定其他模型，否则所有命令默认使用当前已验证的最高质量档位。CLI 不会为了速度或价格自动切换到 Flash、关闭思考、降低图像分辨率或缩短声音样本。

| 能力 | 默认最高质量配置 | 明确降档方式 |
|---|---|---|
| 短音频识别 | 最新快照 `qwen3-asr-flash-2026-02-10`，支持 System Context、语言和 ITN | 不提供本地模型降档 |
| 备用上下文增强识别 | `fun-asr-flash-2026-06-15` | 仅在明确选择 Fun-ASR-Flash 时使用 |
| 长音频识别 | `qwen3-asr-flash-filetrans` 或功能完整的 `fun-asr` | 按是否需要热词、说话人分离和敏感词选择，不按价格自动切换 |
| 声音复刻与合成 | `qwen-audio-3.0-tts-plus`，复刻样本默认最多保留 20 秒 | 明确传入 `--model qwen-audio-3.0-tts-flash` |
| 通用图片理解 | `qwen3.7-plus`、思考模式、高分辨率、`8192` 输出 Token | 使用 `--no-thinking`、`--standard-resolution`、较小的 `--max-tokens` 或明确指定其他模型 |
| 视频与帧序列理解 | `qwen3.7-plus`、思考模式、`8192` 输出 Token | 使用 `--no-thinking`、较小的 `--max-tokens` 或明确指定其他模型 |
| 专用 OCR | `qwen3.5-ocr`、自动旋转矫正、`8192` 输出 Token | 使用 `--no-rotate`、较小的 `--max-tokens` 或明确指定其他兼容模型 |
| 图片生成 | `gpt-image-2`、v2 同步接口、`b64_json`、1K 分辨率、high 质量 | 明确传入 `--quality low` 或 `--model nano-banana-fast`；升级分辨率用 `--resolution 4K` |

> 时间戳粒度、说话人分离、敏感词规则、热词、OCR 任务类型、视频 FPS 等参数决定任务行为，不是质量档位，不会仅因”默认最高质量”而擅自开启或改写。

## 当前命令概览

| 命令组 | 子命令 | 用途 |
|---|---|---|
| 本地媒体处理 | `extract-audio` | 最高保真抽取视频或媒体文件中的音轨 |
| 文件管理 | `upload` | 上传一个或多个本地文件并返回 `file_id` 和签名 URL |
| 文件管理 | `get` | 查询文件属性和当前签名 URL |
| 文件管理 | `list` | 分页列举当前账号的有效文件 |
| 文件管理 | `delete` | 删除一个或多个文件并释放配额 |
| 语音识别 | `recognize` | 使用 Qwen 最新快照、System Context、语言和 ITN 识别本地短音频 |
| 语音识别 | `recognize-context` | 使用上下文增强识别本地短音频 |
| 语音识别 | `transcribe-long` | 异步转写公网长音频并返回时间戳、情感或 SRT |
| 语音识别 | `transcribe-advanced` | 使用热词、说话人分离和敏感词过滤转写公网音频 |
| 语音识别 | `hotword-create` | 创建 Fun-ASR 热词表 |
| 语音识别 | `hotword-status` | 查询热词表状态 |
| 语音识别 | `hotword-list` | 列出热词表 |
| 语音识别 | `hotword-delete` | 删除热词表 |
| 语音生成 | `voice-clone-create` | 使用本地声音样本或公网 URL 创建 Qwen-Audio-TTS 复刻音色 |
| 语音生成 | `voice-clone-list` | 列出当前账号的复刻音色 |
| 语音生成 | `voice-clone-status` | 查询一个复刻音色的详情和状态 |
| 语音生成 | `voice-clone-delete` | 删除不再使用的复刻音色 |
| 语音生成 | `synthesize` | 使用系统音色或复刻音色执行非实时语音合成并下载文件 |
| 视觉理解 | `analyze-images` | 分析单图或多图，完成问答、OCR、定位和文档解析等任务 |
| 视觉理解 | `ocr` | 使用 Qwen-OCR 提取图片文字、位置、表格、公式或结构化字段 |
| 视觉理解 | `ocr-pdf` | 使用 Qwen-OCR 直接解析公网 PDF 文档 |
| 视觉理解 | `analyze-video` | 分析本地或公网视频文件 |
| 视觉理解 | `analyze-frames` | 把至少四张连续图片作为视频帧分析 |
| 图片生成 | `generate` | v2 同步文生图，直接返回图片数据（推荐） |
| 图片生成 | `generate-async` | v1 异步文生图，返回 task_id 并可选轮询下载 |
| 图片生成 | `edit` | v2 同步图片编辑，上传图片按提示词修改 |
| 图片生成 | `query-task` | 查询异步任务状态，完成后自动下载 |
| 图片生成 | `list-models` | 列出所有图片模型和价格 |
| 密钥管理 | `status` | 检查 API Key 是否已配置 |
| 密钥管理 | `set` | 新增或更新 API Key |
| 密钥管理 | `remove` | 删除 API Key |

## 查看帮助

```powershell
python scripts/main.py --help
python scripts/main.py file --help
python scripts/main.py file <upload|get|list|delete> --help
python scripts/main.py media --help
python scripts/main.py media extract-audio --help
python scripts/main.py speech --help
python scripts/main.py speech <子命令> --help
python scripts/main.py tts --help
python scripts/main.py tts <子命令> --help
python scripts/main.py visual --help
python scripts/main.py visual <子命令> --help
python scripts/main.py key --help
python scripts/main.py key <status|set|remove> --help
python scripts/main.py image --help
python scripts/main.py image <generate|generate-async|edit|query-task|list-models> --help
```

统一入口映射如下。后续各命令章节仍保留独立入口语法，参数完全相同；把对应前缀替换为统一入口前缀即可。

| 能力 | 统一入口前缀 | 兼容的独立入口 |
|---|---|---|
| 本地媒体处理 | `python scripts/main.py media` | `python scripts/commands/media_processing_commands.py` |
| 百炼文件管理 | `python scripts/main.py file` | `python scripts/commands/file_management_commands.py` |
| 语音识别 | `python scripts/main.py speech` | `python scripts/commands/speech_recognition_commands.py` |
| 声音复刻与语音合成 | `python scripts/main.py tts` | `python scripts/commands/speech_synthesis_commands.py` |
| 视觉理解与 OCR | `python scripts/main.py visual` | `python scripts/commands/visual_understanding_commands.py` |
| 图片生成与编辑 | `python scripts/main.py image` | `python scripts/commands/image_generation_commands.py` |
| 密钥管理 | `python scripts/main.py key` | `python scripts/commands/env_writer.py` |

## 图片生成

图片生成通过麦子科技 API（`https://www.maizitech.xyz`）调用，支持 12 款模型，覆盖文生图、图生图、图片编辑和 3D 生成。v1 为异步接口（返回 `task_id`，结果保存 24 小时），v2 为同步接口（直接返回 base64 或 URL）。

> 图片生成使用独立的 `MAIZI_API_KEY`，通过 `python scripts/main.py key set --service maizi <密钥>` 配置。

### 图片模型

| 模型 ID | 名称 | 价格 | 分辨率 | 接口 |
|---|---|---|---|---|
| `gpt-image-2` | GPT Image 2 | $0.0090~0.0440/次 | 1K/2K/4K | v1 + v2 |
| `gpt-image-2-official` | GPT Image 2 高质量 | $0.0100起/次 | 1K/2K/4K | v1 + v2 |
| `gpt-image-2-vip` | GPT Image 2 VIP | $0.0220~0.0570/次 | 1K/2K/4K | v1 + v2 |
| `nano-banana-fast` | NanoBanana 极速 | $0.0090/次 | 1K | v1 + v2 |
| `nano-banana-2-lite` | NanoBanana 2 Lite | $0.0090/次 | 1K | v1 + v2 |
| `nano-banana-2` | NanoBanana 标准 | $0.0180/次 | 1K/2K/4K | v1 + v2 |
| `nano-banana-2-vip` | NanoBanana 2 VIP | $0.0642~0.1392/次 | 1K/2K/4K | v1 + v2 |
| `nano-banana-pro` | NanoBanana 专业 | $0.0270/次 | 1K/2K/4K | v1 + v2 |
| `nano-banana-pro-vip` | NanoBanana Pro VIP | $0.1000~0.2000/次 | 1K/2K/4K | v1 + v2 |
| `doubao-seedream-5-0-lite` | Seedream 5.0 Lite | $0.0336/次 | 2K/3K/4K | v1 + v2 |
| `doubao-seedream-5-0-pro` | Seedream 5.0 Pro | $0.0432~0.0864/次 | 1K/2K | v1 + v2 |
| `seed3d-v2-image-to-3d` | Seed3D 图生 3D | — | — | 仅 v1 |

### `generate`

**用途：** 使用 v2 同步接口文生图，直接返回 base64 图片或 URL。兼容 OpenAI SDK，无需轮询。推荐用于自动化脚本和后端服务。

**完整语法：**

```powershell
python scripts/main.py image generate --prompt <提示词> [--model <模型>] [--size <比例或像素>] [--resolution <1K|2K|4K>] [--quality <low|medium|high>] [--image <参考图> ...] [--response-format <b64_json|url>] [--output <输出文件>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--prompt <提示词>` | 描述要生成的图片内容 | 是 | 任意文本 |
| `--model <模型>` | 图片生成模型 | 否 | 默认 `gpt-image-2`；不支持 `seed3d-v2-image-to-3d` |
| `--size <比例或像素>` | 画面比例或像素尺寸 | 否 | 默认 `auto`；支持 `1:1`、`16:9`、`9:16` 等比例，也支持 `1024x1024` 等像素值 |
| `--resolution <1K\|2K\|4K>` | 输出分辨率 | 否 | 默认 `1K`；升级用 `--resolution 4K` |
| `--quality <low\|medium\|high>` | 图片质量 | 否 | 默认最高 `high`；显式降档用 `--quality low` |
| `--image <参考图>` | 参考图片路径或 URL，可重复传入 | 否 | 最多 9 张；本地文件自动转 base64 data URI |
| `--response-format <b64_json\|url>` | 返回格式 | 否 | 默认 `b64_json` |
| `--output <输出文件>` | 保存图片的本地路径 | 否 | 默认自动命名到 `runtime/outputs/` |

**文生图示例：**

```powershell
python scripts/main.py image generate --prompt "一只可爱的猫咪在弹钢琴" --size "1:1" --output "runtime/outputs/cat_piano.png"
```

**降档示例（节省成本）：**

```powershell
python scripts/main.py image generate --prompt "一只可爱的猫咪在弹钢琴" --size "1:1" --resolution "1K" --quality "low"
```

**图生图示例：**

```powershell
python scripts/main.py image generate --model "nano-banana-fast" --prompt "将这张图片转为水彩画风格" --size "1:1" --image "runtime/inputs/photo.jpg" --output "runtime/outputs/watercolor.png"
```

**输出示例：**

```json
{
  "model": "gpt-image-2",
  "prompt": "一只可爱的猫咪在弹钢琴",
  "size": "1:1",
  "resolution": null,
  "quality": null,
  "response_format": "b64_json",
  "api_version": "v2",
  "saved_files": [
    {
      "index": 0,
      "output_file": "C:\\path\\to\\runtime\\outputs\\gpt_image_2_1690000000.png",
      "output_bytes": 245760
    }
  ],
  "usage": {
    "total_cost": 0.018
  }
}
```

---

### `generate-async`

**用途：** 使用 v1 异步接口文生图。接口立即返回 `task_id`，默认轮询等待完成并自动下载。`--no-wait` 可跳过轮询，稍后通过 `image query-task` 查询和下载。`seed3d-v2-image-to-3d`（图生 3D）仅支持此模式，需传入 1 张参考图，完成后下载 ZIP。

**完整语法：**

```powershell
python scripts/main.py image generate-async --prompt <提示词> [--model <模型>] [--size <比例或像素>] [--resolution <1K|2K|4K>] [--quality <low|medium|high>] [--image <参考图> ...] [--output <输出文件>] [--wait|--no-wait] [--timeout <秒>] [--callback-url <回调URL>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--prompt <提示词>` | 描述要生成的图片内容 | 是 | 任意文本 |
| `--model <模型>` | 图片生成模型 | 否 | 默认 `gpt-image-2`；`seed3d-v2-image-to-3d` 仅支持此模式 |
| `--size <比例或像素>` | 画面比例或像素尺寸 | 否 | 默认 `auto` |
| `--resolution <1K\|2K\|4K>` | 输出分辨率 | 否 | 默认 `1K`；升级用 `--resolution 4K` |
| `--quality <low\|medium\|high>` | 图片质量 | 否 | 默认最高 `high` |
| `--image <参考图>` | 参考图片路径或 URL，可重复传入 | 否 | 最多 9 张；`seed3d-v2-image-to-3d` 限 1 张 |
| `--output <输出文件>` | 保存图片的本地路径 | 否 | 默认自动命名到 `runtime/outputs/` |
| `--wait` / `--no-wait` | 是否等待完成并下载 | 否 | 默认 `--wait` |
| `--timeout <秒>` | 等待完成的最长时间 | 否 | 默认 `600`，范围 `60`～`7200` |
| `--callback-url <回调URL>` | 完成后的回调通知地址 | 否 | 暂仅供接口保留，不启用轮询 |

**异步文生图示例：**

```powershell
python scripts/main.py image generate-async --prompt "赛博朋克风格的城市夜景" --size "16:9" --resolution "2K" --timeout 300
```

**仅获取 task_id 示例：**

```powershell
python scripts/main.py image generate-async --prompt "山水画风格的江南古镇" --no-wait
```

**Seed3D 图生 3D 示例：**

```powershell
python scripts/main.py image generate-async --model "seed3d-v2-image-to-3d" --prompt "生成3D模型" --image "runtime/inputs/character.png" --timeout 1200
```

**输出示例（--wait）：**

```json
{
  "model": "gpt-image-2",
  "prompt": "赛博朋克风格的城市夜景",
  "api_version": "v1",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "saved_files": [
    {
      "index": 0,
      "output_file": "C:\\path\\to\\runtime\\outputs\\gpt_image_2_1690000100.png",
      "output_bytes": 1048576
    }
  ]
}
```

**输出示例（--no-wait）：**

```json
{
  "model": "gpt-image-2",
  "prompt": "山水画风格的江南古镇",
  "api_version": "v1",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "tip": "结果文件保存 24 小时，使用 image query-task a1b2c3d4-e5f6-7890-abcd-ef1234567890 查询和下载"
}
```

---

### `query-task`

**用途：** 查询 v1 异步任务状态。待处理或进行中的任务会自动轮询直到完成；已完成的任务直接下载结果。

**完整语法：**

```powershell
python scripts/main.py image query-task <任务ID> [--output <输出文件>] [--timeout <秒>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<任务ID>` | `generate-async --no-wait` 返回的 task_id | 是 | — |
| `--output <输出文件>` | 保存图片的本地路径 | 否 | 默认自动命名 |
| `--timeout <秒>` | 等待完成的最长时间 | 否 | 默认 `600` |

**示例：**

```powershell
python scripts/main.py image query-task "a1b2c3d4-e5f6-7890-abcd-ef1234567890" --output "runtime/outputs/result.png"
```

**输出示例：**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "saved_files": [
    {
      "index": 0,
      "output_file": "C:\\path\\to\\runtime\\outputs\\result.png",
      "output_bytes": 1048576
    }
  ]
}
```

---

### `edit`

**用途：** 使用 v2 同步接口编辑本地图片。支持带遮罩的局部编辑（白色区域修改，透明区域保留）。

**完整语法：**

```powershell
python scripts/main.py image edit --image <图片文件> --prompt <提示词> [--model <模型>] [--mask <遮罩图片>] [--size <比例或像素>] [--quality <low|medium|high>] [--response-format <b64_json|url>] [--output <输出文件>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--image <图片文件>` | 待编辑的本地图片 | 是 | PNG/JPG |
| `--prompt <提示词>` | 描述编辑要求 | 是 | 任意文本 |
| `--model <模型>` | 图片编辑模型 | 否 | 默认 `gpt-image-2-official` |
| `--mask <遮罩图片>` | 遮罩图片，白色区域编辑，透明区域保持不变 | 否 | PNG，与编辑图片尺寸一致 |
| `--size <比例或像素>` | 输出画面比例或像素 | 否 | 默认保持原比例 |
| `--quality <low\|medium\|high>` | 图片质量 | 否 | 默认最高 `high` |
| `--response-format <b64_json\|url>` | 返回格式 | 否 | 默认 `b64_json` |
| `--output <输出文件>` | 保存编辑结果的路径 | 否 | 默认自动命名到 `runtime/outputs/` |

**图片编辑示例：**

```powershell
python scripts/main.py image edit --image "runtime/inputs/photo.png" --prompt "将背景替换为海边日落"
```

**带遮罩局部编辑示例：**

```powershell
python scripts/main.py image edit --image "runtime/inputs/photo.png" --mask "runtime/inputs/mask.png" --prompt "将选中区域替换为蓝天白云" --size "1:1"
```

**输出示例：**

```json
{
  "model": "gpt-image-2-official",
  "prompt": "将背景替换为海边日落",
  "image": "C:\\path\\to\\runtime\\inputs\\photo.png",
  "mask": null,
  "size": null,
  "quality": null,
  "response_format": "b64_json",
  "api_version": "v2 edits",
  "saved_files": [
    {
      "index": 0,
      "output_file": "C:\\path\\to\\runtime\\outputs\\gpt_image_2_official_edited_1690000200.png",
      "output_bytes": 378240
    }
  ]
}
```

---

### `list-models`

**用途：** 列出所有支持的图片模型、价格和分辨率信息。

**完整语法：**

```powershell
python scripts/main.py image list-models
```

**参数：** 无。

**输出示例：** 参见上文"图片模型"表格。

---

## 当前适用范围与已知限制

| 项目 | 当前行为 | 尚未通过 CLI 暴露的能力 |
|---|---|---|
| 视频音轨抽取 | AAC、MP3、FLAC、Opus、Vorbis 优先原样复制；其他编码转无损 FLAC，保留采样率和声道布局 | 不执行降噪、人声增强、降采样或声道混合 |
| 百炼文件管理 | 支持多文件上传、详情与 URL 查询、分页列表和批量删除；默认 `file-extract` | 接口仅在北京 Region 开放；签名 URL 会变化，不是永久公网地址 |
| 本地短音频 | `recognize` 接受本地文件，支持 Qwen System Context、单一语言和 ITN；`recognize-context` 保留 Fun-ASR-Flash 方案 | `recognize` 未主动检查 10 MB、5 分钟上限 |
| 长音频 | `transcribe-long` 和 `transcribe-advanced` 只接受 HTTP/HTTPS URL；本地文件可先通过 `file upload` 取得签名 URL | 识别命令不会自动上传本地文件，需要显式执行两步 |
| 语言与 ITN | `recognize` 和 `transcribe-long` 支持单一语言与 ITN；高级转写支持重复语言提示 | 混合语种时应保留 `language=auto`，不能同时强制多个 Qwen 语言代码 |
| 音频通道 | `transcribe-long` 可重复传入 `--channel-id`；高级转写仍固定通道 `0` | 多音轨 Filetrans 按音轨单独计费 |
| 上下文增强 | `recognize --context` 使用 Qwen System Message；`recognize-context` 使用 Fun-ASR-Flash 单段上下文 | Qwen Filetrans 正式参数未提供 System Context 或热词 |
| SRT 字幕 | `transcribe-long --output-srt` 根据云端句级时间戳写出 UTF-8 SRT | 只接受公网音频 URL；多音轨字幕会增加通道前缀 |
| 热词 | 支持创建、查询、列表、删除和在转写时使用热词表 | 同一条创建命令中的全部热词共用一个权重和语言，不能逐词设置 |
| 流式与生产回调 | 当前使用同步响应或异步轮询 | 未封装流式输出、EventBridge 回调和批量任务调度 |
| 声音复刻与合成 | 默认使用 `qwen-audio-3.0-tts-plus`，可明确指定 Flash；支持本地样本上传、音色管理、控制指令、情感标签和结果下载 | 只封装已实测的非流式输出；未封装需要 Workspace ID 的 SSE 流式输出、声音设计、实时合成和其他模型系列 |
| 专用 OCR | 图片支持七种内置任务、旋转矫正、像素阈值和结构化结果；本地 PDF 可先通过 `file upload` 取得 URL | `ocr-pdf` 不会自动上传本地 PDF；未封装多轮 OCR 对话和 Batch 任务创建 |
| Skill 路由 | 根 `SKILL.md` 根据文件、语音或视觉任务选择命令 | 详细参数统一从本清单读取 |
| 图片生成 | v1 返回签名 URL 24 小时有效，v2 默认返回 base64 | URL 图片未自动续期；seed3d ZIP 下载链接也会过期 |
| 图片编辑 | 仅支持本地文件上传，使用 multipart/form-data | 不支持公网 URL 作为编辑源图；遮罩须与图片尺寸对齐 |
| 图片 API Key | 通过 `key set --service maizi` 配置，存入 `scripts/.env` | 与 DashScope 使用不同密钥，通过 `--service` 切换 |

## 百炼文件管理

文件管理使用北京 Region 的 `https://dashscope.aliyuncs.com/api/v1/files`。`upload` 返回 `file_id` 后会自动查询每个文件的当前签名 URL；URL 包含临时访问凭证，不要公开或长期保存。跨任务复用时保存 `file_id`，执行任务前使用 `get` 获取当前 URL。

服务限制：有效文件总空间不超过 100 GB，总数量不超过 10000 个；`file-extract` 单文件最大 150 MB，`batch` 最大 500 MB，`fine-tune` 最大 300 MB。接口返回的 `failed_uploads` 是单个文件失败结果，多文件请求中的其他文件仍可能成功。

### `upload`

**用途：** 一次上传一个或多个本地文件，并为每个成功文件返回 `file_id`、属性和当前签名 URL。音频、视频、图片、PDF 和其他内容分析素材默认使用 `file-extract`。

**完整语法：**

```powershell
python scripts/main.py file upload <本地文件>... [--purpose <file-extract|batch|fine-tune>] [--description <文件描述>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<本地文件>...` | 一个或多个本地文件路径 | 是 | 文件必须存在；可连续传入多个路径 |
| `--purpose <file-extract\|batch\|fine-tune>` | 文件用途 | 否 | 默认：`file-extract`<br>可选：`file-extract`、`batch`、`fine-tune` |
| `--description <文件描述>` | 为本次上传的全部文件设置相同描述 | 否 | 默认不设置 |

**示例：**

```powershell
python scripts/main.py file upload "runtime/inputs/audio.mp3" "runtime/inputs/image.jpg" --description "内容生产素材"
```

**输出示例：**

```json
{
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "purpose": "file-extract",
  "uploaded_files": [
    {
      "name": "audio.mp3",
      "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "region": "cn-beijing",
      "url": "http://dashscope-file-mgr.oss-cn-beijing.aliyuncs.com/...?Expires=..."
    },
    {
      "name": "image.jpg",
      "file_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
      "region": "cn-beijing",
      "url": "http://dashscope-file-mgr.oss-cn-beijing.aliyuncs.com/...?Expires=..."
    }
  ],
  "failed_uploads": [],
  "url_resolution_failures": []
}
```

> 本轮真实 CLI 使用一个请求成功上传 426995 字节 MP3 和 496395 字节 JPEG，两个文件均返回 `file_id` 和签名 URL。MP3 URL 随后通过 Filetrans 完成 18 秒语音识别，JPEG URL 随后通过 `qwen3.7-plus` 完成视觉理解；另行上传的 13 MB MP4 URL 也通过 `qwen3.7-plus` 完成视频理解。

---

### `get`

**用途：** 根据长期保存的 `file_id` 查询文件属性并取得当前签名 URL。任务执行前重新查询，避免使用已经失效或过期的旧 URL。

**完整语法：**

```powershell
python scripts/main.py file get <文件ID>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<文件ID>` | `upload` 或 `list` 返回的 `file_id` | 是 | — |

**示例：**

```powershell
python scripts/main.py file get "<上传返回的file_id>"
```

**输出示例：**

```json
{
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": {
    "name": "audio.mp3",
    "size": 426995,
    "region": "cn-beijing",
    "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "url": "http://dashscope-file-mgr.oss-cn-beijing.aliyuncs.com/...?Expires=..."
  }
}
```

---

### `list`

**用途：** 分页列出当前账号仍未删除的文件及其属性和当前签名 URL。

**完整语法：**

```powershell
python scripts/main.py file list [--page-no <页码>] [--page-size <每页数量>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--page-no <页码>` | 当前页，从 1 开始 | 否 | 默认 `1`，最小值 `1` |
| `--page-size <每页数量>` | 每页返回数量 | 否 | 默认 `10`，范围 `1` 至 `100` |

**示例：**

```powershell
python scripts/main.py file list --page-no 1 --page-size 20
```

**输出示例：**

```json
{
  "data": {
    "total": 1,
    "files": [
      {
        "name": "audio.mp3",
        "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "url": "http://dashscope-file-mgr.oss-cn-beijing.aliyuncs.com/...?Expires=..."
      }
    ],
    "page_size": 20,
    "page_no": 1
  },
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

---

### `delete`

**用途：** 删除一个或多个百炼文件，释放空间和文件数量配额。CLI 会逐个调用删除接口并分别返回成功和失败结果。

**完整语法：**

```powershell
python scripts/main.py file delete <文件ID>...
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<文件ID>...` | 一个或多个待删除的 `file_id` | 是 | 可连续传入多个 ID |

**示例：**

```powershell
python scripts/main.py file delete "<文件ID1>" "<文件ID2>"
```

**输出示例：**

```json
{
  "deleted_files": [
    {
      "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
  ],
  "failed_deletions": []
}
```

> 本轮真实 CLI 批量删除两个测试文件成功，`failed_deletions=[]`；删除后列表总数从 5 恢复为 3，再次查询已删除 ID 返回 `File not found.`。

---

## 本地媒体处理

### `extract-audio`

**用途：** 从本地视频或其他媒体容器中抽取指定音轨。默认按源编码选择最高保真输出：AAC→M4A、MP3→MP3、FLAC→FLAC、Opus/Vorbis→OGG，复制压缩数据包而不解码或重编码；其他编码转为无损 FLAC，并保留源采样率和声道布局。

**完整语法：**

```powershell
python scripts/main.py media extract-audio <本地视频或媒体文件> [--output <音频文件>] [--audio-stream <音轨位置>] [--overwrite]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<本地视频或媒体文件>` | PyAV 可以读取的本地视频或媒体文件 | 是 | 文件必须存在并至少包含一条音轨 |
| `--output <音频文件>` | 指定输出文件；`.flac` 可明确要求无损转码 | 否 | 默认写入 `runtime/outputs/<输入名>-audio.<自动扩展名>` |
| `--audio-stream <音轨位置>` | 按音轨在文件中的出现顺序选择，从 0 开始 | 否 | 默认 `0`，最小值 `0` |
| `--overwrite` | 允许覆盖已存在的输出文件 | 否 | 默认不覆盖 |

**示例：**

```powershell
python scripts/main.py media extract-audio "runtime/inputs/13426251338329580.mp4"
```

**输出示例：**

```json
{
  "mode": "stream_copy",
  "bit_exact": true,
  "source_codec": "aac",
  "output_codec": "aac",
  "sample_rate": 44100,
  "channels": 2,
  "channel_layout": "stereo",
  "audio_stream_position": 0,
  "audio_stream_count": 1,
  "packet_count": 1859,
  "input_file": "C:\\path\\to\\13426251338329580.mp4",
  "output_file": "C:\\path\\to\\runtime\\outputs\\13426251338329580-audio.m4a",
  "output_size": 698907
}
```

> `bit_exact=true` 表示输出中的压缩音频数据包与源音轨逐包一致。FLAC 回退会显示 `mode=lossless_flac` 和 `bit_exact=false`：压缩包编码已经变化，但解码后的音频仍为无损，并且不会自动降采样、转单声道、降噪或做人声增强。

> 本轮真实 CLI 从 13 MB MP4 中抽取 698907 字节 M4A，输入与输出的 1859 个 AAC 包 SHA-256 完全一致。抽取结果随后通过百炼 Filetrans 识别出完整口播、字级时间戳和 8 条 SRT 字幕。

---

## 语音识别

### `recognize`

**用途：** 使用最新快照 `qwen3-asr-flash-2026-02-10` 识别不超过 5 分钟、10 MB 的本地音频，同时返回文本、情感和语言标注。可通过 Qwen System Context 提供背景文本和实体词表，减少专有词和同音词误识别。

**当前限制：** System Context 只作为识别参考，不能设置模型角色；混合语种音频不应强制指定单一语言。代码尚未主动检查 10 MB 和 5 分钟限制，超限文件由接口返回错误。

**完整语法：**

```powershell
python scripts/main.py speech recognize <音频文件> [--context <背景和实体词>] [--language <语言代码|auto>] [--itn|--no-itn]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频文件>` | 本地音频文件路径 | 是 | 支持 `.aac`、`.flac`、`.m4a`、`.mp3`、`.ogg`、`.wav` |
| `--context <背景和实体词>` | 通过 Qwen System Message 提供背景文本和实体词表 | 否 | 默认不使用上下文 |
| `--language <语言代码\|auto>` | 已知单一语种时指定语言 | 否 | 默认 `auto`；常用 `zh`、`yue`、`en` |
| `--itn` / `--no-itn` | 是否把中英文数字转换为阿拉伯数字 | 否 | 默认 `--no-itn` |

**示例：**

```powershell
python scripts/main.py speech recognize "runtime/inputs/FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3" --language zh --context "背景词汇和实体词：年下、时下、财富、贫穷、名利、贯穿一生。" --no-itn
```

**输出示例：**

```json
{
  "text": "你的年下如果和你的时下相合，那么你就不需要担心你的财富问题……就这四个字贯穿一生。",
  "annotations": [
    {
      "emotion": "neutral",
      "language": "zh",
      "type": "audio_info"
    }
  ],
  "model": "qwen3-asr-flash-2026-02-10",
  "context": "背景词汇和实体词：年下、时下、财富、贫穷、名利、贯穿一生。",
  "language": "zh",
  "enable_itn": false,
  "audio_file": "C:\\path\\to\\audio.mp3",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "seconds": 17,
    "total_tokens": 529
  }
}
```

> 本轮真实 CLI 已确认 `--context`、`--language zh` 和最新快照可组合使用，并正确识别“年下、时下、贯穿一生”。

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

**用途：** 使用固定模型 `qwen3-asr-flash-filetrans` 异步转写公网音频 URL，支持最长 12 小时、2 GB，可指定语言、ITN 和一条或多条音轨，并把句级结果直接写成 SRT。

**当前限制：** 只接受公网 HTTP/HTTPS URL，不能直接传入本地长音频；每条音轨单独计费。Qwen Filetrans 的正式参数不支持 System Context 或热词，需要专业词增强时改用 `transcribe-advanced`。

**完整语法：**

```powershell
python scripts/main.py speech transcribe-long <音频URL> [--timestamp-level <sentence|word>] [--language <语言代码|auto>] [--itn|--no-itn] [--channel-id <音轨索引> ...] [--output-srt <SRT文件>] [--timeout <秒>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音频URL>` | 公网可下载的音频 URL | 是 | 必须以 `http://` 或 `https://` 开头 |
| `--timestamp-level <sentence|word>` | 时间戳级别 | 否 | 默认 `sentence`；可选 `sentence`、`word` |
| `--language <语言代码\|auto>` | 已知单一语种时指定语言 | 否 | 默认 `auto`；常用 `zh`、`yue`、`en` |
| `--itn` / `--no-itn` | 是否把中英文数字转换为阿拉伯数字 | 否 | 默认 `--no-itn` |
| `--channel-id <音轨索引>` | 指定待识别音轨，可重复传入 | 否 | 默认 `0`；每条音轨单独计费 |
| `--output-srt <SRT文件>` | 根据句级时间戳同时写出字幕 | 否 | 默认不写文件；必须使用 `.srt` 扩展名，编码为 UTF-8 BOM |
| `--timeout <秒>` | 等待异步任务完成的最长时间 | 否 | 默认 `1800`，最小 `60` |

**句级时间戳示例：**

```powershell
python scripts/main.py speech transcribe-long "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3" --language zh --timestamp-level sentence --timeout 120
```

**字级时间戳示例：**

```powershell
python scripts/main.py speech transcribe-long "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3" --language zh --itn --timestamp-level word --channel-id 0 --output-srt "runtime/outputs/welcome.srt" --timeout 120
```

**输出示例：**

```json
{
  "model": "qwen3-asr-flash-filetrans",
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "timestamp_level": "word",
  "language": "zh",
  "enable_itn": true,
  "channel_ids": [0],
  "srt_output_file": "C:\\path\\to\\runtime\\outputs\\welcome.srt",
  "subtitle_count": 1,
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

**SRT 输出示例：**

```srt
1
00:00:00,000 --> 00:00:01,440
欢迎使用阿里云。
```

> `timestamp-level=word` 会同时保留句级结果和 `words[]`，并采用 VAD + 标点断句；SRT 仍按句级时间写出。多音轨 SRT 会在字幕文字前增加 `[通道N]`。

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

## 语音生成

语音生成默认使用最高质量的 `qwen-audio-3.0-tts-plus`。只有用户明确要求降低成本或延迟时，才传入 `--model qwen-audio-3.0-tts-flash`。复刻音色创建时即绑定模型，合成时的 `--model` 必须与音色绑定模型一致。声音样本和合成结果均通过现有 `DASHSCOPE_API_KEY` 调用北京地域接口。

### `voice-clone-create`

**用途：** 使用本地 WAV、MP3、M4A 文件或公网音频 URL 创建 Qwen-Audio-TTS 复刻音色。本地文件会先上传至 DashScope 文件服务，创建完成后自动删除临时上传文件。

**完整语法：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-create <声音样本路径或URL> --prefix <音色前缀> [--model <qwen-audio-3.0-tts-plus|qwen-audio-3.0-tts-flash>] [--language-hint <语言代码> ...] [--max-prompt-audio-length <秒>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<声音样本路径或URL>` | 复刻声音使用的本地文件或公网 URL | 是 | WAV、MP3、M4A；本地文件不超过 10 MB |
| `--prefix <音色前缀>` | 生成音色 ID 使用的名称前缀 | 是 | 1～10 位小写字母或数字 |
| `--model <模型名称>` | 复刻音色绑定的 Qwen-Audio-TTS 模型 | 否 | 默认最高质量 `qwen-audio-3.0-tts-plus`；可明确选择 `qwen-audio-3.0-tts-flash` |
| `--language-hint <语言代码>` | 提示声音样本语言，可重复传入 | 否 | 如 `zh`、`en`；默认由服务判断 |
| `--max-prompt-audio-length <秒>` | 预处理后最多保留的样本时长 | 否 | 默认 `20` 秒；范围 1～60 秒 |

**声音样本要求：** 推荐 10～20 秒，最长 60 秒；采样率不低于 16 kHz；至少包含 5 秒连续清晰人声；不能包含背景音乐、明显环境噪音或其他说话人。双声道只处理首声道。

**本地样本示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-create "runtime/inputs/FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3" --prefix codexplus --language-hint zh
```

**输出示例：**

```json
{
  "voice_id": "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "target_model": "qwen-audio-3.0-tts-plus",
  "prefix": "codexplus",
  "source_type": "local_file",
  "language_hints": ["zh"],
  "max_prompt_audio_length": 20.0,
  "temporary_upload_deleted": true,
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

> Qwen-Audio-TTS 创建音色免费。每个账号与 Qwen-Audio-Realtime、CosyVoice 共用最多 1000 个自定义音色配额。音色一年未用于合成时可能被自动删除。

### `voice-clone-list`

**用途：** 分页列出当前账号中的 Qwen-Audio-TTS 复刻音色，可按创建前缀过滤。列表可能同时包含 Plus 和用户明确创建的 Flash 音色。

**完整语法：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-list [--prefix <音色前缀>] [--page-index <索引>] [--page-size <数量>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--prefix <音色前缀>` | 只列出指定前缀的音色 | 否 | 默认不过滤 |
| `--page-index <索引>` | 分页索引 | 否 | 默认 `0`，最小 `0` |
| `--page-size <数量>` | 每页返回数量 | 否 | 默认 `10`，范围 `1`～`100` |

**示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-list --prefix codexplus --page-size 10
```

**输出示例：**

```json
{
  "count": 1,
  "voices": [
    {
      "status": "OK",
      "target_model": "qwen-audio-3.0-tts-plus",
      "voice_id": "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  ],
  "prefix": "codexplus",
  "page_index": 0,
  "page_size": 10
}
```

### `voice-clone-status`

**用途：** 查询一个复刻音色的创建时间、状态和绑定模型。CLI 会移除接口返回的原始样本签名链接，避免声音样本链接进入终端日志。

**完整语法：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-status <音色ID>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音色ID>` | `voice-clone-create` 返回的完整音色 ID | 是 | 无 |

**示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-status "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**输出示例：**

```json
{
  "voice_id": "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "details": {
    "status": "OK",
    "target_model": "qwen-audio-3.0-tts-plus",
    "resource_link_available": true
  },
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### `voice-clone-delete`

**用途：** 永久删除一个不再使用的复刻音色并释放配额。

**完整语法：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-delete <音色ID>
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<音色ID>` | 要删除的完整音色 ID | 是 | 无 |

**示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py voice-clone-delete "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**输出示例：**

```json
{
  "voice_id": "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "deleted": true,
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### `synthesize`

**用途：** 使用 Qwen-Audio-TTS 系统音色或复刻音色执行非实时语音合成。接口音频 URL 只有 24 小时有效，CLI 会立即把音频下载到本地输出文件。

**完整语法：**

```powershell
python scripts/commands/speech_synthesis_commands.py synthesize --text <待合成文本> --voice <音色ID> [--model <qwen-audio-3.0-tts-plus|qwen-audio-3.0-tts-flash>] [--output <输出文件>] [--format <wav|mp3|pcm>] [--sample-rate <采样率Hz>] [--instruction <声音控制指令>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--text <待合成文本>` | 需要转换为语音的完整文本 | 是 | 支持 Qwen-Audio-TTS 情感与拟声标签 |
| `--voice <音色ID>` | 系统音色或复刻音色 ID | 是 | 复刻音色绑定模型必须与 `--model` 一致 |
| `--model <模型名称>` | 执行合成的 Qwen-Audio-TTS 模型 | 否 | 默认最高质量 `qwen-audio-3.0-tts-plus`；Flash 音色必须明确选择 `qwen-audio-3.0-tts-flash` |
| `--output <输出文件>` | 下载音频的本地文件 | 否 | 默认 `runtime/outputs/synthesized.wav` |
| `--format <格式>` | 输出音频格式 | 否 | 默认 `wav`；可选 `wav`、`mp3`、`pcm` |
| `--sample-rate <采样率Hz>` | 输出采样率 | 否 | 默认 `24000`；范围 `8000`～`48000` |
| `--instruction <声音控制指令>` | 控制音调、语速、情感、方言或音色特点 | 否 | 任意自然语言指令 |

**复刻音色合成示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py synthesize --text "每一个好内容都值得被认真听见，把灵感变成声音，让表达更自然，让创作更高效。" --voice "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" --output "runtime/outputs/highest-quality-plus-test.wav"
```

**情感与拟声标签示例：**

```powershell
python scripts/commands/speech_synthesis_commands.py synthesize --text "[excited]今天的天气真不错！[laughing]我们一起出去玩吧！" --voice "longanhuan_v3.6" --output "runtime/outputs/excited.wav"
```

**输出示例：**

```json
{
  "model": "qwen-audio-3.0-tts-plus",
  "voice": "qwen-audio-3.0-tts-plus-codexplus-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "text": "每一个好内容都值得被认真听见，把灵感变成声音，让表达更自然，让创作更高效。",
  "format": "wav",
  "sample_rate": 24000,
  "instruction": null,
  "output_file": "C:\\path\\to\\runtime\\outputs\\highest-quality-plus-test.wav",
  "output_bytes": 403244,
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "usage": {
    "characters": 70
  }
}
```

## 视觉理解

通用视觉理解默认使用 `qwen3.7-plus`，开启思考模式；图片额外默认开启高分辨率，通用视觉输出上限默认为 `8192` Token。专用文字提取默认使用 `qwen3.5-ocr`、自动旋转矫正和 `8192` Token。只有用户明确要求降低成本或延迟时才关闭这些质量选项。

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
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认最高质量 `--thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--high-resolution` / `--standard-resolution` | 是否启用高分辨率图像模式 | 否 | 默认最高质量 `--high-resolution` |
| `--min-pixels <像素数>` | 每张图片的最小像素阈值 | 否 | 正整数 |
| `--max-pixels <像素数>` | 标准分辨率模式的最大像素阈值 | 否 | 正整数；不能与 `--high-resolution` 同时使用 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `8192` |

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
  "reasoning_content": "模型对人物、动物和海滩场景的分析过程……",
  "model": "qwen3.7-plus",
  "thinking": true,
  "high_resolution": true,
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
| `--rotate` / `--no-rotate` | 是否自动矫正倾斜或旋转图像 | 否 | 默认最高质量 `--rotate` |
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
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认最高质量 `--thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `8192` |

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
| `--thinking` / `--no-thinking` | 是否返回模型思考过程 | 否 | 默认最高质量 `--thinking` |
| `--thinking-budget <Token数>` | 思考过程最大 Token 数 | 否 | 正整数 |
| `--max-tokens <Token数>` | 最终回复最大 Token 数 | 否 | 默认 `8192` |

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

密钥管理支持两个服务：`dashscope`（阿里云百炼）和 `maizi`（麦子科技图片生成）。通过 `--service` 选项切换。

### `status`

**用途：** 检查 `scripts/.env` 中是否已配置指定服务的 API Key，不显示密钥内容。

**完整语法：**

```powershell
python scripts/main.py key status [--service <dashscope|maizi>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--service <dashscope\|maizi>` | 目标服务 | 否 | 默认 `dashscope` |

**示例：**

```powershell
python scripts/main.py key status
python scripts/main.py key status --service maizi
```

**输出示例：**

```json
{
  "service": "maizi",
  "configured": true
}
```

### `set`

**用途：** 新增或更新 `scripts/.env` 中指定服务的 API Key，并保留其他配置项。

**完整语法：**

```powershell
python scripts/main.py key set <API密钥> [--service <dashscope|maizi>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `<API密钥>` | API Key | 是 | 无 |
| `--service <dashscope\|maizi>` | 目标服务 | 否 | 默认 `dashscope` |

**示例：**

```powershell
python scripts/main.py key set sk-xxx
python scripts/main.py key set --service maizi sk-your-maizi-key
```

**输出示例：**

```json
{
  "service": "maizi",
  "configured": true
}
```

> 命令行参数可能进入终端历史。不要在聊天、日志或 Git 提交中暴露真实密钥。

### `remove`

**用途：** 从 `scripts/.env` 删除指定服务的 API Key，并保留其他配置项。

**完整语法：**

```powershell
python scripts/main.py key remove [--service <dashscope|maizi>]
```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--service <dashscope\|maizi>` | 目标服务 | 否 | 默认 `dashscope` |

**示例：**

```powershell
python scripts/main.py key remove --service maizi
```

**输出示例：**

```json
{
  "service": "maizi",
  "configured": false
}
```

## 当前封装状态

| 项目 | 当前状态 | 2026-07-20 本轮检查 |
|---|---|---|
| 视频音轨最高保真抽取 | 已封装 | 真实 MP4 的 1859 个 AAC 数据包逐包哈希一致，44100 Hz 双声道保持不变；PCM→FLAC 回退验证通过 |
| 视频口播识别链路 | 已验证 | 抽取 M4A 经文件上传和 Filetrans 返回完整口播、字级时间戳及 8 条 SRT，云端测试文件已删除 |
| 百炼多文件上传与 URL | 已封装 | 真实上传 MP3、JPEG 和 13 MB MP4，均返回 `file_id` 和签名 URL；URL 已分别用于 Filetrans、图片理解和视频理解任务 |
| 文件详情、列表和删除 | 已封装 | 详情与分页列表真实通过；两个测试文件批量删除成功，删除后再次查询返回 `File not found.` |
| 短音频文本、情感和语言 | 已封装 | 最新快照真实 CLI 通过，支持 `--language` 和 ITN，返回 `emotion=neutral`、`language=zh` |
| Qwen System Context | 已封装单轮背景和实体词 | 真实 CLI 正确识别“年下、时下、贯穿一生”；Fun-ASR-Flash 上下文命令继续保留 |
| 长音频异步转写 | 已封装公网 URL | 真实 CLI 通过，支持语言、ITN 和重复音轨参数；历史已使用超过 5 分钟人声音频验证 |
| 句级、字级时间戳和 SRT | 已封装 | 字级时间戳与云端句级 SRT 真实 CLI 通过，生成 UTF-8 BOM 字幕 |
| 本地 Whisper/VAD | 已移除 | 不再提供本地模型、VAD 或 `transcribe-local`；字幕统一使用 Filetrans 云端时间戳生成 |
| 热词创建、查询、列表和删除 | 已封装 | 本轮只执行无写操作的列表查询；创建和删除沿用历史实测结果 |
| 说话人分离 | 已封装 | 真实 CLI 通过并返回 `speaker_id` |
| 敏感词替换和移除 | 已封装 | `阿里巴巴` 替换为 `****`，`实验室` 成功移除 |
| Qwen-Audio-TTS 声音复刻 | 已封装本地文件和公网 URL | 未指定模型时真实创建 Plus 音色，默认保留 20 秒样本，临时上传文件自动删除 |
| 复刻音色列表和详情 | 已封装 | 真实 CLI 返回 `status=OK` 和绑定模型；原始样本签名链接已隐藏 |
| 非实时语音合成 | 已封装系统和复刻音色 | 默认 Plus 生成 403,244 字节 WAV，反向识别文本与输入完全一致 |
| 复刻音色删除 | 已封装 | 为保留本轮生成音色未执行真实删除；命令注册和参数行为检查通过 |
| 单图和多图理解 | 已封装 | 公网图片、本地图片上传和多图比较真实 CLI 通过 |
| 视频文件理解 | 已封装 | 公网视频真实 CLI 通过，支持 `fps` 和 `max_frames` |
| 视频帧序列理解 | 已封装 | 四张连续帧真实 CLI 通过 |
| 视觉最高质量默认 | 已封装 | 未传质量参数时真实返回 `qwen3.7-plus`、`thinking=true`、`high_resolution=true` |
| Qwen-OCR 七种图片任务 | 已封装 | 默认 `qwen3.5-ocr` 与 `rotate=true` 真实 CLI 通过；信息抽取返回 `ocr_result.kv_result` |
| Qwen-OCR PDF 解析 | 已封装公网 URL | 真实 CLI 通过并返回文本与 `ocr_result.layouts` |
| 统一入口 | 已创建 | `scripts/main.py` 注册 `media`、`file`、`speech`、`tts`、`visual`、`image`、`key` 七个命令组，独立入口继续兼容 |
| 根 `SKILL.md` | 已创建 | 可按文件、语音、视觉和图片意图路由到本清单 |
| Windows exe | 未创建，当前不进入打包阶段 | 工程无打包文件，用户未要求首次打包 |
| 图片生成 v2 | 已封装 | `generate` 和 `edit` 支持 base64/URL 直接返回，12 款模型 |
| 图片生成 v1 异步 | 已封装 | `generate-async` 支持 task_id 轮询和 Seed3D 图生 3D |
| 图片模型查询 | 已封装 | `list-models` 列出全部模型、价格和分辨率 |
