from engine.nlp.nickname import speakable_name


def test_ok_little_li_becomes_li_ge() -> None:
    assert speakable_name("ok小李") == "李哥"


def test_ascii_garbage_falls_back_to_generic_name() -> None:
    assert speakable_name("Xx_Kk99") in {"宝子", "家人", "亲"}


def test_surname_prefix_uses_surname() -> None:
    assert speakable_name("张小明") == "张哥"


def test_image_dictionary_name() -> None:
    assert speakable_name("正午晒太阳") == "太阳宝子"

