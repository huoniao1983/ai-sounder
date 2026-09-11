import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from engine.content.generator import ProductBrief
from engine.content.llm import LlmConfig, OpenAICompatibleScriptGenerator


def test_openai_compatible_generator_uses_configuration() -> None:
    captured: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            captured["path"] = self.path
            captured["authorization"] = self.headers.get("Authorization")
            captured["request"] = json.loads(self.rfile.read(length))
            content = json.dumps(
                [
                    {
                        "content": "欢迎新朋友，先看这款羽绒服的用料。",
                        "instruction": "亲切自然，像刚看到观众进直播间，重点词稍微加重。",
                        "ssml": '<speak>欢迎新朋友，<break time="250ms"/>先看这款羽绒服的用料。</speak>',
                    },
                    {"content": "别划走，今天福利只剩最后三分钟。"},
                    {"content": "想要优惠价的朋友，点击关注马上解锁。"},
                ],
                ensure_ascii=False,
            )
            body = json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = LlmConfig(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="test-model",
            api_key="test-key",
        )
        provider = OpenAICompatibleScriptGenerator(config)
        brief = ProductBrief(product="羽绒服", selling_points=["保暖"], audience="家人们")
        scripts = asyncio.run(provider.generate(brief, count=3))
    finally:
        server.shutdown()
        thread.join()

    assert captured["path"] == "/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["request"]["model"] == "test-model"
    assert len(scripts) == 3
    assert scripts[0].content.startswith("欢迎新朋友")
    assert scripts[0].instruction
    assert '<break time="250ms"/>' in scripts[0].ssml
    assert "CosyVoice" in captured["request"]["messages"][0]["content"]
