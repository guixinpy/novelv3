"""正文实体候选提取（实体登记来源扩展，rule 通道）。

中文姓氏白名单 + 「姓+1~2字」模式提取候选人名，跨 ≥2 章出现（chapter_count ≥ 2）才转正
进入 _capture_entities 的实体白名单。纯 Python 规则，无 NLP 依赖。
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import EntityCandidate

# 常见中文姓氏（百家姓主体 + 常见补充 + 复姓）
_COMMON_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹束龙"
    "叶幸司韶郜黎蓟薄印宿白怀蒲邰鄂索咸籍赖卓蔺屠蒙池乔阴郁胥能苍双"
    "闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮牛寿通边扈燕冀郏浦尚农"
    "温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚简饶空"
    "曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)

# 复姓（优先匹配）
_COMPOUND_SURNAMES = (
    "欧阳", "司马", "上官", "诸葛", "东方", "独孤", "南宫", "夏侯", "皇甫",
    "尉迟", "公孙", "慕容", "司徒", "司空", "轩辕", "令狐", "钟离", "长孙",
    "宇文", "鲜于", "闾丘", "子车", "亓官", "司寇", "巫马", "公羊", "太史",
    "端木", "东郭", "百里", "南门", "西门", "东门", "左丘", "梁丘",
)

# 尾字停止词（排除非人名误报：虚词/常用动词/称谓尾）
_STOP_TAIL = set(
    "的了一是在不和有也都很着过就说道看想去来走水光城树年月"
    "人天上里中前后手身心话事情意子儿生死老大么什这那与及或"
    "左右旁边上下内外东西南北中间处地方时间时候刻分秒钟点"
    "自己你我他她它们之其于被把让给对从向为因所以但而如果则"
    "又会又再还才刚正已经将就要着正曾经常一直总终于突然忽然"
    "真真假假好坏错对是非对错真假远近高矮胖瘦美丑善恶"
    "站坐立躺哭喊叫笑望问答回迎送等停待走"
    "先码头嫂婶叔伯爷奶"
    "句个些多白座影面底怀记花家那许明背脊刀枪剑衣鞋帽屋楼桥塔"
    "海江河湖溪泉山石林竹梅兰菊荷柳杨枫松柏桃杏梨枣柿"
    "冷暖雨风雷电晨昏昼夜朝暮"
    "头脸眉目耳鼻口舌齿喉颈肩臂掌指腿足骨血"
    "金木水火土玉珠贝壳彩纹纹路痕印迹声光色香味"
    "官民贼寇盗匪侠士圣贤豪杰英雄百姓凡尘俗世间"
    "眼耳鼻舌身意声色香味触法"
    "条片种两尾庵堂楼阁馆店寺庙观墙窗桌椅凳碗筷杯盏灯烛绳线针"
    "料末文越满久传粉沫粒沙"
)

_COMPOUND_RE = re.compile(r"(?:%s)[一-鿿]{1,2}" % "|".join(_COMPOUND_SURNAMES))
_SINGLE_RE = re.compile(r"(?:[%s])[一-鿿]{1,2}" % "".join(_COMMON_SURNAMES))


_HAN_CHAR = re.compile(r"[一-鿿]")


def _candidate_at(text: str, start: int, surname_len: int) -> str | None:
    """从姓氏位置提取候选：优先 姓+2字名，尾字为停止词则回退 姓+1字名。

    尾字必须为汉字（避免标点被截入：如「欧阳雪。」→「欧阳雪」）。
    """
    full_end = start + surname_len + 2
    if full_end <= len(text) and _HAN_CHAR.match(text[full_end - 1]) and text[full_end - 1] not in _STOP_TAIL:
        return text[start:full_end]
    short_end = start + surname_len + 1
    if short_end <= len(text) and _HAN_CHAR.match(text[short_end - 1]) and text[short_end - 1] not in _STOP_TAIL:
        return text[start:short_end]
    return None


def mine_entities_from_text(text: str) -> list[str]:
    """从正文提取候选人名（去重保序）。复姓优先匹配，避免被单姓拆分。"""
    candidates: list[str] = []
    seen: set[str] = set()

    def accept(name: str) -> None:
        if name not in seen:
            seen.add(name)
            candidates.append(name)

    # 复姓候选（欧阳/司马 等）
    for match in _COMPOUND_RE.finditer(text):
        start = match.start()
        name = _candidate_at(text, start, len("欧阳"))
        if name:
            accept(name)

    # 单姓候选：跳过复姓位置
    for match in _SINGLE_RE.finditer(text):
        start = match.start()
        compound_here = any(
            text.startswith(prefix, start)
            for prefix in _COMPOUND_SURNAMES
        )
        if compound_here:
            continue
        name = _candidate_at(text, start, 1)
        if name:
            accept(name)

    return candidates


def register_entity_candidates(
    db: Session,
    project_id: str,
    chapter_index: int,
    names: list[str],
    source: str = "rule",
) -> int:
    """upsert 候选实体：同章去重（不增计数），新章 chapter_count+1。返回新增数。"""
    added = 0
    for name in names:
        existing = (
            db.query(EntityCandidate)
            .filter(
                EntityCandidate.project_id == project_id,
                EntityCandidate.name == name,
            )
            .first()
        )
        if existing is None:
            db.add(EntityCandidate(
                project_id=project_id,
                name=name,
                source=source,
                first_chapter=chapter_index,
                last_chapter=chapter_index,
                chapter_count=1,
            ))
            added += 1
        else:
            if existing.last_chapter != chapter_index:
                existing.chapter_count = (existing.chapter_count or 1) + 1
            existing.last_chapter = chapter_index
            if existing.first_chapter is None:
                existing.first_chapter = chapter_index
    db.commit()
    return added


def promoted_entity_names(db: Session, project_id: str) -> list[str]:
    """转正候选：rule 来源 chapter_count ≥2 + l2 来源（免转正）。"""
    rows = (
        db.query(EntityCandidate)
        .filter(EntityCandidate.project_id == project_id)
        .all()
    )
    promoted = [
        c.name for c in rows
        if c.source == "l2" or (c.chapter_count or 0) >= 2
    ]
    return sorted(set(promoted))
