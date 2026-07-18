import base64
import io
import json
import os
import pathlib
import sys

# 步骤0：直接运行本命令模块时，先解决 Windows 控制台 GBK 乱码。
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import requests


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
DEFAULT_TARGET_MODEL = "qwen3-tts-vc-2026-01-22"
DEFAULT_PREFERRED_NAME = "myvoice"
MAXIMUM_AUDIO_FILE_SIZE = 10 * 1024 * 1024


# ---------------------------
# 函数说明：创建声音复刻命令组。
# ---------------------------
@click.group()
def cli():
    """创建和管理自定义复刻音色。"""
    pass


# ---------------------------
# 函数说明：读取本地音频并创建 Qwen-TTS 自定义音色。
# ---------------------------
@cli.command(name="create")
@click.argument(
    "audio_file",
    metavar="<音频文件>",
    type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
)
@click.option(
    "--target-model",
    default=DEFAULT_TARGET_MODEL,
    show_default=True,
    metavar="<模型名称>",
    help="音色绑定的 Qwen-TTS 模型，如 qwen3-tts-vc-2026-01-22",
)
@click.option(
    "--name",
    "preferred_name",
    default=DEFAULT_PREFERRED_NAME,
    show_default=True,
    metavar="<音色名称>",
    help="音色名称前缀，仅使用英文字母和数字，如 narrator1",
)
def create_voice_command(audio_file, target_model, preferred_name):
    """使用本地音频创建 Qwen-TTS 音色（例: python scripts/main.py voice create voice.wav --name narrator1）"""
    # 步骤1：读取 API Key。
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：检查音频格式和文件大小。
    audio_extension = audio_file.suffix.lower()
    if audio_extension == ".wav":
        audio_mime_type = "audio/wav"
    elif audio_extension == ".mp3":
        audio_mime_type = "audio/mpeg"
    elif audio_extension == ".m4a":
        audio_mime_type = "audio/mp4"
    else:
        raise click.ClickException("仅支持 WAV、MP3、M4A 音频文件")

    audio_file_size = audio_file.stat().st_size
    if audio_file_size > MAXIMUM_AUDIO_FILE_SIZE:
        raise click.ClickException("音频文件不能超过 10 MB")

    # 步骤3：把本地音频转换为接口接受的 data URI。
    audio_bytes = audio_file.read_bytes()
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    audio_data_uri = "data:" + audio_mime_type + ";base64," + encoded_audio

    # 步骤4：准备请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {
                "data": audio_data_uri,
            },
        },
    }

    # 步骤5：发送声音复刻请求。
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise click.ClickException("请求超时，请检查网络后重试")
    except requests.exceptions.ConnectionError:
        raise click.ClickException("网络连接失败，请检查网络设置")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("请求失败：" + str(error))

    # 步骤6：解析并检查接口响应。
    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException("接口未返回有效 JSON，状态码：" + str(response.status_code))

    if response.status_code != 200:
        response_text = json.dumps(response_data, ensure_ascii=False)
        raise click.ClickException(
            "接口返回错误，状态码："
            + str(response.status_code)
            + "，响应内容："
            + response_text[:500]
        )

    output_data = response_data.get("output")
    if not output_data:
        raise click.ClickException("响应中缺少 output 字段")

    voice_id = output_data.get("voice")
    if not voice_id:
        raise click.ClickException("响应中缺少 output.voice 字段")

    # 步骤7：输出便于 AI 解析的 JSON 结果。
    result = {
        "voice_id": voice_id,
        "target_model": output_data.get("target_model"),
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
