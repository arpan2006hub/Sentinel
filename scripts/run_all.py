"""Run the complete local Sentinel starter experiment (CPU, ~10 seconds).

1. Generate the synthetic multimodal scenario (if missing or --regenerate).
2. Fit the three lightweight baselines (seconds each, synthetic data only).
3. Correlate everything into artifacts/correlation/.

TimeSformer is NOT run here (CPU-heavy); see ai/video/detect_crime.py or
scripts/demo.py --video.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("\n$", " ".join(command))
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/generated")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate the synthetic data even if present")
    args = parser.parse_args()
    root = Path(args.data)
    if args.regenerate or not (PROJECT_ROOT / root / "badge.csv").exists():
        run([sys.executable, "scripts/generate_demo_data.py", "--output", str(root)])
    run([sys.executable, "ai/cyber/train.py", "--data", str(root / "cyber.csv")])
    run([sys.executable, "ai/video/train.py", "--data", str(root / "video.csv")])
    run([sys.executable, "ai/documents/train.py", "--data", str(root / "documents.jsonl")])
    run([sys.executable, "ai/correlation/run.py", "--data-dir", str(root)])
    print("\nComplete. Inspect artifacts/ for models, predictions, metrics, and correlation output.")


if __name__ == "__main__":
    main()
