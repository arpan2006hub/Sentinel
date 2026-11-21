"""Extract CPU-friendly motion features from a video file.

This is a baseline for video anomaly detection. It does not claim to identify
people; it measures frame-to-frame motion and leaves person_count and
restricted_zone at zero until a detector/tracker is added.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", default="data/video/features.csv")
    parser.add_argument("--sample-every", type=int, default=15, help="Process every Nth frame")
    parser.add_argument("--resize-width", type=int, default=320)
    args = parser.parse_args()

    video_path = Path(args.video).expanduser()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    frame_number = 0
    previous = None
    rows = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_number % args.sample_every != 0:
            frame_number += 1
            continue
        width = args.resize_width
        height = max(1, int(frame.shape[0] * width / frame.shape[1]))
        small = cv2.resize(frame, (width, height))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        motion = 0.0 if previous is None else float(np.mean(cv2.absdiff(gray, previous)) / 255.0)
        rows.append({
            "timestamp": frame_number / fps,
            "camera_id": video_path.stem,
            "motion_score": motion,
            "person_count": 0,
            "restricted_zone": 0,
        })
        previous = gray
        frame_number += 1
    capture.release()
    if not rows:
        raise RuntimeError("No frames were read from the video")
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Read {frame_number:,} frames and wrote {len(rows):,} feature rows to {output}")


if __name__ == "__main__":
    main()

