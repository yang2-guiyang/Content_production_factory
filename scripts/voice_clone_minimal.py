import base64
import io
import json
import os
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
TARGET_MODEL = "qwen3-tts-vc-2026-01-22"
PREFERRED_NAME = "codextest"
PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
VOICE_FILE_PATH = PROJECT_DIRECTORY / "runtime" / "inputs" / "voice_sample.wav"


# ---------------------------
# 函数说明：读取本地音频并创建 Qwen-TTS 自定义音色。
# ---------------------------
def create_voice():
    # 步骤1：检查 API Key 和本地音频文件。
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")

    if not VOICE_FILE_PATH.exists():
        raise FileNotFoundError("音频文件不存在: " + str(VOICE_FILE_PATH))

    # 步骤2：把本地音频转换为接口接受的 data URI。
    audio_bytes = VOICE_FILE_PATH.read_bytes()
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    audio_data_uri = "data:audio/wav;base64," + encoded_audio

    # 步骤3：准备请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": TARGET_MODEL,
            "preferred_name": PREFERRED_NAME,
            "audio": {
                "data": audio_data_uri,
            },
        },
    }

    # 步骤4：调用声音复刻接口并检查响应。
    response = requests.post(
        API_URL,
        headers=headers,
        json=data,
        timeout=120,
    )
    response_data = response.json()

    print("HTTP 状态码:", response.status_code)
    print(json.dumps(response_data, ensure_ascii=False, indent=2))

    if response.status_code != 200:
        raise RuntimeError("创建音色失败")

    # 步骤5：读取并返回创建成功的音色 ID。
    output_data = response_data.get("output")
    if not output_data:
        raise RuntimeError("响应中缺少 output 字段")

    voice_id = output_data.get("voice")
    if not voice_id:
        raise RuntimeError("响应中缺少 output.voice 字段")

    return voice_id


# ---------------------------
# 主流程：调用最小请求并输出创建成功的音色 ID。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：创建自定义音色。
    created_voice_id = create_voice()

    # 步骤2：输出后续语音合成需要使用的音色 ID。
    print("声音复刻成功，voice_id:", created_voice_id)
