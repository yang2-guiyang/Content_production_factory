import io
import json
import pathlib
import sys

# 步骤0：仅在需要时切换为 UTF-8，避免统一入口重复导入时关闭输出流。
standard_output_encoding = getattr(sys.stdout, "encoding", "") or ""
normalized_output_encoding = standard_output_encoding.lower().replace("-", "")
if normalized_output_encoding != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import dashscope
import requests

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


DEFAULT_MODEL_NAME = "qwen3.7-plus"
DEFAULT_OCR_MODEL_NAME = "qwen3.5-ocr"
OCR_RESPONSES_API_URL = (
    "https://dashscope.aliyuncs.com/compatible-mode/v1/responses"
)
MAX_LOCAL_IMAGE_BYTES = 10 * 1024 * 1024
MAX_LOCAL_OCR_IMAGE_BYTES = 20 * 1024 * 1024
MAX_LOCAL_VIDEO_BYTES = 100 * 1024 * 1024
OCR_TASK_NAMES = (
    "advanced_recognition",
    "key_information_extraction",
    "table_parsing",
    "document_parsing",
    "formula_recognition",
    "text_recognition",
    "multi_lan",
)
IMAGE_EXTENSIONS = {
    ".bmp",
    ".heic",
    ".jpe",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
VIDEO_EXTENSIONS = {
    ".avi",
    ".flv",
    ".mkv",
    ".mov",
    ".mp4",
    ".wmv",
}


# ---------------------------
# 函数说明：把公网 URL 或本地文件转换为模型可读取的媒体地址。
# ---------------------------
def prepare_media_source(media_source, media_type, local_size_limit_bytes=None):
    # 步骤1：公网 URL 和 Data URL 直接交给模型处理。
    if media_source.startswith("http://"):
        return media_source
    if media_source.startswith("https://"):
        return media_source
    if media_source.startswith("data:"):
        return media_source
    if media_source.startswith("file://"):
        return media_source

    # 步骤2：解析并检查本地文件。
    media_file_path = pathlib.Path(media_source).expanduser().resolve()
    if not media_file_path.exists():
        raise click.ClickException("媒体文件不存在：" + str(media_file_path))
    if not media_file_path.is_file():
        raise click.ClickException("媒体路径不是文件：" + str(media_file_path))

    # 步骤3：按媒体类型检查扩展名和文件大小。
    file_extension = media_file_path.suffix.lower()
    file_size = media_file_path.stat().st_size
    if media_type == "image":
        if file_extension not in IMAGE_EXTENSIONS:
            raise click.ClickException("不支持的图像格式：" + file_extension)
        image_size_limit = MAX_LOCAL_IMAGE_BYTES
        if local_size_limit_bytes is not None:
            image_size_limit = local_size_limit_bytes
        if file_size > image_size_limit:
            size_limit_megabytes = image_size_limit // (1024 * 1024)
            raise click.ClickException(
                "本地图像不能超过 "
                + str(size_limit_megabytes)
                + " MB，请改用公网 URL"
            )
    else:
        if file_extension not in VIDEO_EXTENSIONS:
            raise click.ClickException("不支持的视频格式：" + file_extension)
        if file_size > MAX_LOCAL_VIDEO_BYTES:
            raise click.ClickException("本地视频不能超过 100 MB，请改用公网 URL")

    # 步骤4：使用 DashScope Python SDK 支持的 Windows 本地文件 URI。
    normalized_path = media_file_path.as_posix()
    return "file://" + normalized_path


# ---------------------------
# 函数说明：从 DashScope 多模态响应中提取回复和思考内容。
# ---------------------------
def extract_visual_response(response):
    # 步骤1：检查响应状态。
    status_code = getattr(response, "status_code", None)
    if status_code != 200:
        error_code = getattr(response, "code", "")
        error_message = getattr(response, "message", "")
        raise click.ClickException(
            "视觉理解接口返回错误：" + str(error_code) + "，" + str(error_message)
        )

    # 步骤2：读取第一条回复消息。
    output_data = response.output
    choices = output_data.get("choices")
    if not choices:
        raise click.ClickException("响应中缺少 output.choices 字段")
    first_choice = choices[0]
    message_data = first_choice.get("message")
    if not message_data:
        raise click.ClickException("响应中缺少 message 字段")

    # 步骤3：合并回复中的全部文本片段。
    answer_parts = []
    content_items = message_data.get("content")
    if content_items:
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            content_text = content_item.get("text")
            if content_text:
                answer_parts.append(content_text)
    answer_text = "".join(answer_parts)
    if not answer_text:
        raise click.ClickException("响应中没有可用的回复文本")

    # 步骤4：保留思考内容和结束原因。
    reasoning_content = message_data.get("reasoning_content")
    return answer_text, reasoning_content, first_choice.get("finish_reason")


# ---------------------------
# 函数说明：构造并校验 DashScope OCR 内置任务参数。
# ---------------------------
def build_ocr_options(task_name, result_schema):
    # 步骤1：创建指定的内置任务参数。
    ocr_options = {
        "task": task_name,
    }

    # 步骤2：仅允许信息抽取任务使用结果 Schema。
    if result_schema is not None:
        if task_name != "key_information_extraction":
            raise ValueError("只有 key_information_extraction 任务支持结果 Schema")
        ocr_options["task_config"] = {
            "result_schema": result_schema,
        }
    return ocr_options


# ---------------------------
# 函数说明：读取命令行 JSON 或 JSON 文件中的信息抽取 Schema。
# ---------------------------
def load_result_schema(schema_text, schema_file_path):
    # 步骤1：检查两种 Schema 输入方式不能同时使用。
    if schema_text and schema_file_path:
        raise click.ClickException("--schema 和 --schema-file 只能使用一个")

    # 步骤2：从参数或文件中读取 JSON 文本。
    raw_schema_text = schema_text
    if schema_file_path:
        resolved_schema_path = pathlib.Path(schema_file_path).expanduser().resolve()
        if not resolved_schema_path.exists():
            raise click.ClickException("Schema 文件不存在：" + str(resolved_schema_path))
        if not resolved_schema_path.is_file():
            raise click.ClickException("Schema 路径不是文件：" + str(resolved_schema_path))
        try:
            raw_schema_text = resolved_schema_path.read_text(encoding="utf-8")
        except OSError as error:
            raise click.ClickException("读取 Schema 文件失败：" + str(error))

    # 步骤3：没有输入时返回空值。
    if not raw_schema_text:
        return None

    # 步骤4：解析并检查 JSON Schema 顶层类型。
    try:
        result_schema = json.loads(raw_schema_text)
    except json.JSONDecodeError as error:
        raise click.ClickException("Schema 不是有效 JSON：" + str(error))
    if not isinstance(result_schema, dict):
        raise click.ClickException("Schema 顶层必须是 JSON 对象")
    return result_schema


# ---------------------------
# 函数说明：从 DashScope OCR 响应中提取文本和结构化结果。
# ---------------------------
def extract_ocr_response(response):
    # 步骤1：检查响应状态和回复结构。
    status_code = getattr(response, "status_code", None)
    if status_code != 200:
        error_code = getattr(response, "code", "")
        error_message = getattr(response, "message", "")
        raise click.ClickException(
            "OCR 接口返回错误：" + str(error_code) + "，" + str(error_message)
        )
    output_data = response.output
    choices = output_data.get("choices")
    if not choices:
        raise click.ClickException("OCR 响应中缺少 output.choices 字段")
    first_choice = choices[0]
    message_data = first_choice.get("message")
    if not message_data:
        raise click.ClickException("OCR 响应中缺少 message 字段")

    # 步骤2：逐项收集文本和 OCR 结构化结果。
    text_parts = []
    ocr_results = []
    content_items = message_data.get("content")
    if content_items:
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            content_text = content_item.get("text")
            if content_text:
                text_parts.append(content_text)
            ocr_result = content_item.get("ocr_result")
            if ocr_result is not None:
                ocr_results.append(ocr_result)

    # 步骤3：按结果数量返回易用的结构。
    answer_text = "".join(text_parts)
    structured_result = None
    if len(ocr_results) == 1:
        structured_result = ocr_results[0]
    if len(ocr_results) > 1:
        structured_result = ocr_results
    if not answer_text and structured_result is None:
        raise click.ClickException("OCR 响应中没有可用结果")
    return answer_text, structured_result, first_choice.get("finish_reason")


# ---------------------------
# 函数说明：从 Responses API 结果中提取 PDF 文本和页面布局。
# ---------------------------
def extract_pdf_ocr_response(response_data):
    # 步骤1：检查并遍历输出项。
    output_items = response_data.get("output")
    if not output_items:
        raise click.ClickException("PDF OCR 响应中缺少 output 字段")
    text_parts = []
    ocr_results = []
    for output_item in output_items:
        if not isinstance(output_item, dict):
            continue
        content_items = output_item.get("content")
        if not content_items:
            continue
        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue
            content_text = content_item.get("text")
            if content_text:
                text_parts.append(content_text)
            ocr_result = content_item.get("ocr_result")
            if ocr_result is not None:
                ocr_results.append(ocr_result)

    # 步骤2：合并文本并保留全部页面布局结果。
    answer_text = "\n".join(text_parts)
    structured_result = None
    if len(ocr_results) == 1:
        structured_result = ocr_results[0]
    if len(ocr_results) > 1:
        structured_result = ocr_results
    if not answer_text and structured_result is None:
        raise click.ClickException("PDF OCR 响应中没有可用结果")
    return answer_text, structured_result


# ---------------------------
# 函数说明：调用视觉理解模型并返回统一 JSON 结果。
# ---------------------------
def call_visual_model(
    content_items,
    model_name,
    enable_thinking,
    thinking_budget,
    high_resolution,
    max_tokens,
):
    # 步骤1：读取现有 DashScope API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：构造用户消息和可选模型参数。
    messages = [
        {
            "role": "user",
            "content": content_items,
        }
    ]
    call_parameters = {
        "api_key": api_key,
        "model": model_name,
        "messages": messages,
        "enable_thinking": enable_thinking,
        "max_tokens": max_tokens,
        "vl_high_resolution_images": high_resolution,
    }
    if thinking_budget is not None:
        call_parameters["thinking_budget"] = thinking_budget

    # 步骤3：执行请求并转换常见异常。
    try:
        response = dashscope.MultiModalConversation.call(**call_parameters)
    except Exception as error:
        raise click.ClickException("视觉理解请求失败：" + str(error))

    # 步骤4：提取结构化结果。
    answer_text, reasoning_content, finish_reason = extract_visual_response(response)
    result = {
        "text": answer_text,
        "reasoning_content": reasoning_content,
        "model": model_name,
        "thinking": enable_thinking,
        "high_resolution": high_resolution,
        "finish_reason": finish_reason,
        "request_id": response.request_id,
        "usage": response.usage,
    }
    return result


# ---------------------------
# 函数说明：调用 Qwen-OCR 图像接口并返回统一 JSON 结果。
# ---------------------------
def call_ocr_model(content_items, model_name, ocr_options, max_tokens):
    # 步骤1：读取现有 DashScope API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：构造 OCR 请求参数。
    messages = [
        {
            "role": "user",
            "content": content_items,
        }
    ]
    call_parameters = {
        "api_key": api_key,
        "model": model_name,
        "messages": messages,
        "ocr_options": ocr_options,
        "max_tokens": max_tokens,
    }

    # 步骤3：执行请求并转换常见异常。
    try:
        response = dashscope.MultiModalConversation.call(**call_parameters)
    except Exception as error:
        raise click.ClickException("OCR 请求失败：" + str(error))

    # 步骤4：保留文本和专用 OCR 结构化结果。
    answer_text, ocr_result, finish_reason = extract_ocr_response(response)
    result = {
        "text": answer_text,
        "ocr_result": ocr_result,
        "model": model_name,
        "task": ocr_options.get("task"),
        "finish_reason": finish_reason,
        "request_id": response.request_id,
        "usage": response.usage,
    }
    return result


# ---------------------------
# 函数说明：通过 Responses API 直接解析公网 PDF。
# ---------------------------
def call_pdf_ocr(pdf_url, model_name):
    # 步骤1：读取现有 DashScope API Key。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException("未配置 DASHSCOPE_API_KEY")

    # 步骤2：构造固定的 PDF 文档解析请求。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }
    request_data = {
        "model": model_name,
        "ocr_options": {
            "task": "document_parsing",
        },
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_url": pdf_url,
                    }
                ],
            }
        ],
    }

    # 步骤3：发送请求并读取 JSON 响应。
    try:
        response = requests.post(
            OCR_RESPONSES_API_URL,
            headers=headers,
            json=request_data,
            timeout=600,
        )
    except requests.RequestException as error:
        raise click.ClickException("PDF OCR 请求失败：" + str(error))
    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "PDF OCR 接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )
    if response.status_code != 200:
        error_data = response_data.get("error")
        raise click.ClickException(
            "PDF OCR 接口返回错误，HTTP "
            + str(response.status_code)
            + "："
            + json.dumps(error_data, ensure_ascii=False)
        )

    # 步骤4：提取文本、布局和用量信息。
    answer_text, ocr_result = extract_pdf_ocr_response(response_data)
    result = {
        "text": answer_text,
        "ocr_result": ocr_result,
        "model": model_name,
        "task": "document_parsing",
        "input_type": "pdf_url",
        "input": pdf_url,
        "request_id": response_data.get("id"),
        "status": response_data.get("status"),
        "usage": response_data.get("usage"),
    }
    return result


