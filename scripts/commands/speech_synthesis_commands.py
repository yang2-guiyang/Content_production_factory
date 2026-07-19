import io
import json
import pathlib
import re
import sys

# 步骤0：仅在需要时切换为 UTF-8，避免统一入口重复导入时关闭输出流。
standard_output_encoding = getattr(sys.stdout, "encoding", "") or ""
normalized_output_encoding = standard_output_encoding.lower().replace("-", "")
if normalized_output_encoding != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import requests
from dashscope import Files
from dashscope.audio.tts_v2.enrollment import VoiceEnrollmentException
from dashscope.audio.tts_v2.enrollment import VoiceEnrollmentService

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
PROJECT_DIRECTORY = SCRIPTS_DIRECTORY.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


DEFAULT_TTS_MODEL_NAME = "qwen-audio-3.0-tts-plus"
TTS_MODEL_NAMES = (
    "qwen-audio-3.0-tts-plus",
    "qwen-audio-3.0-tts-flash",
)
VOICE_ENROLLMENT_MODEL_NAME = "voice-enrollment"
SPEECH_SYNTHESIS_API_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
)
MAX_VOICE_SAMPLE_BYTES = 10 * 1024 * 1024
DEFAULT_OUTPUT_FILE = PROJECT_DIRECTORY / "runtime" / "outputs" / "synthesized.wav"
VOICE_SAMPLE_EXTENSIONS = {
    ".m4a",
    ".mp3",
    ".wav",
}


# ---------------------------
# 函数说明：读取百炼 API Key。
# ---------------------------
def get_api_key():
    # 步骤1：从项目现有 .env 配置读取密钥。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")
    return api_key


# ---------------------------
# 函数说明：检查复刻音色前缀是否符合百炼限制。
# ---------------------------
def validate_voice_prefix(prefix):
    # 步骤1：只允许 1 到 10 位小写字母或数字。
    if not re.fullmatch(r"[a-z0-9]{1,10}", prefix):
        raise ValueError("音色前缀必须由 1 到 10 位小写字母或数字组成")


# ---------------------------
# 函数说明：检查声音样本 URL 或本地文件。
# ---------------------------
def validate_voice_sample(audio_source):
    # 步骤1：公网 URL 直接返回。
    if audio_source.startswith("http://"):
        return "url", audio_source
    if audio_source.startswith("https://"):
        return "url", audio_source

    # 步骤2：解析本地文件并检查存在性。
    audio_file_path = pathlib.Path(audio_source).expanduser().resolve()
    if not audio_file_path.exists():
        raise click.ClickException("声音样本不存在：" + str(audio_file_path))
    if not audio_file_path.is_file():
        raise click.ClickException("声音样本路径不是文件：" + str(audio_file_path))

    # 步骤3：检查格式和 10 MB 大小限制。
    file_extension = audio_file_path.suffix.lower()
    if file_extension not in VOICE_SAMPLE_EXTENSIONS:
        raise click.ClickException("声音样本只支持 WAV、MP3 或 M4A")
    file_size = audio_file_path.stat().st_size
    if file_size > MAX_VOICE_SAMPLE_BYTES:
        raise click.ClickException("声音样本不能超过 10 MB")
    return "local_file", str(audio_file_path)


# ---------------------------
# 函数说明：从 DashScope 文件上传响应中提取文件 ID。
# ---------------------------
def extract_uploaded_file_id(output_data):
    # 步骤1：读取成功上传的文件列表。
    uploaded_files = output_data.get("uploaded_files")
    if not uploaded_files:
        failed_uploads = output_data.get("failed_uploads")
        raise click.ClickException(
            "上传声音样本失败："
            + json.dumps(failed_uploads, ensure_ascii=False)
        )

    # 步骤2：提取第一个文件的 ID。
    uploaded_file = uploaded_files[0]
    file_id = uploaded_file.get("file_id")
    if not file_id:
        raise click.ClickException("上传声音样本失败：响应中缺少 file_id")
    return file_id


