"""OpenAI-compatible chat-completions provider for AI script generation."""

from __future__ import annotations

import asyncio
import json
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError

from engine.content.generator import ProductBrief
from engine.content.script_performance import build_instruction, sanitize_ssml
from engine.scheduler.script_scheduler import Script

SCRIPT_SYSTEM_PROMPT = """你是一位顶级直播带货主播和口播导演，不是文案机器。你的任务是把商品信息写成“真人此刻正在直播”的台词。

真实性规则：
1. 像对手机前的一个具体顾客说话，不用公告腔、播音腔、论文腔。
2. 多用短句、追问、自答、转折、提醒和行动指令；一句话只表达一个重点。
3. 语气词只在真人会说的位置使用，例如“来”“你看”“我跟你说”“别急”“说真的”，禁止每句都堆“家人们”“宝子们”。
4. 允许自然的重复、强调和口语修正，但不要制造虚假库存、虚假价格、绝对化承诺或医疗功效。
5. 每条话术要体现情绪推进：例如先抓住注意，再解释，再制造决策压力，最后给行动指令。
6. 保留主播直播时会有的呼吸位置，不要所有句子等长、等速。

交付格式必须是 JSON 数组，不要 Markdown，不要解释。每个元素包含：
- content: 最终朗读文本，中文口语，适合直接播报。
- instruction: 给 CosyVoice 的表演指令，描述情绪、语速、重音、节奏和呼吸感，控制在 120 个中文字符内。
- ssml: 可选。若使用，必须是完整 <speak>...</speak>，只能使用 <break time="...ms"/>、<phoneme>、<say-as>、<sub>、<soundEvent> 标签；不要使用 prosody 或 emphasis。

ssml 中停顿要克制真实：短句间 150-350ms，情绪转折或重点前 350-700ms，单条话术通常 0-3 个 break。不要为了效果堆砌标签。

示例：
[{"content":"来，刚进直播间的先别急着走。","instruction":"亲切、带一点急切，像刚看到新观众进直播间；前半句平稳，后半句稍微加快并强调“别急着走”。","ssml":"<speak>来，<break time=\\"250ms\\"/>刚进直播间的先别急着走。</speak>"}]"""


@dataclass(slots=True)
class LlmConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    temperature: float = 0.85
    max_tokens: int = 3200


class OpenAICompatibleScriptGenerator:
    """Call any OpenAI-compatible ``/chat/completions`` endpoint.

    ``base_url`` may point at the vendor root or directly at an existing
    ``/chat/completions`` URL; the request always targets chat completions.
    """

    def __init__(self, config: LlmConfig | None = None) -> None:
        self.config = config or LlmConfig()

    async def generate(self, brief: ProductBrief, count: int = 5) -> list[Script]:
        return await asyncio.to_thread(self._generate_sync, brief, count)

    def _generate_sync(self, brief: ProductBrief, count: int) -> list[Script]:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": SCRIPT_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "count": count,
                            "product": brief.product,
                            "selling_points": brief.selling_points,
                            "audience": brief.audience,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            self._chat_url(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed ({exc.code}): {detail[:500]}") from exc
        return self._parse_response(body, count)

    def _chat_url(self) -> str:
        base = self.config.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _parse_response(self, body: str, count: int) -> list[Script]:
        try:
            response = json.loads(body)
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unexpected LLM response: {body[:500]}") from exc

        text = content.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        entries: list[Any] = []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [line.strip() for line in text.splitlines() if line.strip()]
        if isinstance(parsed, dict):
            parsed = parsed.get("scripts", [])
        if not isinstance(parsed, list):
            parsed = [text]

        generated: list[tuple[str, str, str]] = []
        for item in parsed:
            if isinstance(item, dict):
                content_value = item.get("content", item.get("text"))
                instruction_value = item.get("instruction", "")
                ssml_value = item.get("ssml", "")
            else:
                content_value = item
                instruction_value = ""
                ssml_value = ""
            if isinstance(content_value, str) and content_value.strip():
                generated.append(
                    (
                        content_value.strip(),
                        build_instruction(str(instruction_value)),
                        sanitize_ssml(str(ssml_value)),
                    )
                )

        # Keep distinct items only; providers occasionally repeat a template.
        seen: set[str] = set()
        result: list[Script] = []
        for index, (entry, instruction, ssml) in enumerate(generated):
            if entry in seen:
                continue
            seen.add(entry)
            result.append(
                Script(
                    id=f"llm-{index}",
                    content=entry,
                    weight=1.0,
                    instruction=instruction,
                    ssml=ssml,
                )
            )
            if len(result) >= count:
                break
        return result


__all__ = ["LlmConfig", "OpenAICompatibleScriptGenerator"]