# ---------------------------
# 函数说明：创建视觉理解命令组。
# ---------------------------
@click.group()
def cli():
    """分析图片、视频文件和视频帧。"""
    pass


# ---------------------------
# 函数说明：分析一张或多张图片。
# ---------------------------
@cli.command(name="analyze-images")
@click.option(
    "--image",
    "image_sources",
    multiple=True,
    required=True,
    metavar="<图片路径或URL>",
    help="输入图片，可重复使用以传入多张图片",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<问题或任务>",
    help="描述、问答、OCR、定位或信息抽取要求",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_MODEL_NAME,
    show_default=True,
    metavar="<模型名称>",
    help="使用的视觉理解模型",
)
@click.option(
    "--thinking/--no-thinking",
    "enable_thinking",
    default=True,
    show_default=True,
    help="是否开启模型思考模式",
)
@click.option(
    "--thinking-budget",
    type=click.IntRange(min=1),
    default=None,
    metavar="<Token数>",
    help="思考过程最大 Token 数",
)
@click.option(
    "--high-resolution/--standard-resolution",
    "high_resolution",
    default=True,
    show_default=True,
    help="是否启用高分辨率图像模式",
)
@click.option(
    "--min-pixels",
    type=click.IntRange(min=1),
    default=None,
    metavar="<像素数>",
    help="每张图片的最小像素阈值",
)
@click.option(
    "--max-pixels",
    type=click.IntRange(min=1),
    default=None,
    metavar="<像素数>",
    help="标准分辨率模式下每张图片的最大像素阈值",
)
@click.option(
    "--max-tokens",
    type=click.IntRange(min=1),
    default=8192,
    show_default=True,
    metavar="<Token数>",
    help="模型回复最大 Token 数",
)
def analyze_images_command(
    image_sources,
    prompt,
    model_name,
    enable_thinking,
    thinking_budget,
    high_resolution,
    min_pixels,
    max_pixels,
    max_tokens,
):
    """分析单图或多图，任务类型由提示词决定。"""
    # 步骤1：检查相互冲突的图像参数。
    if high_resolution and max_pixels is not None:
        raise click.ClickException("高分辨率模式会忽略 max_pixels，请只选择一种方式")

    # 步骤2：逐张准备图片内容。
    content_items = []
    resolved_sources = []
    for image_source in image_sources:
        resolved_source = prepare_media_source(image_source, "image")
        image_item = {
            "image": resolved_source,
        }
        if min_pixels is not None:
            image_item["min_pixels"] = min_pixels
        if max_pixels is not None:
            image_item["max_pixels"] = max_pixels
        content_items.append(image_item)
        resolved_sources.append(resolved_source)
    content_items.append({"text": prompt})

    # 步骤3：调用模型并补充输入摘要。
    result = call_visual_model(
        content_items,
        model_name,
        enable_thinking,
        thinking_budget,
        high_resolution,
        max_tokens,
    )
    result["input_type"] = "images"
    result["inputs"] = resolved_sources
    result["prompt"] = prompt
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：使用 Qwen-OCR 识别一张或多张图片。
# ---------------------------
@cli.command(name="ocr")
@click.option(
    "--image",
    "image_sources",
    multiple=True,
    required=True,
    metavar="<图片路径或URL>",
    help="输入图片，可重复使用以传入多张图片",
)
@click.option(
    "--task",
    "task_name",
    type=click.Choice(OCR_TASK_NAMES, case_sensitive=True),
    default="text_recognition",
    show_default=True,
    help="选择 Qwen-OCR 内置任务",
)
@click.option(
    "--prompt",
    default=None,
    metavar="<补充要求>",
    help="在内置任务之外补充用户要求",
)
@click.option(
    "--schema",
    "schema_text",
    default=None,
    metavar="<JSON对象>",
    help="信息抽取任务使用的 JSON 字段模板",
)
@click.option(
    "--schema-file",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="<JSON文件>",
    help="从 UTF-8 JSON 文件读取信息抽取字段模板",
)
@click.option(
    "--rotate/--no-rotate",
    "enable_rotate",
    default=True,
    show_default=True,
    help="是否自动矫正倾斜或旋转图像",
)
@click.option(
    "--min-pixels",
    type=click.IntRange(min=1),
    default=None,
    metavar="<像素数>",
    help="每张图片的最小像素阈值",
)
@click.option(
    "--max-pixels",
    type=click.IntRange(min=1),
    default=None,
    metavar="<像素数>",
    help="每张图片的最大像素阈值",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_OCR_MODEL_NAME,
    show_default=True,
    metavar="<模型名称>",
    help="使用的 Qwen-OCR 模型",
)
@click.option(
    "--max-tokens",
    type=click.IntRange(min=1),
    default=8192,
    show_default=True,
    metavar="<Token数>",
    help="模型回复最大 Token 数",
)
def ocr_command(
    image_sources,
    task_name,
    prompt,
    schema_text,
    schema_file,
    enable_rotate,
    min_pixels,
    max_pixels,
    model_name,
    max_tokens,
):
    """识别图片文字、表格、公式、布局或结构化字段。"""
    # 步骤1：读取 Schema 并构造 OCR 内置任务参数。
    result_schema = load_result_schema(schema_text, schema_file)
    try:
        ocr_options = build_ocr_options(task_name, result_schema)
    except ValueError as error:
        raise click.ClickException(str(error))

    # 步骤2：逐张准备图片和图像处理参数。
    content_items = []
    resolved_sources = []
    for image_source in image_sources:
        resolved_source = prepare_media_source(
            image_source,
            "image",
            MAX_LOCAL_OCR_IMAGE_BYTES,
        )
        image_item = {
            "image": resolved_source,
            "enable_rotate": enable_rotate,
        }
        if min_pixels is not None:
            image_item["min_pixels"] = min_pixels
        if max_pixels is not None:
            image_item["max_pixels"] = max_pixels
        content_items.append(image_item)
        resolved_sources.append(resolved_source)
    if prompt:
        content_items.append({"text": prompt})

    # 步骤3：调用 OCR 模型并补充输入摘要。
    result = call_ocr_model(
        content_items,
        model_name,
        ocr_options,
        max_tokens,
    )
    result["input_type"] = "images"
    result["inputs"] = resolved_sources
    result["prompt"] = prompt
    result["rotate"] = enable_rotate
    result["min_pixels"] = min_pixels
    result["max_pixels"] = max_pixels
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：使用 Qwen-OCR 直接解析公网 PDF。
# ---------------------------
@cli.command(name="ocr-pdf")
@click.option(
    "--pdf-url",
    required=True,
    metavar="<公网PDF URL>",
    help="输入不超过 50 页、100 MB 的公网 PDF",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_OCR_MODEL_NAME,
    show_default=True,
    metavar="<模型名称>",
    help="使用的 Qwen-OCR 模型",
)
def ocr_pdf_command(pdf_url, model_name):
    """通过 Responses API 直接解析公网 PDF。"""
    # 步骤1：检查 PDF 必须使用公网 URL。
    is_http_url = pdf_url.startswith("http://")
    is_https_url = pdf_url.startswith("https://")
    if not is_http_url and not is_https_url:
        raise click.ClickException("PDF 目前只支持公网 http:// 或 https:// URL")

    # 步骤2：调用 PDF OCR 并输出完整 JSON。
    result = call_pdf_ocr(pdf_url, model_name)
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：分析视频文件。
# ---------------------------
@cli.command(name="analyze-video")
@click.option(
    "--video",
    "video_source",
    required=True,
    metavar="<视频路径或URL>",
    help="输入一个视频文件",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<问题或任务>",
    help="视频摘要、事件定位或时间戳提取要求",
)
@click.option(
    "--fps",
    type=click.FloatRange(min=0.1, max=10.0),
    default=2.0,
    show_default=True,
    metavar="<0.1-10>",
    help="每秒抽取的视频帧数",
)
@click.option(
    "--max-frames",
    type=click.IntRange(min=1),
    default=None,
    metavar="<帧数>",
    help="视频最多抽取帧数",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_MODEL_NAME,
    show_default=True,
    metavar="<模型名称>",
    help="使用的视觉理解模型",
)
@click.option(
    "--thinking/--no-thinking",
    "enable_thinking",
    default=True,
    show_default=True,
    help="是否开启模型思考模式",
)
@click.option(
    "--thinking-budget",
    type=click.IntRange(min=1),
    default=None,
    metavar="<Token数>",
    help="思考过程最大 Token 数",
)
@click.option(
    "--max-tokens",
    type=click.IntRange(min=1),
    default=8192,
    show_default=True,
    metavar="<Token数>",
    help="模型回复最大 Token 数",
)
def analyze_video_command(
    video_source,
    prompt,
    fps,
    max_frames,
    model_name,
    enable_thinking,
    thinking_budget,
    max_tokens,
):
    """分析视频文件并按提示词生成结果。"""
    # 步骤1：准备视频内容和抽帧参数。
    resolved_source = prepare_media_source(video_source, "video")
    video_item = {
        "video": resolved_source,
        "fps": fps,
    }
    if max_frames is not None:
        video_item["max_frames"] = max_frames
    content_items = [
        video_item,
        {"text": prompt},
    ]

    # 步骤2：调用模型并补充输入摘要。
    result = call_visual_model(
        content_items,
        model_name,
        enable_thinking,
        thinking_budget,
        False,
        max_tokens,
    )
    result["input_type"] = "video"
    result["inputs"] = [resolved_source]
    result["prompt"] = prompt
    result["fps"] = fps
    result["max_frames"] = max_frames
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：把预先抽取的图片按视频帧序列分析。
# ---------------------------
@cli.command(name="analyze-frames")
@click.option(
    "--frame",
    "frame_sources",
    multiple=True,
    required=True,
    metavar="<帧图片路径或URL>",
    help="按时间顺序输入视频帧，至少重复使用 4 次",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<问题或任务>",
    help="描述帧序列中的事件、动作或时间关系",
)
@click.option(
    "--fps",
    type=click.FloatRange(min=0.1, max=10.0),
    default=2.0,
    show_default=True,
    metavar="<0.1-10>",
    help="这些帧来自原视频时的抽帧率",
)
@click.option(
    "--model",
    "model_name",
    default=DEFAULT_MODEL_NAME,
    show_default=True,
    metavar="<模型名称>",
    help="使用的视觉理解模型",
)
@click.option(
    "--thinking/--no-thinking",
    "enable_thinking",
    default=True,
    show_default=True,
    help="是否开启模型思考模式",
)
@click.option(
    "--thinking-budget",
    type=click.IntRange(min=1),
    default=None,
    metavar="<Token数>",
    help="思考过程最大 Token 数",
)
@click.option(
    "--max-tokens",
    type=click.IntRange(min=1),
    default=8192,
    show_default=True,
    metavar="<Token数>",
    help="模型回复最大 Token 数",
)
def analyze_frames_command(
    frame_sources,
    prompt,
    fps,
    model_name,
    enable_thinking,
    thinking_budget,
    max_tokens,
):
    """把至少四张图片作为连续视频帧分析。"""
    # 步骤1：检查帧数量并逐帧准备媒体地址。
    if len(frame_sources) < 4:
        raise click.ClickException("视频帧列表至少需要 4 张图片")
    resolved_sources = []
    for frame_source in frame_sources:
        resolved_source = prepare_media_source(frame_source, "image")
        resolved_sources.append(resolved_source)

    # 步骤2：按视频帧列表格式构造消息。
    content_items = [
        {
            "video": resolved_sources,
            "fps": fps,
        },
        {
            "text": prompt,
        },
    ]

    # 步骤3：调用模型并补充输入摘要。
    result = call_visual_model(
        content_items,
        model_name,
        enable_thinking,
        thinking_budget,
        False,
        max_tokens,
    )
    result["input_type"] = "video_frames"
    result["inputs"] = resolved_sources
    result["prompt"] = prompt
    result["fps"] = fps
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行视觉理解 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动 Click 命令组。
    cli()
