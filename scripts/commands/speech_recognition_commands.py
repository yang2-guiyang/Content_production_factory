import base64
import io
import json
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import requests

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
MODEL_NAME = "qwen3-asr-flash"
AUDIO_MIME_TYPES = {
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}


# ---------------------------
# 函数说明：把本地音频转换为 API 接受的 Base64 data URI。
# ---------------------------
def create_audio_data_uri(audio_file_path):
    # 步骤1：检查音频文件是否存在。
    if not audio_file_path.exists():
        raise click.ClickException("音频文件不存在：" + str(audio_file_path))
    if not audio_file_path.is_file():
        raise click.ClickException("音频路径不是文件：" + str(audio_file_path))

    # 步骤2：根据扩展名确定音频 MIME 类型。
    file_extension = audio_file_path.suffix.lower()
    audio_mime_type = AUDIO_MIME_TYPES.get(file_extension)
    if not audio_mime_type:
        supported_extensions = ", ".join(AUDIO_MIME_TYPES.keys())
        raise click.ClickException("不支持的音频格式，当前支持：" + supported_extensions)

    # 步骤3：读取音频并生成 Base64 data URI。
    audio_bytes = audio_file_path.read_bytes()
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    return "data:" + audio_mime_type + ";base64," + encoded_audio


# ---------------------------
# 函数说明：从 Qwen3-ASR-Flash 响应中提取识别文本。
# ---------------------------
def extract_recognition_text(response_data):
    # 步骤1：读取 output 字段。
    output_data = response_data.get("output")
    if not output_data:
        raise click.ClickException("响应中缺少 output 字段")

    # 步骤2：优先读取 output.text。
    recognition_text = output_data.get("text")
    if recognition_text:
        return recognition_text

    # 步骤3：兼容从 output.choices 返回文本的响应结构。
    choices = output_data.get("choices")
    if not choices:
        raise click.ClickException("响应中缺少 output.text 和 output.choices 字段")

    first_choice = choices[0]
    message_data = first_choice.get("message")
    if not message_data:
        raise click.ClickException("响应中缺少 message 字段")

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

    # 步骤4：没有找到文本时返回明确错误。
    raise click.ClickException("响应中没有可用的识别文本")


# ---------------------------
# 函数说明：创建语音识别命令组。
# ---------------------------
@click.group()
def cli():
    """使用 Qwen3-ASR-Flash 将本地音频识别为文本。"""
    pass


# ---------------------------
# 函数说明：识别本地音频并输出结构化结果。
# ---------------------------
@cli.command(name="recognize")
@click.argument(
    "audio_file",
    type=click.Path(path_type=pathlib.Path),
    metavar="<音频文件>",
)
def recognize_command(audio_file):
    """识别本地音频（例: python scripts/main.py speech recognize audio.mp3）"""
    # 步骤1：读取 DashScope API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：读取音频并生成 Base64 data URI。
    resolved_audio_file = audio_file.resolve()
    audio_data_uri = create_audio_data_uri(resolved_audio_file)

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
    try:
        response = requests.post(
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
        raise click.ClickException(
            "接口未返回有效 JSON，状态码：" + str(response.status_code)
        )

    if response.status_code != 200:
        response_text = json.dumps(response_data, ensure_ascii=False)
        raise click.ClickException(
            "接口返回错误，状态码："
            + str(response.status_code)
            + "，响应内容："
            + response_text[:500]
        )

    # 步骤6：提取文本并输出便于 AI 解析的 JSON。
    recognition_text = extract_recognition_text(response_data)
    result = {
        "text": recognition_text,
        "model": MODEL_NAME,
        "audio_file": str(resolved_audio_file),
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行语音识别 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动 Click 命令组。
    cli()
