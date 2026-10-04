"""Convert CERT r4.2 logs into Sentinel per-user/per-day features.

The CERT release has no row-level anomaly label in the ordinary log files, so
this first pass is intentionally unsupervised. It creates behavioural features
for Isolation Forest. CSVs are read in chunks to keep memory usage reasonable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def aggregate_file(path: Path, kind: str, chunksize: int = 100_000) -> pd.DataFrame:
    required = {"date", "user"}
    totals: dict[tuple[str, str], dict[str, float]] = {}
    for chunk in pd.read_csv(path, usecols=lambda c: c in {"date", "user"}, chunksize=chunksize, on_bad_lines="skip"):
        chunk["date"] = pd.to_datetime(chunk["date"], errors="coerce")
        chunk = chunk.dropna(subset=["date", "user"])
        chunk["day"] = chunk["date"].dt.strftime("%Y-%m-%d")
        grouped = chunk.groupby(["user", "day"], sort=False).size()
        for (user, day), count in grouped.items():
            key = (str(user), str(day))
            row = totals.setdefault(key, {})
            row.setdefault(kind, 0.0)
            row[kind] += float(count)
    return pd.DataFrame([
        {"user_id": user, "day": day, kind: values.get(kind, 0.0)}
        for (user, day), values in totals.items()
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert-dir", required=True, help="Path to CERT release directory, e.g. ~/sentinel-data/cert/r4.2")
    parser.add_argument("--output", default="data/cert/cyber_features.csv")
    parser.add_argument("--chunksize", type=int, default=100_000)
    args = parser.parse_args()

    root = Path(args.cert_dir).expanduser()
    if not root.exists():
        raise FileNotFoundError(root)
    paths = {
        "login_count": root / "logon.csv",
        "file_reads": root / "file.csv",
        "usb_events": root / "device.csv",
        "http_events": root / "http.csv",
        "email_events": root / "email.csv",
    }
    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(path)

    combined: pd.DataFrame | None = None
    for feature, path in paths.items():
        print(f"Reading {path.name} in chunks...")
        current = aggregate_file(path, feature, args.chunksize)
        combined = current if combined is None else combined.merge(current, on=["user_id", "day"], how="outer")

    assert combined is not None
    for column in ["login_count", "file_reads", "usb_events", "http_events", "email_events", "bytes_out"]:
        if column not in combined:
            combined[column] = 0.0
        combined[column] = combined[column].fillna(0.0)
    combined["timestamp"] = pd.to_datetime(combined["day"], utc=True).astype(str)
    combined = combined[["timestamp", "user_id", "login_count", "file_reads", "usb_events", "http_events", "email_events", "bytes_out"]].sort_values(["timestamp", "user_id"])
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    print(f"Wrote {len(combined):,} rows to {output}")


if __name__ == "__main__":
    main()
