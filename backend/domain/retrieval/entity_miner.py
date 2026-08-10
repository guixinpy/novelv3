"""正文实体候选提取（实体登记来源扩展，rule 通道）。

中文姓氏白名单 + 「姓+1~2字」模式提取候选人名，跨 ≥2 章出现（chapter_count ≥ 2）才转正
进入 _capture_entities 的实体白名单。纯 Python 规则，无 NLP 依赖。
"""
from __future__ import annotations

import re
from itertools import combinations

from sqlalchemy import and_, or_, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import EntityCandidate, EntityRelation

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

_COMPOUND_RE = re.compile(rf"(?:{'|'.join(_COMPOUND_SURNAMES)})[一-鿿]{{1,2}}")
_SINGLE_RE = re.compile(rf"(?:[{''.join(_COMMON_SURNAMES)}])[一-鿿]{{1,2}}")


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
    """批量 upsert 候选实体：同章去重（不增计数），新章 chapter_count+1。返回新增数。

    批量实现（code-review #11）：一次查询取回全部已有名，消除逐名 SELECT/commit。
    """
    unique = sorted(set(names))
    if not unique:
        return 0
    existing_rows = (
        db.query(EntityCandidate)
        .filter(
            EntityCandidate.project_id == project_id,
            EntityCandidate.name.in_(unique),
        )
        .all()
    )
    existing = {e.name: e for e in existing_rows}
    added = 0
    for name in unique:
        entry = existing.get(name)
        if entry is None:
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
            if entry.last_chapter != chapter_index:
                entry.chapter_count = (entry.chapter_count or 1) + 1
            entry.last_chapter = chapter_index
            if entry.first_chapter is None:
                entry.first_chapter = chapter_index
    try:
        db.commit()
    except IntegrityError:
        # 并发写同实体：后提交者撞唯一约束（code-review #14）——回滚后重试一次：
        # 重查会命中对方已插入的行（走 update 分支），不丢本批其他候选
        # （code-review 三轮 #6：此前整批 rollback 丢弃同批已成功行且计数失真）
        db.rollback()
        existing2 = {
            e.name: e
            for e in db.query(EntityCandidate)
            .filter(
                EntityCandidate.project_id == project_id,
                EntityCandidate.name.in_(unique),
            )
            .all()
        }
        for name in unique:
            entry = existing2.get(name)
            if entry is None:
                continue  # 仍不存在（罕见）：放弃该行，不炸
            if entry.last_chapter != chapter_index:
                entry.chapter_count = (entry.chapter_count or 1) + 1
            entry.last_chapter = chapter_index
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


def record_entity_cooccurrences(
    db: Session,
    project_id: str,
    chapter_index: int,
    names: list[str],
) -> int:
    """同章实体共现建边（openhuman 共现图，特化：存 (count, last_chapter) 双字段）。

    同章提取到的实体两两成对 upsert 无向边（entity_a < entity_b 字典序）；
    同章重复出现不累计（register_entity_candidates 同章去重语义一致），
    新章共现 count+1。返回新增边数。

    批量实现（code-review #11）：一次 tuple IN 取回全部已存在边，
    消除 C(k,2) 次逐对 SELECT。
    """
    unique = sorted(set(names))
    if len(unique) < 2:
        return 0
    pairs = list(combinations(unique, 2))
    existing_rows = (
        db.query(EntityRelation)
        .filter(
            EntityRelation.project_id == project_id,
            tuple_(EntityRelation.entity_a, EntityRelation.entity_b).in_(pairs),
        )
        .all()
    )
    existing = {(r.entity_a, r.entity_b): r for r in existing_rows}
    added = 0
    for a, b in pairs:
        entry = existing.get((a, b))
        if entry is None:
            db.add(EntityRelation(
                project_id=project_id,
                entity_a=a,
                entity_b=b,
                count=1,
                last_chapter=chapter_index,
            ))
            added += 1
        else:
            if entry.last_chapter != chapter_index:
                entry.count = (entry.count or 1) + 1
            entry.last_chapter = chapter_index
    try:
        db.commit()
    except IntegrityError:
        # 并发写同对共现：后提交者撞唯一约束（code-review #14）——回滚后重试一次：
        # 重查命中对方已插入的边（走 count+1 分支），不丢本批其他边
        # （code-review 三轮 #6：此前整批 rollback 丢数据且计数失真）
        db.rollback()
        existing2 = {
            (r.entity_a, r.entity_b): r
            for r in db.query(EntityRelation)
            .filter(
                EntityRelation.project_id == project_id,
                tuple_(EntityRelation.entity_a, EntityRelation.entity_b).in_(pairs),
            )
            .all()
        }
        for a, b in pairs:
            entry = existing2.get((a, b))
            if entry is None:
                continue  # 仍不存在（罕见）：放弃该边，不炸
            if entry.last_chapter != chapter_index:
                entry.count = (entry.count or 1) + 1
            entry.last_chapter = chapter_index
        db.commit()
    return added


def related_entities(
    db: Session,
    project_id: str,
    entity: str,
    *,
    limit: int = 8,
    only_promoted: bool = True,
) -> list[dict]:
    """查询与指定实体共现的关联实体（按共现章数降序）。

    only_promoted=True（默认）：只返回已转正实体（chapter_count ≥2 或 l2）的关联，
    挡掉规则提取的噪声边。SQL 层直接过滤转正侧（code-review #12：此前先取 limit*3
    再内存过滤，截断线以下的合法转正关联会被静默漏掉）。
    """
    query = db.query(EntityRelation).filter(
        EntityRelation.project_id == project_id,
        (EntityRelation.entity_a == entity) | (EntityRelation.entity_b == entity),
    )
    if only_promoted:
        promoted = set(promoted_entity_names(db, project_id))
        if not promoted:
            return []
        # other 侧（非查询实体）必须是转正实体
        query = query.filter(
            or_(
                and_(EntityRelation.entity_a == entity, EntityRelation.entity_b.in_(promoted)),
                and_(EntityRelation.entity_b == entity, EntityRelation.entity_a.in_(promoted)),
            )
        )
    pairs = (
        query.order_by(EntityRelation.count.desc(), EntityRelation.last_chapter.desc())
        .limit(limit)
        .all()
    )
    result: list[dict] = []
    for pair in pairs:
        other = pair.entity_b if pair.entity_a == entity else pair.entity_a
        result.append({
            "entity": other,
            "cooccurrence_count": pair.count,
            "last_chapter": pair.last_chapter,
        })
    return result
