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
import requests

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
PROJECT_DIRECTORY = SCRIPTS_DIRECTORY.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


# ---------------------------
# 常量定义
# ---------------------------
MAIZI_API_BASE_URL = "https://www.maizitech.xyz"
V1_GENERATIONS_URL = MAIZI_API_BASE_URL + "/v1/images/generations"
V2_GENERATIONS_URL = MAIZI_API_BASE_URL + "/v2/images/generations"
V2_EDITS_URL = MAIZI_API_BASE_URL + "/v2/images/edits"

IMAGE_MODELS = {
    "nano-banana-2-lite": "NanoBanana 2 Lite — $0.0090/次，1K",
    "nano-banana-fast": "NanoBanana 极速 — $0.0090/次，1K",
    "gpt-image-2-vip": "GPT Image 2 VIP — $0.0220~0.0570/次，1K/2K/4K",
    "nano-banana-2": "NanoBanana 标准 — $0.0180/次，1K/2K/4K",
    "nano-banana-pro": "NanoBanana 专业 — $0.0270/次，1K/2K/4K",
    "doubao-seedream-5-0-lite": "Seedream 5.0 Lite — $0.0336/次，2K/3K/4K",
    "doubao-seedream-5-0-pro": "Seedream 5.0 Pro — $0.0432~0.0864/次，1K/2K",
    "gpt-image-2": "GPT Image 2 — $0.0090~0.0440/次，1K/2K/4K",
    "nano-banana-2-vip": "NanoBanana 2 VIP — $0.0642~0.1392/次，1K/2K/4K",
    "nano-banana-pro-vip": "NanoBanana Pro VIP — $0.1000~0.2000/次，1K/2K/4K",
    "gpt-image-2-official": "GPT Image 2 高质量 — $0.0100起/次，1K/2K/4K",
    "seed3d-v2-image-to-3d": "Seed3D 图生3D（仅 v1 异步）— 返回 ZIP",
}

DEFAULT_IMAGE_MODEL = "gpt-image-2"
VALID_SIZES = (
    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
    "5:4", "4:5", "21:9", "9:2", "1:2", "2:1", "1:3", "3:1",
)
VALID_RESOLUTIONS = ("1K", "2K", "4K")
VALID_QUALITIES = ("low", "medium", "high")
VALID_RESPONSE_FORMATS = ("b64_json", "url")
VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".heic"}

DEFAULT_OUTPUT_DIR = PROJECT_DIRECTORY / "runtime" / "outputs"
DEFAULT_TIMEOUT_SECONDS = 600
POLL_INTERVAL_SECONDS = 3


# ---------------------------
# 函数说明：读取麦子科技 API Key。
# ---------------------------
def get_api_key():
    # 步骤1：从项目 .env 读取 MAIZI_API_KEY。
    api_key = get_env_value("MAIZI_API_KEY")
    if not api_key:
        raise click.ClickException(
            "未配置 MAIZI_API_KEY，请在 scripts/.env 中设置 MAIZI_API_KEY=sk-your-key"
        )
    return api_key


# ---------------------------
# 函数说明：构造请求头。
# ---------------------------
def build_headers(api_key, content_type="application/json"):
    # 步骤1：构造 Bearer Token 认证和内容类型头。
    return {
        "Authorization": "Bearer " + api_key,
        "Content-Type": content_type,
    }


# ---------------------------
# 函数说明：确保输出目录存在。
# ---------------------------
def ensure_output_dir():
    # 步骤1：创建默认输出目录。
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------
# 函数说明：根据模型和参数生成默认输出文件名。
# ---------------------------
def build_default_output_path(model_name):
    # 步骤1：使用模型和时间戳构造文件名。
    timestamp = str(int(time.time()))
    safe_model_name = model_name.replace("-", "_")
    return str(DEFAULT_OUTPUT_DIR / f"{safe_model_name}_{timestamp}.png")


# ---------------------------
# 函数说明：从 base64 JSON 响应中解码并保存图片。
# ---------------------------
def save_b64_json(data_items, output_path, api_key):
    # 步骤1：遍历 data 列表，找到 b64_json 并解码保存。
    saved_files = []
    for index, item in enumerate(data_items):
        b64_data = item.get("b64_json")
        if not b64_data:
            continue

        # 步骤2：多图时自动编号；单图使用用户指定的路径。
        if len(data_items) > 1:
            base_path = pathlib.Path(output_path)
            numbered_path = base_path.parent / f"{base_path.stem}_{index}{base_path.suffix}"
            resolved_path = str(numbered_path)
        else:
            resolved_path = output_path

        resolved = pathlib.Path(resolved_path).expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        try:
            image_bytes = base64.b64decode(b64_data)
        except Exception as error:
            raise click.ClickException("解码 base64 图片数据失败：" + str(error))

        with resolved.open("wb") as f:
            f.write(image_bytes)
        saved_files.append({
            "index": index,
            "output_file": str(resolved),
            "output_bytes": len(image_bytes),
        })
    return saved_files


