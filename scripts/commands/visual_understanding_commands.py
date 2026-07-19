import io
import json
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import dashscope

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


DEFAULT_MODEL_NAME = "qwen3.7-plus"
MAX_LOCAL_IMAGE_BYTES = 10 * 1024 * 1024
MAX_LOCAL_VIDEO_BYTES = 100 * 1024 * 1024
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
def prepare_media_source(media_source, media_type):
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
        if file_size > MAX_LOCAL_IMAGE_BYTES:
            raise click.ClickException("本地图像不能超过 10 MB，请改用公网 URL")
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
    default=False,
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
    default=False,
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
    default=2048,
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
    default=False,
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
    default=2048,
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
    default=False,
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
    default=2048,
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
