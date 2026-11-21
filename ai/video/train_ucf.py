"""Train/evaluate a supervised video-level UCF-Crime baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, classification_report, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURES = ["motion_mean", "motion_std", "motion_max", "motion_p95", "motion_spikes", "duration_seconds"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="artifacts/video-ucf")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data).dropna(subset=FEATURES + ["label"])
    train, test = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])
    model = RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced", random_state=42, n_jobs=-1)
    model.fit(train[FEATURES], train["label"])
    scores = model.predict_proba(test[FEATURES])[:, 1]
    prediction = (scores >= args.threshold).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(test["label"], prediction, average="binary", zero_division=0)
    metrics = {"train_rows": len(train), "test_rows": len(test), "precision": float(p), "recall": float(r), "f1": float(f1), "threshold": args.threshold}
    if test["label"].nunique() == 2:
        metrics["roc_auc"] = float(roc_auc_score(test["label"], scores))
        metrics["average_precision"] = float(average_precision_score(test["label"], scores))
    result = test.copy()
    result["risk_score"] = scores
    result["prediction"] = prediction
    result.to_csv(out / "predictions.csv", index=False)
    joblib.dump({"model": model, "features": FEATURES}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(classification_report(test["label"], prediction, zero_division=0))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

