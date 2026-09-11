from engine.platform.douyin import DouyinLiveAdapter
from engine.platform.kuaishou import KuaishouLiveAdapter
from engine.platform.service import PlatformService


def test_douyin_chat_message_normalization() -> None:
    adapter = DouyinLiveAdapter()
    event = adapter.normalize(
        {
            "type": "WebcastChatMessage",
            "user": {"id": "u1", "nickname": "小李"},
            "content": "多少钱",
        }
    )
    assert event is not None
    assert event.platform == "douyin"
    assert event.type == "danmaku"
    assert event.nickname == "小李"
    assert event.content == "多少钱"


def test_kuaishou_gift_message_normalization() -> None:
    adapter = KuaishouLiveAdapter()
    event = adapter.normalize(
        {
            "type": "GIFT",
            "user": {"id": "u2", "nickname": "礼物哥"},
            "content": "大火箭",
            "gift_count": 2,
        }
    )
    assert event is not None
    assert event.platform == "kuaishou"
    assert event.type == "gift"
    assert event.gift_count == 2


def test_callback_ingest_adds_platform_event() -> None:
    service = PlatformService()
    result = service.ingest(
        "douyin",
        {
            "type": "WebcastMemberMessage",
            "user": {"id": "u3", "nickname": "新观众"},
        },
    )
    assert result == {"accepted": True, "type": "enter"}
    assert service.recent_events(1)[0]["nickname"] == "新观众"
