"""Train a simple document suspiciousness classifier (TF-IDF + logistic regression).

JSONL rows require: document_id, text, optional timestamp and optional label
(1 = suspicious). The extraction output also includes entities used by the
correlation engine.

This is a demo baseline: with tiny synthetic corpora the reported numbers are
in-sample and must not be presented as a held-out evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.processing.processors import extract_entities  # noqa: E402


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
    if len(set(labels)) < 2:
        raise ValueError("Training data needs both suspicious (1) and normal (0) labels")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("classifier", LogisticRegression(max_iter=500, class_weight="balanced")),
    ])
    pipeline.fit(texts, labels)
    scores = pipeline.predict_proba(texts)[:, 1]
    predictions = (scores >= 0.5).astype(int)
    with (out / "document_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row, pred, score in zip(rows, predictions, scores):
            handle.write(json.dumps({
                **row, "prediction": int(pred), "suspicious_score": float(score),
                "entities": extract_entities(row["text"]),
            }) + "\n")
    joblib.dump({"model": pipeline, "features": ["text"]}, out / "model.joblib")
    print(json.dumps({"rows": len(rows), "predicted_suspicious": int(predictions.sum()),
                      "note": "in-sample predictions (demo baseline)"}, indent=2))


if __name__ == "__main__":
    main()
