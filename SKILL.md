---
name: content-production-factory
description: 提供 FFmpeg 视频剪辑（裁剪/拼接/缩放/调速/滤镜/字幕烧录/转场/调色/画中画）、视频音轨无损抽取、百炼多文件上传、file_id 与签名 URL 管理、语音识别、Qwen System Context 准确率增强、长音频时间戳与 SRT 字幕导出、Qwen-Audio-TTS 声音复刻与非实时语音合成、视觉理解、Qwen-OCR CLI 和麦子科技图片生成。用于用户需要从本地视频提取口播文案、字幕或多人对话，默认生成 SRT，并在明确要求时输出 TXT；也用于上传和复用音频、视频、图片或文档，以及处理语音、OCR、视觉任务和 AI 图片生成。
---

# Content Production Factory

## 执行规则

1. 先读取 [references/CLI.md](references/CLI.md)，根据任务选择统一入口中的真实 Python 命令。
2. 输入文件优先放入 `runtime/inputs/`，输出文件放入 `runtime/outputs/`。
3. 调用外部模型前，使用密钥状态命令确认 `DASHSCOPE_API_KEY` 已配置。
4. 执行命令后解析标准输出中的 JSON；发生错误时保留 CLI 返回的中文错误信息。
5. 默认通过 `python scripts/main.py <命令组> <子命令>` 调用；`scripts/commands/` 下的独立入口仅用于兼容和开发调试。
6. 除非用户明确要求降低成本、缩短延迟或指定其他模型，否则保留 `references/CLI.md` 规定的最高质量默认模型和参数，不自动切换到 Flash 或关闭质量选项。
7. URL 输入命令遇到本地文件时，先用 `file upload` 获得 `file_id` 和签名 URL；长期保存 `file_id`，任务执行前用 `file get` 刷新 URL。
8. 视频口播识别先用 `media extract-audio` 无损抽取音轨，再按时长和功能选择 `speech` 命令；不要用只分析画面的 `visual analyze-video` 识别口播。
9. 视频文案、字幕和对话转写默认交付 SRT；只有用户明确要求 TXT、`.txt` 或文本文件时才额外输出 TXT。
10. **FFmpeg 规则**：视频剪辑直接使用 FFmpeg CLI，读取 [references/ffmpeg.md](references/ffmpeg.md)。首次执行前运行 `ffmpeg -version` 检查可用性；若找不到命令，引导用户安装：`winget install ffmpeg`。`-c copy` 为无损操作首选，需重编码时默认 `libx264 -crf 18` + `aac -b:a 192k`。

## 路由

