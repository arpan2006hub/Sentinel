"""Train a supervised CERT insider-day classifier with a chronological split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, classification_report, precision_recall_fscore_support, roc_auc_score

FEATURES = ["login_count", "file_reads", "usb_events", "http_events", "email_events", "bytes_out"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="artifacts/cyber-supervised")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.data)
    if "label" not in df:
        raise ValueError("This supervised trainer requires a label column")
    features = [c for c in FEATURES if c in df.columns]
    df = df.sort_values("timestamp").reset_index(drop=True)
    split = int(len(df) * (1 - args.test_fraction))
    x_train = df.loc[: split - 1, features].fillna(0)
    x_test = df.loc[split:, features].fillna(0)
    y_train = df.loc[: split - 1, "label"].astype(int)
    y_test = df.loc[split:, "label"].astype(int)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=16,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= args.threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predictions, average="binary", zero_division=0)
    metrics = {
        "train_rows": len(x_train), "test_rows": len(x_test),
        "test_positive_rows": int(y_test.sum()), "predicted_positive_rows": int(predictions.sum()),
        "threshold": args.threshold, "precision": float(precision),
        "recall": float(recall), "f1": float(f1),
    }
    if y_test.nunique() == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))
        metrics["average_precision"] = float(average_precision_score(y_test, probabilities))
    result = df.iloc[split:].copy()
    result["risk_score"] = probabilities
    result["prediction"] = predictions
    result.to_csv(out / "predictions.csv", index=False)
    joblib.dump({"model": model, "features": features}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(classification_report(y_test, predictions, zero_division=0))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

