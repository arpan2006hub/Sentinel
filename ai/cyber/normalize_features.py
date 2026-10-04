"""Create per-user behavioural deviation features for CERT data.

Raw counts mostly identify busy users. This script converts each count to a
log-scaled z-score relative to that same user's history, which better answers
whether a day was unusual for that user.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES = ["login_count", "file_reads", "usb_events", "http_events", "email_events", "bytes_out"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    available = [c for c in FEATURES if c in df.columns]
    if not available:
        raise ValueError("No recognised behaviour features found")

    result = df[["timestamp", "user_id"]].copy()
    for feature in available:
        raw = df[feature].fillna(0).astype(float)
        transformed = pd.Series(np.log1p(raw), index=df.index)
        means = transformed.groupby(df["user_id"]).transform("mean")
        stds = transformed.groupby(df["user_id"]).transform("std").fillna(0)
        result[feature] = ((transformed - means) / (stds + 1e-6)).fillna(0)
        result[f"raw_{feature}"] = raw

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(f"Wrote {len(result):,} user-normalized rows to {output}")


if __name__ == "__main__":
    main()
