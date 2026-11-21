"""Runtime validation for Sentinel's canonical event contract.

The schema is intentionally aligned with the event dictionaries emitted by
``ai.processing.processors``. It accepts the runtime ``timestamp`` field and
the video pipeline's ``timestamp_start`` field, while allowing optional fields
used by individual modalities.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "data" / "schemas" / "event.schema.json"


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    """Load and compile the canonical event schema once per process."""
    import json

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Unable to read canonical event schema at {SCHEMA_PATH}: {exc}") from exc
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=FormatChecker())


def validate_canonical_events(
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split events into schema-valid records and concise validation failures.

    Invalid events are excluded from correlation instead of being silently
    coerced into plausible evidence. The returned errors identify the input
    position and invalid fields without copying the evidence payload itself.
    """
    validator = _validator()
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    first_index_by_id: dict[str, int] = {}

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            invalid.append({
                "index": index,
                "event_id": None,
                "errors": ["event must be a JSON object"],
            })
            continue

        event_id = event.get("event_id")
        errors = sorted(
            validator.iter_errors(event),
            key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
        )
        messages = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
            for error in errors
        ]
        if isinstance(event_id, str) and event_id:
            if event_id in first_index_by_id:
                messages.append(
                    f"event_id: duplicate identifier (first seen at index {first_index_by_id[event_id]})"
                )
            else:
                first_index_by_id[event_id] = index

        if messages:
            invalid.append({"index": index, "event_id": event_id, "errors": messages})
            continue
        valid.append(event)

    return valid, invalid