# ---------------------------
# 函数说明：从 URL 下载图片并保存。
# ---------------------------
def save_url_images(data_items, output_path, api_key):
    # 步骤1：遍历 data 列表，从 url 下载图片。
    saved_files = []
    for index, item in enumerate(data_items):
        image_url = item.get("url")
        if not image_url:
            continue

        if len(data_items) > 1:
            base_path = pathlib.Path(output_path)
            numbered_path = base_path.parent / f"{base_path.stem}_{index}{base_path.suffix}"
            resolved_path = str(numbered_path)
        else:
            resolved_path = output_path

        resolved = pathlib.Path(resolved_path).expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = requests.get(image_url, stream=True, timeout=300)
            response.raise_for_status()
            with resolved.open("wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        except requests.RequestException as error:
            raise click.ClickException("下载图片失败：" + str(error))

        output_size = resolved.stat().st_size
        saved_files.append({
            "index": index,
            "output_file": str(resolved),
            "output_bytes": output_size,
            "source_url": image_url,
        })
    return saved_files


# ---------------------------
# 函数说明：准备参考图片列表，支持本地文件和 data URI。
# ---------------------------
def prepare_reference_images(image_paths):
    # 步骤1：检查最多 9 张参考图。
    if not image_paths:
        return None
    if len(image_paths) > 9:
        raise click.ClickException("参考图片最多 9 张")

    # 步骤2：逐张解析为 data URI 或保留 URL。
    images = []
    for image_path in image_paths:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            images.append(image_path)
            continue
        if image_path.startswith("data:image/"):
            images.append(image_path)
            continue

        # 步骤3：本地文件转 base64 data URI。
        resolved = pathlib.Path(image_path).expanduser().resolve()
        if not resolved.exists():
            raise click.ClickException("参考图片不存在：" + str(resolved))
        suffix = resolved.suffix.lower()
        if suffix not in VALID_IMAGE_EXTENSIONS:
            raise click.ClickException(
                "不支持的参考图片格式：" + suffix + "，支持 PNG、JPG、JPEG、WEBP、BMP、TIFF、HEIC"
            )
        mime_type = "image/" + suffix.lstrip(".")
        if suffix == ".jpg":
            mime_type = "image/jpeg"
        with resolved.open("rb") as f:
            image_data = f.read()
        data_uri = f"data:{mime_type};base64,{base64.b64encode(image_data).decode()}"
        images.append(data_uri)
    return images


# ---------------------------
# 函数说明：调用 v1 异步图片生成接口。
# ---------------------------
def call_v1_generation(api_key, model, prompt, size, resolution, quality, images):
    # 步骤1：构造 JSON 请求体。
    request_data = {
        "model": model,
        "prompt": prompt,
    }
    if size:
        request_data["size"] = size
    if resolution:
        request_data["resolution"] = resolution
    if quality:
        request_data["quality"] = quality
    if images:
        request_data["images"] = images

    # 步骤2：发送 POST 请求。
    headers = build_headers(api_key)
    try:
        response = requests.post(
            V1_GENERATIONS_URL,
            headers=headers,
            json=request_data,
            timeout=120,
        )
    except requests.RequestException as error:
        raise click.ClickException("v1 图片生成请求失败：" + str(error))

    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "v1 图片生成接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )

    if response.status_code != 200:
        raise click.ClickException(
            "v1 图片生成接口返回错误（HTTP "
            + str(response.status_code)
            + "）："
            + json.dumps(response_data, ensure_ascii=False)
        )
    return response_data


# ---------------------------
# 函数说明：查询 v1 异步任务状态。
# ---------------------------
def query_v1_task(api_key, task_id):
    # 步骤1：GET 查询任务。
    task_url = V1_GENERATIONS_URL + "/" + task_id
    headers = build_headers(api_key)
    try:
        response = requests.get(task_url, headers=headers, timeout=30)
    except requests.RequestException as error:
        raise click.ClickException("查询任务状态失败：" + str(error))

    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "查询任务接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )

    if response.status_code != 200:
        raise click.ClickException(
            "查询任务状态失败（HTTP "
            + str(response.status_code)
            + "）："
            + json.dumps(response_data, ensure_ascii=False)
        )
    return response_data


# ---------------------------
# 函数说明：轮询 v1 异步任务直到完成或超时。
# ---------------------------
def poll_v1_task(api_key, task_id, timeout_seconds):
    # 步骤1：循环轮询直至完成、失败或超时。
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout_seconds:
            raise click.ClickException(
                "等待图片生成任务完成超时（" + str(timeout_seconds) + " 秒），"
                "可稍后使用 image query-task " + task_id + " 查询结果"
            )

        task_data = query_v1_task(api_key, task_id)
        status = task_data.get("status", "").lower()

        if status == "completed":
            return task_data
        if status == "failed":
            error_info = task_data.get("error", task_data.get("message", "未知错误"))
            raise click.ClickException("图片生成任务失败：" + str(error_info))

        time.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------
# 函数说明：调用 v2 同步图片生成接口。
# ---------------------------
def call_v2_generation(
    api_key, model, prompt, size, resolution, quality, images, response_format
):
    # 步骤1：构造 JSON 请求体。
    request_data = {
        "model": model,
        "prompt": prompt,
    }
    if size:
        request_data["size"] = size
    if resolution:
        request_data["resolution"] = resolution
    if quality:
        request_data["quality"] = quality
    if images:
        request_data["images"] = images
    if response_format:
        request_data["response_format"] = response_format

    # 步骤2：发送 POST 请求。
    headers = build_headers(api_key)
    try:
        response = requests.post(
            V2_GENERATIONS_URL,
            headers=headers,
            json=request_data,
            timeout=600,
        )
    except requests.RequestException as error:
        raise click.ClickException("v2 图片生成请求失败：" + str(error))

    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "v2 图片生成接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )

    # 步骤3：200 为成功，202 表示超时未完成。
    if response.status_code == 202:
        task_id = response_data.get("task_id", "")
        raise click.ClickException(
            "v2 同步接口超时未完成，task_id=" + str(task_id) + "，"
            "请稍后使用 image query-task " + str(task_id) + " 查询"
        )
    if response.status_code != 200:
        raise click.ClickException(
            "v2 图片生成接口返回错误（HTTP "
            + str(response.status_code)
            + "）："
            + json.dumps(response_data, ensure_ascii=False)
        )
    return response_data


# ---------------------------
# 函数说明：调用 v2 图片编辑接口（multipart/form-data）。
# ---------------------------
def call_v2_edit(api_key, model, prompt, image_path, mask_path, size, quality, response_format):
    # 步骤1：读取图片和可选遮罩，构造 multipart 请求。
    resolved_image = pathlib.Path(image_path).expanduser().resolve()
    if not resolved_image.exists():
        raise click.ClickException("待编辑图片不存在：" + str(resolved_image))

    files = {
        "image": (resolved_image.name, resolved_image.open("rb"), "application/octet-stream"),
    }
    data = {
        "prompt": prompt,
    }
    if model:
        data["model"] = model
    if size:
        data["size"] = size
    if quality:
        data["quality"] = quality
    if response_format:
        data["response_format"] = response_format

    # 步骤2：处理遮罩图片。
    mask_file_handle = None
    if mask_path:
        resolved_mask = pathlib.Path(mask_path).expanduser().resolve()
        if not resolved_mask.exists():
            raise click.ClickException("遮罩图片不存在：" + str(resolved_mask))
        mask_file_handle = resolved_mask.open("rb")
        files["mask"] = (resolved_mask.name, mask_file_handle, "application/octet-stream")

    # 步骤3：发送 multipart 请求。
    headers = {"Authorization": "Bearer " + api_key}
    try:
        response = requests.post(
            V2_EDITS_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=600,
        )
    except requests.RequestException as error:
        raise click.ClickException("图片编辑请求失败：" + str(error))
    finally:
        # 步骤4：打开的文件句柄确保关闭。
        for _, (_, file_handle, _) in files.items():
            file_handle.close()
        if mask_file_handle:
            mask_file_handle.close()

    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "图片编辑接口返回了非 JSON 内容，HTTP " + str(response.status_code)
        )

    if response.status_code != 200:
        raise click.ClickException(
            "图片编辑接口返回错误（HTTP "
            + str(response.status_code)
            + "）："
            + json.dumps(response_data, ensure_ascii=False)
        )
    return response_data


