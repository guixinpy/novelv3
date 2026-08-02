from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.athena_setup_entity_cleanup import cleanup_phrase_like_setup_entities
from app.db import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup phrase-like Athena Setup world entities.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Apply the cleanup. Defaults to dry-run.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = cleanup_phrase_like_setup_entities(db, args.project_id, apply=args.apply)
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
