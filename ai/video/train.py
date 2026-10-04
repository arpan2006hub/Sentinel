"""Train a CPU-friendly video anomaly baseline on extracted frame features.

For real videos, first create a CSV with motion_score, person_count,
restricted_zone, and optional label columns. This avoids pretending that
UCF-Crime's weak video-level labels are bounding-box labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

FEATURES = ["motion_score", "person_count", "restricted_zone"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="artifacts/video")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data)
    x = df[FEATURES].fillna(0).astype(float)
    scaler = StandardScaler().fit(x)
    model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42, n_jobs=-1).fit(scaler.transform(x))
    pred = (model.predict(scaler.transform(x)) == -1).astype(int)
    result = df.copy()
    result["anomaly_score"] = -model.score_samples(scaler.transform(x))
    result["prediction"] = pred
    result.to_csv(out / "video_predictions.csv", index=False)
    joblib.dump({"model": model, "scaler": scaler, "features": FEATURES}, out / "model.joblib")
    metrics = {"rows": len(df), "predicted_anomalies": int(pred.sum())}
    if "label" in df:
        p, r, f1, _ = precision_recall_fscore_support(df["label"], pred, average="binary", zero_division=0)
        metrics.update({"precision": float(p), "recall": float(r), "f1": float(f1)})
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

