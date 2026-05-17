from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a synthetic longform scale smoke test.")
    parser.add_argument("--chapters", type=int, default=1000)
    parser.add_argument("--words-per-chapter", type=int, default=1000)
    parser.add_argument("--target-chapter", type=int, default=None)
    parser.add_argument("--query", type=str, default="星环钥匙")
    parser.add_argument("--max-elapsed-ms", type=int, default=None)
    parser.add_argument("--cleanup", action="store_true", help="Delete the synthetic smoke project after reporting.")
    parser.add_argument(
        "--max-stage-ms",
        action="append",
        default=[],
        metavar="STAGE=MS",
        help="Fail when a timing stage exceeds the threshold. Can be repeated.",
    )
    args = parser.parse_args(argv)
    try:
        max_stage_ms = _parse_stage_thresholds(args.max_stage_ms)
    except ValueError as exc:
        parser.error(str(exc))

    report = _run_smoke_report(args)
    try:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        failures = _threshold_failures(
            report,
            max_elapsed_ms=args.max_elapsed_ms,
            max_stage_ms=max_stage_ms,
        )
        if failures:
            for failure in failures:
                print(failure, file=sys.stderr)
            return 1
        return 0
    finally:
        if args.cleanup:
            _cleanup_smoke_project(str(report["project_id"]))


def _run_smoke_report(args: argparse.Namespace) -> dict:
    from app.core.longform_scale_smoke import run_longform_scale_smoke
    from app.db import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return run_longform_scale_smoke(
            db,
            chapter_count=args.chapters,
            words_per_chapter=args.words_per_chapter,
            target_chapter_index=args.target_chapter,
            query=args.query,
        )
    finally:
        db.close()


def _cleanup_smoke_project(project_id: str) -> None:
    from app.api.projects import delete_project
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        delete_project(project_id, db)
    finally:
        db.close()


def _parse_stage_thresholds(raw_thresholds: list[str]) -> dict[str, int]:
    thresholds: dict[str, int] = {}
    for raw_threshold in raw_thresholds:
        if "=" not in raw_threshold:
            raise ValueError(f"invalid --max-stage-ms value: {raw_threshold}")
        stage, value = raw_threshold.split("=", 1)
        stage = stage.strip()
        if not stage:
            raise ValueError(f"invalid --max-stage-ms value: {raw_threshold}")
        thresholds[stage] = int(value)
    return thresholds


def _threshold_failures(
    report: dict,
    *,
    max_elapsed_ms: int | None,
    max_stage_ms: dict[str, int],
) -> list[str]:
    failures: list[str] = []
    elapsed_ms = int(report.get("elapsed_ms") or 0)
    if max_elapsed_ms is not None and elapsed_ms > max_elapsed_ms:
        failures.append(f"elapsed_ms {elapsed_ms} exceeded max {max_elapsed_ms}")
    timings = report.get("timings_ms") or {}
    for stage, threshold in max_stage_ms.items():
        if stage not in timings:
            available = ", ".join(sorted(timings)) or "none"
            failures.append(f"unknown timing stage {stage}; available stages: {available}")
            continue
        actual = int(timings.get(stage) or 0)
        if actual > threshold:
            failures.append(f"{stage} {actual} exceeded max {threshold}")
    repeat_reindex = report.get("repeat_reindex") or {}
    if repeat_reindex:
        repeat_indexed = repeat_reindex.get("indexed") or {}
        indexed_documents = int(repeat_indexed.get("documents") or 0)
        removed_documents = int(repeat_reindex.get("removed_documents") or 0)
        preserved_documents = int(repeat_reindex.get("preserved_documents") or 0)
        expected_preserved = int((report.get("retrieval") or {}).get("total_documents") or 0)
        if indexed_documents != 0:
            failures.append(f"repeat_reindex indexed {indexed_documents} documents; expected 0")
        if removed_documents != 0:
            failures.append(f"repeat_reindex removed {removed_documents} documents; expected 0")
        if expected_preserved and preserved_documents != expected_preserved:
            failures.append(
                f"repeat_reindex preserved {preserved_documents} documents; expected {expected_preserved}"
            )
    context = report.get("context") or {}
    if context:
        retrieval_item_count = int(context.get("query_aware_retrieval_item_count") or 0)
        if retrieval_item_count < 1:
            failures.append(
                f"query_aware_retrieval returned {retrieval_item_count} items; expected at least 1"
            )
        if not context.get("query_aware_retrieval_has_explanations"):
            failures.append("query_aware_retrieval explanations missing")
        out_of_range_count = int(context.get("query_aware_retrieval_out_of_range_count") or 0)
        if out_of_range_count:
            failures.append(
                f"query_aware_retrieval included {out_of_range_count} future/out-of-range items"
            )
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
