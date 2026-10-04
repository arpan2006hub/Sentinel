"""Correlate anomaly outputs into a compact investigation timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/generated")
    parser.add_argument("--output", default="artifacts/correlation/events.jsonl")
    parser.add_argument("--window-minutes", type=int, default=60)
    args = parser.parse_args()
    root = Path(args.data_dir)
    events = []
    cyber = pd.read_csv("artifacts/cyber/cyber_predictions.csv")
    for _, row in cyber[cyber.prediction == 1].iterrows():
        events.append({"timestamp": row.timestamp, "source": "cyber", "entity": row.user_id, "score": float(row.anomaly_score), "kind": "cyber_anomaly"})
    video = pd.read_csv("artifacts/video/video_predictions.csv")
    for _, row in video[video.prediction == 1].iterrows():
        events.append({"timestamp": row.timestamp, "source": "video", "entity": "unknown", "score": float(row.anomaly_score), "kind": "video_anomaly"})
    for line in Path("artifacts/documents/document_predictions.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["prediction"]:
            for entity in row["entities"]["users"] or ["unknown"]:
                events.append({"timestamp": "2025-01-01T00:00:00+00:00", "source": "document", "entity": entity, "score": row["suspicious_score"], "kind": "document_claim", "document_id": row["document_id"]})
    frame = pd.DataFrame(events)
    if frame.empty:
        raise RuntimeError("No anomaly events were produced.")
    # pandas 3.x requires mixed-format parsing when sources use different
    # ISO timestamp spellings (for example, space vs. T separators).
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, format="mixed")
    frame = frame.sort_values("timestamp")
    groups = []
    for _, row in frame.iterrows():
        matching = [g for g in groups if row["entity"] != "unknown" and row["entity"] in g["entities"] and abs((row["timestamp"] - g["last_timestamp"]).total_seconds()) <= args.window_minutes * 60]
        if matching:
            group = matching[0]
            group["events"].append(row.to_dict())
            group["last_timestamp"] = row["timestamp"]
            group["sources"].add(row["source"])
        else:
            groups.append({"entities": {row["entity"]}, "sources": {row["source"]}, "last_timestamp": row["timestamp"], "events": [row.to_dict()]})
    result = [{"entities": sorted(g["entities"]), "sources": sorted(g["sources"]), "event_count": len(g["events"]), "events": [{**e, "timestamp": e["timestamp"].isoformat()} for e in g["events"]]} for g in groups]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"clusters": len(result), "events": len(events), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
