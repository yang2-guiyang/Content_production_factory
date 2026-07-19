---
name: content-production-factory
description: 提供语音识别和视觉理解 CLI。用于用户需要识别短音频或长音频、获取情感和时间戳、使用热词或上下文增强、执行说话人分离和敏感词过滤，以及分析单图、多图、视频或视频帧，完成图片描述、视觉问答、OCR、信息抽取、物体定位、文档解析、创意写作和视频事件理解时。
---

# Content Production Factory

## 执行规则

1. 先读取 [references/CLI.md](references/CLI.md)，根据任务选择真实存在的独立 Python 命令。
2. 输入文件优先放入 `runtime/inputs/`，输出文件放入 `runtime/outputs/`。
3. 调用外部模型前，使用密钥状态命令确认 `DASHSCOPE_API_KEY` 已配置。
4. 执行命令后解析标准输出中的 JSON；发生错误时保留 CLI 返回的中文错误信息。
5. 当前没有统一 `main.py` 和 exe，直接调用 `scripts/commands/` 下的命令模块。

## 路由

- 语音转文字、长音频、时间戳、情感、热词、上下文增强、说话人分离或敏感词过滤：使用语音识别命令组。
- 图片描述、视觉问答、OCR、表格或票据信息抽取、物体定位、文档解析、多图比较：使用 `analyze-images`。
- 视频摘要、动作分析、事件定位或视频时间戳：使用 `analyze-video`。
- 已经抽取为连续图片的视频：使用 `analyze-frames`。
- 查询、设置或删除 DashScope API Key：使用密钥管理命令组。

## 参考

- 完整命令、参数限制和已验证示例：[references/CLI.md](references/CLI.md)
- Skill 开发与维护规范：[SKILL开发说明.md](SKILL开发说明.md)
