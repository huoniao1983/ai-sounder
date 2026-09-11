"""Regex contact extraction and behavior-weighted lead scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
WECHAT_RE = re.compile(r"(?:(?:微信|vx|wx|weixin|wechat)[:：\s]*)([A-Za-z][-_A-Za-z0-9]{5,19})")
INTENT_KEYWORDS = ("优惠", "多少钱", "怎么买", "怎么卖", "哪里买", "链接", "下单", "私信", "团购", "价格", "订购")
SCORE_BY_EVENT = {
    "gift": 20,
    "follow": 15,
    "fans": 25,
    "danmaku": 0,
    "enter": 0,
    "like": 5,
}


@dataclass(slots=True)
class IntentSignal:
    platform: str
    user_id: str
    nickname: str
    event_type: str
    score: int
    level: str
    contacts: dict[str, str] = field(default_factory=dict)
    intent_words: list[str] = field(default_factory=list)


def extract_contacts(content: str) -> dict[str, str]:
    contacts: dict[str, str] = {}
    phone = PHONE_RE.search(content)
    if phone:
        contacts["phone"] = phone.group(0)
    wechat = WECHAT_RE.search(content)
    if wechat:
        contacts["wechat"] = wechat.group(1)
    return contacts


def score_event(event_type: str, content: str = "", gift_count: int = 0) -> int:
    base = SCORE_BY_EVENT.get(event_type, 0)
    if event_type == "gift":
        base = max(gift_count, 1) * 20
    intent_words = [word for word in INTENT_KEYWORDS if word in content]
    return base + min(len(intent_words) * 10, 30)


def classify_lead(score: int) -> str:
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    if score >= 10:
        return "low"
    return "none"


def build_signal(
    platform: str,
    user_id: str,
    nickname: str,
    event_type: str,
    content: str = "",
    gift_count: int = 0,
) -> IntentSignal:
    score = score_event(event_type, content, gift_count)
    contacts = extract_contacts(content)
    intent_words = [word for word in INTENT_KEYWORDS if word in content]
    return IntentSignal(
        platform=platform,
        user_id=user_id,
        nickname=nickname,
        event_type=event_type,
        score=score,
        level=classify_lead(score),
        contacts=contacts,
        intent_words=intent_words,
    )


__all__ = ["IntentSignal", "build_signal", "classify_lead", "extract_contacts", "score_event"]
