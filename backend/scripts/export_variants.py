"""B1: export one instance of every GreenlineEvent variant to
frontend/src/state/__fixtures__/allVariants.json, for Person A's reducer tests.

This is the ONLY file under frontend/ that Person B's tooling writes. It is
test data, not demo data (docs/04-EVENT-CONTRACT.md).

Run from backend/: .venv\\Scripts\\python.exe scripts\\export_variants.py
"""

from __future__ import annotations

import json
from pathlib import Path

from greenline.events.fixtures import ALL_VARIANTS
from greenline.events.models import dump_event

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "state" / "__fixtures__" / "allVariants.json"


def main() -> None:
    payload = {name: dump_event(event) for name, event in ALL_VARIANTS.items()}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", newline="\n")
    print(f"Wrote {len(payload)} variants to {OUTPUT}")


if __name__ == "__main__":
    main()
