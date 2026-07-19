---
name: content-production-factory
description: 提供语音识别、Qwen-Audio-TTS 声音复刻与非实时语音合成、视觉理解和 Qwen-OCR CLI。用于用户需要识别短音频或长音频、获取情感和时间戳、使用热词或上下文增强、执行说话人分离和敏感词过滤，使用声音样本创建或管理复刻音色、把文本合成为语音、控制合成情感语速方言或拟声效果，以及分析单图、多图、视频或视频帧，完成图片描述、视觉问答、文字定位、票据证照信息抽取、表格解析、公式识别、多语言 OCR、扫描文档或 PDF 解析、物体定位、创意写作和视频事件理解时。
---

# Content Production Factory

## 执行规则

1. 先读取 [references/CLI.md](references/CLI.md)，根据任务选择真实存在的独立 Python 命令。
2. 输入文件优先放入 `runtime/inputs/`，输出文件放入 `runtime/outputs/`。
3. 调用外部模型前，使用密钥状态命令确认 `DASHSCOPE_API_KEY` 已配置。
4. 执行命令后解析标准输出中的 JSON；发生错误时保留 CLI 返回的中文错误信息。
5. 当前没有统一 `main.py` 和 exe，直接调用 `scripts/commands/` 下的命令模块。
6. 除非用户明确要求降低成本、缩短延迟或指定其他模型，否则保留 `references/CLI.md` 规定的最高质量默认模型和参数，不自动切换到 Flash 或关闭质量选项。

## 路由

- 语音转文字、长音频、时间戳、情感、热词、上下文增强、说话人分离或敏感词过滤：使用语音识别命令组。
- 使用本地声音样本或公网 URL 创建复刻音色，以及查询、列出或删除复刻音色：使用语音生成命令组的 `voice-clone-*` 命令。
- 使用系统音色或复刻音色将文本转换为音频，控制情感、语速、方言或拟声效果：使用语音生成命令组的 `synthesize`。
- 图片描述、视觉问答、物体定位、创意写作或多图比较：使用 `analyze-images`。
- 通用文字识别、高精文字定位、票据证照信息抽取、表格解析、公式识别、多语言 OCR 或扫描图片文档解析：使用 `ocr`。
- 直接解析公网 PDF 并获取文本和版面布局：使用 `ocr-pdf`。
- 视频摘要、动作分析、事件定位或视频时间戳：使用 `analyze-video`。
- 已经抽取为连续图片的视频：使用 `analyze-frames`。
- 查询、设置或删除 DashScope API Key：使用密钥管理命令组。

## 参考

- 完整命令、参数限制和已验证示例：[references/CLI.md](references/CLI.md)
- Skill 开发与维护规范：[SKILL开发说明.md](SKILL开发说明.md)
