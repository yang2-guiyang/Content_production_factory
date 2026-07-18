import importlib
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIRECTORY = PROJECT_DIRECTORY / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))


# ---------------------------
# 类说明：验证 scripts/.env 只读配置模块。
# ---------------------------
class EnvReaderTestCase(unittest.TestCase):
    # ---------------------------
    # 函数说明：验证密钥值中的等号不会被错误截断。
    # ---------------------------
    def test_get_env_value_keeps_equals_in_value(self):
        # 步骤1：加载待实现的配置读取模块。
        try:
            env_reader = importlib.import_module("commands.env_reader")
        except ModuleNotFoundError:
            self.fail("commands.env_reader 尚未实现")

        # 步骤2：创建包含等号的临时配置。
        with tempfile.TemporaryDirectory() as temporary_directory:
            application_directory = pathlib.Path(temporary_directory)
            env_file_path = application_directory / ".env"
            env_file_path.write_text(
                "DASHSCOPE_API_KEY=test=value=with=equals\n",
                encoding="utf-8",
            )

            # 步骤3：把读取目录临时指向测试目录并核对完整值。
            with mock.patch.object(
                env_reader,
                "get_application_directory",
                return_value=application_directory,
            ):
                env_value = env_reader.get_env_value("DASHSCOPE_API_KEY")

        self.assertEqual(env_value, "test=value=with=equals")


if __name__ == "__main__":
    unittest.main()