# ---------------------------
# 函数说明：从 DashScope 文件详情中提取签名 HTTP URL。
# ---------------------------
def extract_uploaded_file_url(file_details):
    # 步骤1：读取可供声音复刻接口访问的签名 URL。
    file_url = file_details.get("url")
    if not file_url:
        raise click.ClickException("上传声音样本失败：文件详情中缺少 URL")
    if not file_url.startswith("http://") and not file_url.startswith("https://"):
        raise click.ClickException("上传声音样本失败：文件 URL 不是 HTTP 地址")
    return file_url


# ---------------------------
# 函数说明：把本地声音样本上传到 DashScope 文件服务。
# ---------------------------
def upload_local_voice_sample(audio_file_path, api_key):
    # 步骤1：上传本地文件用于模型推理。
    try:
        upload_response = Files.upload(
            file_path=audio_file_path,
            purpose="inference",
            api_key=api_key,
        )
    except Exception as error:
        raise click.ClickException("上传声音样本失败：" + str(error))
    if upload_response.status_code != 200:
        raise click.ClickException(
            "上传声音样本失败："
            + str(upload_response.code)
            + "，"
            + str(upload_response.message)
        )
    uploaded_file_id = extract_uploaded_file_id(upload_response.output)

    # 步骤2：查询文件详情并获取签名 HTTP URL。
    try:
        file_response = Files.get(
            file_id=uploaded_file_id,
            api_key=api_key,
        )
    except Exception as error:
        raise click.ClickException("获取声音样本 URL 失败：" + str(error))
    if file_response.status_code != 200:
        raise click.ClickException(
            "获取声音样本 URL 失败："
            + str(file_response.code)
            + "，"
            + str(file_response.message)
        )
    uploaded_file_url = extract_uploaded_file_url(file_response.output)
    return uploaded_file_url, uploaded_file_id


# ---------------------------
# 函数说明：删除完成复刻后不再需要的临时上传文件。
# ---------------------------
def delete_temporary_uploaded_file(file_id, api_key):
    # 步骤1：公网 URL 不需要清理。
    if not file_id:
        return True

    # 步骤2：删除 DashScope 文件服务中的临时文件。
    try:
        delete_response = Files.delete(
            file_id=file_id,
            api_key=api_key,
        )
    except Exception:
        return False
    if delete_response.status_code != 200:
        return False
    return True


# ---------------------------
# 函数说明：准备声音复刻接口可访问的样本 URL。
# ---------------------------
def prepare_voice_sample(audio_source, api_key):
    # 步骤1：检查输入并直接保留公网 URL。
    source_type, resolved_source = validate_voice_sample(audio_source)
    if source_type == "url":
        return source_type, resolved_source, None

    # 步骤2：上传本地文件并返回签名 HTTP URL。
    uploaded_url, uploaded_file_id = upload_local_voice_sample(
        resolved_source,
        api_key,
    )
    return source_type, uploaded_url, uploaded_file_id


# ---------------------------
# 函数说明：创建声音复刻管理服务。
# ---------------------------
def create_voice_enrollment_service(api_key):
    # 步骤1：使用固定的声音复刻服务模型创建客户端。
    return VoiceEnrollmentService(
        api_key=api_key,
        model=VOICE_ENROLLMENT_MODEL_NAME,
    )


# ---------------------------
# 函数说明：移除音色详情中的原始样本签名链接。
# ---------------------------
def sanitize_voice_details(voice_details):
    # 步骤1：逐项复制允许输出的音色详情字段。
    safe_voice_details = {}
    for detail_name in voice_details:
        if detail_name == "resource_link":
            continue
        safe_voice_details[detail_name] = voice_details[detail_name]

    # 步骤2：只说明样本链接是否存在，不暴露链接内容。
    resource_link = voice_details.get("resource_link")
    safe_voice_details["resource_link_available"] = bool(resource_link)
    return safe_voice_details


# ---------------------------
# 函数说明：构造非实时语音合成 input 参数。
# ---------------------------
def build_synthesis_input(
    text,
    voice,
    audio_format,
    sample_rate,
    instruction,
):
    # 步骤1：写入必需的文本、音色和音频参数。
    synthesis_input = {
        "text": text,
        "voice": voice,
        "format": audio_format,
        "sample_rate": sample_rate,
    }

    # 步骤2：按需加入自然语言声音控制指令。
    if instruction:
        synthesis_input["instruction"] = instruction
    return synthesis_input


