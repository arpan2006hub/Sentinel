"""Extract one motion-feature row per UCF-Crime video.

This is a lightweight video-level baseline. UCF-Crime provides weak video-level
labels for training, so this is not the paper's frame-level deep MIL model.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def video_features(path: Path, sample_every: int, max_samples: int) -> dict:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open {path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    previous = None
    motions = []
    frame = 0
    while len(motions) < max_samples:
        ok, image = capture.read()
        if not ok:
            break
        if frame % sample_every == 0:
            small = cv2.resize(image, (160, 90))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                motions.append(float(np.mean(cv2.absdiff(gray, previous)) / 255.0))
            previous = gray
        frame += 1
    capture.release()
    if not motions:
        motions = [0.0]
    values = np.asarray(motions, dtype=float)
    return {
        "video": str(path), "motion_mean": float(values.mean()),
        "motion_std": float(values.std()), "motion_max": float(values.max()),
        "motion_p95": float(np.percentile(values, 95)),
        "motion_spikes": float(np.mean(values > max(0.15, values.mean() + values.std()))),
        "duration_seconds": float(frame_count / fps) if frame_count else 0.0,
        "sample_count": len(values),
        "label": int("Normal" not in path.parent.name),
        "category": path.parent.name,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", required=True, help="UCF_Crimes/Videos directory")
    parser.add_argument("--output", default="data/video/ucf_features.csv")
    parser.add_argument("--sample-every", type=int, default=30)
    parser.add_argument("--max-samples", type=int, default=300)
    args = parser.parse_args()
    root = Path(args.videos).expanduser()
    files = sorted([p for p in root.rglob("*") if p.suffix.lower() in {".mp4", ".avi", ".mpeg", ".mpg"}])
    if not files:
        raise FileNotFoundError(f"No videos found below {root}")
    rows = []
    for index, path in enumerate(files, 1):
        try:
            rows.append(video_features(path, args.sample_every, args.max_samples))
            if index % 25 == 0:
                print(f"Processed {index}/{len(files)} videos...")
        except RuntimeError as error:
            print(f"Skipping {path}: {error}")
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Wrote {len(rows)} video rows to {output}")


if __name__ == "__main__":
    main()

