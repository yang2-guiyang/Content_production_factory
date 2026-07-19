import base64
import io
import json
import pathlib
import sys
import time

# 步骤0：仅在需要时切换为 UTF-8，避免统一入口重复导入时关闭输出流。
standard_output_encoding = getattr(sys.stdout, "encoding", "") or ""
normalized_output_encoding = standard_output_encoding.lower().replace("-", "")
if normalized_output_encoding != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import dashscope
import requests
from dashscope.audio.asr import VocabularyService

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
ASYNC_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
ASYNC_QUERY_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/"
MODEL_NAME = "qwen3-asr-flash-2026-02-10"
CONTEXT_MODEL_NAME = "fun-asr-flash-2026-06-15"
LONG_AUDIO_MODEL_NAME = "qwen3-asr-flash-filetrans"
FUN_ASR_MODEL_NAME = "fun-asr"
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
# 函数说明：从 Qwen3-ASR-Flash 响应中提取情感和语言标注。
# ---------------------------
def extract_recognition_annotations(response_data):
    # 步骤1：读取 output.choices。
    output_data = response_data.get("output")
    if not output_data:
        return []

    choices = output_data.get("choices")
    if not choices:
        return []

    # 步骤2：读取第一条消息的 annotations。
    first_choice = choices[0]
    message_data = first_choice.get("message")
    if not message_data:
        return []

    annotations = message_data.get("annotations")
    if not annotations:
        return []
    return annotations


# ---------------------------
# 函数说明：从 Fun-ASR-Flash 同步响应中提取文本。
# ---------------------------
def extract_fun_asr_flash_text(response_data):
    # 步骤1：读取 output.text。
    output_data = response_data.get("output")
    if not output_data:
        raise click.ClickException("响应中缺少 output 字段")

    recognition_text = output_data.get("text")
    if not recognition_text:
        raise click.ClickException("响应中缺少 output.text 字段")
    return recognition_text


# ---------------------------
# 函数说明：检查音频 URL 是否为公网 HTTP 地址。
# ---------------------------
def validate_audio_url(audio_url):
    # 步骤1：只接受 HTTP 或 HTTPS URL。
    if not audio_url.startswith("https://") and not audio_url.startswith("http://"):
        raise click.ClickException("音频 URL 必须以 http:// 或 https:// 开头")


# ---------------------------
# 函数说明：发送 HTTP 请求并返回 JSON。
# ---------------------------
def send_json_request(request_method, url, headers, data=None, timeout=30):
    # 步骤1：按请求方法发送请求。
    try:
        if request_method == "POST":
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=timeout,
            )
        else:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
            )
    except requests.exceptions.Timeout:
        raise click.ClickException("请求超时，请检查网络后重试")
    except requests.exceptions.ConnectionError:
        raise click.ClickException("网络连接失败，请检查网络设置")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("请求失败：" + str(error))

    # 步骤2：解析 JSON 响应。
    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "接口未返回有效 JSON，状态码：" + str(response.status_code)
        )

    # 步骤3：检查 HTTP 状态码。
    if response.status_code != 200:
        response_text = json.dumps(response_data, ensure_ascii=False)
        raise click.ClickException(
            "接口返回错误，状态码："
            + str(response.status_code)
            + "，响应内容："
            + response_text[:500]
        )
    return response_data


# ---------------------------
# 函数说明：提交异步语音转写任务。
# ---------------------------
def submit_async_transcription(api_key, model_name, input_data, parameters):
    # 步骤1：准备异步请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    data = {
        "model": model_name,
        "input": input_data,
        "parameters": parameters,
    }

    # 步骤2：提交任务并提取任务 ID。
    response_data = send_json_request(
        "POST",
        ASYNC_SUBMIT_URL,
        headers,
        data=data,
        timeout=30,
    )
    output_data = response_data.get("output")
    if not output_data:
        raise click.ClickException("提交响应缺少 output 字段")

    task_id = output_data.get("task_id")
    if not task_id:
        raise click.ClickException("提交响应缺少 output.task_id 字段")
    return task_id, response_data.get("request_id")


