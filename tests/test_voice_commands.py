import json
import os
import pathlib
import sys
import unittest

from click.testing import CliRunner


PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIRECTORY = PROJECT_DIRECTORY / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from commands import voice_commands


# ---------------------------
# 类说明：提供固定成功响应，避免测试产生真实接口费用。
# ---------------------------
class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "output": {
                "voice_id": "qwen-audio-test-voice",
                "target_model": "qwen-audio-3.0-tts-flash",
            },
            "usage": {
                "count": 1,
            },
            "request_id": "test-request-id",
        }


# ---------------------------
# 类说明：记录声音复刻请求，供测试核对接口协议。
# ---------------------------
class FakeSession:
    request_url = None
    request_headers = None
    request_data = None
    request_timeout = None

    def __init__(self):
        self.trust_env = True

    def post(self, url, headers, json, timeout):
        FakeSession.request_url = url
        FakeSession.request_headers = headers
        FakeSession.request_data = json
        FakeSession.request_timeout = timeout
        return FakeResponse()


# ---------------------------
# 类说明：验证 Qwen-Audio-TTS 声音复刻命令的外部行为。
# ---------------------------
class VoiceCommandsTestCase(unittest.TestCase):
    # ---------------------------
    # 函数说明：保存环境并替换网络会话。
    # ---------------------------
    def setUp(self):
        # 步骤1：保存原始环境，避免测试污染本机配置。
        self.original_api_key = os.environ.get("DASHSCOPE_API_KEY")
        self.original_session = voice_commands.requests.Session

        # 步骤2：配置测试密钥和固定网络响应。
        os.environ["DASHSCOPE_API_KEY"] = "test-api-key"
        voice_commands.requests.Session = FakeSession

    # ---------------------------
    # 函数说明：恢复测试前的环境。
    # ---------------------------
    def tearDown(self):
        # 步骤1：恢复网络会话。
        voice_commands.requests.Session = self.original_session

        # 步骤2：恢复 API Key。
        if self.original_api_key is None:
            del os.environ["DASHSCOPE_API_KEY"]
        else:
            os.environ["DASHSCOPE_API_KEY"] = self.original_api_key

    # ---------------------------
    # 函数说明：验证 create 命令使用 Qwen-Audio-TTS 协议。
    # ---------------------------
    def test_create_uses_qwen_audio_tts_request(self):
        # 步骤1：按预期的新 CLI 接口执行命令。
        runner = CliRunner()
        result = runner.invoke(
            voice_commands.cli,
            [
                "create",
                "https://example.com/voice.wav",
                "--target-model",
                "qwen-audio-3.0-tts-flash",
                "--prefix",
                "narrator",
            ],
        )

        # 步骤2：核对命令执行结果。
        self.assertEqual(result.exit_code, 0, result.output)
        result_data = json.loads(result.output)
        self.assertEqual(result_data["voice_id"], "qwen-audio-test-voice")

        # 步骤3：核对发送给接口的固定协议。
        self.assertEqual(FakeSession.request_data["model"], "voice-enrollment")
        input_data = FakeSession.request_data["input"]
        self.assertEqual(input_data["action"], "create_voice")
        self.assertEqual(input_data["target_model"], "qwen-audio-3.0-tts-flash")
        self.assertEqual(input_data["prefix"], "narrator")
        self.assertEqual(input_data["url"], "https://example.com/voice.wav")
        self.assertEqual(FakeSession.request_timeout, 120)

    # ---------------------------
    # 函数说明：验证命令拒绝 Qwen-Audio-TTS 之外的目标模型。
    # ---------------------------
    def test_create_rejects_non_qwen_audio_tts_model(self):
        # 步骤1：传入旧版 Qwen-TTS 模型。
        runner = CliRunner()
        result = runner.invoke(
            voice_commands.cli,
            [
                "create",
                "https://example.com/voice.wav",
                "--target-model",
                "qwen3-tts-vc-2026-01-22",
            ],
        )

        # 步骤2：确认 Click 返回模型取值错误。
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("qwen-audio-3.0-tts-flash", result.output)


if __name__ == "__main__":
    unittest.main()
