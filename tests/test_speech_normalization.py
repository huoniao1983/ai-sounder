from engine.api_server import _speech_ready


def test_speech_text_is_single_coherent_chinese_utterance() -> None:
    text = "欢迎 ok小李 来到直播间来到直播间"
    assert _speech_ready(text) == "欢迎小李来到直播间"


def test_speech_text_keeps_normal_utterance_unchanged() -> None:
    assert _speech_ready("欢迎小李来到直播间") == "欢迎小李来到直播间"

