"""Multimodal Correlation Orchestrator.

Combines Entity Resolution, Incident Timeline Construction, Multi-Source
Contradiction Detection, and Evidence Graph Generation into a unified
investigation pipeline.

Two entry points:

* ``load_events_from_artifacts`` + ``run_correlation`` — CLI / batch mode used by
  ``ai/correlation/run.py`` on the global ``artifacts/`` outputs.
* ``run_correlation`` alone — used by the backend analysis service with
  canonical events produced per case by ``ai.processing``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ai.correlation.entity_resolution.resolver import EntityResolver
from ai.correlation.evidence_graph.builder import EvidenceGraphBuilder
from ai.correlation.timeline.builder import IncidentTimelineBuilder, _score

OUTPUT_FILES = {
    "events": "events.jsonl",
    "timeline": "timeline.json",
    "graph": "evidence_graph.json",
    "cytoscape": "cytoscape_graph.json",
    "contradictions": "contradictions.json",
    "suspects": "suspect_ranking.json",
    "summary": "summary.json",
}


class MultimodalCorrelator:
    """Master correlation engine for multimodal insider threat investigation."""

    def __init__(self, window_minutes: int = 60) -> None:
        self.window_minutes = window_minutes
        self.resolver = EntityResolver()
        self.timeline_builder = IncidentTimelineBuilder(window_minutes=window_minutes)
        self.graph_builder = EvidenceGraphBuilder()

    def load_events_from_artifacts(
        self,
        cyber_csv: Optional[Path | str] = "artifacts/cyber/cyber_predictions.csv",
        video_csv: Optional[Path | str] = "artifacts/video/video_predictions.csv",
        crime_jsonl: Optional[Path | str] = "artifacts/video/crime_events.jsonl",
        document_jsonl: Optional[Path | str] = "artifacts/documents/document_predictions.jsonl",
        badge_csv: Optional[Path | str] = None,
    ) -> list[dict[str, Any]]:
        """Load model prediction files from ``artifacts/`` as canonical events."""
        from ai.processing import processors

        events: list[dict[str, Any]] = []
        if cyber_csv and Path(cyber_csv).exists():
            events += processors.events_from_scored_cyber(Path(cyber_csv), source_id="artifacts-cyber")
        if video_csv and Path(video_csv).exists():
            events += processors.events_from_scored_video_features(Path(video_csv), source_id="artifacts-video")
        if crime_jsonl and Path(crime_jsonl).exists():
            events += processors.process_canonical_jsonl(Path(crime_jsonl), source_id="artifacts-crime")
        if document_jsonl and Path(document_jsonl).exists():
            events += processors.events_from_scored_documents(Path(document_jsonl), source_id="artifacts-documents")
        if badge_csv and Path(badge_csv).exists():
            events += processors.process_badge_csv(Path(badge_csv), source_id="artifacts-badge")
        return events

    @staticmethod
    def _rank_suspects(events: list[dict[str, Any]], contradictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aggregate per-entity risk with explicit evidence references (explainability)."""
        entity_risk: dict[str, dict[str, Any]] = {}
        for ev in events:
            entity = ev.get("canonical_entity", "unknown")
            if entity == "unknown":
                continue
            flagged = ev.get("prediction") == 1 or (
                ev.get("prediction") is None and _score(ev) >= 0.5
            )
            if not flagged:
                continue  # context-only events (e.g. granted badge swipes) don't add risk
            r = entity_risk.setdefault(entity, {
                "entity": entity, "event_count": 0, "sources": set(), "max_score": 0.0,
                "total_score": 0.0, "event_ids": [], "evidence_ids": set(),
            })
            score = _score(ev)
            r["event_count"] += 1
            r["sources"].add(ev.get("source", "unknown"))
            r["max_score"] = max(r["max_score"], score)
            r["total_score"] += score
            r["event_ids"].append(ev.get("event_id"))
            if ev.get("source_id"):
                r["evidence_ids"].add(ev["source_id"])

        severity_weight = {"critical": 1.0, "high": 0.75, "medium": 0.4, "low": 0.2}
        ranking = []
        for r in entity_risk.values():
            related = [c for c in contradictions if c.get("entity") == r["entity"]]
            contradiction_bonus = sum(severity_weight.get(c.get("severity", "low"), 0.2) for c in related)
            aggregate = r["total_score"] * (1.0 + 0.25 * len(r["sources"])) + contradiction_bonus
            reasons = [f"{r['event_count']} flagged event(s) across {len(r['sources'])} source(s): "
                       f"{', '.join(sorted(r['sources']))}"]
            reasons += [f"{c['type']} ({c['severity']}): {c['description']}" for c in related]
            ranking.append({
                "entity": r["entity"],
                "event_count": r["event_count"],
                "distinct_sources": len(r["sources"]),
                "sources": sorted(r["sources"]),
                "max_score": round(r["max_score"], 3),
                "contradiction_count": len(related),
                "aggregate_risk_score": round(aggregate, 3),
                "event_ids": r["event_ids"],
                "evidence_ids": sorted(r["evidence_ids"]),
                "anomaly_ids": [c["anomaly_id"] for c in related if c.get("anomaly_id")],
                "reasons": reasons,
            })
        ranking.sort(key=lambda x: x["aggregate_risk_score"], reverse=True)
        for rank, item in enumerate(ranking, 1):
            item["rank"] = rank
        return ranking

    def run_correlation(
        self,
        events: list[dict[str, Any]],
        output_dir: Optional[Path | str] = "artifacts/correlation",
        case_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute the full correlation pipeline on events and write outputs."""
        if not events:
            raise RuntimeError("No input events provided for correlation.")

        resolved_events = [self.resolver.resolve_event(e) for e in events]
        timeline_result = self.timeline_builder.build_timeline(resolved_events)

        self.graph_builder = EvidenceGraphBuilder()
        self.graph_builder.build_from_events(
            events=timeline_result["events"],
            contradictions=timeline_result["contradictions"],
        )
        graph_dict = self.graph_builder.to_dict()
        cytoscape_dict = self.graph_builder.to_cytoscape()

        suspect_ranking = self._rank_suspects(timeline_result["events"], timeline_result["contradictions"])

        summary = {
            "case_id": case_id,
            "total_events": len(timeline_result["events"]),
            "skipped_events": len(timeline_result["skipped_events"]),
            "incident_clusters": len(timeline_result["clusters"]),
            "cross_modal_clusters": sum(1 for c in timeline_result["clusters"] if c["is_cross_modal"]),
            "contradictions_detected": len(timeline_result["contradictions"]),
            "graph_nodes": len(graph_dict["nodes"]),
            "graph_edges": len(graph_dict["edges"]),
            "ranked_suspects": len(suspect_ranking),
            "top_suspect": suspect_ranking[0]["entity"] if suspect_ranking else None,
            "sources_represented": timeline_result["summary"]["sources_represented"],
        }
        timeline_result["summary"].update({"case_id": case_id})

        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)

            def dump(name: str, payload: Any) -> None:
                (out_path / OUTPUT_FILES[name]).write_text(
                    json.dumps(payload, indent=2, default=str), encoding="utf-8"
                )

            # True JSON Lines: one incident cluster per line.
            with (out_path / OUTPUT_FILES["events"]).open("w", encoding="utf-8") as handle:
                for cluster in timeline_result["clusters"]:
                    handle.write(json.dumps(cluster, default=str) + "\n")
            dump("timeline", timeline_result)
            dump("graph", graph_dict)
            dump("cytoscape", cytoscape_dict)
            dump("contradictions", timeline_result["contradictions"])
            dump("suspects", suspect_ranking)
            dump("summary", summary)

        return {
            "summary": summary,
            "suspect_ranking": suspect_ranking,
            "contradictions": timeline_result["contradictions"],
            "clusters": timeline_result["clusters"],
            "skipped_events": timeline_result["skipped_events"],
        }
