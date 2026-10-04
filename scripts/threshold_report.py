"""Show precision/recall trade-offs for a saved supervised prediction file."""

from __future__ import annotations

import argparse

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.predictions)
    print("threshold  alerts  precision  recall  f1")
    for threshold in [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        prediction = (df["risk_score"] >= threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(df["label"], prediction, average="binary", zero_division=0)
        print(f"{threshold:9.2f} {int(prediction.sum()):7d} {precision:10.3f} {recall:7.3f} {f1:5.3f}")


if __name__ == "__main__":
    main()

