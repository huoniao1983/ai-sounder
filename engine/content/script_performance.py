"""Validation helpers for expressive, CosyVoice-safe generated scripts."""

from __future__ import annotations

import re

ALLOWED_TAGS = ("speak", "break", "phoneme", "say-as", "soundEvent", "sub")
DEFAULT_INSTRUCTION = (
    "像有经验的真人带货主播一样自然表达，语气真诚、有交流感，不要播音腔。"
    "重点词稍微加重，句间保留自然呼吸，不要机械匀速。"
)

_TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9:-]*)(?:\s[^>]*)?/?>")
_BREAK_RE = re.compile(r"<break\s+time=[\"'](\d+(?:\.\d+)?)(ms|s)[\"']\s*/?>")


def sanitize_ssml(value: str) -> str:
    """Keep only SSML tags documented for CosyVoice and require a speak root."""

    text = (value or "").strip()
    if not text:
        return ""
    text = _TAG_RE.sub(
        lambda match: match.group(0) if match.group(1) in ALLOWED_TAGS else "",
        text,
    )
    text = _normalize_break_durations(text)
    if not text.startswith("<speak>") or not text.endswith("</speak>"):
        return ""
    return text


def build_instruction(value: str, emotion: str = "", pace: str = "") -> str:
    fields = [part.strip() for part in (value, emotion, pace) if part and part.strip()]
    if not fields:
        return DEFAULT_INSTRUCTION
    combined = "；".join(fields)
    if "直播" not in combined and "主播" not in combined:
        combined = f"{combined}；保持直播交流感和自然呼吸"
    return combined[:1600]


def _normalize_break_durations(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        amount = float(match.group(1))
        milliseconds = amount * 1000 if match.group(2) == "s" else amount
        milliseconds = max(50.0, min(10000.0, milliseconds))
        rendered = str(int(milliseconds)) if milliseconds.is_integer() else f"{milliseconds:g}"
        return f'<break time="{rendered}ms"/>'

    return _BREAK_RE.sub(replace, value)


__all__ = ["ALLOWED_TAGS", "DEFAULT_INSTRUCTION", "build_instruction", "sanitize_ssml"]

