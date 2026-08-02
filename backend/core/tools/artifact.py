"""Artifact 落盘路径校验（openhuman：路径解析 fail-closed）。

工具把大产出写文件后回传 ArtifactRef；本模块保证路径不逃逸工作目录
（拒绝绝对路径 / `..` / 空路径）。
"""
from __future__ import annotations

from pathlib import Path

from core.tools.base import ArtifactRef


def validate_artifact_path(
    raw: str,
    work_root: Path,
    allow_subdirs: bool = True,
) -> ArtifactRef | None:
    """校验并构造 ArtifactRef。非法路径返回 None（调用方应视为失败）。

    Args:
        raw: 工具声称的产出路径（相对 work_root）。
        work_root: 允许落盘的根目录（fail-closed：根目录外一律拒绝）。
        allow_subdirs: 是否允许根目录下任意子目录（False 则只允许根目录直属文件）。
    """
    if not raw or raw.strip() in (".", ".."):
        return None
    p = Path(raw)
    if p.is_absolute():
        return None
    if ".." in p.parts:
        return None
    if p.parts and p.parts[0] in ("~",):
        return None
    root = work_root.resolve()
    candidate = (work_root / p).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not allow_subdirs and candidate.parent != root:
        return None
    return ArtifactRef(path=str(candidate))
