"""Local capability server used by the desktop UI in development.

The browser shell cannot read arbitrary disk files or call the DashScope API
directly without CORS, so this stdlib server exposes local assets, CosyVoice
v3.5 synthesis, voice cloning and AI script generation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import mimetypes
import os
import re
import sys
import unicodedata
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from engine.content.generator import ProductBrief
from engine.content.llm import LlmConfig, OpenAICompatibleScriptGenerator
from engine.platform.service import PlatformService
from engine.tts.cosyvoice import CosyVoiceClient, CosyVoiceError, load_config

LOGGER = logging.getLogger("aisounder.api")
if os.environ.get("AISOUNDER_RESOURCE_DIR"):
    ROOT = Path(os.environ["AISOUNDER_RESOURCE_DIR"]).resolve()
elif getattr(sys, "frozen", False):
    ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    ROOT = Path(__file__).resolve().parents[1]
MUSIC_DIR = ROOT / "assets" / "music"
VOICE_DIR = ROOT / "assets" / "voices"
RUNTIME_DIR = Path(os.environ.get("AISOUNDER_DATA_DIR") or ROOT / "runtime")
CUSTOM_VOICE_FILE = RUNTIME_DIR / "custom-voices.json"
PLATFORM_SERVICE = PlatformService()

MUSIC_META = {
    "sold-out.mp3": {"title": "Sold Out", "category": "燃向促销", "duration": "03:33"},
    "wake.mp3": {"title": "Wake", "category": "轻快带货", "duration": "04:15"},
}

def _speech_ready(text: str) -> str:
    """Normalize one TTS utterance so placeholders and spacing never break flow."""

    value = unicodedata.normalize("NFKC", text)
    value = re.sub(r"[｛{]\s*nickname\s*[｝}]", "朋友", value, flags=re.IGNORECASE)
    value = re.sub(r"[｛{]\s*gift\s*[｝}]", "礼物", value, flags=re.IGNORECASE)
    value = re.sub(r"[｛{]\s*keyword\s*[｝}]", "福利", value, flags=re.IGNORECASE)
    value = re.sub(r"[｛{][^｝}]*[｝}]", "朋友", value)
    value = re.sub(r"\bxxx\b", "朋友", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"([\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", r"\1", value)
    value = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9_\- ]+)(?=[\u4e00-\u9fff])", r"\1", value)
    duplicate = re.compile(r"([\u4e00-\u9fff]{3,})\1")
    while duplicate.search(value):
        value = duplicate.sub(r"\1", value)
    return value.strip()


def _load_custom_voices() -> list[dict[str, Any]]:
    if not CUSTOM_VOICE_FILE.exists():
        return []
    try:
        return json.loads(CUSTOM_VOICE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save_custom_voices(items: list[dict[str, Any]]) -> None:
    CUSTOM_VOICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_VOICE_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _refresh_custom_voices() -> list[dict[str, Any]]:
    items = _load_custom_voices()
    if not items:
        return items
    changed = False
    try:
        client = _cosyvoice_client()
    except CosyVoiceError:
        return items
    for item in items:
        if item.get("status") == "OK" or not item.get("id"):
            continue
        try:
            remote = client.query_voice(str(item["id"]))
        except CosyVoiceError as exc:
            LOGGER.warning("refresh voice %s failed: %s", item.get("id"), exc)
            continue
        status = remote.get("status")
        if status and status != item.get("status"):
            item["status"] = status
            changed = True
        for field in ("gmt_create", "gmt_modified"):
            if remote.get(field) and remote.get(field) != item.get(field):
                item[field] = remote[field]
                changed = True
    if changed:
        _save_custom_voices(items)
    return items


def _cosyvoice_client() -> CosyVoiceClient:
    config = load_config(RUNTIME_DIR)
    return CosyVoiceClient(config)


def _synthesize_cosyvoice(
    voice: str,
    text: str,
    instruction: str = "",
    ssml: str = "",
) -> bytes:
    cache_dir = RUNTIME_DIR / "tts-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(
        f"{voice}|{text}|{instruction}|{ssml}".encode("utf-8")
    ).hexdigest()[:24]
    cache_path = cache_dir / f"{voice}-{key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes()
    audio = _cosyvoice_client().synthesize(
        text,
        voice,
        instruction=instruction,
        ssml=ssml,
    )
    cache_path.write_bytes(audio)
    return audio


def _mime(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "AISounderApi/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)

    def _send_headers(self, status: int = 200, content_type: str = "application/json", length: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        if content_type:
            self.send_header("Content-Type", content_type)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid json: {exc}") from exc
        return parsed if isinstance(parsed, dict) else {}

    def do_OPTIONS(self) -> None:
        self._send_headers(204)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/health":
                return self._json({"ok": True, "service": "aisounder-local-api"})
            if parsed.path == "/assets/music":
                items = []
                for path in sorted(MUSIC_DIR.glob("*.mp3")):
                    meta = MUSIC_META.get(path.name, {})
                    items.append(
                        {
                            "id": path.stem,
                            "file": path.name,
                            "url": f"/media/music/{path.name}",
                            **meta,
                        }
                    )
                return self._json({"items": items})
            if parsed.path == "/assets/voices":
                custom = _refresh_custom_voices()
                return self._json({"items": custom})
            if parsed.path.startswith("/media/"):
                return self._serve_media(parsed.path)
            if parsed.path == "/tts":
                return self._serve_tts(query)
            if parsed.path == "/engines":
                config = load_config(RUNTIME_DIR)
                return self._json(
                    {
                        "cosyvoice": bool(config.api_key),
                        "model": config.model,
                        "provider": "DashScope CosyVoice",
                    }
                )
            if parsed.path == "/platform/status":
                return self._json({"items": PLATFORM_SERVICE.status()})
            if parsed.path == "/platform/events":
                return self._json({"items": PLATFORM_SERVICE.recent_events()})
            if parsed.path == "/config/tts":
                config = load_config(RUNTIME_DIR)
                return self._json(
                    {
                        "configured": bool(config.api_key),
                        "base_url": config.base_url,
                        "model": config.model,
                    }
                )
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            LOGGER.exception("GET %s failed", self.path)
            self._json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/scripts/generate":
                return self._generate_scripts()
            if parsed.path == "/voice/upload":
                return self._upload_voice()
            if parsed.path == "/voice/delete":
                return self._delete_voice()
            if parsed.path == "/data/save":
                return self._save_data()
            if parsed.path == "/platform/connect":
                body = self._read_json()
                platform = str(body.get("platform", ""))
                config = body.get("config", {})
                if not platform or not isinstance(config, dict):
                    raise ValueError("platform and config are required")
                return self._json(PLATFORM_SERVICE.connect(platform, config))
            if parsed.path == "/platform/disconnect":
                body = self._read_json()
                platform = str(body.get("platform", ""))
                if not platform:
                    raise ValueError("platform is required")
                return self._json(PLATFORM_SERVICE.disconnect(platform))
            if parsed.path == "/platform/callback":
                body = self._read_json()
                platform = str(body.get("platform", ""))
                payload = body.get("payload", {})
                if not platform or not isinstance(payload, dict):
                    raise ValueError("platform and payload are required")
                return self._json(PLATFORM_SERVICE.ingest(platform, payload))
            if parsed.path == "/config/tts":
                body = self._read_json()
                config_path = RUNTIME_DIR / "tts-config.json"
                existing: dict[str, Any] = {}
                if config_path.exists():
                    try:
                        existing = json.loads(config_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        existing = {}
                api_key = str(body.get("api_key", "")).strip() or str(existing.get("api_key", ""))
                base_url = str(body.get("base_url", "")).strip() or str(
                    existing.get("base_url", "https://dashscope.aliyuncs.com/api/v1")
                )
                model = str(body.get("model", "")).strip() or str(
                    existing.get("model", "cosyvoice-v3.5-flash")
                )
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(
                    json.dumps(
                        {"api_key": api_key, "base_url": base_url, "model": model},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return self._json({"saved": True, "configured": bool(api_key), "model": model})
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            LOGGER.exception("POST %s failed", self.path)
            self._json({"error": str(exc)}, 500)

    def _serve_media(self, path: str) -> None:
        rel = path.removeprefix("/media/")
        allowed = {
            "music": MUSIC_DIR,
            "voices": VOICE_DIR,
            "uploads": RUNTIME_DIR / "uploads",
        }
        kind, _, name = rel.partition("/")
        if kind not in allowed:
            return self._json({"error": "invalid media path"}, 404)
        base = allowed[kind].resolve()
        target = (allowed[kind] / name).resolve()
        if not target.is_file() or base not in target.parents:
            return self._json({"error": "media not found"}, 404)
        data = target.read_bytes()
        self._send_headers(200, _mime(target), len(data))
        self.wfile.write(data)

    def _serve_tts(self, query: dict[str, list[str]]) -> None:
        voice = query.get("voice", [""])[0]
        text = query.get("text", ["你好"])[0]
        instruction = query.get("instruction", [""])[0]
        ssml = query.get("ssml", [""])[0]
        text = _speech_ready(text)
        data = _synthesize_cosyvoice(voice, text, instruction, ssml)
        self._serve_bytes(data, "audio/mpeg")

    def _serve_bytes(self, data: bytes, content_type: str) -> None:
        self._send_headers(200, content_type, len(data))
        self.wfile.write(data)

    def _generate_scripts(self) -> None:
        body = self._read_json()
        config = LlmConfig(
            base_url=body.get("base_url") or "https://api.openai.com/v1",
            model=body.get("model") or "gpt-4o-mini",
            api_key=body.get("api_key", ""),
        )
        brief = ProductBrief(
            product=body.get("product", ""),
            selling_points=list(body.get("selling_points", [])),
            audience=body.get("audience", ""),
        )
        count = int(body.get("count", 5))
        generator = OpenAICompatibleScriptGenerator(config)
        scripts = asyncio.run(generator.generate(brief, count=count))
        self._json(
            {
                "scripts": [
                    {
                        "id": s.id,
                        "label": f"AI 文案 {index + 1:02d}",
                        "content": s.content,
                        "weight": s.weight,
                        "instruction": s.instruction,
                        "ssml": s.ssml,
                    }
                    for index, s in enumerate(scripts)
                ]
            }
        )

    def _upload_voice(self) -> None:
        body = self._read_json()
        sample_url = str(body.get("sample_url", "")).strip()
        if not sample_url:
            raise ValueError("CosyVoice 声音复刻需要公网可访问的音频 URL")
        display_name = str(body.get("display_name") or body.get("name") or "我的音色").strip()
        description = str(body.get("description", "")).strip()
        cloned = _cosyvoice_client().create_voice(sample_url, display_name, description)
        custom = _load_custom_voices()
        profile = {
            "id": cloned.id,
            "name": cloned.name,
            "description": cloned.description,
            "sample_url": cloned.sample_url,
            "status": cloned.status,
            "target_model": cloned.target_model,
            "provider": "DashScope CosyVoice",
            "created_at": cloned.created_at,
        }
        custom.append(profile)
        _save_custom_voices(custom)
        self._json({"profile": profile})

    def _delete_voice(self) -> None:
        body = self._read_json()
        voice_id = body.get("id")
        if voice_id:
            try:
                _cosyvoice_client().delete_voice(str(voice_id))
            except CosyVoiceError:
                pass
        items = [item for item in _load_custom_voices() if item.get("id") != voice_id]
        _save_custom_voices(items)
        self._json({"ok": True})

    def _save_data(self) -> None:
        body = self._read_json()
        kind = re.sub(r"[^a-zA-Z0-9_-]", "", body.get("kind", "app"))
        (RUNTIME_DIR / "state").mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / "state" / f"{kind}.json").write_text(
            json.dumps(body.get("data", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._json({"ok": True})

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    RUNTIME_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"AISounder local API: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
