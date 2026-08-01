"""设定上下文数据快照（v1 绞杀：从 prompting/providers/storyline 迁出，供一致性/后台分析使用）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SetupContextSnapshot:
    world_building: object
    characters: object
    core_concept: object