- 视频口播文案、字幕、带时间戳转写或多人对话：读取 [references/视频提取口播与字幕.md](references/视频提取口播与字幕.md)，按无损音轨流程执行并默认输出 SRT。
- 只从本地视频提取原始音轨、不做识别：使用 `media extract-audio`；优先原样复制兼容编码，不兼容时转无损 FLAC。
- 上传一个或多个本地音频、视频、图片、PDF 或其他文档并取得可复用 URL：使用 `file upload`。
- 查询文件当前 URL、分页列举文件或删除文件释放配额：使用 `file get`、`file list` 或 `file delete`。
- 本地短音频高准确率识别：使用 `speech recognize --language <语言> --context <背景和实体词>`。
- 公网长音频、句级或字级时间戳及 SRT 字幕：使用 `speech transcribe-long`。
- 热词、说话人分离或敏感词过滤：使用 `speech transcribe-advanced` 及 `hotword-*` 命令。
- 使用本地声音样本或公网 URL 创建复刻音色，以及查询、列出或删除复刻音色：使用 `tts voice-clone-*` 命令。
- 使用系统音色或复刻音色将文本转换为音频，控制情感、语速、方言或拟声效果：使用 `tts synthesize`。
- 图片描述、视觉问答、物体定位、创意写作或多图比较：使用 `visual analyze-images`。
- 通用文字识别、高精文字定位、票据证照信息抽取、表格解析、公式识别、多语言 OCR 或扫描图片文档解析：使用 `visual ocr`。
- 直接解析公网 PDF 并获取文本和版面布局：使用 `visual ocr-pdf`。
- 视频摘要、动作分析、事件定位或视频时间戳：使用 `visual analyze-video`。
- 已经抽取为连续图片的视频：使用 `visual analyze-frames`。
- 查询、设置或删除 DashScope API Key：使用 `key` 命令组。
- 文生图、图生图、图片编辑或图生 3D：使用 `image generate`（v2 同步，推荐）、`image generate-async`（v1 异步）或 `image edit`（v2 编辑）。
- 查询异步图片任务或下载结果：使用 `image query-task`。
- 查看图片模型列表和价格：使用 `image list-models`。
- 查看视频元信息：使用 `ffprobe -v quiet -print_format json -show_format -show_streams input.mp4`。
- 视频裁剪、截取片段：使用 `ffmpeg -i input.mp4 -ss <开始> -to <结束> -c copy output.mp4`。
- 删除中间片段：使用 `ffmpeg -i input.mp4 -filter_complex "[0:v]trim...;[0:a]atrim..."` 分段后再 concat。
- 视频倒放：使用 `ffmpeg -i input.mp4 -vf "reverse" -af "areverse" output.mp4`。
- 定格/冻结帧：使用 trim + loop + concat 组合实现。
- 多段视频拼接：创建 `files.txt` 后使用 `ffmpeg -f concat -safe 0 -i files.txt -c copy output.mp4`。
- 视频缩放、裁切、旋转、翻转：使用 `ffmpeg -i input.mp4 -vf "<scale|crop|transpose|hflip|vflip>" output.mp4`。
- 横竖屏比例转换（模糊背景填充）：使用 split + scale + boxblur + overlay 滤镜链。
- 视频匀速变速（快放/慢放）：使用 `ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=<PTS>[v];[0:a]atempo=<速度>[a]" output.mp4`。
- 曲线变速：分段 trim + 各段分别 setpts/atempo + concat 拼接。
- 音频音量调节：使用 `ffmpeg -i input.mp4 -af "volume=<倍数>" -c:v copy output.mp4`。
- 音频降噪：使用 `anlmdn`（轻度）或 `afftdn`（强力）滤镜。
- 变声：使用 `asetrate` + `aresample` 改变音调。
- 淡入淡出（画面或音频）：使用 `ffmpeg -i input.mp4 -vf "fade..." -af "afade..." output.mp4`。
- 音频替换、BGM 混音：使用 `ffmpeg -i video.mp4 -i audio.mp3 -filter_complex "amix..." output.mp4`。
- 画中画、图片水印、文字叠加：使用 `ffmpeg -i main.mp4 -i overlay.png -filter_complex "overlay=..." output.mp4`。
- 分屏（左右/上下/四宫格）：使用 `hstack` / `vstack` 滤镜。
- SRT 字幕烧录到画面：使用 `ffmpeg -i video.mp4 -vf "subtitles=subs.srt" output.mp4`。
- ASS 字幕动画烧录：先用 `python scripts/commands/srt_to_ass.py --style <pop|slide|fade|karaoke>` 将 SRT 转 ASS，再 `ffmpeg -vf "ass=..."` 烧录。
- 视频转场效果：使用 `ffmpeg -i a.mp4 -i b.mp4 -filter_complex "xfade=transition=<效果>:duration=<秒>" output.mp4`。
- 基础调色（亮度/对比度/饱和度/色温/Gamma）：使用 `eq` / `colorbalance` / `curves` / `hue` 滤镜。
- LUT 调色：使用 `ffmpeg -i input.mp4 -vf "lut3d=lut.cube" output.mp4`。
- 风格化滤镜（灰度/老电影/模糊/锐化/毛玻璃/卡通化/负片）：使用 `hue=s=0` / `boxblur` / `gblur` / `unsharp` / `edgedetect` / `negate` 等滤镜。
- 绿幕抠像：使用 `chromakey` 或 `colorkey` 滤镜替换纯色背景。
- 蒙版（圆形/矩形/遮罩图片）：使用 `geq` + `alphamerge` 或裁剪叠加实现。
- 背景填充（纯色/模糊/自定义颜色）：使用 `pad` 滤镜或 split + boxblur + overlay 组合。
- 抽帧缩时摄影：使用 `fps` + `setpts` 大幅变速。
- 容器或编码格式转换：使用 `ffmpeg -i input.mkv -c:v libx264 -crf 18 -c:a aac output.mp4`（也支持 GIF/WebM）。
- 以上所有 FFmpeg 命令的完整参数和示例见 [references/ffmpeg.md](references/ffmpeg.md)。

## 参考

- 完整命令、参数限制和已验证示例：[references/CLI.md](references/CLI.md)
- FFmpeg 视频剪辑命令参考：[references/ffmpeg.md](references/ffmpeg.md)
- 视频口播、字幕与对话 SOP：[references/视频提取口播与字幕.md](references/视频提取口播与字幕.md)
- Skill 开发与维护规范：[SKILL开发说明.md](SKILL开发说明.md)
- 图片生成 API Key：通过 `key set --service maizi` 配置，与 DashScope 使用不同密钥