# ---------------------------
# 函数说明：提取非实时语音合成响应中的音频信息。
# ---------------------------
def extract_synthesis_result(response_data):
    # 步骤1：读取 output.audio 对象。
    output_data = response_data.get("output")
    if not isinstance(output_data, dict):
        raise click.ClickException("语音合成响应中缺少 output 字段")
    audio_data = output_data.get("audio")
    if not isinstance(audio_data, dict):
        raise click.ClickException("语音合成响应中缺少 output.audio 字段")

    # 步骤2：检查下载 URL 并保留过期时间。
    audio_url = audio_data.get("url")
    if not audio_url:
        raise click.ClickException("语音合成响应中缺少音频下载 URL")
    result = {
        "url": audio_url,
        "expires_at": audio_data.get("expires_at"),
    }
    return result


# ---------------------------
# 函数说明：移除合成结果中的签名音频下载链接。
# ---------------------------
def sanitize_synthesis_result(audio_result):
    # 步骤1：只保留链接过期时间，不输出可直接访问音频的 URL。
    safe_audio_result = {
        "expires_at": audio_result.get("expires_at"),
    }
    return safe_audio_result


# ---------------------------
# 函数说明：把合成音频下载到本地文件。
# ---------------------------
def download_audio_file(audio_url, output_file_path):
    # 步骤1：创建输出目录。
    resolved_output_path = pathlib.Path(output_file_path).expanduser().resolve()
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    # 步骤2：流式下载音频，避免一次性占用过多内存。
    try:
        response = requests.get(audio_url, stream=True, timeout=300)
        response.raise_for_status()
        with resolved_output_path.open("wb") as output_file:
            for audio_chunk in response.iter_content(chunk_size=65536):
                if audio_chunk:
                    output_file.write(audio_chunk)
    except requests.RequestException as error:
        raise click.ClickException("下载合成音频失败：" + str(error))
    except OSError as error:
        raise click.ClickException("写入合成音频失败：" + str(error))

    # 步骤3：返回文件路径和实际大小。
    output_size = resolved_output_path.stat().st_size
    if output_size == 0:
        raise click.ClickException("下载的合成音频为空文件")
    return str(resolved_output_path), output_size


# ---------------------------
# 函数说明：调用 Qwen-Audio-TTS 非实时 HTTP 接口。
# ---------------------------
def call_speech_synthesis(api_key, synthesis_input, model_name):
    # 步骤1：构造固定模型的 HTTP 请求。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    request_data = {
        "model": model_name,
        "input": synthesis_input,
    }

    # 步骤2：发送请求并读取 JSON 响应。
    try:
        response = requests.post(
            SPEECH_SYNTHESIS_API_URL,
            headers=headers,
            json=request_data,
            timeout=300,
        )
    except requests.RequestException as error:
        raise click.ClickException("语音合成请求失败：" + str(error))
    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "语音合成接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )

    # 步骤3：转换接口错误并返回成功结果。
    if response.status_code != 200:
        error_code = response_data.get("code")
        error_message = response_data.get("message")
        raise click.ClickException(
            "语音合成接口返回错误："
            + str(error_code)
            + "，"
            + str(error_message)
        )
    return response_data


# ---------------------------
# 函数说明：创建语音生成命令组。
# ---------------------------
@click.group()
def cli():
    """使用 Qwen-Audio-TTS 复刻音色并生成语音。"""
    pass