# ---------------------------
# 函数说明：轮询异步任务直到完成。
# ---------------------------
def wait_for_async_transcription(api_key, task_id, timeout_seconds):
    # 步骤1：准备查询请求头和截止时间。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    deadline = time.monotonic() + timeout_seconds

    # 步骤2：按 5 秒间隔轮询任务状态。
    while time.monotonic() < deadline:
        response_data = send_json_request(
            "GET",
            ASYNC_QUERY_URL + task_id,
            headers,
            timeout=30,
        )
        output_data = response_data.get("output")
        if not output_data:
            raise click.ClickException("查询响应缺少 output 字段")

        task_status = output_data.get("task_status")
        click.echo("任务状态：" + str(task_status), err=True)
        if task_status == "SUCCEEDED":
            return response_data
        if task_status == "FAILED" or task_status == "CANCELED":
            error_code = output_data.get("code")
            error_message = output_data.get("message")
            raise click.ClickException(
                "异步任务失败："
                + str(error_code)
                + "，"
                + str(error_message)
            )
        time.sleep(5)

    # 步骤3：超过截止时间时返回明确错误。
    raise click.ClickException("等待异步任务完成超时，任务 ID：" + task_id)


# ---------------------------
# 函数说明：下载异步转写结果 JSON。
# ---------------------------
def download_transcription_result(transcription_url):
    # 步骤1：下载公网结果文件。
    try:
        response = requests.get(transcription_url, timeout=60)
    except requests.exceptions.Timeout:
        raise click.ClickException("下载转写结果超时")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("下载转写结果失败：" + str(error))

    # 步骤2：检查下载状态并解析 JSON。
    if response.status_code != 200:
        raise click.ClickException(
            "下载转写结果失败，状态码：" + str(response.status_code)
        )
    try:
        return response.json()
    except ValueError:
        raise click.ClickException("转写结果不是有效 JSON")


# ---------------------------
# 函数说明：把毫秒转换为 SRT 时间格式。
# ---------------------------
def format_srt_timestamp(milliseconds_value):
    # 步骤1：把时间转换为非负整数毫秒。
    total_milliseconds = round(milliseconds_value)
    if total_milliseconds < 0:
        total_milliseconds = 0

    # 步骤2：依次计算小时、分钟、秒和毫秒。
    hours = total_milliseconds // 3600000
    remaining_milliseconds = total_milliseconds % 3600000
    minutes = remaining_milliseconds // 60000
    remaining_milliseconds = remaining_milliseconds % 60000
    seconds = remaining_milliseconds // 1000
    milliseconds = remaining_milliseconds % 1000

    # 步骤3：生成标准 SRT 时间文本。
    return (
        f"{hours:02d}:{minutes:02d}:{seconds:02d},"
        f"{milliseconds:03d}"
    )


# ---------------------------
# 函数说明：提供字幕条目的时间排序依据。
# ---------------------------
def get_subtitle_sort_key(subtitle_item):
    # 步骤1：先按开始时间排序，相同开始时间再按结束时间排序。
    return (
        subtitle_item["begin_time"],
        subtitle_item["end_time"],
    )


# ---------------------------
# 函数说明：把 Qwen Filetrans 结果写成 SRT 字幕。
# ---------------------------
def write_transcription_srt(transcription_data, output_file_path):
    # 步骤1：检查输出文件扩展名并创建目录。
    resolved_output_file = output_file_path.resolve()
    if resolved_output_file.suffix.lower() != ".srt":
        raise click.ClickException("字幕输出文件必须使用 .srt 扩展名")
    resolved_output_file.parent.mkdir(parents=True, exist_ok=True)

    # 步骤2：收集全部音轨中的有效句子。
    transcripts = transcription_data.get("transcripts")
    if not transcripts:
        raise click.ClickException("转写结果中没有 transcripts，无法生成 SRT")

    subtitle_items = []
    transcript_count = len(transcripts)
    for transcript in transcripts:
        channel_id = transcript.get("channel_id", 0)
        sentences = transcript.get("sentences")
        if not sentences:
            continue

        for sentence in sentences:
            subtitle_text = str(sentence.get("text", "")).strip()
            begin_time = sentence.get("begin_time")
            end_time = sentence.get("end_time")
            if not subtitle_text or begin_time is None or end_time is None:
                continue

            if transcript_count > 1:
                subtitle_text = "[通道" + str(channel_id) + "] " + subtitle_text

            subtitle_item = {
                "begin_time": begin_time,
                "end_time": end_time,
                "text": subtitle_text,
            }
            subtitle_items.append(subtitle_item)

    if not subtitle_items:
        raise click.ClickException("转写结果中没有有效句子，无法生成 SRT")

    # 步骤3：按原始音频时间顺序排列全部字幕。
    subtitle_items.sort(key=get_subtitle_sort_key)

    # 步骤4：先写临时文件，完整成功后再替换目标文件。
    temporary_output_file = resolved_output_file.with_suffix(".srt.tmp")
    try:
        with open(temporary_output_file, "w", encoding="utf-8-sig") as srt_file:
            subtitle_index = 1
            for subtitle_item in subtitle_items:
                start_timestamp = format_srt_timestamp(
                    subtitle_item["begin_time"]
                )
                end_timestamp = format_srt_timestamp(
                    subtitle_item["end_time"]
                )

                srt_file.write(str(subtitle_index) + "\n")
                srt_file.write(start_timestamp + " --> " + end_timestamp + "\n")
                srt_file.write(subtitle_item["text"] + "\n\n")
                subtitle_index = subtitle_index + 1
    except OSError as error:
        if temporary_output_file.exists():
            temporary_output_file.unlink()
        raise click.ClickException("写入 SRT 字幕失败：" + str(error))

    # 步骤5：替换目标文件并返回写出摘要。
    temporary_output_file.replace(resolved_output_file)
    return resolved_output_file, len(subtitle_items)


