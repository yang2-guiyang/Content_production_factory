import io
import json
import mimetypes
import pathlib
import sys

# 步骤0：仅在需要时切换为 UTF-8，避免统一入口重复导入时关闭输出流。
standard_output_encoding = getattr(sys.stdout, "encoding", "") or ""
normalized_output_encoding = standard_output_encoding.lower().replace("-", "")
if normalized_output_encoding != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click
import requests

# 步骤1：把 scripts 目录加入模块搜索路径。
SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands.env_reader import get_env_value


FILES_API_URL = "https://dashscope.aliyuncs.com/api/v1/files"
SUPPORTED_PURPOSES = ["file-extract", "batch", "fine-tune"]


# ---------------------------
# 函数说明：读取文件管理接口需要的 API Key。
# ---------------------------
def get_api_key():
    # 步骤1：读取 scripts/.env 中的密钥。
    api_key = get_env_value("DASHSCOPE_API_KEY")
    if not api_key:
        raise click.ClickException(
            "未配置 DASHSCOPE_API_KEY，请先执行："
            "python scripts/main.py key set <API密钥>"
        )

    # 步骤2：返回可用密钥。
    return api_key


# ---------------------------
# 函数说明：解析接口 JSON，并统一处理网络和 HTTP 错误。
# ---------------------------
def parse_api_response(response):
    # 步骤1：尝试解析 JSON 响应。
    try:
        response_data = response.json()
    except ValueError:
        raise click.ClickException(
            "接口未返回有效 JSON，状态码：" + str(response.status_code)
        )

    # 步骤2：非成功状态返回接口原始错误信息。
    if response.status_code != 200:
        response_text = json.dumps(response_data, ensure_ascii=False)
        raise click.ClickException(
            "接口返回错误，状态码："
            + str(response.status_code)
            + "，响应内容："
            + response_text[:1000]
        )

    # 步骤3：返回成功响应。
    return response_data


# ---------------------------
# 函数说明：发送普通文件管理请求并返回 JSON。
# ---------------------------
def send_file_request(request_method, api_key, url, parameters=None):
    # 步骤1：准备不包含密钥内容的请求头。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }

    # 步骤2：根据方法发送请求。
    try:
        if request_method == "GET":
            response = requests.get(
                url,
                headers=headers,
                params=parameters,
                timeout=60,
            )
        else:
            response = requests.delete(
                url,
                headers=headers,
                timeout=60,
            )
    except requests.exceptions.Timeout:
        raise click.ClickException("请求超时，请检查网络后重试")
    except requests.exceptions.ConnectionError:
        raise click.ClickException("网络连接失败，请检查网络设置")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("请求失败：" + str(error))

    # 步骤3：解析并返回接口响应。
    return parse_api_response(response)


# ---------------------------
# 函数说明：查询一个文件对象的完整属性和签名 URL。
# ---------------------------
def get_file_details(api_key, file_id):
    # 步骤1：拼接经过 URL 编码的文件详情地址。
    encoded_file_id = requests.utils.quote(file_id, safe="")
    file_url = FILES_API_URL + "/" + encoded_file_id

    # 步骤2：调用详情接口并检查 data 字段。
    response_data = send_file_request("GET", api_key, file_url)
    file_data = response_data.get("data")
    if not file_data:
        raise click.ClickException("文件详情响应中缺少 data 字段")

    # 步骤3：返回请求标识和文件对象。
    return response_data.get("request_id"), file_data


# ---------------------------
# 函数说明：上传一个或多个本地文件。
# ---------------------------
def upload_files(api_key, file_paths, purpose, description):
    # 步骤1：逐个打开文件并准备 multipart/form-data 字段。
    opened_files = []
    multipart_files = []
    form_data = []
    try:
        for file_path in file_paths:
            resolved_file_path = file_path.resolve()
            file_handle = open(resolved_file_path, "rb")
            opened_files.append(file_handle)

            content_type = mimetypes.guess_type(resolved_file_path.name)[0]
            if not content_type:
                content_type = "application/octet-stream"

            multipart_file = (
                "files",
                (
                    resolved_file_path.name,
                    file_handle,
                    content_type,
                ),
            )
            multipart_files.append(multipart_file)
            form_data.append(("purpose", purpose))
            if description:
                form_data.append(("descriptions", description))

        # 步骤2：发送多文件上传请求。
        headers = {
            "Authorization": "Bearer " + api_key,
            "Accept": "application/json",
        }
        response = requests.post(
            FILES_API_URL,
            headers=headers,
            files=multipart_files,
            data=form_data,
            timeout=1800,
        )
    except requests.exceptions.Timeout:
        raise click.ClickException("上传超时，请检查网络后重试")
    except requests.exceptions.ConnectionError:
        raise click.ClickException("网络连接失败，请检查网络设置")
    except requests.exceptions.RequestException as error:
        raise click.ClickException("上传失败：" + str(error))
    except OSError as error:
        raise click.ClickException("读取本地文件失败：" + str(error))
    finally:
        # 步骤3：无论上传成功与否都关闭本地文件。
        for file_handle in opened_files:
            file_handle.close()

    # 步骤4：解析并返回上传响应。
    return parse_api_response(response)


# ---------------------------
# 函数说明：创建百炼文件管理命令组。
# ---------------------------
@click.group()
def cli():
    """上传、查询、列举和删除百炼文件。"""
    pass


