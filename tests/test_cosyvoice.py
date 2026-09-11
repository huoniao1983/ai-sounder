import json
from unittest.mock import patch

from engine.content.script_performance import sanitize_ssml
from engine.tts.cosyvoice import CosyVoiceClient, CosyVoiceConfig


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_cosyvoice_synthesis_returns_audio_bytes() -> None:
    client = CosyVoiceClient(CosyVoiceConfig(api_key="test", model="cosyvoice-v3.5-flash"))
    response = {"output": {"audio": {"data": "aGVsbG8=", "url": ""}}}
    with patch("urllib.request.urlopen", return_value=_Response(response)):
        assert client.synthesize("你好", "voice-id") == b"hello"


def test_cosyvoice_clone_returns_profile() -> None:
    client = CosyVoiceClient(CosyVoiceConfig(api_key="test", model="cosyvoice-v3.5-flash"))
    response = {
        "output": {
            "voice_id": "cosyvoice-v3.5-flash-demo-123",
            "target_model": "cosyvoice-v3.5-flash",
            "status": "DEPLOYING",
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(response)):
        profile = client.create_voice(
            "https://example.com/sample.mp3",
            "Demo Voice",
            "Warm female voice",
        )
    assert profile.id == "cosyvoice-v3.5-flash-demo-123"
    assert profile.description == "Warm female voice"


def test_ssml_whitelist_keeps_breaks_and_removes_prosody() -> None:
    value = '<speak><prosody rate="fast">来，<break time="2s"/>听我说。</prosody></speak>'
    result = sanitize_ssml(value)
    assert "<prosody" not in result
    assert '<break time="2000ms"/>' in result


def test_synthesis_payload_includes_instruction_and_ssml() -> None:
    client = CosyVoiceClient(CosyVoiceConfig(api_key="test", model="cosyvoice-v3.5-flash"))
    captured: dict = {}

    def fake_post(path: str, payload: dict) -> dict:
        captured["path"] = path
        captured["payload"] = payload
        return {"output": {"audio": {"data": "aGVsbG8="}}}

    client._post = fake_post  # type: ignore[method-assign]
    assert client.synthesize(
        "欢迎来到直播间",
        "voice-id",
        instruction="亲切、有交流感，重点词加重",
        ssml='<speak>欢迎来到直播间<break time="300ms"/>先点个关注。</speak>',
    ) == b"hello"
    assert captured["payload"]["input"]["enable_ssml"] is True
    assert "instruction" in captured["payload"]["input"]
