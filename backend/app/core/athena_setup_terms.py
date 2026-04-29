"""Deterministic Setup world-term extraction for Athena imports."""

from __future__ import annotations

import re

from app.models import Setup


def extract_setup_world_terms(setup: Setup) -> dict[str, list[dict[str, str]]]:
    buckets: dict[str, list[dict[str, str]]] = {"locations": [], "factions": [], "artifacts": []}
    seen: dict[str, set[str]] = {key: set() for key in buckets}
    world_building = setup.world_building if isinstance(setup.world_building, dict) else {}
    core_concept = setup.core_concept if isinstance(setup.core_concept, dict) else {}
    sources = [
        ("background", str(world_building.get("background") or "")),
        ("geography", str(world_building.get("geography") or "")),
        ("society", str(world_building.get("society") or "")),
        ("rules", str(world_building.get("rules") or "")),
        ("atmosphere", str(world_building.get("atmosphere") or "")),
        ("premise", str(core_concept.get("premise") or "")),
        ("hook", str(core_concept.get("hook") or "")),
        ("unique_selling_point", str(core_concept.get("unique_selling_point") or "")),
    ]
    for source_name, text in sources:
        for term, context in quoted_terms_with_context(text):
            bucket = classify_setup_term(term, context, source_name)
            if not bucket:
                continue
            append_setup_term(buckets=buckets, seen=seen, bucket=bucket, term=term, context=context, source_name=source_name)
        for term, context in unquoted_terms_with_context(text):
            bucket = classify_setup_term(term, context, source_name)
            if not bucket:
                continue
            append_setup_term(buckets=buckets, seen=seen, bucket=bucket, term=term, context=context, source_name=source_name)
    return buckets


def append_setup_term(
    *,
    buckets: dict[str, list[dict[str, str]]],
    seen: dict[str, set[str]],
    bucket: str,
    term: str,
    context: str,
    source_name: str,
) -> None:
    if term in seen[bucket] or any(term != existing and term in existing for existing in seen[bucket]):
        return
    shorter_existing = [existing for existing in seen[bucket] if existing != term and existing in term]
    if shorter_existing:
        seen[bucket].difference_update(shorter_existing)
        buckets[bucket] = [item for item in buckets[bucket] if item["name"] not in shorter_existing]
    seen[bucket].add(term)
    buckets[bucket].append(
        {
            "name": term,
            "notes": f"来源：Setup 世界设定（{source_name}）。相关片段：{context[:220]}",
        }
    )


def quoted_terms_with_context(text: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for match in re.finditer(r"[‘'“\"]([^’'”\"]{2,30})[’'”\"]", text or ""):
        term = match.group(1).strip()
        if not term:
            continue
        start = max(0, match.start() - 45)
        end = min(len(text), match.end() + 45)
        results.append((term, text[start:end].strip()))
    return results


def unquoted_terms_with_context(text: str) -> list[tuple[str, str]]:
    normalized = (text or "").strip()
    if not normalized:
        return []
    suffixes = (
        "稳定区",
        "守夜人联盟",
        "联盟",
        "学院",
        "教会",
        "公司",
        "政府",
        "军方",
        "阵线",
        "基地",
        "空间",
        "区域",
        "海域",
        "城市",
        "星球",
        "钥匙",
        "密钥",
        "装置",
        "系统",
        "协议",
        "档案",
        "计划",
        "城",
        "港",
        "岛",
        "塔",
        "局",
        "门",
    )
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    segments = re.split(
        r"[，。；、\s]+|旁|里|内|外|中|由|被|与|和|及|到|从|在|负责|控制|存放|开启|隐瞒|看守|矗立|封锁|必须|保持",
        normalized,
    )
    for segment in segments:
        segment = segment.strip()
        if len(segment) < 2:
            continue
        for suffix in suffixes:
            for match in re.finditer(rf"[\u4e00-\u9fffA-Za-z0-9]{{1,18}}{re.escape(suffix)}", segment):
                term = clean_unquoted_setup_term(match.group(0))
                if not term or term in seen:
                    continue
                seen.add(term)
                start = max(0, normalized.find(segment) - 35)
                end = min(len(normalized), normalized.find(segment) + len(segment) + 35)
                results.append((term, normalized[start:end].strip()))
    return prefer_longer_setup_terms(results)


def prefer_longer_setup_terms(results: list[tuple[str, str]]) -> list[tuple[str, str]]:
    preferred: list[tuple[str, str]] = []
    for term, context in sorted(results, key=lambda item: (-len(item[0]), item[0])):
        if any(term != kept_term and term in kept_term for kept_term, _ in preferred):
            continue
        preferred.append((term, context))
    return preferred


def clean_unquoted_setup_term(term: str) -> str:
    cleaned = re.sub(
        r"^(?:(故事|世界|这个|一种|一个|负责|控制|存放|开启|隐瞒|巡查|矗立|封锁|必须|保持|真实用途))+",
        "",
        term.strip(),
    )
    for delimiter in ("发生在", "位于", "藏有", "藏在", "存放", "控制", "负责", "看守", "矗立", "开启"):
        if delimiter in cleaned:
            cleaned = cleaned.split(delimiter)[-1].strip()
    if len(cleaned) < 2 or len(cleaned) > 12:
        return ""
    return cleaned


def classify_setup_term(term: str, context: str, source_name: str) -> str | None:
    location_hints = ("站", "基地", "空间", "稳定区", "区域", "海域", "室", "维度", "城市", "城", "港", "岛", "塔", "星球")
    faction_hints = ("局", "阵线", "政府", "军方", "组织", "联盟", "公司", "学院", "教会", "计划")
    artifact_hints = ("门", "装置", "锚点", "档案", "系统", "协议", "钥", "密钥", "芯片")
    if any(hint in term for hint in location_hints):
        return "locations"
    if any(hint in term for hint in faction_hints):
        return "factions"
    if source_name == "society" and term.endswith("者"):
        return "factions"
    if any(hint in term for hint in artifact_hints) or "AI" in context or "人工智能" in context:
        return "artifacts"
    return None