# ---------------------------
# 函数说明：创建已配置鉴权的热词服务。
# ---------------------------
def create_vocabulary_service(api_key):
    # 步骤1：为 DashScope SDK 配置与识别接口相同的 API Key。
    dashscope.api_key = api_key
    return VocabularyService()


# ---------------------------
# 函数说明：等待新建热词表处理完成。
# ---------------------------
def wait_for_vocabulary_ready(service, vocabulary_id):
    # 步骤1：最多等待 60 秒。
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        vocabulary_data = service.query_vocabulary(vocabulary_id)
        vocabulary_status = vocabulary_data.get("status")
        if vocabulary_status == "OK":
            return vocabulary_data
        if vocabulary_status == "FAILED":
            raise click.ClickException("热词表处理失败")
        time.sleep(1)

    # 步骤2：超过截止时间时返回明确错误。
    raise click.ClickException("等待热词表可用超时")


# ---------------------------
# 函数说明：创建语音识别命令组。
# ---------------------------
@click.group()
def cli():
    """执行短音频、长音频和增强语音识别。"""
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
@click.option(
    "--context",
    "context_text",
    default=None,
    metavar="<背景和实体词>",
    help="通过 Qwen System Message 提供背景文本和实体词表",
)
@click.option(
    "--language",
    default="auto",
    show_default=True,
    metavar="<语言代码|auto>",
    help="已知单一语种时指定，如 zh、yue、en；auto 表示自动判断",
)
@click.option(
    "--itn/--no-itn",
    "enable_itn",
    default=False,
    show_default=True,
    help="是否把中英文数字转换为阿拉伯数字",
)
def recognize_command(audio_file, context_text, language, enable_itn):
    """识别本地音频（例: python scripts/main.py speech recognize audio.mp3）"""
    # 步骤1：读取 DashScope API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：读取音频并生成 Base64 data URI。
    resolved_audio_file = audio_file.resolve()
    audio_data_uri = create_audio_data_uri(resolved_audio_file)

    # 步骤3：按需加入 Qwen System Context，再加入本地音频。
    messages = []
    if context_text:
        messages.append(
            {
                "role": "system",
                "content": [
                    {
                        "text": context_text,
                    },
                ],
            }
        )

    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "audio": audio_data_uri,
                },
            ],
        }
    )

    # 步骤4：准备语言和 ITN 参数。
    asr_options = {
        "enable_itn": enable_itn,
    }
    if language != "auto":
        asr_options["language"] = language

    # 步骤5：准备请求头和请求数据。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL_NAME,
        "input": {
            "messages": messages,
        },
        "parameters": {
            "asr_options": asr_options,
        },
    }

    # 步骤6：调用同步语音识别接口。
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

    # 步骤7：解析并检查接口响应。
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

    # 步骤8：提取文本并输出便于 AI 解析的 JSON。
    recognition_text = extract_recognition_text(response_data)
    recognition_annotations = extract_recognition_annotations(response_data)
    result = {
        "text": recognition_text,
        "annotations": recognition_annotations,
        "model": MODEL_NAME,
        "context": context_text,
        "language": language,
        "enable_itn": enable_itn,
        "audio_file": str(resolved_audio_file),
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：使用上下文增强识别本地短音频。
# ---------------------------
@cli.command(name="recognize-context")
@click.argument(
    "audio_file",
    type=click.Path(path_type=pathlib.Path),
    metavar="<音频文件>",
)
@click.option(
    "--context",
    "context_text",
    required=True,
    metavar="<上下文文本>",
    help="音频中可能出现的领域词汇或前文，最多 400 个字符",
)
@click.option(
    "--sample-rate",
    required=True,
    type=click.IntRange(min=8000),
    metavar="<采样率Hz>",
    help="音频真实采样率，如 16000 或 44100",
)
def recognize_context_command(audio_file, context_text, sample_rate):
    """使用上下文增强识别本地短音频。"""
    # 步骤1：读取 API Key 并检查上下文长度。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    if len(context_text) > 400:
        raise click.ClickException("上下文文本不能超过 400 个字符")

    # 步骤2：读取音频并确定格式。
    resolved_audio_file = audio_file.resolve()
    audio_data_uri = create_audio_data_uri(resolved_audio_file)
    audio_format = resolved_audio_file.suffix.lower().lstrip(".")

    # 步骤3：准备上下文增强请求。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    data = {
        "model": CONTEXT_MODEL_NAME,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": context_text,
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_data_uri,
                            },
                        },
                    ],
                },
            ],
        },
        "parameters": {
            "format": audio_format,
            "sample_rate": sample_rate,
        },
    }

    # 步骤4：调用同步上下文增强接口。
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

    # 步骤5：解析并检查响应。
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

    # 步骤6：输出上下文和识别结果。
    recognition_text = extract_fun_asr_flash_text(response_data)
    result = {
        "text": recognition_text,
        "context": context_text,
        "model": CONTEXT_MODEL_NAME,
        "audio_file": str(resolved_audio_file),
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：异步转写公网长音频并返回完整时间戳结果。
# ---------------------------
@cli.command(name="transcribe-long")
@click.argument("audio_url", metavar="<音频URL>")
@click.option(
    "--timestamp-level",
    type=click.Choice(["sentence", "word"], case_sensitive=True),
    default="sentence",
    show_default=True,
    metavar="<sentence|word>",
    help="返回句级或字级时间戳",
)
@click.option(
    "--language",
    default="auto",
    show_default=True,
    metavar="<语言代码|auto>",
    help="已知单一语种时指定，如 zh、yue、en；auto 表示自动判断",
)
@click.option(
    "--itn/--no-itn",
    "enable_itn",
    default=False,
    show_default=True,
    help="是否把中英文数字转换为阿拉伯数字",
)
@click.option(
    "--channel-id",
    "channel_ids",
    multiple=True,
    default=(0,),
    show_default=True,
    type=click.IntRange(min=0),
    metavar="<音轨索引>",
    help="指定待识别音轨，可重复使用；每条音轨单独计费",
)
@click.option(
    "--output-srt",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    metavar="<SRT文件>",
    help="把句级结果同时写入 UTF-8 SRT 字幕",
)
@click.option(
    "--timeout",
    "timeout_seconds",
    type=click.IntRange(min=60),
    default=1800,
    show_default=True,
    metavar="<秒>",
    help="等待异步任务完成的最长时间",
)
def transcribe_long_command(
    audio_url,
    timestamp_level,
    language,
    enable_itn,
    channel_ids,
    output_srt,
    timeout_seconds,
):
    """转写最长 12 小时的公网音频 URL。"""
    # 步骤1：读取 API Key 并检查 URL。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    validate_audio_url(audio_url)

    # 步骤2：根据时间戳级别准备异步任务参数。
    enable_words = False
    if timestamp_level == "word":
        enable_words = True
    input_data = {
        "file_url": audio_url,
    }
    parameters = {
        "channel_id": list(channel_ids),
        "enable_itn": enable_itn,
        "enable_words": enable_words,
    }
    if language != "auto":
        parameters["language"] = language

    # 步骤3：提交并等待长音频任务。
    task_id, request_id = submit_async_transcription(
        api_key,
        LONG_AUDIO_MODEL_NAME,
        input_data,
        parameters,
    )
    task_response = wait_for_async_transcription(
        api_key,
        task_id,
        timeout_seconds,
    )

    # 步骤4：读取结果下载 URL。
    output_data = task_response.get("output")
    if not output_data:
        raise click.ClickException("任务响应缺少 output 字段")
    result_data = output_data.get("result")
    if not result_data:
        raise click.ClickException("任务响应缺少 output.result 字段")
    transcription_url = result_data.get("transcription_url")
    if not transcription_url:
        raise click.ClickException("任务响应缺少 transcription_url 字段")

    # 步骤5：下载完整转写结果。
    transcription_data = download_transcription_result(transcription_url)

    # 步骤6：按需写出标准 SRT 字幕。
    srt_output_file = None
    subtitle_count = None
    if output_srt:
        srt_output_file, subtitle_count = write_transcription_srt(
            transcription_data,
            output_srt,
        )

    # 步骤7：输出完整结果和实际使用的准确率参数。
    srt_output_file_text = None
    if srt_output_file:
        srt_output_file_text = str(srt_output_file)

    result = {
        "model": LONG_AUDIO_MODEL_NAME,
        "task_id": task_id,
        "request_id": request_id,
        "timestamp_level": timestamp_level,
        "language": language,
        "enable_itn": enable_itn,
        "channel_ids": list(channel_ids),
        "srt_output_file": srt_output_file_text,
        "subtitle_count": subtitle_count,
        "usage": task_response.get("usage"),
        "transcription": transcription_data,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：创建绑定 Fun-ASR 的热词表。
# ---------------------------
@cli.command(name="hotword-create")
@click.argument("prefix", metavar="<前缀>")
@click.option(
    "--word",
    "words",
    multiple=True,
    required=True,
    metavar="<热词>",
    help="加入热词，可重复使用",
)
@click.option(
    "--weight",
    type=click.IntRange(min=1, max=5),
    default=4,
    show_default=True,
    metavar="<1-5>",
    help="全部热词使用的权重",
)
@click.option(
    "--language",
    default="zh",
    show_default=True,
    metavar="<语言代码>",
    help="热词语言代码",
)
def hotword_create_command(prefix, words, weight, language):
    """创建 Fun-ASR 热词表。"""
    # 步骤1：读取 API Key 并检查前缀。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    if len(prefix) > 10:
        raise click.ClickException("热词表前缀不能超过 10 个字符")

    # 步骤2：准备热词数组。
    vocabulary = []
    for word_text in words:
        vocabulary_item = {
            "text": word_text,
            "weight": weight,
            "lang": language,
        }
        vocabulary.append(vocabulary_item)

    # 步骤3：调用 SDK 创建热词表。
    service = create_vocabulary_service(api_key)
    try:
        vocabulary_id = service.create_vocabulary(
            prefix=prefix,
            target_model=FUN_ASR_MODEL_NAME,
            vocabulary=vocabulary,
        )
    except Exception as error:
        raise click.ClickException("创建热词表失败：" + str(error))
    if not vocabulary_id:
        raise click.ClickException("创建热词表失败：响应中没有热词表 ID")

    # 步骤4：等待热词表可用并输出真实状态。
    try:
        vocabulary_data = wait_for_vocabulary_ready(service, vocabulary_id)
    except Exception as error:
        raise click.ClickException("查询热词表失败：" + str(error))
    result = {
        "vocabulary_id": vocabulary_id,
        "target_model": FUN_ASR_MODEL_NAME,
        "status": vocabulary_data.get("status"),
        "vocabulary": vocabulary,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：查询一个热词表的状态和内容。
# ---------------------------
@cli.command(name="hotword-status")
@click.argument("vocabulary_id", metavar="<热词表ID>")
def hotword_status_command(vocabulary_id):
    """查询热词表状态。"""
    # 步骤1：读取 API Key 并查询热词表。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    service = create_vocabulary_service(api_key)
    try:
        vocabulary_data = service.query_vocabulary(vocabulary_id)
    except Exception as error:
        raise click.ClickException("查询热词表失败：" + str(error))

    # 步骤2：输出 SDK 返回的完整数据。
    click.echo(json.dumps(vocabulary_data, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：列出当前账号的热词表。
# ---------------------------
@cli.command(name="hotword-list")
@click.option(
    "--prefix",
    default=None,
    metavar="<前缀>",
    help="只列出指定前缀的热词表",
)
def hotword_list_command(prefix):
    """列出热词表。"""
    # 步骤1：读取 API Key 并查询热词表列表。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    service = create_vocabulary_service(api_key)
    try:
        vocabulary_items = service.list_vocabularies(prefix=prefix)
    except Exception as error:
        raise click.ClickException("列出热词表失败：" + str(error))

    # 步骤2：输出列表和数量。
    result = {
        "count": len(vocabulary_items),
        "items": vocabulary_items,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：删除指定热词表。
# ---------------------------
@cli.command(name="hotword-delete")
@click.argument("vocabulary_id", metavar="<热词表ID>")
def hotword_delete_command(vocabulary_id):
    """删除热词表。"""
    # 步骤1：读取 API Key 并删除热词表。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    service = create_vocabulary_service(api_key)
    try:
        service.delete_vocabulary(vocabulary_id)
    except Exception as error:
        raise click.ClickException("删除热词表失败：" + str(error))

    # 步骤2：输出删除状态。
    result = {
        "vocabulary_id": vocabulary_id,
        "deleted": True,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：使用 Fun-ASR 执行热词、分离和敏感词高级转写。
# ---------------------------
@cli.command(name="transcribe-advanced")
@click.argument("audio_url", metavar="<音频URL>")
@click.option(
    "--vocabulary-id",
    default=None,
    metavar="<热词表ID>",
    help="使用 hotword-create 创建的 Fun-ASR 热词表 ID",
)
@click.option(
    "--diarization/--no-diarization",
    default=False,
    show_default=True,
    help="是否启用说话人分离",
)
@click.option(
    "--filter-signed",
    "signed_words",
    multiple=True,
    metavar="<敏感词>",
    help="将敏感词替换为等长星号，可重复使用",
)
@click.option(
    "--filter-empty",
    "empty_words",
    multiple=True,
    metavar="<敏感词>",
    help="从结果中移除敏感词，可重复使用",
)
@click.option(
    "--system-sensitive-filter/--no-system-sensitive-filter",
    default=True,
    show_default=True,
    help="是否同时启用系统预置敏感词表",
)
@click.option(
    "--language-hint",
    "language_hints",
    multiple=True,
    metavar="<语言代码>",
    help="指定音频语种，可重复使用",
)
@click.option(
    "--timeout",
    "timeout_seconds",
    type=click.IntRange(min=60),
    default=1800,
    show_default=True,
    metavar="<秒>",
    help="等待异步任务完成的最长时间",
)
def transcribe_advanced_command(
    audio_url,
    vocabulary_id,
    diarization,
    signed_words,
    empty_words,
    system_sensitive_filter,
    language_hints,
    timeout_seconds,
):
    """执行 Fun-ASR 高级异步转写。"""
    # 步骤1：读取 API Key 并检查 URL。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    validate_audio_url(audio_url)

    # 步骤2：准备基础输入和参数。
    input_data = {
        "file_urls": [
            audio_url,
        ],
    }
    parameters = {
        "channel_id": [0],
        "diarization_enabled": diarization,
    }
    if vocabulary_id:
        parameters["vocabulary_id"] = vocabulary_id
    if language_hints:
        language_hint_items = []
        for language_hint in language_hints:
            language_hint_items.append(language_hint)
        parameters["language_hints"] = language_hint_items

    # 步骤3：按需加入敏感词过滤配置。
    if signed_words or empty_words or not system_sensitive_filter:
        signed_word_items = []
        for signed_word in signed_words:
            signed_word_items.append(signed_word)

        empty_word_items = []
        for empty_word in empty_words:
            empty_word_items.append(empty_word)

        parameters["special_word_filter"] = {
            "filter_with_signed": {
                "word_list": signed_word_items,
            },
            "filter_with_empty": {
                "word_list": empty_word_items,
            },
            "system_reserved_filter": system_sensitive_filter,
        }

    # 步骤4：提交并等待 Fun-ASR 任务。
    task_id, request_id = submit_async_transcription(
        api_key,
        FUN_ASR_MODEL_NAME,
        input_data,
        parameters,
    )
    task_response = wait_for_async_transcription(
        api_key,
        task_id,
        timeout_seconds,
    )

    # 步骤5：读取 Fun-ASR 结果下载 URL。
    output_data = task_response.get("output")
    results = output_data.get("results")
    if not results:
        raise click.ClickException("任务响应缺少 output.results 字段")
    first_result = results[0]
    transcription_url = first_result.get("transcription_url")
    if not transcription_url:
        raise click.ClickException("任务响应缺少 transcription_url 字段")

    # 步骤6：下载并输出完整高级转写结果。
    transcription_data = download_transcription_result(transcription_url)
    options = {
        "vocabulary_id": vocabulary_id,
        "diarization": diarization,
        "filter_signed": list(signed_words),
        "filter_empty": list(empty_words),
        "system_sensitive_filter": system_sensitive_filter,
        "language_hints": list(language_hints),
    }
    result = {
        "model": FUN_ASR_MODEL_NAME,
        "task_id": task_id,
        "request_id": request_id,
        "options": options,
        "usage": task_response.get("usage"),
        "transcription": transcription_data,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行语音识别 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动 Click 命令组。
    cli()
