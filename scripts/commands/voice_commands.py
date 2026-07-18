import io
import json
import os
import sys

# 步骤0：直接运行本命令模块时，先解决 Windows 控制台 GBK 乱码。
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import requests

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIRECTORY)

from commands.env_reader import get_env_value


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
DEFAULT_TARGET_MODEL = "qwen-audio-3.0-tts-flash"
DEFAULT_VOICE_PREFIX = "myvoice"
QWEN_AUDIO_TTS_MODELS = (
    "qwen-audio-3.0-tts-flash",
    "qwen-audio-3.0-tts-plus",
)


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
    "audio_url",
    metavar="<音频URL>",
)
@click.option(
    "--target-model",
    default=DEFAULT_TARGET_MODEL,
    show_default=True,
    type=click.Choice(QWEN_AUDIO_TTS_MODELS, case_sensitive=True),
    metavar="<模型名称>",
    help="音色绑定的 Qwen-Audio-TTS 模型，如 qwen-audio-3.0-tts-flash",
)
@click.option(
    "--prefix",
    default=DEFAULT_VOICE_PREFIX,
    show_default=True,
    metavar="<音色前缀>",
    help="音色 ID 前缀，仅使用英文字母和数字，如 narrator1",
)
def create_voice_command(audio_url, target_model, prefix):
    """使用公网音频创建 Qwen-Audio-TTS 音色（例: python scripts/main.py voice create https://example.com/voice.wav --prefix narrator1）"""
    # 步骤1：读取 API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：检查音频 URL。
    if not audio_url.startswith("https://") and not audio_url.startswith("http://"):
        raise click.ClickException("音频 URL 必须以 http:// 或 https:// 开头")

    # 步骤3：准备请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": "voice-enrollment",
        "input": {
            "action": "create_voice",
            "target_model": target_model,
            "prefix": prefix,
            "url": audio_url,
        },
    }

    # 步骤4：发送声音复刻请求。
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=120,
        )
    except requests.exceptions.Timeout:
        raise click.ClickException("请求超时，请检查网络后重试")
    except requests.exceptions.ConnectionError:
        raise click.ClickException("网络连接失败，请检查网络设置")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("请求失败：" + str(error))

    # 步骤5：解析并检查接口响应。
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

    voice_id = output_data.get("voice_id")
    if not voice_id:
        raise click.ClickException("响应中缺少 output.voice_id 字段")

    # 步骤6：输出便于 AI 解析的 JSON 结果。
    result = {
        "voice_id": voice_id,
        "target_model": target_model,
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
