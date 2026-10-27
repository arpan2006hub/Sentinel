"""CLI runner for Sentinel TimeSformer Crime Detector.

Runs Nikeytas/timesformer-best-crime-detector against video files and outputs:
1. JSON summary & segment classifications
2. Canonical events in JSONL format (ready for correlation pipeline)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.video.timesformer_crime_detector import TimesformerCrimeDetector


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run TimeSformer crime detection on video evidence."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to the video file to analyze.",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Local path to model.pth (if already downloaded).",
    )
    parser.add_argument(
        "--auto-download",
        action="store_true",
        help="Automatically download Nikeytas/timesformer-best-crime-detector from Hugging Face if not present.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/video/crime_analysis.json",
        help="Output path for the analysis JSON summary.",
    )
    parser.add_argument(
        "--events-output",
        default="artifacts/video/crime_events.jsonl",
        help="Output path for Sentinel Canonical Events in JSONL format.",
    )
    parser.add_argument(
        "--case-id",
        default="CASE-001",
        help="Investigation case identifier.",
    )
    parser.add_argument(
        "--location-id",
        default="ZONE-CORRIDOR-01",
        help="Physical location or camera zone ID.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Crime probability threshold (default: 0.5).",
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=2.0,
        help="Window duration in seconds for each clip.",
    )
    parser.add_argument(
        "--stride-seconds",
        type=float,
        default=1.0,
        help="Stride in seconds between successive clips.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Compute device ('cuda', 'cpu', or auto-detected).",
    )

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Initializing TimeSformer Crime Detector (model: Nikeytas/timesformer-best-crime-detector)...")
    detector = TimesformerCrimeDetector(
        model_path=args.model_path,
        device=args.device,
        auto_download=args.auto_download,
    )

    print(f"Running video analysis on {video_path} (window: {args.window_seconds}s, stride: {args.stride_seconds}s)...")
    results = detector.analyze_video(
        video_path=video_path,
        window_seconds=args.window_seconds,
        stride_seconds=args.stride_seconds,
        threshold=args.threshold,
        case_id=args.case_id,
        location_id=args.location_id,
    )

    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Analysis saved to: {out_file}")

    events = results.get("canonical_events", [])
    if events:
        events_file = Path(args.events_output)
        events_file.parent.mkdir(parents=True, exist_ok=True)
        with open(events_file, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")
        print(f"Emitted {len(events)} canonical crime event(s) to: {events_file}")
    else:
        print("No crime events detected exceeding threshold.")

    print("\nSummary:")
    print(f"- Status: {results['status']}")
    print(f"- Duration: {results['duration_seconds']}s")
    print(f"- Analyzed Segments: {results['analyzed_segments_count']}")
    print(f"- Crime Segments: {results['crime_detected_count']}")
    print(f"- Max Crime Probability: {results['max_crime_probability']}")


if __name__ == "__main__":
    main()
