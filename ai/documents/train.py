"""Train a simple document suspiciousness classifier.

JSONL rows require: document_id, text, and optional label (1 = suspicious).
The extraction output also includes simple entities useful to correlation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def entities(text: str) -> dict:
    return {
        "users": sorted(set(re.findall(r"\buser_\d{3}\b", text))),
        "times": sorted(set(re.findall(r"\b\d{1,2}:\d{2}\s*(?:UTC)?\b", text, flags=re.I))),
        "keywords": sorted(set(re.findall(r"\b(?:restricted|USB|removable media|copied|accessed)\b", text, flags=re.I))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="artifacts/documents")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    texts = [r["text"] for r in rows]
    labels = [int(r.get("label", 0)) for r in rows]
    pipeline = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)), ("classifier", LogisticRegression(max_iter=500, class_weight="balanced"))])
    pipeline.fit(texts, labels)
    scores = pipeline.predict_proba(texts)[:, 1]
    predictions = (scores >= 0.5).astype(int)
    output = []
    for row, pred, score in zip(rows, predictions, scores):
        output.append({**row, "prediction": int(pred), "suspicious_score": float(score), "entities": entities(row["text"])})
    with (out / "document_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in output:
            handle.write(json.dumps(row) + "\n")
    joblib.dump(pipeline, out / "model.joblib")
    print(json.dumps({"rows": len(rows), "predicted_suspicious": int(predictions.sum())}, indent=2))


if __name__ == "__main__":
    main()

