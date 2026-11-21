"""Attach official CERT r4.2 insider-scenario labels to user-day features."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--insiders", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    answers = pd.read_csv(args.insiders)
    answers["dataset_text"] = answers["dataset"].astype(str)
    answers = answers[answers["dataset_text"].str.fullmatch(r"4[.]2")].copy()
    if answers.empty:
        raise ValueError("No dataset=4.2 rows found in insiders.csv")

    features["day"] = pd.to_datetime(features["timestamp"], utc=True).dt.date
    features["label"] = 0
    features["scenario"] = 0

    answers["start"] = pd.to_datetime(answers["start"], errors="coerce")
    answers["end"] = pd.to_datetime(answers["end"], errors="coerce")
    for _, row in answers.dropna(subset=["start", "end"]).iterrows():
        start = row["start"].date()
        end = row["end"].date()
        mask = (features["user_id"] == row["user"]) & features["day"].between(start, end)
        features.loc[mask, "label"] = 1
        features.loc[mask, "scenario"] = int(row["scenario"])

    features = features.drop(columns=["day"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output, index=False)
    print(f"Official r4.2 scenarios: {len(answers)}")
    print(f"Labeled malicious user-days: {int(features['label'].sum())}")
    print(f"Total rows: {len(features)}")
    print(features["scenario"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()

