from engine.leads.detector import build_signal, classify_lead, extract_contacts


def test_extracts_wechat_and_phone() -> None:
    contacts = extract_contacts("加微信 liu_2023，手机13800138000")
    assert contacts == {"wechat": "liu_2023", "phone": "13800138000"}


def test_intent_danmaku_is_low_lead() -> None:
    signal = build_signal("mock", "u1", "买家", "danmaku", "这个多少钱？")
    assert signal.score == 10
    assert signal.level == "low"


def test_gift_with_intent_is_medium_or_higher() -> None:
    signal = build_signal("mock", "u2", "礼物哥", "gift", "想下单怎么买", gift_count=1)
    assert signal.level in {"medium", "high"}


def test_high_value_gift_is_high_lead() -> None:
    assert classify_lead(build_signal("mock", "u3", "大客户", "gift", gift_count=3).score) == "high"