# ---------------------------
# 函数说明：使用本地文件或公网 URL 创建复刻音色。
# ---------------------------
@cli.command(name="voice-clone-create")
@click.argument("audio_source")
@click.option(
    "--prefix",
    required=True,
    metavar="<音色前缀>",
    help="1 到 10 位小写字母或数字",
)
@click.option(
    "--model",
    "model_name",
    type=click.Choice(TTS_MODEL_NAMES, case_sensitive=True),
    default=DEFAULT_TTS_MODEL_NAME,
    show_default=True,
    help="绑定的 Qwen-Audio-TTS 模型，默认最高质量 Plus",
)
@click.option(
    "--language-hint",
    "language_hints",
    multiple=True,
    metavar="<语言代码>",
    help="提示样本语言，可重复传入",
)
@click.option(
    "--max-prompt-audio-length",
    type=click.FloatRange(min=1.0, max=60.0),
    default=20.0,
    show_default=True,
    metavar="<秒>",
    help="预处理后最多保留的声音样本时长",
)
def voice_clone_create_command(
    audio_source,
    prefix,
    model_name,
    language_hints,
    max_prompt_audio_length,
):
    """创建绑定所选 Qwen-Audio-TTS 模型的复刻音色。"""
    # 步骤1：检查前缀并读取密钥。
    try:
        validate_voice_prefix(prefix)
    except ValueError as error:
        raise click.ClickException(str(error))
    api_key = get_api_key()

    # 步骤2：准备公网或 DashScope OSS 声音样本地址。
    source_type, prepared_audio_url, uploaded_file_id = prepare_voice_sample(
        audio_source,
        api_key,
    )

    # 步骤3：调用声音复刻服务创建音色。
    service = create_voice_enrollment_service(api_key)
    language_hint_list = None
    if language_hints:
        language_hint_list = list(language_hints)
    temporary_upload_deleted = True
    try:
        voice_id = service.create_voice(
            target_model=model_name,
            prefix=prefix,
            url=prepared_audio_url,
            language_hints=language_hint_list,
            max_prompt_audio_length=max_prompt_audio_length,
        )
    except VoiceEnrollmentException as error:
        raise click.ClickException("创建复刻音色失败：" + str(error))
    except Exception as error:
        raise click.ClickException("创建复刻音色失败：" + str(error))
    finally:
        temporary_upload_deleted = delete_temporary_uploaded_file(
            uploaded_file_id,
            api_key,
        )

    # 步骤4：输出可供合成命令直接使用的音色 ID。
    result = {
        "voice_id": voice_id,
        "target_model": model_name,
        "prefix": prefix,
        "source_type": source_type,
        "language_hints": language_hint_list,
        "max_prompt_audio_length": max_prompt_audio_length,
        "temporary_upload_deleted": temporary_upload_deleted,
        "request_id": service.get_last_request_id(),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：列出当前账号的复刻音色。
# ---------------------------
@cli.command(name="voice-clone-list")
@click.option(
    "--prefix",
    default=None,
    metavar="<音色前缀>",
    help="只列出指定前缀的音色",
)
@click.option(
    "--page-index",
    type=click.IntRange(min=0),
    default=0,
    show_default=True,
    help="分页索引",
)
@click.option(
    "--page-size",
    type=click.IntRange(min=1, max=100),
    default=10,
    show_default=True,
    help="每页音色数量",
)
def voice_clone_list_command(prefix, page_index, page_size):
    """列出 Qwen-Audio-TTS 复刻音色。"""
    # 步骤1：读取密钥并创建服务。
    api_key = get_api_key()
    service = create_voice_enrollment_service(api_key)

    # 步骤2：查询指定分页的音色列表。
    try:
        voices = service.list_voices(
            prefix=prefix,
            page_index=page_index,
            page_size=page_size,
        )
    except VoiceEnrollmentException as error:
        raise click.ClickException("查询复刻音色列表失败：" + str(error))
    except Exception as error:
        raise click.ClickException("查询复刻音色列表失败：" + str(error))

    # 步骤3：输出列表和查询条件。
    result = {
        "count": len(voices),
        "voices": voices,
        "prefix": prefix,
        "page_index": page_index,
        "page_size": page_size,
        "request_id": service.get_last_request_id(),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：查询一个复刻音色的详细信息。
# ---------------------------
@cli.command(name="voice-clone-status")
@click.argument("voice_id")
def voice_clone_status_command(voice_id):
    """查询一个 Qwen-Audio-TTS 复刻音色。"""
    # 步骤1：读取密钥并创建服务。
    api_key = get_api_key()
    service = create_voice_enrollment_service(api_key)

    # 步骤2：查询音色详情。
    try:
        voice_details = service.query_voice(voice_id)
    except VoiceEnrollmentException as error:
        raise click.ClickException("查询复刻音色失败：" + str(error))
    except Exception as error:
        raise click.ClickException("查询复刻音色失败：" + str(error))

    # 步骤3：输出音色详情。
    safe_voice_details = sanitize_voice_details(voice_details)
    result = {
        "voice_id": voice_id,
        "details": safe_voice_details,
        "request_id": service.get_last_request_id(),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：删除一个复刻音色。
# ---------------------------
@cli.command(name="voice-clone-delete")
@click.argument("voice_id")
def voice_clone_delete_command(voice_id):
    """删除一个 Qwen-Audio-TTS 复刻音色。"""
    # 步骤1：读取密钥并创建服务。
    api_key = get_api_key()
    service = create_voice_enrollment_service(api_key)

    # 步骤2：删除指定音色。
    try:
        service.delete_voice(voice_id)
    except VoiceEnrollmentException as error:
        raise click.ClickException("删除复刻音色失败：" + str(error))
    except Exception as error:
        raise click.ClickException("删除复刻音色失败：" + str(error))

    # 步骤3：输出删除结果。
    result = {
        "voice_id": voice_id,
        "deleted": True,
        "request_id": service.get_last_request_id(),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：使用系统音色或复刻音色执行非实时语音合成。
# ---------------------------
@cli.command(name="synthesize")
@click.option(
    "--text",
    required=True,
    metavar="<待合成文本>",
    help="支持直接嵌入 Qwen-Audio-TTS 情感和拟声标签",
)
@click.option(
    "--voice",
    required=True,
    metavar="<音色ID>",
    help="系统音色或 voice-clone-create 返回的复刻音色",
)
@click.option(
    "--model",
    "model_name",
    type=click.Choice(TTS_MODEL_NAMES, case_sensitive=True),
    default=DEFAULT_TTS_MODEL_NAME,
    show_default=True,
    help="使用的 Qwen-Audio-TTS 模型，默认最高质量 Plus",
)
@click.option(
    "--output",
    "output_file_path",
    default=str(DEFAULT_OUTPUT_FILE),
    show_default=True,
    type=click.Path(dir_okay=False),
    metavar="<输出文件>",
    help="下载合成音频到该文件",
)
@click.option(
    "--format",
    "audio_format",
    type=click.Choice(["wav", "mp3", "pcm"], case_sensitive=False),
    default="wav",
    show_default=True,
    help="输出音频格式",
)
@click.option(
    "--sample-rate",
    type=click.IntRange(min=8000, max=48000),
    default=24000,
    show_default=True,
    metavar="<采样率Hz>",
    help="输出音频采样率",
)
@click.option(
    "--instruction",
    default=None,
    metavar="<声音控制指令>",
    help="控制音调、语速、情感、方言或音色特点",
)
def synthesize_command(
    text,
    voice,
    model_name,
    output_file_path,
    audio_format,
    sample_rate,
    instruction,
):
    """执行 Qwen-Audio-TTS 非实时语音合成并下载结果。"""
    # 步骤1：检查文本和输出扩展名。
    if not text.strip():
        raise click.ClickException("待合成文本不能为空")
    output_suffix = pathlib.Path(output_file_path).suffix.lower()
    expected_suffix = "." + audio_format.lower()
    if output_suffix != expected_suffix:
        raise click.ClickException(
            "输出文件扩展名必须与 --format 一致，应为 " + expected_suffix
        )

    # 步骤2：构造参数并调用非实时合成接口。
    api_key = get_api_key()
    synthesis_input = build_synthesis_input(
        text,
        voice,
        audio_format,
        sample_rate,
        instruction,
    )
    response_data = call_speech_synthesis(
        api_key,
        synthesis_input,
        model_name,
    )
    audio_result = extract_synthesis_result(response_data)

    # 步骤3：下载音频到本地输出目录。
    resolved_output_path, output_size = download_audio_file(
        audio_result["url"],
        output_file_path,
    )
    safe_audio_result = sanitize_synthesis_result(audio_result)

    # 步骤4：输出合成结果和文件信息。
    result = {
        "model": model_name,
        "voice": voice,
        "text": text,
        "format": audio_format,
        "sample_rate": sample_rate,
        "instruction": instruction,
        "expires_at": safe_audio_result["expires_at"],
        "output_file": resolved_output_path,
        "output_bytes": output_size,
        "request_id": response_data.get("request_id"),
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行语音生成 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动 Click 命令组。
    cli()
