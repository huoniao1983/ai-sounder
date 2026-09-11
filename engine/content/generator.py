"""Script generation provider contract plus a deterministic test provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.scheduler.script_scheduler import Script


@dataclass(slots=True)
class ProductBrief:
    product: str
    selling_points: list[str]
    audience: str


class ScriptGenerator(Protocol):
    async def generate(self, brief: ProductBrief, count: int = 5) -> list[Script]:
        ...


class DeterministicScriptGenerator:
    """Deterministic provider used in tests and offline demos."""

    async def generate(self, brief: ProductBrief, count: int = 5) -> list[Script]:
        points = ", ".join(brief.selling_points) or "值得入手"
        templates = [
            f"欢迎新进直播间的{brief.audience}，今天重点讲{brief.product}：{points}。",
            f"不要划走，{brief.product}今天有惊喜价，先点关注再听我讲。",
            f"这款{brief.product}，{brief.selling_points[0] if brief.selling_points else '口碑很好'}，库存有限。",
            f"想要{brief.product}的朋友扣个 1，我按顺序介绍福利。",
            f"最后一轮讲{brief.product}，{brief.audience}现在下单最划算。",
        ]
        return [
            Script(
                id=f"generated-{index}",
                content=template,
                weight=1.0 + (0.25 * index),
                instruction="像真人主播自然交流，语气亲切，重点词稍微强调；句间短停，不要匀速念稿。",
            )
            for index, template in enumerate(templates[:count])
        ]
