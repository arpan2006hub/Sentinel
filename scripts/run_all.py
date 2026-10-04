"""Run the complete local Sentinel starter experiment."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    print("\n$", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/generated")
    args = parser.parse_args()
    root = Path(args.data)
    if not (root / "cyber.csv").exists():
        run([sys.executable, "scripts/generate_demo_data.py", "--output", str(root)])
    run([sys.executable, "ai/cyber/train.py", "--data", str(root / "cyber.csv")])
    run([sys.executable, "ai/video/train.py", "--data", str(root / "video.csv")])
    run([sys.executable, "ai/documents/train.py", "--data", str(root / "documents.jsonl")])
    run([sys.executable, "ai/correlation/run.py", "--data-dir", str(root)])
    print("\nComplete. Inspect artifacts/ for models, predictions, metrics, and correlation output.")


if __name__ == "__main__":
    main()