# ---------------------------
# 函数说明：处理生成/编辑响应并保存图片。
# ---------------------------
def process_image_response(response_data, output_path, api_key):
    # 步骤1：提取 data 列表。
    data_items = response_data.get("data", [])
    if not data_items:
        raise click.ClickException("API 响应中缺少 data 字段")

    # 步骤2：检查是否有错误项。
    for item in data_items:
        if item.get("error"):
            raise click.ClickException("图片生成失败：" + str(item.get("error")))

    # 步骤3：按 b64_json 或 url 分别处理。
    has_b64 = any(item.get("b64_json") for item in data_items)
    has_url = any(item.get("url") for item in data_items)

    if has_b64:
        return save_b64_json(data_items, output_path, api_key), "b64_json"
    elif has_url:
        return save_url_images(data_items, output_path, api_key), "url"
    else:
        raise click.ClickException("API 响应中既没有 b64_json 也没有 url")


# ---------------------------
# 函数说明：校验 size 参数。
# ---------------------------
def validate_size(size):
    # 步骤1：像素尺寸格式（如 1024x1024）直接通过。
    if "x" in size:
        parts = size.split("x")
        if len(parts) != 2:
            raise click.ClickException("size 像素格式应为 宽x高，如 1024x1024")
        try:
            int(parts[0])
            int(parts[1])
        except ValueError:
            raise click.ClickException("size 像素值必须为整数，如 1024x1024")
        return

    # 步骤2：比例值必须为已知比例。
    if size not in VALID_SIZES and size != "auto":
        raise click.ClickException(
            "size 必须是有效比例值（如 1:1、16:9）或像素值（如 1024x1024），"
            "当前值：" + size
        )


