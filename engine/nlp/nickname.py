"""Rule layer for turning raw nicknames into spoken Chinese names."""

from __future__ import annotations

import re
import unicodedata

_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF"
    "]+"
)
_SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄麹家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴郁胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公")
_IMAGE_POOL = {
    "太阳": "太阳宝子",
    "月亮": "月亮宝子",
    "奶茶": "奶茶宝子",
    "猫咪": "猫猫宝子",
    "小狗": "狗狗宝子",
}
_FALLBACK_POOL = ("宝子", "家人", "亲")


def _clean(nickname: str) -> str:
    text = unicodedata.normalize("NFKC", nickname)
    text = _EMOJI.sub("", text)
    return text.strip(" _-")


def _remove_ascii_prefix(text: str) -> str:
    match = re.match(r"^[A-Za-z0-9_\- ]*(?=[\u4e00-\u9fff])", text)
    if match:
        return text[match.end() :]
    return text


def speakable_name(nickname: str) -> str:
    if not nickname:
        return "宝子"
    text = _clean(nickname)
    lowered = text.lower()
    text = _remove_ascii_prefix(lowered)
    if not text:
        return _FALLBACK_POOL[hash(nickname) % len(_FALLBACK_POOL)]

    for keyword, spoken in _IMAGE_POOL.items():
        if keyword in text:
            return spoken

    for prefix in ("小", "阿"):
        if len(text) >= 2 and text[0] == prefix and text[1] in _SURNAMES:
            return f"{text[1]}哥"
    if text[0] in _SURNAMES:
        return f"{text[0]}哥"
    if text.endswith(("哥", "姐", "总", "老板")):
        return text
    return _FALLBACK_POOL[hash(nickname) % len(_FALLBACK_POOL)]


__all__ = ["speakable_name"]

