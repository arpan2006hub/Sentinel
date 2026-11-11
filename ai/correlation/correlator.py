"""Multimodal Correlation Orchestrator.

Combines Entity Resolution, Incident Timeline Construction, Multi-Source Contradiction
Detection, and Evidence Graph Generation into a unified investigation pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ai.correlation.entity_resolution.resolver import EntityResolver
from ai.correlation.evidence_graph.builder import EvidenceGraphBuilder
from ai.correlation.timeline.builder import IncidentTimelineBuilder


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
    ) -> list[dict[str, Any]]:
        """Load and normalize model predictions and canonical events across all modalities."""
        events: list[dict[str, Any]] = []

        # 1. Cyber log anomalies
        if cyber_csv and Path(cyber_csv).exists():
            df_cyber = pd.read_csv(cyber_csv)
            if "prediction" in df_cyber.columns:
                anomalies = df_cyber[df_cyber["prediction"] == 1]
                for _, row in anomalies.iterrows():
                    events.append({
                        "event_id": f"EVT-CYBER-{len(events) + 1:04d}",
                        "timestamp": row["timestamp"],
                        "source": "cyber",
                        "source_type": "endpoint_log",
                        "actor_id": str(row.get("user_id", "unknown")),
                        "kind": "cyber_anomaly",
                        "score": float(row.get("anomaly_score", 0.8)),
                        "details": {
                            "login_count": row.get("login_count", 0),
                            "file_reads": row.get("file_reads", 0),
                            "usb_events": row.get("usb_events", 0),
                        },
                    })

        # 2. Video motion / tabular anomalies
        if video_csv and Path(video_csv).exists():
            df_video = pd.read_csv(video_csv)
            if "prediction" in df_video.columns:
                anomalies = df_video[df_video["prediction"] == 1]
                for _, row in anomalies.iterrows():
                    events.append({
                        "event_id": f"EVT-VIDEO-MOT-{len(events) + 1:04d}",
                        "timestamp": row["timestamp"],
                        "source": "video",
                        "source_type": "cctv_video",
                        "actor_id": "unknown",
                        "location_id": row.get("camera_id", "ZONE-CCTV"),
                        "kind": "video_motion_anomaly",
                        "score": float(row.get("anomaly_score", 0.75)),
                    })

        # 3. Video TimeSformer crime events
        if crime_jsonl and Path(crime_jsonl).exists():
            for line in Path(crime_jsonl).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        evt = json.loads(line)
                        events.append({
                            "event_id": evt.get("event_id") or f"EVT-CRIME-{len(events) + 1:04d}",
                            "timestamp": evt.get("timestamp_start"),
                            "source": "video",
                            "source_type": "cctv_video",
                            "actor_id": evt.get("actor_id", "unknown"),
                            "location_id": evt.get("location_id", "ZONE-SURVEILLANCE"),
                            "action": evt.get("action", "crime_detected"),
                            "kind": "video_crime",
                            "score": float(evt.get("confidence", 0.88)),
                            "metadata": evt.get("metadata", {}),
                        })
                    except Exception:
                        pass

        # 4. Document claims & entity reports
        if document_jsonl and Path(document_jsonl).exists():
            for line in Path(document_jsonl).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        row = json.loads(line)
                        if row.get("prediction"):
                            users = row.get("entities", {}).get("users") or ["unknown"]
                            for user in users:
                                events.append({
                                    "event_id": f"EVT-DOC-{len(events) + 1:04d}",
                                    "timestamp": row.get("timestamp", "2026-01-15T12:00:00+00:00"),
                                    "source": "document",
                                    "source_type": "pdf_document",
                                    "actor_id": user,
                                    "kind": "document_claim",
                                    "score": float(row.get("suspicious_score", 0.7)),
                                    "document_id": row.get("document_id", "DOC-001"),
                                    "text": row.get("text", ""),
                                })
                    except Exception:
                        pass

        return events

    def run_correlation(
        self,
        events: list[dict[str, Any]],
        output_dir: Optional[Path | str] = "artifacts/correlation",
    ) -> dict[str, Any]:
        """Execute full correlation pipeline on events and write outputs."""
        if not events:
            raise RuntimeError("No input events provided for correlation.")

        # Step 1: Entity Resolution
        resolved_events = [self.resolver.resolve_event(e) for e in events]

        # Step 2: Timeline Construction & Contradiction Detection
        timeline_result = self.timeline_builder.build_timeline(resolved_events)

        # Step 3: Evidence Graph Construction
        self.graph_builder.build_from_events(
            events=timeline_result["events"],
            contradictions=timeline_result["contradictions"],
        )
        graph_dict = self.graph_builder.to_dict()
        cytoscape_dict = self.graph_builder.to_cytoscape()

        # Step 4: Suspect / Entity Risk Aggregation
        entity_risk: dict[str, dict[str, Any]] = {}
        for ev in timeline_result["events"]:
            entity = ev.get("canonical_entity", "unknown")
            if entity == "unknown":
                continue
            r = entity_risk.setdefault(entity, {"entity": entity, "event_count": 0, "sources": set(), "max_score": 0.0, "total_score": 0.0})
            r["event_count"] += 1
            r["sources"].add(ev.get("source", "unknown"))
            score = float(ev.get("score") or ev.get("confidence") or 0.0)
            r["max_score"] = max(r["max_score"], score)
            r["total_score"] += score

        suspect_ranking = [
            {
                "entity": r["entity"],
                "event_count": r["event_count"],
                "distinct_sources": len(r["sources"]),
                "sources": sorted(list(r["sources"])),
                "max_score": round(r["max_score"], 3),
                "aggregate_risk_score": round(r["total_score"] * (1.0 + 0.25 * len(r["sources"])), 3),
            }
            for r in entity_risk.values()
        ]
        suspect_ranking.sort(key=lambda x: x["aggregate_risk_score"], reverse=True)

        # Save artifacts
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)

            # 1. events.jsonl (Format expected by scripts and evaluation)
            events_jsonl_path = out_path / "events.jsonl"
            events_jsonl_path.write_text(
                json.dumps(timeline_result["clusters"], indent=2, default=str),
                encoding="utf-8",
            )

            # 2. timeline.json
            (out_path / "timeline.json").write_text(
                json.dumps(timeline_result, indent=2, default=str),
                encoding="utf-8",
            )

            # 3. evidence_graph.json
            (out_path / "evidence_graph.json").write_text(
                json.dumps(graph_dict, indent=2, default=str),
                encoding="utf-8",
            )

            # 4. cytoscape_graph.json
            (out_path / "cytoscape_graph.json").write_text(
                json.dumps(cytoscape_dict, indent=2, default=str),
                encoding="utf-8",
            )

            # 5. contradictions.json
            (out_path / "contradictions.json").write_text(
                json.dumps(timeline_result["contradictions"], indent=2, default=str),
                encoding="utf-8",
            )

            # 6. suspect_ranking.json
            (out_path / "suspect_ranking.json").write_text(
                json.dumps(suspect_ranking, indent=2, default=str),
                encoding="utf-8",
            )

        return {
            "summary": {
                "total_events": len(resolved_events),
                "incident_clusters": len(timeline_result["clusters"]),
                "contradictions_detected": len(timeline_result["contradictions"]),
                "graph_nodes": len(graph_dict["nodes"]),
                "graph_edges": len(graph_dict["edges"]),
                "ranked_suspects": len(suspect_ranking),
            },
            "suspect_ranking": suspect_ranking,
            "contradictions": timeline_result["contradictions"],
            "clusters": timeline_result["clusters"],
        }