# ---------------------------
# 函数说明：创建图片生成命令组。
# ---------------------------
@click.group()
def cli():
    """使用麦子科技 API 生成和编辑图片。"""
    pass


# ---------------------------
# 函数说明：v2 同步文生图（推荐）。
# ---------------------------
@cli.command(name="generate")
@click.option(
    "--model",
    "model_name",
    type=click.Choice(list(IMAGE_MODELS.keys()), case_sensitive=True),
    default=DEFAULT_IMAGE_MODEL,
    show_default=True,
    help="图片生成模型",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<提示词>",
    help="描述要生成的图片内容",
)
@click.option(
    "--size",
    default=None,
    metavar="<比例或像素>",
    help="画面比例（如 1:1、16:9）或像素尺寸（如 1024x1024），默认 auto",
)
@click.option(
    "--resolution",
    type=click.Choice(VALID_RESOLUTIONS, case_sensitive=True),
    default="1K",
    show_default=True,
    metavar="<1K|2K|4K>",
    help="输出分辨率，默认 1K",
)
@click.option(
    "--quality",
    type=click.Choice(VALID_QUALITIES, case_sensitive=False),
    default="high",
    show_default=True,
    metavar="<low|medium|high>",
    help="图片质量，默认最高 high",
)
@click.option(
    "--image",
    "ref_images",
    multiple=True,
    metavar="<图片路径或URL>",
    help="参考图片，可重复传入，最多 9 张；本地文件自动转 base64",
)
@click.option(
    "--response-format",
    "response_format",
    type=click.Choice(VALID_RESPONSE_FORMATS, case_sensitive=True),
    default="b64_json",
    show_default=True,
    help="返回格式：b64_json（默认）或 url",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="<输出文件>",
    help="保存图片的路径，默认自动命名到 runtime/outputs/",
)
def generate_command(
    model_name,
    prompt,
    size,
    resolution,
    quality,
    ref_images,
    response_format,
    output_path,
):
    """v2 同步文生图，直接返回图片数据（推荐）。"""
    # 步骤1：校验参数。
    if not prompt.strip():
        raise click.ClickException("提示词不能为空")
    if model_name == "seed3d-v2-image-to-3d":
        raise click.ClickException(
            "seed3d-v2-image-to-3d 仅支持 v1 异步接口，请使用 image generate-async"
        )
    if size:
        validate_size(size)

    # 步骤2：准备参考图片和输出路径。
    api_key = get_api_key()
    ensure_output_dir()
    ref_image_list = prepare_reference_images(list(ref_images)) if ref_images else None
    resolved_output = output_path or build_default_output_path(model_name)

    # 步骤3：调用 v2 同步接口。
    response_data = call_v2_generation(
        api_key, model_name, prompt, size, resolution,
        quality, ref_image_list, response_format,
    )
    saved_files, result_format = process_image_response(
        response_data, resolved_output, api_key,
    )

    # 步骤4：输出结果。
    result = {
        "model": model_name,
        "prompt": prompt,
        "size": size,
        "resolution": resolution,
        "quality": quality,
        "response_format": response_format,
        "api_version": "v2",
        "saved_files": saved_files,
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：v1 异步文生图。
# ---------------------------
@cli.command(name="generate-async")
@click.option(
    "--model",
    "model_name",
    type=click.Choice(list(IMAGE_MODELS.keys()), case_sensitive=True),
    default=DEFAULT_IMAGE_MODEL,
    show_default=True,
    help="图片生成模型。seed3d-v2-image-to-3d 仅支持此模式",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<提示词>",
    help="描述要生成的图片内容",
)
@click.option(
    "--size",
    default=None,
    metavar="<比例或像素>",
    help="画面比例（如 1:1、16:9）或像素尺寸（如 1024x1024）",
)
@click.option(
    "--resolution",
    type=click.Choice(VALID_RESOLUTIONS, case_sensitive=True),
    default="1K",
    show_default=True,
    metavar="<1K|2K|4K>",
    help="输出分辨率，默认 1K",
)
@click.option(
    "--quality",
    type=click.Choice(VALID_QUALITIES, case_sensitive=False),
    default="high",
    show_default=True,
    metavar="<low|medium|high>",
    help="图片质量，默认最高 high",
)
@click.option(
    "--image",
    "ref_images",
    multiple=True,
    metavar="<图片路径或URL>",
    help="参考图片，可重复传入，最多 9 张",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="<输出文件>",
    help="保存图片的路径，默认自动命名到 runtime/outputs/",
)
@click.option(
    "--wait/--no-wait",
    default=True,
    show_default=True,
    help="是否等待任务完成并自动下载结果。--no-wait 仅返回 task_id",
)
@click.option(
    "--timeout",
    type=click.IntRange(min=60, max=7200),
    default=DEFAULT_TIMEOUT_SECONDS,
    show_default=True,
    metavar="<秒>",
    help="等待任务完成的最长时间",
)
@click.option(
    "--callback-url",
    default=None,
    metavar="<回调URL>",
    help="完成后的回调通知地址",
)
def generate_async_command(
    model_name,
    prompt,
    size,
    resolution,
    quality,
    ref_images,
    output_path,
    wait,
    timeout,
    callback_url,
):
    """v1 异步文生图，返回 task_id 并可选轮询下载。"""
    # 步骤1：校验参数。
    if not prompt.strip():
        raise click.ClickException("提示词不能为空")
    if size:
        validate_size(size)

    # 步骤2：准备参考图片和输出路径。
    api_key = get_api_key()
    ensure_output_dir()
    ref_image_list = prepare_reference_images(list(ref_images)) if ref_images else None
    resolved_output = output_path or build_default_output_path(model_name)

    # 步骤3：调用 v1 异步接口。
    response_data = call_v1_generation(
        api_key, model_name, prompt, size, resolution,
        quality, ref_image_list,
    )
    task_id = response_data.get("data", [{}])[0].get("task_id") if response_data.get("data") else None
    if not task_id:
        raise click.ClickException("v1 接口未返回 task_id")

    # 步骤4：仅返回 task_id 模式。
    if not wait:
        result = {
            "model": model_name,
            "prompt": prompt,
            "api_version": "v1",
            "task_id": task_id,
            "status": "pending",
            "tip": "结果文件保存 24 小时，使用 image query-task " + task_id + " 查询和下载",
            "usage": response_data.get("usage"),
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 步骤5：轮询直到完成并下载。
    completed_data = poll_v1_task(api_key, task_id, timeout)
    saved_files, _ = process_image_response(completed_data, resolved_output, api_key)

    # 步骤6：输出结果。
    result = {
        "model": model_name,
        "prompt": prompt,
        "api_version": "v1",
        "task_id": task_id,
        "status": "completed",
        "saved_files": saved_files,
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：查询 v1/v2 异步任务状态。
# ---------------------------
@cli.command(name="query-task")
@click.argument("task_id", metavar="<任务ID>")
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="<输出文件>",
    help="任务完成后保存图片的路径",
)
@click.option(
    "--timeout",
    type=click.IntRange(min=60, max=7200),
    default=DEFAULT_TIMEOUT_SECONDS,
    show_default=True,
    metavar="<秒>",
    help="等待任务完成的最长时间",
)
def query_task_command(task_id, output_path, timeout):
    """查询异步任务状态，完成后自动下载。"""
    # 步骤1：查询任务。
    api_key = get_api_key()
    task_data = query_v1_task(api_key, task_id)
    status = task_data.get("status", "").lower()

    # 步骤2：pending/processing 时进入轮询等待。
    if status in ("pending", "processing"):
        click.echo(
            json.dumps(
                {"task_id": task_id, "status": status, "tip": "任务进行中，等待完成……"},
                ensure_ascii=False,
            )
        )
        task_data = poll_v1_task(api_key, task_id, timeout)
        status = "completed"

    # 步骤3：已完成时下载结果。
    if status == "completed":
        ensure_output_dir()
        resolved_output = output_path or build_default_output_path(task_id[:16])
        saved_files, _ = process_image_response(task_data, resolved_output, api_key)
        result = {
            "task_id": task_id,
            "status": "completed",
            "saved_files": saved_files,
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 步骤4：失败状态。
    if status == "failed":
        error_info = task_data.get("error", task_data.get("message", "未知错误"))
        raise click.ClickException("任务失败：" + str(error_info))

    # 步骤5：未知状态直接输出。
    click.echo(json.dumps(task_data, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：v2 图片编辑。
# ---------------------------
@cli.command(name="edit")
@click.option(
    "--image",
    "image_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    metavar="<图片文件>",
    help="待编辑的本地图片（PNG/JPG）",
)
@click.option(
    "--prompt",
    required=True,
    metavar="<提示词>",
    help="描述编辑要求",
)
@click.option(
    "--model",
    "model_name",
    type=click.Choice(list(IMAGE_MODELS.keys()), case_sensitive=True),
    default="gpt-image-2-official",
    show_default=True,
    help="图片编辑模型，默认 gpt-image-2-official",
)
@click.option(
    "--mask",
    "mask_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    metavar="<遮罩图片>",
    help="遮罩图片，白色区域编辑，透明区域保持不变",
)
@click.option(
    "--size",
    default=None,
    metavar="<比例或像素>",
    help="输出画面比例（如 1:1、16:9）或像素尺寸",
)
@click.option(
    "--quality",
    type=click.Choice(VALID_QUALITIES, case_sensitive=False),
    default="high",
    show_default=True,
    metavar="<low|medium|high>",
    help="图片质量，默认最高 high",
)
@click.option(
    "--response-format",
    "response_format",
    type=click.Choice(VALID_RESPONSE_FORMATS, case_sensitive=True),
    default="b64_json",
    show_default=True,
    help="返回格式",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False),
    metavar="<输出文件>",
    help="保存编辑结果的路径",
)
def edit_command(
    image_path,
    prompt,
    model_name,
    mask_path,
    size,
    quality,
    response_format,
    output_path,
):
    """v2 图片编辑：上传图片并按提示词修改。"""
    # 步骤1：校验参数。
    if not prompt.strip():
        raise click.ClickException("提示词不能为空")
    if size:
        validate_size(size)
    if model_name == "seed3d-v2-image-to-3d":
        raise click.ClickException("seed3d-v2-image-to-3d 不支持图片编辑")

    # 步骤2：准备输出路径并调用编辑接口。
    api_key = get_api_key()
    ensure_output_dir()
    resolved_output = output_path or build_default_output_path(model_name + "_edited")

    response_data = call_v2_edit(
        api_key, model_name, prompt, image_path, mask_path,
        size, quality, response_format,
    )
    saved_files, result_format = process_image_response(
        response_data, resolved_output, api_key,
    )

    # 步骤3：输出结果。
    result = {
        "model": model_name,
        "prompt": prompt,
        "image": str(pathlib.Path(image_path).resolve()),
        "mask": str(pathlib.Path(mask_path).resolve()) if mask_path else None,
        "size": size,
        "quality": quality,
        "response_format": response_format,
        "api_version": "v2 edits",
        "saved_files": saved_files,
        "usage": response_data.get("usage"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：列出支持的图片模型。
# ---------------------------
@cli.command(name="list-models")
def list_models_command():
    """列出所有支持的图片生成模型和价格。"""
    # 步骤1：格式化输出模型列表。
    models_list = []
    for model_id, description in IMAGE_MODELS.items():
        models_list.append({
            "model": model_id,
            "description": description,
        })

    result = {
        "count": len(models_list),
        "models": models_list,
        "tip": "seed3d-v2-image-to-3d 仅支持 v1 异步接口（image generate-async）",
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行图片生成 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动 Click 命令组。
    cli()
