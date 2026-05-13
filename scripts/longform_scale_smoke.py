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
        actual = int(timings.get(stage) or 0)
        if actual > threshold:
            failures.append(f"{stage} {actual} exceeded max {threshold}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
