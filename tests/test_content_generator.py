import asyncio

from engine.content.generator import DeterministicScriptGenerator, ProductBrief


def test_generator_produces_distinct_scripts() -> None:
    generator = DeterministicScriptGenerator()
    brief = ProductBrief(
        product="羽绒服",
        selling_points=["保暖", "显瘦", "工厂直发"],
        audience="家人们",
    )
    scripts = asyncio.run(generator.generate(brief, count=5))
    assert len(scripts) == 5
    assert len({script.content for script in scripts}) == 5
    assert all(script.enabled for script in scripts)

