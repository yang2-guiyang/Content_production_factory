import io
import json
import pathlib
import sys

# 步骤0：直接运行本命令模块时，先解决 Windows 控制台 GBK 乱码。
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click


# 步骤1：定义服务对应的 .env 键名。
SERVICE_KEYS = {
    "dashscope": "DASHSCOPE_API_KEY",
    "maizi": "MAIZI_API_KEY",
}
DEFAULT_SERVICE = "dashscope"


# ---------------------------
# 函数说明：获取 scripts 目录，兼容源码和 PyInstaller 运行模式。
# ---------------------------
def get_application_directory():
    # 步骤1：打包后返回 exe 所在目录。
    if getattr(sys, "frozen", False):
        executable_path = pathlib.Path(sys.executable).resolve()
        return executable_path.parent

    # 步骤2：源码运行时从 commands 目录返回上一级 scripts 目录。
    current_file_path = pathlib.Path(__file__).resolve()
    return current_file_path.parent.parent


# ---------------------------
# 函数说明：创建 API 密钥维护命令组。
# ---------------------------
@click.group()
def cli():
    """维护 scripts/.env 中的 API 密钥（支持 dashscope 和 maizi）。"""
    pass


# ---------------------------
# 函数说明：查看 API 密钥是否已配置。
# ---------------------------
@cli.command(name="status")
@click.option(
    "--service",
    type=click.Choice(list(SERVICE_KEYS.keys()), case_sensitive=True),
    default=DEFAULT_SERVICE,
    show_default=True,
    help="目标服务",
)
def status_command(service):
    """查看密钥配置状态，不显示密钥内容（例: python scripts/main.py key status --service maizi）"""
    # 步骤1：获取目标键名并定位 .env 文件。
    env_key = SERVICE_KEYS[service]
    application_directory = get_application_directory()
    env_file_path = application_directory / ".env"

    # 步骤2：逐行检查目标密钥。
    configured = False
    if env_file_path.exists():
        env_file = open(env_file_path, "r", encoding="utf-8")
        for raw_line in env_file:
            line_text = raw_line.strip()
            line_parts = line_text.split("=", 1)
            if len(line_parts) < 2:
                continue

            current_key = line_parts[0].strip()
            current_value = line_parts[1].strip()
            if current_key == env_key and current_value:
                configured = True
                break
        env_file.close()

    # 步骤3：只输出配置状态，不输出密钥。
    result = {
        "service": service,
        "configured": configured,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：新增或更新 API 密钥。
# ---------------------------
@cli.command(name="set")
@click.argument("api_key", metavar="<API密钥>")
@click.option(
    "--service",
    type=click.Choice(list(SERVICE_KEYS.keys()), case_sensitive=True),
    default=DEFAULT_SERVICE,
    show_default=True,
    help="目标服务",
)
def set_command(api_key, service):
    """写入 API 密钥（例: python scripts/main.py key set --service maizi sk-xxx）"""
    # 步骤1：获取目标键名并定位 .env 文件。
    env_key = SERVICE_KEYS[service]
    application_directory = get_application_directory()
    env_file_path = application_directory / ".env"
    existing_lines = []
    if env_file_path.exists():
        env_file = open(env_file_path, "r", encoding="utf-8")
        for raw_line in env_file:
            existing_lines.append(raw_line.rstrip("\r\n"))
        env_file.close()

    # 步骤2：更新目标密钥并保留其他配置。
    updated_lines = []
    key_updated = False
    for line_text in existing_lines:
        line_parts = line_text.split("=", 1)
        if len(line_parts) >= 2:
            current_key = line_parts[0].strip()
            if current_key == env_key:
                updated_lines.append(env_key + "=" + api_key)
                key_updated = True
                continue
        updated_lines.append(line_text)

    if not key_updated:
        updated_lines.append(env_key + "=" + api_key)

    # 步骤3：创建目录（首次写入 .env 时可能不存在）并立即写回。
    application_directory.mkdir(parents=True, exist_ok=True)
    env_file = open(env_file_path, "w", encoding="utf-8")
    for line_text in updated_lines:
        env_file.write(line_text + "\n")
    env_file.close()

    # 步骤4：只输出写入状态，不回显密钥。
    result = {
        "service": service,
        "configured": True,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------
# 函数说明：删除 API 密钥并保留其他配置。
# ---------------------------
@cli.command(name="remove")
@click.option(
    "--service",
    type=click.Choice(list(SERVICE_KEYS.keys()), case_sensitive=True),
    default=DEFAULT_SERVICE,
    show_default=True,
    help="目标服务",
)
def remove_command(service):
    """删除 API 密钥（例: python scripts/main.py key remove --service maizi）"""
    # 步骤1：获取目标键名并定位 .env 文件。
    env_key = SERVICE_KEYS[service]
    application_directory = get_application_directory()
    env_file_path = application_directory / ".env"
    if not env_file_path.exists():
        result = {
            "service": service,
            "configured": False,
        }
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 步骤2：读取并过滤目标密钥。
    retained_lines = []
    env_file = open(env_file_path, "r", encoding="utf-8")
    for raw_line in env_file:
        line_text = raw_line.rstrip("\r\n")
        line_parts = line_text.split("=", 1)
        if len(line_parts) >= 2:
            current_key = line_parts[0].strip()
            if current_key == env_key:
                continue
        retained_lines.append(line_text)
    env_file.close()

    # 步骤3：立即写回其他配置。
    env_file = open(env_file_path, "w", encoding="utf-8")
    for line_text in retained_lines:
        env_file.write(line_text + "\n")
    env_file.close()

    # 步骤4：只输出删除后的配置状态。
    result = {
        "service": service,
        "configured": False,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
