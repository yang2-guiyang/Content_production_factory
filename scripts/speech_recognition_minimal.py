import base64
import io
import json
import os
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
MODEL_NAME = "qwen3-asr-flash"
PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
AUDIO_FILE_PATH = PROJECT_DIRECTORY / "FBAFB6CA-3EE7-42cd-B256-AF255C40D577.mp3"


# ---------------------------
# 函数说明：读取本地 MP3 并调用 Qwen3-ASR-Flash 识别文本。
# ---------------------------
def recognize_audio():
    # 步骤1：检查 API Key 和测试音频。
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")

    if not AUDIO_FILE_PATH.exists():
        raise FileNotFoundError("音频文件不存在: " + str(AUDIO_FILE_PATH))

    # 步骤2：把本地 MP3 转换为 Base64 data URI。
    audio_bytes = AUDIO_FILE_PATH.read_bytes()
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    audio_data_uri = "data:audio/mpeg;base64," + encoded_audio

    # 步骤3：准备请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL_NAME,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "audio": audio_data_uri,
                        },
                    ],
                },
            ],
        },
        "parameters": {
            "asr_options": {
                "enable_itn": False,
            },
        },
    }

    # 步骤4：调用同步语音识别接口。
    response = requests.post(
        API_URL,
        headers=headers,
        json=data,
        timeout=120,
    )

    try:
        response_data = response.json()
    except ValueError:
        raise RuntimeError(
            "接口未返回有效 JSON，状态码: " + str(response.status_code)
        )

    print("HTTP 状态码:", response.status_code)
    print(json.dumps(response_data, ensure_ascii=False, indent=2))

    if response.status_code != 200:
        raise RuntimeError("语音识别失败")

    # 步骤5：从真实响应中提取识别文本。
    output_data = response_data.get("output")
    if not output_data:
        raise RuntimeError("响应中缺少 output 字段")

    recognition_text = output_data.get("text")
    if recognition_text:
        return recognition_text

    choices = output_data.get("choices")
    if not choices:
        raise RuntimeError("响应中缺少 output.text 和 output.choices 字段")

    first_choice = choices[0]
    message_data = first_choice.get("message")
    if not message_data:
        raise RuntimeError("响应中缺少 message 字段")

    content_data = message_data.get("content")
    if isinstance(content_data, str):
        return content_data

    if isinstance(content_data, list):
        for content_item in content_data:
            if not isinstance(content_item, dict):
                continue
            item_text = content_item.get("text")
            if item_text:
                return item_text

    raise RuntimeError("响应中没有可用的识别文本")


# ---------------------------
# 主流程：执行最小语音识别并输出最终文本。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：调用真实语音识别接口。
    final_text = recognize_audio()

    # 步骤2：输出最终识别文本。
    print("识别文本:", final_text)
