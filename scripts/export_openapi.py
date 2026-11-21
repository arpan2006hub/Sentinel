#!/usr/bin/env python3
"""Export the FastAPI OpenAPI schema to docs/architecture/openapi.json.

The frontend can generate TypeScript types from it, e.g.:
    npx openapi-typescript ../docs/architecture/openapi.json -o src/types/api.d.ts
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.main import app  # noqa: E402


def main() -> None:
    out = PROJECT_ROOT / "docs" / "architecture" / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(app.openapi()['paths'])} paths)")


if __name__ == "__main__":
    main()
