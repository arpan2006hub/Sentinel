"""Correlate multimodal anomaly outputs into unified investigation timelines, graphs, and incidents.

Batch/CLI mode over the global ``artifacts/`` outputs written by the baseline
trainers (``scripts/run_all.py``). The backend performs the same correlation
per case through ``POST /api/analysis/start``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.correlation.correlator import MultimodalCorrelator


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Multimodal Evidence Correlation Engine")
    parser.add_argument("--data-dir", default="data/generated", help="Directory with raw inputs (badge.csv is read from here)")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Base artifacts directory")
    parser.add_argument("--output", default="artifacts/correlation/events.jsonl", help="Target output file for correlated clusters")
    parser.add_argument("--window-minutes", type=int, default=60, help="Sliding temporal correlation window in minutes")
    args = parser.parse_args()

    artifacts_path = Path(args.artifacts_dir)
    data_path = Path(args.data_dir)
    output_dir = Path(args.output).parent

    correlator = MultimodalCorrelator(window_minutes=args.window_minutes)
    events = correlator.load_events_from_artifacts(
        cyber_csv=artifacts_path / "cyber" / "cyber_predictions.csv",
        video_csv=artifacts_path / "video" / "video_predictions.csv",
        crime_jsonl=artifacts_path / "video" / "crime_events.jsonl",
        document_jsonl=artifacts_path / "documents" / "document_predictions.jsonl",
        badge_csv=data_path / "badge.csv",
    )

    if not events:
        print("[!] No anomaly predictions found under artifacts/. Run starter training first.", file=sys.stderr)
        sys.exit(1)

    result = correlator.run_correlation(events=events, output_dir=output_dir)
    print(json.dumps({**result["summary"], "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
