#!/usr/bin/env python3
"""create_case.py — Create a new investigation case in Sentinel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.app.schemas.cases import CaseCreate
from backend.app.services.case_service import CaseService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new investigation case in Sentinel")
    parser.add_argument("--title", required=True, help="Investigation case title")
    parser.add_argument("--description", default="", help="Detailed case description")
    parser.add_argument("--metadata", default="{}", help="Optional JSON metadata string")
    args = parser.parse_args()

    try:
        metadata = json.loads(args.metadata)
    except json.JSONDecodeError as err:
        print(f"Error: Invalid JSON for --metadata: {err}", file=sys.stderr)
        sys.exit(1)

    case_in = CaseCreate(
        title=args.title,
        description=args.description,
        metadata=metadata,
    )

    service = CaseService.get_instance()
    # pyrefly: ignore[bad-argument-type]
    created = service.create_case(case_in)

    print("\n[+] Investigation Case Created Successfully:")
    print(f"  Case ID:     {created.case_id}")
    print(f"  Title:       {created.title}")
    print(f"  Status:      {created.status}")
    print(f"  Description: {created.description or '(None)'}")
    print(f"  Created At:  {created.created_at}")
    print(f"  Metadata:    {json.dumps(created.metadata)}")


if __name__ == "__main__":
    main()
