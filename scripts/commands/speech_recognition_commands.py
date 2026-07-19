import base64
import ctypes
import io
import json
import os
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
PROJECT_DIRECTORY = SCRIPTS_DIRECTORY.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
ASYNC_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
ASYNC_QUERY_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/"
MODEL_NAME = "qwen3-asr-flash"
CONTEXT_MODEL_NAME = "fun-asr-flash-2026-06-15"
LONG_AUDIO_MODEL_NAME = "qwen3-asr-flash-filetrans"
FUN_ASR_MODEL_NAME = "fun-asr"
DEFAULT_LOCAL_WHISPER_MODEL_NAME = "large-v3"
AUDIO_MIME_TYPES = {
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}
LOCAL_MEDIA_EXTENSIONS = {
    ".aac",
    ".avi",
    ".flac",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
    ".wmv",
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
# 函数说明：检查本地转写输入并返回绝对路径。
# ---------------------------
def validate_local_media_file(media_file_path):
    # 步骤1：检查输入路径是否为本地文件。
    resolved_media_file = media_file_path.resolve()
    if not resolved_media_file.exists():
        raise click.ClickException("本地媒体文件不存在：" + str(resolved_media_file))
    if not resolved_media_file.is_file():
        raise click.ClickException("本地媒体路径不是文件：" + str(resolved_media_file))

    # 步骤2：检查文件扩展名是否受本地解码器支持。
    media_file_extension = resolved_media_file.suffix.lower()
    if media_file_extension not in LOCAL_MEDIA_EXTENSIONS:
        supported_extensions = ", ".join(sorted(LOCAL_MEDIA_EXTENSIONS))
        raise click.ClickException(
            "不支持的本地媒体格式，当前支持：" + supported_extensions
        )

    # 步骤3：返回通过检查的绝对路径。
    return resolved_media_file


# ---------------------------
# 函数说明：把秒数转换为 SRT 使用的时间格式。
# ---------------------------
def format_srt_timestamp(seconds_value):
    # 步骤1：把秒数转换为非负整数毫秒。
    total_milliseconds = round(seconds_value * 1000)
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
# 函数说明：确定本地字幕输出文件。
# ---------------------------
def resolve_srt_output_file(media_file_path, output_file_path):
    # 步骤1：用户传入输出路径时使用该路径。
    if output_file_path:
        resolved_output_file = output_file_path.resolve()
    else:
        output_file_name = media_file_path.stem + ".srt"
        resolved_output_file = (
            PROJECT_DIRECTORY / "runtime" / "outputs" / output_file_name
        )

    # 步骤2：限制输出格式为 SRT。
    if resolved_output_file.suffix.lower() != ".srt":
        raise click.ClickException("字幕输出文件必须使用 .srt 扩展名")

    # 步骤3：创建输出目录并返回绝对路径。
    resolved_output_file.parent.mkdir(parents=True, exist_ok=True)
    return resolved_output_file


# ---------------------------
# 函数说明：加载本地 Whisper 模型并完整执行一次转写。
# ---------------------------
def run_local_whisper_transcription(
    whisper_model_class,
    model_name,
    device,
    compute_type,
    media_file_path,
    language,
):
    # 步骤1：按指定设备和计算精度加载模型。
    whisper_model = whisper_model_class(
        model_name,
        device=device,
        compute_type=compute_type,
    )

    # 步骤2：启动带 VAD 的高质量本地转写。
    segments, transcription_information = whisper_model.transcribe(
        str(media_file_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    # 步骤3：立即完成生成器迭代，让推理错误在写文件前返回。
    segment_items = []
    for segment in segments:
        segment_items.append(segment)

    return segment_items, transcription_information


# ---------------------------
# 函数说明：在 Windows 上为自动设备选择检查本地 CUDA 运行库。
# ---------------------------
def resolve_local_whisper_runtime(device, compute_type):
    # 步骤1：用户明确指定设备时不改写配置。
    if device != "auto":
        return device, compute_type, None

    # 步骤2：非 Windows 平台交给 CTranslate2 自动选择。
    if os.name != "nt":
        return device, compute_type, None

    # 步骤3：检查当前版本在 Windows GPU 推理时需要的 DLL。
    required_cuda_libraries = ["cublas64_12.dll", "cudnn64_9.dll"]
    missing_cuda_libraries = []
    for library_name in required_cuda_libraries:
        try:
            ctypes.WinDLL(library_name)
        except OSError:
            missing_cuda_libraries.append(library_name)

    # 步骤4：运行库完整时继续使用自动设备。
    if not missing_cuda_libraries:
        return device, compute_type, None

    # 步骤5：运行库不完整时直接选择低内存 CPU 计算，避免重复加载模型。
    fallback_reason = (
        "自动设备缺少 CUDA 运行库：" + ", ".join(missing_cuda_libraries)
    )
    return "cpu", "int8", fallback_reason


# ---------------------------
# 函数说明：创建语音识别命令组。
# ---------------------------
@click.group()
def cli():
    """执行本地字幕、短音频、长音频和增强语音识别。"""
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
    recognition_annotations = extract_recognition_annotations(response_data)
    result = {
        "text": recognition_text,
        "annotations": recognition_annotations,
        "model": MODEL_NAME,
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
# 函数说明：使用本地 Whisper 模型转写媒体文件并生成 SRT 字幕。
# ---------------------------
@cli.command(name="transcribe-local")
@click.argument(
    "media_file",
    type=click.Path(path_type=pathlib.Path),
    metavar="<本地音频或视频>",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(path_type=pathlib.Path),
    metavar="<SRT文件>",
    help="字幕输出路径，默认写入 runtime/outputs/<输入文件名>.srt",
)
@click.option(
    "--language",
    default="auto",
    show_default=True,
    metavar="<语言代码|auto>",
    help="指定识别语言，如 zh、en；auto 表示自动检测",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_LOCAL_WHISPER_MODEL_NAME,
    show_default=True,
    metavar="<模型名称或路径>",
    help="faster-whisper 模型名称或本地模型目录",
)
@click.option(
    "--device",
    default="auto",
    show_default=True,
    type=click.Choice(["auto", "cpu", "cuda"], case_sensitive=True),
    metavar="<auto|cpu|cuda>",
    help="本地推理设备",
)
@click.option(
    "--compute-type",
    default="auto",
    show_default=True,
    metavar="<计算精度>",
    help="CTranslate2 计算精度，如 auto、float16、int8",
)
def transcribe_local_command(
    media_file,
    output_file,
    language,
    model_name,
    device,
    compute_type,
):
    """本地识别音频或视频并生成 SRT 字幕。"""
    # 步骤1：检查输入文件并确定字幕输出路径。
    resolved_media_file = validate_local_media_file(media_file)
    resolved_output_file = resolve_srt_output_file(
        resolved_media_file,
        output_file,
    )

    # 步骤2：延迟加载本地模型依赖，避免影响其他语音识别命令。
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise click.ClickException(
            "缺少 faster-whisper，请先运行："
            "python -m pip install -U faster-whisper"
        )

    # 步骤3：准备语言配置。
    transcription_language = language
    if language == "auto":
        transcription_language = None

    # 步骤4：在加载模型前确定实际设备和计算精度。
    actual_device, actual_compute_type, device_fallback_reason = (
        resolve_local_whisper_runtime(device, compute_type)
    )

    # 步骤5：执行一次完整本地转写。
    try:
        segment_items, transcription_information = run_local_whisper_transcription(
            WhisperModel,
            model_name,
            actual_device,
            actual_compute_type,
            resolved_media_file,
            transcription_language,
        )
    except Exception as error:
        raise click.ClickException("本地媒体转写失败：" + str(error))

    # 步骤6：逐段写入临时 SRT 文件并汇总完整文本。
    temporary_output_file = resolved_output_file.with_suffix(".srt.tmp")
    subtitle_count = 0
    full_text_parts = []
    try:
        with open(temporary_output_file, "w", encoding="utf-8-sig") as srt_file:
            for segment in segment_items:
                subtitle_text = " ".join(segment.text.strip().split())
                if not subtitle_text:
                    continue

                subtitle_count = subtitle_count + 1
                start_timestamp = format_srt_timestamp(segment.start)
                end_timestamp = format_srt_timestamp(segment.end)

                srt_file.write(str(subtitle_count) + "\n")
                srt_file.write(start_timestamp + " --> " + end_timestamp + "\n")
                srt_file.write(subtitle_text + "\n\n")
                full_text_parts.append(subtitle_text)
    except Exception as error:
        if temporary_output_file.exists():
            temporary_output_file.unlink()
        raise click.ClickException("生成 SRT 字幕失败：" + str(error))

    # 步骤7：识别完成后用完整字幕替换目标文件。
    temporary_output_file.replace(resolved_output_file)

    # 步骤8：输出便于后续处理的 JSON 摘要。
    result = {
        "model": model_name,
        "requested_device": device,
        "requested_compute_type": compute_type,
        "device": actual_device,
        "compute_type": actual_compute_type,
        "device_fallback_reason": device_fallback_reason,
        "media_file": str(resolved_media_file),
        "output_file": str(resolved_output_file),
        "encoding": "utf-8-sig",
        "language": transcription_information.language,
        "language_probability": transcription_information.language_probability,
        "duration_seconds": transcription_information.duration,
        "subtitle_count": subtitle_count,
        "text": "".join(full_text_parts),
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
    "--timeout",
    "timeout_seconds",
    type=click.IntRange(min=60),
    default=1800,
    show_default=True,
    metavar="<秒>",
    help="等待异步任务完成的最长时间",
)
def transcribe_long_command(audio_url, timestamp_level, timeout_seconds):
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
        "channel_id": [0],
        "enable_itn": False,
        "enable_words": enable_words,
    }

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
    result_data = output_data.get("result")
    if not result_data:
        raise click.ClickException("任务响应缺少 output.result 字段")
    transcription_url = result_data.get("transcription_url")
    if not transcription_url:
        raise click.ClickException("任务响应缺少 transcription_url 字段")

    # 步骤5：下载并输出完整转写结果。
    transcription_data = download_transcription_result(transcription_url)
    result = {
        "model": LONG_AUDIO_MODEL_NAME,
        "task_id": task_id,
        "request_id": request_id,
        "timestamp_level": timestamp_level,
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
