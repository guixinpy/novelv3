"""Canonical world-model context assembly for Athena and Hermes."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.model_call_trace import build_context_block
from app.models import (
    ConsistencyCheck,
    Outline,
    ProjectProfileVersion,
    Setup,
    WorldArtifact,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldRelation,
    WorldRule,
)

DialogTarget = Literal["athena", "hermes"]
logger = logging.getLogger(__name__)


def source_for_record(record: Any, *, label: str | None = None, chapter_index: int | None = None) -> dict:
    source = {
        "source_type": record.__class__.__name__,
        "source_id": record.id,
    }
    if label:
        source["label"] = label
    if chapter_index is not None:
        source["chapter_index"] = chapter_index
    return source


def format_context_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


class WorldContextAssembler:
    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id
        self.profile = self._current_profile()

    def dialog_context_blocks(self, target: DialogTarget, *, chapter_index: int | None = None) -> list[dict]:
        if self.profile is None:
            if target == "athena":
                return [self._setup_fallback_block("athena")]
            return []
        if target == "hermes":
            return self._hermes_blocks(chapter_index=chapter_index)
        return self._athena_blocks()

    def dialog_context_text(self, target: DialogTarget, *, chapter_index: int | None = None) -> str:
        blocks = self.dialog_context_blocks(target, chapter_index=chapter_index)
        if self.profile is None:
            return blocks[0]["content"] if blocks else ""
        if target == "hermes":
            return "\n".join(block["content"] for block in blocks)
        if len(blocks) == 1 and blocks[0]["kind"] == "world_profile":
            return blocks[0]["content"]
        return "\n\n".join(f"## {block['title']}\n{block['content']}" for block in blocks)

    def chapter_context_package(self, chapter_index: int) -> dict[str, Any]:
        sections: list[dict[str, Any]] = []
        lines: list[str] = [f"【目标章节】第{chapter_index}章"]

        if self.profile is None:
            setup = self._setup()
            if setup:
                lines.append("【世界模型】尚未导入正式 world-model，以下仅为 Setup 草稿。")
                self._append_setup_context(lines, setup)
                self._append_retrieval_context(chapter_index=chapter_index, lines=lines, sections=sections)
            return {
                "chapter_index": chapter_index,
                "profile_version": None,
                "project_profile_version_id": None,
                "sections": sections,
                "prompt_context": "\n".join(lines),
            }

        lines.append(f"【世界模型】Profile v{self.profile.version}")
        self._append_outline_context(chapter_index=chapter_index, lines=lines, sections=sections)
        self._append_retrieval_context(chapter_index=chapter_index, lines=lines, sections=sections)
        self._append_chapter_entities(lines=lines, sections=sections)
        self._append_chapter_rules(lines=lines, sections=sections)
        self._append_chapter_facts(chapter_index=chapter_index, lines=lines, sections=sections)
        self._append_open_issues(lines=lines, sections=sections)
        return {
            "chapter_index": chapter_index,
            "profile_version": self.profile.version,
            "project_profile_version_id": self.profile.id,
            "sections": sections,
            "prompt_context": "\n".join(lines),
        }

    def _current_profile(self) -> ProjectProfileVersion | None:
        return (
            self.db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.project_id == self.project_id)
            .order_by(ProjectProfileVersion.version.desc())
            .first()
        )

    def _setup(self) -> Setup | None:
        return self.db.query(Setup).filter(Setup.project_id == self.project_id).first()

    def _setup_fallback_block(self, key_prefix: str) -> dict:
        setup = self._setup()
        if setup is None:
            return build_context_block(
                key=f"{key_prefix}.setup_fallback",
                kind="setup_fallback",
                title="Setup 草稿兜底",
                content="当前项目尚未建立正式 world-model profile，也没有可参考的 Setup 草稿。",
            )

        lines = [
            "当前项目尚未建立正式 world-model profile；以下内容来自 Setup 草稿，尚未导入 canonical world-model。",
        ]
        self._append_setup_context(lines, setup)
        return build_context_block(
            key=f"{key_prefix}.setup_fallback",
            kind="setup_fallback",
            title="Setup 草稿兜底",
            content="\n".join(lines),
            sources=[source_for_record(setup, label="Setup 草稿")],
        )

    def _athena_blocks(self) -> list[dict]:
        blocks: list[dict] = []
        entity_block = self._entity_block(limit_characters=20, limit_locations=10, limit_factions=10)
        if entity_block:
            blocks.append(entity_block)
        blocks.extend(
            block
            for block in [
                self._relations_block(limit=30, key_prefix="athena", title="关系网络"),
                self._rules_block(limit=20),
                self._facts_block(limit=50, key_prefix="athena", title="当前确认事实"),
                self._events_block(limit=30),
            ]
            if block
        )
        if not blocks:
            blocks.append(
                build_context_block(
                    key="athena.world_profile",
                    kind="world_profile",
                    title="世界档案",
                    content="世界档案已建立（v{}），但尚无结构化数据。".format(self.profile.version),
                    sources=[source_for_record(self.profile, label=f"profile v{self.profile.version}")],
                )
            )
        return blocks

    def _hermes_blocks(self, *, chapter_index: int | None) -> list[dict]:
        blocks: list[dict] = []
        characters = self._characters(limit=10)
        if characters:
            blocks.append(
                build_context_block(
                    key="hermes.world_entities",
                    kind="world_entity",
                    title="主要角色",
                    content="主要角色：" + "、".join(item.name for item in characters),
                    sources=[source_for_record(item, label=item.name) for item in characters],
                )
            )
        facts = self._facts(limit=20, chapter_index=chapter_index, ascending=True)
        if facts:
            blocks.append(
                build_context_block(
                    key="hermes.world_facts",
                    kind="world_fact",
                    title="关键事实",
                    content="\n".join(
                        f"- {item.subject_ref}.{item.predicate} = {format_context_value(item.object_ref_or_value)}"
                        for item in facts
                    ),
                    sources=[
                        source_for_record(item, label=item.claim_id, chapter_index=item.chapter_index)
                        for item in facts
                    ],
                )
            )
        relation_block = self._relations_block(limit=15, key_prefix="hermes", title="角色关系")
        if relation_block:
            blocks.append(relation_block)
        return blocks

    def _entity_block(self, *, limit_characters: int, limit_locations: int, limit_factions: int) -> dict | None:
        characters = self._characters(limit=limit_characters)
        locations = self._locations(limit=limit_locations)
        factions = self._factions(limit=limit_factions)
        lines = []
        sources = []
        for character in characters:
            lines.append(f"- 角色：{character.name}（{character.role_type}）")
            sources.append(source_for_record(character, label=character.name))
        for location in locations:
            lines.append(f"- 地点：{location.name}")
            sources.append(source_for_record(location, label=location.name))
        for faction in factions:
            lines.append(f"- 阵营：{faction.name}")
            sources.append(source_for_record(faction, label=faction.name))
        if not lines:
            return None
        return build_context_block(
            key="athena.world_entities",
            kind="world_entity",
            title="世界实体",
            content="\n".join(lines),
            sources=sources,
        )

    def _relations_block(self, *, limit: int, key_prefix: str, title: str) -> dict | None:
        relations = (
            self.db.query(WorldRelation)
            .filter(WorldRelation.project_id == self.project_id, WorldRelation.profile_version == self.profile.version)
            .order_by(
                WorldRelation.source_entity_ref.asc(),
                WorldRelation.relation_type.asc(),
                WorldRelation.target_entity_ref.asc(),
                WorldRelation.id.asc(),
            )
            .limit(limit)
            .all()
        )
        if not relations:
            return None
        return build_context_block(
            key=f"{key_prefix}.world_relations",
            kind="world_relation",
            title=title,
            content="\n".join(
                f"- {item.source_entity_ref} → {item.relation_type} → {item.target_entity_ref}"
                for item in relations
            ),
            sources=[source_for_record(item, label=item.relation_id) for item in relations],
        )

    def _rules_block(self, *, limit: int) -> dict | None:
        rules = (
            self.db.query(WorldRule)
            .filter(WorldRule.project_id == self.project_id, WorldRule.profile_version == self.profile.version)
            .order_by(WorldRule.primary_alias.asc(), WorldRule.canonical_id.asc(), WorldRule.id.asc())
            .limit(limit)
            .all()
        )
        if not rules:
            return None
        return build_context_block(
            key="athena.world_rules",
            kind="world_rule",
            title="世界规则",
            content="\n".join(f"- {item.name}：{item.statement}" for item in rules),
            sources=[source_for_record(item, label=item.name) for item in rules],
        )

    def _facts_block(self, *, limit: int, key_prefix: str, title: str) -> dict | None:
        facts = self._facts(limit=limit, ascending=True)
        if not facts:
            return None
        return build_context_block(
            key=f"{key_prefix}.world_facts",
            kind="world_fact",
            title=title,
            content="\n".join(
                f"- {item.subject_ref}.{item.predicate} = {format_context_value(item.object_ref_or_value)}"
                for item in facts
            ),
            sources=[source_for_record(item, label=item.claim_id, chapter_index=item.chapter_index) for item in facts],
        )

    def _events_block(self, *, limit: int) -> dict | None:
        events = (
            self.db.query(WorldEvent)
            .filter(
                WorldEvent.project_id == self.project_id,
                WorldEvent.project_profile_version_id == self.profile.id,
                WorldEvent.profile_version == self.profile.version,
            )
            .order_by(
                WorldEvent.chapter_index.asc(),
                WorldEvent.intra_chapter_seq.asc(),
                WorldEvent.event_id.asc(),
                WorldEvent.id.asc(),
            )
            .limit(limit)
            .all()
        )
        if not events:
            return None
        return build_context_block(
            key="athena.world_timeline",
            kind="world_timeline",
            title="时间线事件",
            content="\n".join(
                f"- 第{item.chapter_index}章：{item.event_type} {format_context_value(item.primitive_payload)}"
                for item in events
            ),
            sources=[source_for_record(item, label=item.event_id, chapter_index=item.chapter_index) for item in events],
        )

    def _characters(self, *, limit: int) -> list[WorldCharacter]:
        return (
            self.db.query(WorldCharacter)
            .filter(WorldCharacter.project_id == self.project_id, WorldCharacter.profile_version == self.profile.version)
            .order_by(WorldCharacter.name.asc(), WorldCharacter.canonical_id.asc(), WorldCharacter.id.asc())
            .limit(limit)
            .all()
        )

    def _locations(self, *, limit: int) -> list[WorldLocation]:
        return (
            self.db.query(WorldLocation)
            .filter(WorldLocation.project_id == self.project_id, WorldLocation.profile_version == self.profile.version)
            .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc(), WorldLocation.id.asc())
            .limit(limit)
            .all()
        )

    def _factions(self, *, limit: int) -> list[WorldFaction]:
        return (
            self.db.query(WorldFaction)
            .filter(WorldFaction.project_id == self.project_id, WorldFaction.profile_version == self.profile.version)
            .order_by(WorldFaction.name.asc(), WorldFaction.canonical_id.asc(), WorldFaction.id.asc())
            .limit(limit)
            .all()
        )

    def _facts(self, *, limit: int, chapter_index: int | None = None, ascending: bool) -> list[WorldFactClaim]:
        query = self.db.query(WorldFactClaim).filter(
            WorldFactClaim.project_id == self.project_id,
            WorldFactClaim.project_profile_version_id == self.profile.id,
            WorldFactClaim.profile_version == self.profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        if chapter_index is not None:
            query = query.filter((WorldFactClaim.chapter_index.is_(None)) | (WorldFactClaim.chapter_index <= chapter_index))
        if ascending:
            query = query.order_by(
                WorldFactClaim.chapter_index.asc(),
                WorldFactClaim.intra_chapter_seq.asc(),
                WorldFactClaim.claim_id.asc(),
                WorldFactClaim.id.asc(),
            )
        else:
            query = query.order_by(
                WorldFactClaim.chapter_index.desc(),
                WorldFactClaim.intra_chapter_seq.desc(),
                WorldFactClaim.claim_id.asc(),
                WorldFactClaim.id.asc(),
            )
        return query.limit(limit).all()

    def _append_setup_context(self, lines: list[str], setup: Setup) -> None:
        if setup.characters:
            names = [str(item.get("name")) for item in setup.characters if isinstance(item, dict) and item.get("name")]
            if names:
                lines.append("Setup 草稿角色：" + "、".join(names[:20]))
        if isinstance(setup.world_building, dict) and setup.world_building:
            lines.append(f"Setup 草稿世界设定：{setup.world_building}")
        if isinstance(setup.core_concept, dict) and setup.core_concept:
            lines.append(f"Setup 草稿核心概念：{setup.core_concept}")

    def _append_outline_context(self, *, chapter_index: int, lines: list[str], sections: list[dict[str, Any]]) -> None:
        outline = self.db.query(Outline).filter(Outline.project_id == self.project_id).first()
        if not outline or not outline.chapters:
            return
        for chapter_outline in outline.chapters:
            if isinstance(chapter_outline, dict) and chapter_outline.get("chapter_index") == chapter_index:
                summary = f"{chapter_outline.get('title', '')}：{chapter_outline.get('summary', '')}".strip("：")
                lines.append(f"【本章大纲】{summary}")
                sections.append({"key": "outline", "title": "本章大纲", "items": [chapter_outline]})
                return

    def _append_retrieval_context(self, *, chapter_index: int, lines: list[str], sections: list[dict[str, Any]]) -> None:
        try:
            from app.core.athena_retrieval import build_chapter_retrieval_context

            retrieval_context = build_chapter_retrieval_context(
                db=self.db,
                project_id=self.project_id,
                chapter_index=chapter_index,
            )
        except Exception as exc:
            logger.exception("Failed to build Athena retrieval context for project %s chapter %s", self.project_id, chapter_index)
            sections.append(
                {
                    "key": "retrieval_warning",
                    "title": "检索诊断",
                    "items": [
                        {
                            "code": "retrieval_context_failed",
                            "message": "检索证据暂不可用，已跳过本次证据注入。",
                            "error_type": exc.__class__.__name__,
                        }
                    ],
                }
            )
            lines.append("【检索证据】检索证据暂不可用，已跳过本次证据注入。")
            return
        if not retrieval_context:
            return
        sections.append(retrieval_context["section"])
        lines.extend(retrieval_context["prompt_lines"])

    def _append_chapter_entities(self, *, lines: list[str], sections: list[dict[str, Any]]) -> None:
        characters = self._characters(limit=30)
        if characters:
            items = [
                {"ref": item.canonical_id, "name": item.name, "role_type": item.role_type, "notes": item.notes}
                for item in characters
            ]
            sections.append({"key": "characters", "title": "相关角色", "items": items})
            lines.append("【相关角色】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

        locations = self._locations(limit=20)
        if locations:
            items = [
                {"ref": item.canonical_id, "name": item.name, "location_type": item.location_type, "notes": item.notes}
                for item in locations
            ]
            sections.append({"key": "locations", "title": "关键地点", "items": items})
            lines.append("【关键地点】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

        factions = self._factions(limit=20)
        if factions:
            items = [
                {"ref": item.canonical_id, "name": item.name, "faction_type": item.faction_type, "notes": item.notes}
                for item in factions
            ]
            sections.append({"key": "factions", "title": "关键势力", "items": items})
            lines.append("【关键势力】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

        artifacts = (
            self.db.query(WorldArtifact)
            .filter(WorldArtifact.project_id == self.project_id, WorldArtifact.profile_version == self.profile.version)
            .order_by(WorldArtifact.name.asc(), WorldArtifact.canonical_id.asc(), WorldArtifact.id.asc())
            .limit(20)
            .all()
        )
        if artifacts:
            items = [
                {"ref": item.canonical_id, "name": item.name, "artifact_type": item.artifact_type, "notes": item.notes}
                for item in artifacts
            ]
            sections.append({"key": "artifacts", "title": "关键物件", "items": items})
            lines.append("【关键物件】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

    def _append_chapter_rules(self, *, lines: list[str], sections: list[dict[str, Any]]) -> None:
        rules = (
            self.db.query(WorldRule)
            .filter(WorldRule.project_id == self.project_id, WorldRule.profile_version == self.profile.version)
            .order_by(WorldRule.name.asc(), WorldRule.canonical_id.asc(), WorldRule.id.asc())
            .limit(12)
            .all()
        )
        if not rules:
            return
        items = [
            {"ref": item.canonical_id, "name": item.name, "rule_type": item.rule_type, "statement": item.statement}
            for item in rules
        ]
        sections.append({"key": "rules", "title": "世界规则", "items": items})
        lines.append("【世界规则】")
        for rule in items[:8]:
            statement = str(rule["statement"]).replace("\n", " ")[:300]
            lines.append(f"- {rule['name']}({rule['ref']}): {statement}")

    def _append_chapter_facts(self, *, chapter_index: int, lines: list[str], sections: list[dict[str, Any]]) -> None:
        facts = self._facts(limit=40, chapter_index=chapter_index, ascending=False)
        if not facts:
            return
        items = [
            {
                "claim_id": item.claim_id,
                "subject_ref": item.subject_ref,
                "predicate": item.predicate,
                "value": item.object_ref_or_value,
                "chapter_index": item.chapter_index,
            }
            for item in facts
        ]
        sections.append({"key": "facts", "title": "已确认事实", "items": items})
        lines.append("【已确认事实】")
        for fact in items[:20]:
            lines.append(f"- {fact['subject_ref']}.{fact['predicate']} = {format_context_value(fact['value'])}")

    def _append_open_issues(self, *, lines: list[str], sections: list[dict[str, Any]]) -> None:
        issues = (
            self.db.query(ConsistencyCheck)
            .filter(
                ConsistencyCheck.project_id == self.project_id,
                ConsistencyCheck.status == "pending",
                ConsistencyCheck.severity.in_(["fatal", "warn"]),
            )
            .order_by(ConsistencyCheck.chapter_index.desc())
            .limit(20)
            .all()
        )
        if not issues:
            return
        items = [
            {
                "chapter_index": item.chapter_index,
                "severity": item.severity,
                "checker_name": item.checker_name,
                "description": item.description,
                "suggested_fix": item.suggested_fix,
            }
            for item in issues
        ]
        sections.append({"key": "open_issues", "title": "未解决一致性问题", "items": items})
        lines.append("【未解决一致性问题】")
        for issue in items[:8]:
            lines.append(f"- {issue['severity']} 第{issue['chapter_index']}章 {issue['description']}")


def build_dialog_context_blocks(
    db: Session,
    project_id: str,
    target: DialogTarget,
    *,
    chapter_index: int | None = None,
) -> list[dict]:
    return WorldContextAssembler(db, project_id).dialog_context_blocks(target, chapter_index=chapter_index)


def build_dialog_context_text(
    db: Session,
    project_id: str,
    target: DialogTarget,
    *,
    chapter_index: int | None = None,
) -> str:
    return WorldContextAssembler(db, project_id).dialog_context_text(target, chapter_index=chapter_index)


def build_chapter_world_context_package(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    return WorldContextAssembler(db, project_id).chapter_context_package(chapter_index)
