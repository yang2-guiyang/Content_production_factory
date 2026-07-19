import io
import sys

# 步骤0：统一入口最先固定 UTF-8，避免 Windows 终端输出中文时出现乱码。
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import click

from commands.env_writer import cli as key_cli
from commands.speech_recognition_commands import cli as speech_cli
from commands.speech_synthesis_commands import cli as tts_cli
from commands.visual_understanding_commands import cli as visual_cli


# ---------------------------
# 函数说明：注册 Content Production Factory 的全部 CLI 命令组。
# ---------------------------
@click.group()
def cli():
    """统一调用语音识别、语音生成、视觉理解和密钥管理命令。"""
    pass


# 步骤1：注册语音识别命令组。
cli.add_command(speech_cli, name="speech")

# 步骤2：注册声音复刻和语音合成命令组。
cli.add_command(tts_cli, name="tts")

# 步骤3：注册视觉理解和 OCR 命令组。
cli.add_command(visual_cli, name="visual")

# 步骤4：注册 API 密钥管理命令组。
cli.add_command(key_cli, name="key")


if __name__ == "__main__":
    # 步骤5：启动统一 CLI 入口。
    cli()
