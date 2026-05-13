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
    args = parser.parse_args(argv)

    from app.core.longform_scale_smoke import run_longform_scale_smoke
    from app.db import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        report = run_longform_scale_smoke(
            db,
            chapter_count=args.chapters,
            words_per_chapter=args.words_per_chapter,
            target_chapter_index=args.target_chapter,
            query=args.query,
        )
    finally:
        db.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
