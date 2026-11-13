"""Evidence processors: turn one evidence file into Sentinel canonical events.

Every processor is CPU-light (seconds on a laptop) and never trains a model
that needs a separate training step:

* if a saved baseline model exists (``artifacts/<modality>/model.joblib``) it is
  used for scoring;
* otherwise the unsupervised Isolation Forest is fitted on the evidence file
  itself (legitimate for unsupervised anomaly detection), or a transparent
  keyword heuristic is used for documents.

Event dictionaries share these keys (a superset of
``data/schemas/event.schema.json`` used internally by the correlation engine)::

    event_id, case_id, timestamp, timestamp_end, source, source_type, source_id,
    actor_id, action, kind, location_id, object_id, score, confidence,
    prediction, details/metadata
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

CYBER_FEATURES = [
    "login_count", "file_reads", "usb_events", "bytes_out",
    "http_events", "email_events", "after_hours_events",
]
VIDEO_FEATURES = ["motion_score", "person_count", "restricted_zone"]

SUSPICIOUS_TERMS = {
    "usb": 0.15, "removable media": 0.15, "external storage": 0.15, "copied": 0.12, "copying": 0.12,
    "exfiltrat": 0.25, "restricted": 0.12, "server room": 0.1, "confidential": 0.1,
    "source code": 0.1, "after hours": 0.1, "tailgat": 0.2, "denied": 0.1,
    "unauthori": 0.2, "personal email": 0.15, "resign": 0.1, "competitor": 0.2,
    "delete": 0.08, "password": 0.1, "shared credential": 0.2,
}

USER_PATTERN = re.compile(r"\b(?:user[_\-]?\d{1,4}|badge[_\-]?\d{1,4})\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
ISO_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?\b")
ZONE_PATTERN = re.compile(r"\bZONE-[A-Z0-9-]+\b")


def _event_id(prefix: str, source_id: str, index: int) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", str(source_id))[:8].upper() or "SRC"
    return f"EVT-{prefix}-{token}-{index:04d}"


def _clean(value: Any) -> Any:
    """Convert numpy / NaN values to JSON-friendly Python values."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _rank_scores(raw: np.ndarray) -> np.ndarray:
    """Map raw anomaly scores to [0, 1] by percentile rank within the file."""
    if len(raw) == 0:
        return raw
    order = pd.Series(raw).rank(method="average", pct=True).to_numpy()
    return np.clip(order, 0.0, 1.0)


def _load_bundle(model_path: Optional[Path]) -> Optional[dict[str, Any]]:
    if not model_path or not Path(model_path).is_file():
        return None
    import joblib

    bundle = joblib.load(model_path)
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle
    return {"model": bundle}