# ---------------------------
# 函数说明：多文件上传后立即查询可复用签名 URL。
# ---------------------------
@cli.command(name="upload")
@click.argument(
    "file_paths",
    nargs=-1,
    required=True,
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        path_type=pathlib.Path,
    ),
    metavar="<本地文件>...",
)
@click.option(
    "--purpose",
    type=click.Choice(SUPPORTED_PURPOSES, case_sensitive=True),
    default="file-extract",
    show_default=True,
    metavar="<file-extract|batch|fine-tune>",
    help="文件用途；音频、视频、图片和文档内容分析使用 file-extract",
)
@click.option(
    "--description",
    default=None,
    metavar="<文件描述>",
    help="为本次上传的全部文件设置相同描述",
)
def upload_command(file_paths, purpose, description):
    """上传一个或多个文件并返回 file_id 和签名 URL。"""
    # 步骤1：读取密钥并上传全部本地文件。
    api_key = get_api_key()
    upload_response = upload_files(
        api_key,
        file_paths,
        purpose,
        description,
    )

    # 步骤2：读取上传成功和失败列表。
    upload_data = upload_response.get("data")
    if not upload_data:
        raise click.ClickException("上传响应中缺少 data 字段")

    uploaded_files = upload_data.get("uploaded_files") or []
    failed_uploads = upload_data.get("failed_uploads") or []

    # 步骤3：逐个查询完整文件对象，取得可用于任务的签名 URL。
    resolved_files = []
    url_resolution_failures = []
    for uploaded_file in uploaded_files:
        file_id = uploaded_file.get("file_id")
        if not file_id:
            url_resolution_failure = {
                "name": uploaded_file.get("name"),
                "message": "上传结果缺少 file_id",
            }
            url_resolution_failures.append(url_resolution_failure)
            continue

        try:
            details_request_id, file_data = get_file_details(api_key, file_id)
            file_data["details_request_id"] = details_request_id
            resolved_files.append(file_data)
        except click.ClickException as error:
            url_resolution_failure = {
                "file_id": file_id,
                "name": uploaded_file.get("name"),
                "message": str(error),
            }
            url_resolution_failures.append(url_resolution_failure)

    # 步骤4：输出可供 AI 继续调用任务的结构化结果。
    result = {
        "request_id": upload_response.get("request_id"),
        "purpose": purpose,
        "uploaded_files": resolved_files,
        "failed_uploads": failed_uploads,
        "url_resolution_failures": url_resolution_failures,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：查询一个文件对象及其当前签名 URL。
# ---------------------------
@cli.command(name="get")
@click.argument("file_id", metavar="<文件ID>")
def get_command(file_id):
    """获取指定文件的属性和当前签名 URL。"""
    # 步骤1：读取密钥并查询文件详情。
    api_key = get_api_key()
    request_id, file_data = get_file_details(api_key, file_id)

    # 步骤2：输出接口中的完整文件对象。
    result = {
        "request_id": request_id,
        "data": file_data,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：分页列出当前账号的有效文件。
# ---------------------------
@cli.command(name="list")
@click.option(
    "--page-no",
    default=1,
    show_default=True,
    type=click.IntRange(min=1),
    metavar="<页码>",
    help="当前页码",
)
@click.option(
    "--page-size",
    default=10,
    show_default=True,
    type=click.IntRange(min=1, max=100),
    metavar="<每页数量>",
    help="每页返回的文件数量",
)
def list_command(page_no, page_size):
    """分页列出当前账号的有效文件。"""
    # 步骤1：读取密钥并准备分页参数。
    api_key = get_api_key()
    parameters = {
        "page_no": page_no,
        "page_size": page_size,
    }

    # 步骤2：调用列表接口并输出原始结构。
    response_data = send_file_request(
        "GET",
        api_key,
        FILES_API_URL,
        parameters=parameters,
    )
    click.echo(json.dumps(response_data, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：删除一个或多个百炼文件。
# ---------------------------
@cli.command(name="delete")
@click.argument(
    "file_ids",
    nargs=-1,
    required=True,
    metavar="<文件ID>...",
)
def delete_command(file_ids):
    """删除一个或多个文件并释放空间和数量配额。"""
    # 步骤1：读取密钥并初始化批量删除结果。
    api_key = get_api_key()
    deleted_files = []
    failed_deletions = []

    # 步骤2：逐个调用单文件删除接口。
    for file_id in file_ids:
        encoded_file_id = requests.utils.quote(file_id, safe="")
        file_url = FILES_API_URL + "/" + encoded_file_id
        try:
            response_data = send_file_request("DELETE", api_key, file_url)
            deleted_file = {
                "file_id": file_id,
                "request_id": response_data.get("request_id"),
            }
            deleted_files.append(deleted_file)
        except click.ClickException as error:
            failed_deletion = {
                "file_id": file_id,
                "message": str(error),
            }
            failed_deletions.append(failed_deletion)

    # 步骤3：输出全部成功和失败项，避免批量操作丢失结果。
    result = {
        "deleted_files": deleted_files,
        "failed_deletions": failed_deletions,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 主流程：运行百炼文件管理 Click 命令组。
# ---------------------------
if __name__ == "__main__":
    # 步骤1：启动文件管理命令组。
    cli()
