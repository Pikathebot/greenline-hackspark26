"""B12: CLI wrapper for greenline.demo.export (docs/05-BACKEND-SPEC.md §11).

Picks the best completed live run per case and writes it to
demo_runs/<caseId>.json. Needs real run history in the DB first (run
scripts/run_batch.py, or just play with the app for a while).

Run from backend/: .venv\\Scripts\\python.exe scripts\\export_demo_runs.py
"""

from __future__ import annotations

from greenline.config import get_settings
from greenline.demo.export import export_all
from greenline.persistence.db import init_db


def main() -> None:
    settings = get_settings()
    db = init_db(settings.db_full_path())
    result = export_all(db, settings.demo_runs_path())

    for case_id, run_id in result["exported"].items():
        print(f"{case_id}: exported from {run_id}")
    for case_id in result["skipped"]:
        print(f"{case_id}: no qualifying completed live run yet -- skipped")

    total = len(result["exported"]) + len(result["skipped"])
    print(f"\nExported {len(result['exported'])}/{total} cases.")
    if result["skipped"]:
        print(f"Still missing: {', '.join(result['skipped'])} -- run scripts/run_batch.py first.")


if __name__ == "__main__":
    main()