def _score_tabular(
    df: pd.DataFrame,
    default_features: list[str],
    model_path: Optional[Path],
    contamination: float,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Return (score in [0,1], prediction 0/1, scoring method) for each row."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    bundle = _load_bundle(model_path)
    if bundle:
        features = list(bundle.get("features") or default_features)
        x = df.reindex(columns=features).fillna(0).astype(float)
        model = bundle["model"]
        if "scaler" in bundle:  # Isolation Forest baseline bundle
            xs = bundle["scaler"].transform(x)
            raw = -model.score_samples(xs)
            prediction = (model.predict(xs) == -1).astype(int)
            return _rank_scores(raw), prediction, f"isolation_forest:{Path(model_path).name}"
        if hasattr(model, "predict_proba"):  # supervised (e.g. CERT Random Forest)
            proba = model.predict_proba(x)[:, 1]
            threshold = float(bundle.get("threshold", 0.5))
            return proba, (proba >= threshold).astype(int), f"supervised:{Path(model_path).name}"

    features = [c for c in default_features if c in df.columns]
    if not features:
        raise ValueError(f"None of the expected feature columns are present: {default_features}")
    x = df[features].fillna(0).astype(float)
    if len(x) < 8:
        # Too few rows to fit a meaningful model: z-score heuristic.
        z = ((x - x.mean()) / (x.std(ddof=0) + 1e-6)).abs().max(axis=1).to_numpy()
        score = np.clip(z / 3.0, 0.0, 1.0)
        return score, (score >= 0.75).astype(int), "zscore_heuristic"
    xs = StandardScaler().fit_transform(x)
    model = IsolationForest(n_estimators=150, contamination=contamination, random_state=42)
    model.fit(xs)
    raw = -model.score_samples(xs)
    prediction = (model.predict(xs) == -1).astype(int)
    return _rank_scores(raw), prediction, "isolation_forest:fitted_on_evidence"


# ---------------------------------------------------------------------------
# Cyber logs (user-day / user-hour feature CSV)
# ---------------------------------------------------------------------------

def process_cyber_csv(
    path: Path,
    source_id: str,
    case_id: Optional[str] = None,
    model_path: Optional[Path] = None,
    contamination: float = 0.03,
) -> list[dict[str, Any]]:
    """Score a cyber activity CSV and emit one event per flagged row."""
    df = pd.read_csv(path)
    if "timestamp" not in df.columns or "user_id" not in df.columns:
        raise ValueError("Cyber CSV requires 'timestamp' and 'user_id' columns")
    score, prediction, method = _score_tabular(df, CYBER_FEATURES, model_path, contamination)
    df = df.assign(anomaly_score=score, prediction=prediction)
    return events_from_scored_cyber(df, source_id=source_id, case_id=case_id, method=method)


def events_from_scored_cyber(
    data: Path | pd.DataFrame,
    source_id: str,
    case_id: Optional[str] = None,
    method: str = "precomputed",
) -> list[dict[str, Any]]:
    df = pd.read_csv(data) if isinstance(data, Path) else data
    if "prediction" not in df.columns:
        return []
    score_col = "anomaly_score" if "anomaly_score" in df.columns else ("risk_score" if "risk_score" in df.columns else None)
    events = []
    flagged = df[df["prediction"] == 1]
    for _, row in flagged.iterrows():
        raw_score = float(row[score_col]) if score_col else 0.8
        score = raw_score if 0.0 <= raw_score <= 1.0 else float(np.clip(raw_score, 0, 1))
        details = {c: _clean(row[c]) for c in CYBER_FEATURES if c in row.index}
        events.append({
            "event_id": _event_id("CYBER", source_id, len(events) + 1),
            "case_id": case_id,
            "timestamp": str(row["timestamp"]),
            "source": "cyber",
            "source_type": "endpoint_log",
            "source_id": source_id,
            "actor_id": str(row.get("user_id", "unknown")),
            "action": "anomalous_activity",
            "kind": "cyber_anomaly",
            "location_id": _clean(row.get("location_id")) if "location_id" in row.index else None,
            "object_id": _clean(row.get("host")) if "host" in row.index else None,
            "score": round(score, 4),
            "confidence": round(score, 4),
            "prediction": 1,
            "details": details,
            "metadata": {"scoring_method": method},
        })
    return events


# ---------------------------------------------------------------------------
# Physical access (badge) logs
# ---------------------------------------------------------------------------

def process_badge_csv(path: Path, source_id: str, case_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Every badge swipe becomes an event (badges are facts, not predictions)."""
    df = pd.read_csv(path)
    actor_col = next((c for c in ("user_id", "badge_id", "actor_id") if c in df.columns), None)
    loc_col = next((c for c in ("location_id", "door_id", "zone") if c in df.columns), None)
    if "timestamp" not in df.columns or not actor_col or not loc_col:
        raise ValueError("Badge CSV requires 'timestamp', 'user_id'/'badge_id' and 'location_id'/'door_id'")
    events = []
    for _, row in df.iterrows():
        result = str(row.get("result", "granted")).strip().lower()
        denied = result in {"denied", "rejected", "failed", "0", "false"}
        events.append({
            "event_id": _event_id("BADGE", source_id, len(events) + 1),
            "case_id": case_id,
            "timestamp": str(row["timestamp"]),
            "source": "physical",
            "source_type": "badge_log",
            "source_id": source_id,
            "actor_id": str(row[actor_col]),
            "action": "badge_denied" if denied else "badge_swipe",
            "kind": "badge_denied" if denied else "badge_access",
            "location_id": str(row[loc_col]),
            "object_id": _clean(row.get("door_id")) if "door_id" in row.index else None,
            "score": 0.6 if denied else 0.1,
            "confidence": 1.0,
            "prediction": 1 if denied else 0,
            "metadata": {"result": result},
        })
    return events


# ---------------------------------------------------------------------------
# Video motion features (CSV produced by ai/video/extract_features.py)
# ---------------------------------------------------------------------------

def process_video_features_csv(
    path: Path,
    source_id: str,
    case_id: Optional[str] = None,
    model_path: Optional[Path] = None,
    contamination: float = 0.05,
) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError("Video feature CSV requires an ISO 'timestamp' column")
    score, prediction, method = _score_tabular(df, VIDEO_FEATURES, model_path, contamination)
    df = df.assign(anomaly_score=score, prediction=prediction)
    return events_from_scored_video_features(df, source_id=source_id, case_id=case_id, method=method)


def events_from_scored_video_features(
    data: Path | pd.DataFrame,
    source_id: str,
    case_id: Optional[str] = None,
    method: str = "precomputed",
) -> list[dict[str, Any]]:
    df = pd.read_csv(data) if isinstance(data, Path) else data
    if "prediction" not in df.columns:
        return []
    events = []
    for _, row in df[df["prediction"] == 1].iterrows():
        raw = float(row.get("anomaly_score", 0.75))
        score = float(np.clip(raw, 0, 1))
        location = row.get("location_id") if "location_id" in row.index else None
        camera = row.get("camera_id") if "camera_id" in row.index else None
        events.append({
            "event_id": _event_id("VIDMOT", source_id, len(events) + 1),
            "case_id": case_id,
            "timestamp": str(row["timestamp"]),
            "source": "video",
            "source_type": "cctv_video",
            "source_id": source_id,
            "actor_id": "unknown",
            "action": "motion_anomaly",
            "kind": "video_motion_anomaly",
            "location_id": _clean(location) or _clean(camera) or "ZONE-CCTV",
            "object_id": _clean(camera),
            "score": round(score, 4),
            "confidence": round(score, 4),
            "prediction": 1,
            "details": {c: _clean(row[c]) for c in VIDEO_FEATURES if c in row.index},
            "metadata": {"scoring_method": method},
        })
    return events


# ---------------------------------------------------------------------------
# Documents (JSONL rows or a single plain-text file)
# ---------------------------------------------------------------------------

def extract_entities(text: str) -> dict[str, list[str]]:
    return {
        "users": sorted({m.lower().replace("-", "_") for m in USER_PATTERN.findall(text)}),
        "emails": sorted(set(EMAIL_PATTERN.findall(text))),
        "times": sorted(set(ISO_PATTERN.findall(text))),
        "locations": sorted(set(ZONE_PATTERN.findall(text))),
        "keywords": sorted({term for term in SUSPICIOUS_TERMS if term in text.lower()}),
    }


def _dedupe_actors(raw_actors: Iterable[str]) -> list[str]:
    """Collapse aliases of the same person (e.g. 'badge_007' and 'user_007')."""
    from ai.correlation.entity_resolution.resolver import EntityResolver

    resolver = EntityResolver()
    seen: dict[str, str] = {}
    for actor in raw_actors:
        canonical, _ = resolver.resolve(actor)
        seen.setdefault(canonical, actor)
    return [c for c in seen if c != "unknown"]


def keyword_score(text: str) -> float:
    lowered = text.lower()
    return float(min(0.95, 0.1 + sum(w for term, w in SUSPICIOUS_TERMS.items() if term in lowered)))


def _read_documents(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else [payload]
    if path.suffix.lower() in {".txt", ".md", ".eml", ".log"}:
        return [{"document_id": path.stem, "text": path.read_text(encoding="utf-8", errors="replace")}]
    raise ValueError(f"Unsupported document format '{path.suffix}' (PDF/OCR is not implemented yet)")


def process_documents(
    path: Path,
    source_id: str,
    case_id: Optional[str] = None,
    model_path: Optional[Path] = None,
    default_timestamp: Optional[str] = None,
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Score documents; flagged documents yield one event per mentioned person.

    The document timestamp comes from (in order): the row's ``timestamp`` field,
    the first ISO timestamp in the text, or ``default_timestamp`` (evidence
    metadata ``recorded_at``). If none is available the event is still emitted
    with ``timestamp=None`` and the timeline reports it as skipped — Sentinel
    never invents a time.
    """
    rows = _read_documents(path)
    texts = [str(r.get("text", "")) for r in rows]
    bundle = _load_bundle(model_path)
    if bundle and hasattr(bundle["model"], "predict_proba"):
        scores = bundle["model"].predict_proba(texts)[:, 1]
        method = f"tfidf_classifier:{Path(model_path).name}"
    else:
        scores = np.array([keyword_score(t) for t in texts])
        method = "keyword_heuristic"

    events = []
    for row, text, score in zip(rows, texts, scores):
        if score < threshold:
            continue
        ents = extract_entities(text)
        timestamp = row.get("timestamp") or (ents["times"][0] if ents["times"] else None) or default_timestamp
        actors: Iterable[str] = _dedupe_actors(ents["users"] or [e.split("@")[0] for e in ents["emails"]]) or ["unknown"]
        for actor in actors:
            events.append({
                "event_id": _event_id("DOC", source_id, len(events) + 1),
                "case_id": case_id,
                "timestamp": timestamp,
                "source": "document",
                "source_type": "text_document",
                "source_id": source_id,
                "actor_id": actor,
                "action": "document_claim",
                "kind": "document_claim",
                "location_id": ents["locations"][0] if ents["locations"] else None,
                "document_id": str(row.get("document_id", path.stem)),
                "score": round(float(score), 4),
                "confidence": round(float(score), 4),
                "prediction": 1,
                "text": text[:1000],
                "details": {"entities": ents},
                "metadata": {"scoring_method": method},
            })
    return events


def events_from_scored_documents(path: Path, source_id: str, case_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Convert ``artifacts/documents/document_predictions.jsonl`` into events."""
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("prediction"):
            continue
        ents = row.get("entities") or extract_entities(row.get("text", ""))
        for actor in _dedupe_actors(ents.get("users") or []) or ["unknown"]:
            events.append({
                "event_id": _event_id("DOC", source_id, len(events) + 1),
                "case_id": case_id,
                "timestamp": row.get("timestamp"),
                "source": "document",
                "source_type": "text_document",
                "source_id": source_id,
                "actor_id": actor,
                "action": "document_claim",
                "kind": "document_claim",
                "location_id": (ents.get("locations") or [None])[0],
                "document_id": row.get("document_id"),
                "score": float(row.get("suspicious_score", 0.7)),
                "confidence": float(row.get("suspicious_score", 0.7)),
                "prediction": 1,
                "text": str(row.get("text", ""))[:1000],
            })
    return events


# ---------------------------------------------------------------------------
# Canonical events JSONL (e.g. artifacts/video/crime_events.jsonl)
# ---------------------------------------------------------------------------

def process_canonical_jsonl(path: Path, source_id: str, case_id: Optional[str] = None) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        evt = json.loads(line)
        source_type = evt.get("source_type", "unknown")
        is_video = source_type == "cctv_video"
        confidence = float(evt.get("confidence", 0.0))
        crime_prob = (evt.get("metadata") or {}).get("crime_probability")
        events.append({
            **evt,
            "event_id": evt.get("event_id") or _event_id("EXT", source_id, len(events) + 1),
            "case_id": case_id or evt.get("case_id"),
            "timestamp": evt.get("timestamp") or evt.get("timestamp_start"),
            "timestamp_end": evt.get("timestamp_end"),
            "source": evt.get("source") or ("video" if is_video else source_type),
            "source_id": evt.get("source_id") or source_id,
            "kind": evt.get("kind") or ("video_crime" if evt.get("action") == "crime_detected" else evt.get("action")),
            "score": float(crime_prob) if crime_prob is not None else confidence,
        })
    return events
