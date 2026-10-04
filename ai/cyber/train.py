"""Train and evaluate a cyber-log anomaly detector.

Input CSV columns: timestamp, user_id, login_count, file_reads, usb_events,
bytes_out, and optional label (1 = suspicious).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, precision_recall_fscore_support, roc_auc_score
from sklearn.preprocessing import StandardScaler

BASE_FEATURES = ["login_count", "file_reads", "usb_events", "bytes_out"]
OPTIONAL_FEATURES = ["http_events", "email_events", "after_hours_events"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="artifacts/cyber")
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--test-fraction", type=float, default=0.2, help="Chronological held-out fraction; use 0 to evaluate in-sample")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data)
    FEATURES = [c for c in BASE_FEATURES + OPTIONAL_FEATURES if c in df.columns]
    missing = [c for c in BASE_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if not 0 <= args.test_fraction < 1:
        raise ValueError("--test-fraction must be >= 0 and < 1")
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)
    x = df[FEATURES].fillna(0).astype(float)
    split_index = len(df) if args.test_fraction == 0 else max(1, int(len(df) * (1 - args.test_fraction)))
    x_train = x.iloc[:split_index]
    scaler = StandardScaler().fit(x_train)
    x_scaled = scaler.transform(x)
    x_train_scaled = x_scaled[:split_index]
    model = IsolationForest(n_estimators=200, contamination=args.contamination, random_state=42, n_jobs=-1)
    model.fit(x_train_scaled)
    prediction = (model.predict(x_scaled) == -1).astype(int)
    result = df.copy()
    result["anomaly_score"] = -model.score_samples(x_scaled)
    result["prediction"] = prediction
    result.to_csv(out / "cyber_predictions.csv", index=False)
    joblib.dump({"model": model, "scaler": scaler, "features": FEATURES}, out / "model.joblib")

    metrics = {"rows": len(df), "train_rows": split_index, "test_rows": len(df) - split_index, "predicted_anomalies": int(prediction.sum())}
    if "label" in df:
        y = df["label"].astype(int)
        eval_y = y.iloc[split_index:] if split_index < len(df) else y
        eval_prediction = pd.Series(prediction, index=df.index).iloc[split_index:] if split_index < len(df) else pd.Series(prediction)
        eval_scores = result["anomaly_score"].iloc[split_index:] if split_index < len(df) else result["anomaly_score"]
        p, r, f1, _ = precision_recall_fscore_support(eval_y, eval_prediction, average="binary", zero_division=0)
        metrics.update({"precision": float(p), "recall": float(r), "f1": float(f1)})
        if eval_y.nunique() == 2:
            metrics["roc_auc"] = float(roc_auc_score(eval_y, eval_scores))
        print(classification_report(eval_y, eval_prediction, zero_division=0))
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
