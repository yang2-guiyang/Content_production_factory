---
name: content-production-factory
description: 提供百炼语音识别、Qwen System Context 准确率增强、长音频时间戳与 SRT 字幕导出、Qwen-Audio-TTS 声音复刻与非实时语音合成、视觉理解和 Qwen-OCR CLI。用于用户需要识别短音频或长音频、通过背景和实体词减少同音误识别、指定语言或 ITN、生成字幕、获取情感和时间戳、使用热词、执行说话人分离和敏感词过滤，以及处理语音生成、图片、视频、OCR 和 PDF 时。
---

# Content Production Factory

## 执行规则

1. 先读取 [references/CLI.md](references/CLI.md)，根据任务选择统一入口中的真实 Python 命令。
2. 输入文件优先放入 `runtime/inputs/`，输出文件放入 `runtime/outputs/`。
3. 调用外部模型前，使用密钥状态命令确认 `DASHSCOPE_API_KEY` 已配置。
4. 执行命令后解析标准输出中的 JSON；发生错误时保留 CLI 返回的中文错误信息。
5. 默认通过 `python scripts/main.py <命令组> <子命令>` 调用；`scripts/commands/` 下的独立入口仅用于兼容和开发调试。
6. 除非用户明确要求降低成本、缩短延迟或指定其他模型，否则保留 `references/CLI.md` 规定的最高质量默认模型和参数，不自动切换到 Flash 或关闭质量选项。

## 路由

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

## 参考

- 完整命令、参数限制和已验证示例：[references/CLI.md](references/CLI.md)
- Skill 开发与维护规范：[SKILL开发说明.md](SKILL开发说明.md)
