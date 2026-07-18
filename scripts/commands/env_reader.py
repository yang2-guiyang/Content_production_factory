import pathlib
import sys


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
# 函数说明：从 scripts/.env 读取指定配置值。
# ---------------------------
def get_env_value(env_key):
    # 步骤1：定位 .env 文件。
    application_directory = get_application_directory()
    env_file_path = application_directory / ".env"
    if not env_file_path.exists():
        return None

    # 步骤2：逐行读取并跳过空行和注释。
    env_file = open(env_file_path, "r", encoding="utf-8")
    for raw_line in env_file:
        line_text = raw_line.strip()
        if not line_text:
            continue
        if line_text.startswith("#"):
            continue

        # 步骤3：只拆分第一个等号，避免密钥内容被截断。
        line_parts = line_text.split("=", 1)
        if len(line_parts) < 2:
            continue

        current_key = line_parts[0].strip()
        current_value = line_parts[1].strip()
        if current_key == env_key:
            env_file.close()
            return current_value

    # 步骤4：未找到配置时关闭文件并返回空值。
    env_file.close()
    return None
