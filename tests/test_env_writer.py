import importlib
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from click.testing import CliRunner


PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIRECTORY = PROJECT_DIRECTORY / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))


# ---------------------------
# 类说明：验证 scripts/.env 密钥维护命令。
# ---------------------------
class EnvWriterTestCase(unittest.TestCase):
    # ---------------------------
    # 函数说明：加载待实现的配置写入模块。
    # ---------------------------
    def load_env_writer(self):
        # 步骤1：加载模块，缺失时给出明确测试失败。
        try:
            return importlib.import_module("commands.env_writer")
        except ModuleNotFoundError:
            self.fail("commands.env_writer 尚未实现")

    # ---------------------------
    # 函数说明：验证 set 命令保留其他配置和密钥中的等号。
    # ---------------------------
    def test_set_preserves_other_values_and_equals(self):
        # 步骤1：准备临时 .env。
        env_writer = self.load_env_writer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            application_directory = pathlib.Path(temporary_directory)
            env_file_path = application_directory / ".env"
            env_file_path.write_text(
                "OTHER_KEY=keep\nDASHSCOPE_API_KEY=old\n",
                encoding="utf-8",
            )

            # 步骤2：执行密钥写入命令。
            with mock.patch.object(
                env_writer,
                "get_application_directory",
                return_value=application_directory,
            ):
                runner = CliRunner()
                result = runner.invoke(
                    env_writer.cli,
                    [
                        "set",
                        "new=value=with=equals",
                    ],
                )

            # 步骤3：确认只更新目标密钥。
            self.assertEqual(result.exit_code, 0, result.output)
            env_content = env_file_path.read_text(encoding="utf-8")
            self.assertEqual(
                env_content,
                "OTHER_KEY=keep\nDASHSCOPE_API_KEY=new=value=with=equals\n",
            )

    # ---------------------------
    # 函数说明：验证 status 命令不泄露密钥。
    # ---------------------------
    def test_status_does_not_reveal_api_key(self):
        # 步骤1：准备带密钥的临时 .env。
        env_writer = self.load_env_writer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            application_directory = pathlib.Path(temporary_directory)
            env_file_path = application_directory / ".env"
            env_file_path.write_text(
                "DASHSCOPE_API_KEY=secret-test-value\n",
                encoding="utf-8",
            )

            # 步骤2：执行状态查询命令。
            with mock.patch.object(
                env_writer,
                "get_application_directory",
                return_value=application_directory,
            ):
                runner = CliRunner()
                result = runner.invoke(env_writer.cli, ["status"])

            # 步骤3：确认只输出配置状态。
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('"configured": true', result.output)
            self.assertNotIn("secret-test-value", result.output)

    # ---------------------------
    # 函数说明：验证 remove 命令只删除 DashScope 密钥。
    # ---------------------------
    def test_remove_only_deletes_dashscope_api_key(self):
        # 步骤1：准备包含两个配置的临时 .env。
        env_writer = self.load_env_writer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            application_directory = pathlib.Path(temporary_directory)
            env_file_path = application_directory / ".env"
            env_file_path.write_text(
                "OTHER_KEY=keep\nDASHSCOPE_API_KEY=remove-me\n",
                encoding="utf-8",
            )

            # 步骤2：执行删除命令。
            with mock.patch.object(
                env_writer,
                "get_application_directory",
                return_value=application_directory,
            ):
                runner = CliRunner()
                result = runner.invoke(env_writer.cli, ["remove"])

            # 步骤3：确认其他配置仍然存在。
            self.assertEqual(result.exit_code, 0, result.output)
            env_content = env_file_path.read_text(encoding="utf-8")
            self.assertEqual(env_content, "OTHER_KEY=keep\n")


if __name__ == "__main__":
    unittest.main()
