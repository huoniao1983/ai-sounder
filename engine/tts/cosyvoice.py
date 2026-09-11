"""DashScope CosyVoice v3.5 Flash synthesis and voice cloning client."""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.content.script_performance import build_instruction, sanitize_ssml


@dataclass(slots=True)
class CosyVoiceConfig:
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    model: str = "cosyvoice-v3.5-flash"


@dataclass(slots=True)
class VoiceProfile:
    id: str
    name: str
    description: str
    sample_url: str
    status: str
    target_model: str
    created_at: float


class CosyVoiceError(RuntimeError):
    pass


def load_config(runtime_dir: Path) -> CosyVoiceConfig:
    config_path = runtime_dir / "tts-config.json"
    stored: dict[str, Any] = {}
    if config_path.exists():
        try:
            stored = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stored = {}
    api_key = os.environ.get("DASHSCOPE_API_KEY") or stored.get("api_key", "")
    base_url = os.environ.get("DASHSCOPE_BASE_URL") or stored.get(
        "base_url",
        "https://dashscope.aliyuncs.com/api/v1",
    )
    model = os.environ.get("COSYVOICE_MODEL") or stored.get("model", "cosyvoice-v3.5-flash")
    return CosyVoiceConfig(api_key=api_key, base_url=base_url, model=model)


class CosyVoiceClient:
    def __init__(self, config: CosyVoiceConfig) -> None:
        if not config.api_key:
            raise CosyVoiceError("未配置 DashScope API Key")
        self.config = config

    def synthesize(
        self,
        text: str,
        voice_id: str,
        instruction: str = "",
        ssml: str = "",
    ) -> bytes:
        if not voice_id:
            raise CosyVoiceError("请先选择或创建一个 CosyVoice 音色")
        clean_ssml = sanitize_ssml(ssml)
        payload = {
            "model": self.config.model,
            "input": {
                "text": clean_ssml or text,
                "voice": voice_id,
                "format": "mp3",
                "sample_rate": 24000,
                "volume": 50,
                "rate": 1.0,
                "pitch": 1.0,
                "language_hints": ["zh"],
            },
        }
        if clean_ssml:
            payload["input"]["enable_ssml"] = True
        if instruction:
            payload["input"]["instruction"] = build_instruction(instruction)
        body = self._post("/services/audio/tts/SpeechSynthesizer", payload)
        audio = body.get("output", {}).get("audio", {})
        if audio.get("data"):
            return base64.b64decode(audio["data"])
        url = audio.get("url")
        if not url:
            raise CosyVoiceError(f"CosyVoice 未返回音频：{body}")
        return self._download(url)

    def create_voice(self, sample_url: str, name: str, description: str = "") -> VoiceProfile:
        if not sample_url:
            raise CosyVoiceError("声音复刻需要公网可访问的音频 URL")
        prefix = _voice_prefix(name)
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": self.config.model,
                "prefix": prefix,
                "url": sample_url,
                "language_hints": ["zh"],
            },
        }
        body = self._post("/services/audio/tts/customization", payload)
        output = body.get("output", {})
        voice_id = output.get("voice_id") or output.get("voice")
        if not voice_id:
            raise CosyVoiceError(f"声音复刻未返回 voice_id：{body}")
        return VoiceProfile(
            id=voice_id,
            name=name,
            description=description,
            sample_url=sample_url,
            status=output.get("status", "DEPLOYING"),
            target_model=output.get("target_model", self.config.model),
            created_at=time.time(),
        )

    def query_voice(self, voice_id: str) -> dict[str, Any]:
        body = self._post(
            "/services/audio/tts/customization",
            {
                "model": "voice-enrollment",
                "input": {"action": "query_voice", "voice_id": voice_id},
            },
        )
        return body.get("output", {})

    def delete_voice(self, voice_id: str) -> None:
        self._post(
            "/services/audio/tts/customization",
            {
                "model": "voice-enrollment",
                "input": {"action": "delete_voice", "voice_id": voice_id},
            },
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CosyVoiceError(f"DashScope 请求失败 ({exc.code}): {detail[:800]}") from exc
        except urllib.error.URLError as exc:
            raise CosyVoiceError(f"DashScope 连接失败：{exc}") from exc
        return body

    @staticmethod
    def _download(url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=90) as response:
            return response.read()


def _voice_prefix(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]", "", name)
    if not value:
        value = f"voice{int(time.time())}"
    return value[:10]


__all__ = ["CosyVoiceClient", "CosyVoiceConfig", "CosyVoiceError", "VoiceProfile", "load_config"]
