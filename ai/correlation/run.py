"""Correlate multimodal anomaly outputs into unified investigation timelines, graphs, and incidents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.correlation.correlator import MultimodalCorrelator


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Multimodal Evidence Correlation Engine")
    parser.add_argument("--data-dir", default="data/generated", help="Directory of generated/raw input data")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Base artifacts directory")
    parser.add_argument("--output", default="artifacts/correlation/events.jsonl", help="Target output file for correlated clusters")
    parser.add_argument("--window-minutes", type=int, default=60, help="Sliding temporal correlation window in minutes")
    args = parser.parse_args()

    artifacts_path = Path(args.artifacts_dir)
    output_path = Path(args.output)
    output_dir = output_path.parent

    correlator = MultimodalCorrelator(window_minutes=args.window_minutes)

    events = correlator.load_events_from_artifacts(
        cyber_csv=artifacts_path / "cyber" / "cyber_predictions.csv",
        video_csv=artifacts_path / "video" / "video_predictions.csv",
        crime_jsonl=artifacts_path / "video" / "crime_events.jsonl",
        document_jsonl=artifacts_path / "documents" / "document_predictions.jsonl",
    )

    if not events:
        print("[!] No anomaly predictions found under artifacts/. Run starter training first.", file=sys.stderr)
        sys.exit(1)

    result = correlator.run_correlation(events=events, output_dir=output_dir)

    print(json.dumps({
        "clusters": result["summary"]["incident_clusters"],
        "events": result["summary"]["total_events"],
        "contradictions": result["summary"]["contradictions_detected"],
        "graph_nodes": result["summary"]["graph_nodes"],
        "graph_edges": result["summary"]["graph_edges"],
        "output": str(output_path),
    }, indent=2))


if __name__ == "__main__":
    main()
