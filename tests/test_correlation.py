"""Comprehensive Tests for the Multimodal Correlation Engine."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from ai.correlation.correlator import MultimodalCorrelator
from ai.correlation.entity_resolution.resolver import EntityResolver
from ai.correlation.evidence_graph.builder import EvidenceGraphBuilder
from ai.correlation.timeline.builder import IncidentTimelineBuilder


class TestEntityResolver:
    """Test suite for cross-modal entity resolution."""

    def test_direct_and_alias_lookup(self) -> None:
        resolver = EntityResolver()
        resolver.register_entity(
            canonical_id="user_007",
            aliases=["jbond", "james.bond@mi6.gov.uk", "BADGE-007"],
            entity_type="user",
        )

        canonical, conf = resolver.resolve("jbond")
        assert canonical == "user_007"
        assert conf == 1.0

        canonical, conf = resolver.resolve("BADGE-007")
        assert canonical == "user_007"
        assert conf == 1.0

    def test_domain_and_email_normalization(self) -> None:
        resolver = EntityResolver()
        resolver.register_entity("alice", aliases=["alice.smith"])

        canonical, conf = resolver.resolve(r"ENTERPRISE\alice.smith")
        assert canonical == "alice"
        assert conf >= 0.9

        canonical, conf = resolver.resolve("alice.smith@corp.com")
        assert canonical == "alice"
        assert conf >= 0.9

    def test_pattern_normalization(self) -> None:
        resolver = EntityResolver()
        canonical, conf = resolver.resolve("USER_003")
        assert canonical == "user_003"
        assert conf >= 0.85

        canonical, conf = resolver.resolve("badge-042")
        assert canonical == "user_042"
        assert conf >= 0.85

        canonical, conf = resolver.resolve("ws-user-099")
        assert canonical == "user_099"
        assert conf >= 0.80

    def test_event_enrichment(self) -> None:
        resolver = EntityResolver()
        event = {"event_id": "EVT-1", "actor_id": "CORP\\user_012", "action": "login"}
        enriched = resolver.resolve_event(event)
        assert enriched["canonical_entity"] == "user_012"
        assert enriched["entity_resolution_confidence"] >= 0.9


class TestIncidentTimelineBuilder:
    """Test suite for timeline building and contradiction detection."""

    def test_chronological_ordering(self) -> None:
        builder = IncidentTimelineBuilder(window_minutes=60)
        events = [
            {"event_id": "EVT-3", "timestamp": "2026-01-15T10:30:00Z", "actor_id": "user_001"},
            {"event_id": "EVT-1", "timestamp": "2026-01-15T09:00:00Z", "actor_id": "user_001"},
            {"event_id": "EVT-2", "timestamp": "2026-01-15T10:00:00Z", "actor_id": "user_001"},
        ]
        timeline = builder.build_timeline(events)
        ids = [e["event_id"] for e in timeline["events"]]
        assert ids == ["EVT-1", "EVT-2", "EVT-3"]
        assert len(timeline["clusters"]) >= 1

    def test_impossible_travel_contradiction(self) -> None:
        builder = IncidentTimelineBuilder(window_minutes=60)
        events = [
            {
                "event_id": "EVT-LOC-A",
                "timestamp": "2026-01-15T10:00:00Z",
                "canonical_entity": "user_002",
                "location_id": "ZONE-NEW-YORK-HQ",
            },
            {
                "event_id": "EVT-LOC-B",
                "timestamp": "2026-01-15T10:01:00Z",  # 1 min later
                "canonical_entity": "user_002",
                "location_id": "ZONE-LONDON-BRANCH",
            },
        ]
        timeline = builder.build_timeline(events)
        contradictions = timeline["contradictions"]
        assert len(contradictions) >= 1
        assert any(c["type"] == "impossible_travel" for c in contradictions)
        assert any("user_002" in c["description"] for c in contradictions)

    def test_uncredentialed_presence_contradiction(self) -> None:
        builder = IncidentTimelineBuilder(window_minutes=60)
        events = [
            {
                "event_id": "EVT-CRIME-99",
                "timestamp": "2026-01-15T14:00:00Z",
                "source": "video",
                "source_type": "cctv_video",
                "action": "crime_detected",
                "location_id": "ZONE-RESTRICTED-VAULT",
                "confidence": 0.92,
            },
            {
                "event_id": "EVT-BADGE-1",
                "timestamp": "2026-01-15T18:00:00Z",  # 4 hours later, outside window
                "source_type": "badge_log",
                "action": "badge_swipe",
                "location_id": "ZONE-LOBBY",
            },
        ]
        timeline = builder.build_timeline(events)
        contradictions = timeline["contradictions"]
        assert any(c["type"] == "uncredentialed_presence" for c in contradictions)


class TestEvidenceGraphBuilder:
    """Test suite for evidence graph construction and Cytoscape export."""

    def test_graph_construction(self) -> None:
        graph = EvidenceGraphBuilder()
        events = [
            {
                "event_id": "EVT-01",
                "canonical_entity": "user_001",
                "source": "cyber",
                "kind": "data_exfiltration",
                "location_id": "ZONE-HQ",
                "document_id": "DOC-SECRET-01",
                "score": 0.95,
            }
        ]
        graph.build_from_events(events)
        data = graph.to_dict()

        # Nodes: Event, User, Location, Document
        node_ids = {n["id"] for n in data["nodes"]}
        assert "EVT-01" in node_ids
        assert "user_001" in node_ids
        assert "ZONE-HQ" in node_ids
        assert "DOC-SECRET-01" in node_ids

        # Cytoscape export
        cyto = graph.to_cytoscape()
        assert "elements" in cyto
        assert len(cyto["elements"]["nodes"]) >= 4
        assert len(cyto["elements"]["edges"]) >= 3


class TestMultimodalCorrelator:
    """End-to-end integration test for the MultimodalCorrelator engine."""

    def test_full_correlation_pipeline(self, tmp_path) -> None:
        correlator = MultimodalCorrelator(window_minutes=60)
        sample_events = [
            {
                "event_id": "EVT-C1",
                "timestamp": "2026-01-15T09:00:00Z",
                "source": "cyber",
                "actor_id": "CORP\\user_005",
                "kind": "mass_download",
                "score": 0.88,
            },
            {
                "event_id": "EVT-V1",
                "timestamp": "2026-01-15T09:15:00Z",
                "source": "video",
                "actor_id": "actor_user_005",
                "location_id": "ZONE-SERVER-ROOM",
                "kind": "crime_detected",
                "score": 0.92,
            },
            {
                "event_id": "EVT-D1",
                "timestamp": "2026-01-15T09:30:00Z",
                "source": "document",
                "actor_id": "user_005",
                "document_id": "DOC-INCIDENT-LOG",
                "kind": "claim",
                "score": 0.70,
            },
        ]

        result = correlator.run_correlation(events=sample_events, output_dir=tmp_path)
        assert result["summary"]["total_events"] == 3
        assert result["summary"]["incident_clusters"] >= 1
        assert len(result["suspect_ranking"]) >= 1

        top_suspect = result["suspect_ranking"][0]
        assert top_suspect["entity"] == "user_005"
        assert top_suspect["distinct_sources"] == 3  # cyber, video, document

        # Verify artifacts were generated
        assert (tmp_path / "events.jsonl").exists()
        assert (tmp_path / "timeline.json").exists()
        assert (tmp_path / "evidence_graph.json").exists()
        assert (tmp_path / "cytoscape_graph.json").exists()
        assert (tmp_path / "suspect_ranking.json").exists()



class TestCorrelationRegressions:
    """Regression tests for bugs fixed during the demo-readiness pass."""

    def test_unparseable_timestamp_is_skipped_not_replaced_with_now(self) -> None:
        builder = IncidentTimelineBuilder()
        timeline = builder.build_timeline([
            {"event_id": "EVT-OK", "timestamp": "2026-01-15T10:00:00Z", "actor_id": "user_001"},
            {"event_id": "EVT-BAD", "timestamp": "yesterday-ish", "actor_id": "user_001"},
            {"event_id": "EVT-NONE", "actor_id": "user_001"},
        ])
        assert [e["event_id"] for e in timeline["events"]] == ["EVT-OK"]
        assert {s["event_id"] for s in timeline["skipped_events"]} == {"EVT-BAD", "EVT-NONE"}

    def test_badge_at_other_location_does_not_authorise_presence(self) -> None:
        builder = IncidentTimelineBuilder()
        timeline = builder.build_timeline([
            {"event_id": "EVT-V", "timestamp": "2026-01-15T14:00:00Z", "source": "video",
             "source_type": "cctv_video", "action": "crime_detected", "location_id": "ZONE-RESTRICTED-VAULT"},
            {"event_id": "EVT-B", "timestamp": "2026-01-15T14:05:00Z", "source_type": "badge_log",
             "action": "badge_swipe", "location_id": "ZONE-LOBBY"},
        ])
        assert any(c["type"] == "uncredentialed_presence" for c in timeline["contradictions"])

    def test_badge_at_same_location_authorises_presence(self) -> None:
        builder = IncidentTimelineBuilder()
        timeline = builder.build_timeline([
            {"event_id": "EVT-V", "timestamp": "2026-01-15T14:00:00Z", "source": "video",
             "source_type": "cctv_video", "action": "crime_detected", "location_id": "ZONE-RESTRICTED-VAULT"},
            {"event_id": "EVT-B", "timestamp": "2026-01-15T13:55:00Z", "source_type": "badge_log",
             "action": "badge_swipe", "location_id": "ZONE-RESTRICTED-VAULT"},
        ])
        assert not any(c["type"] == "uncredentialed_presence" for c in timeline["contradictions"])

    def test_low_score_unrestricted_video_is_not_uncredentialed(self) -> None:
        builder = IncidentTimelineBuilder()
        timeline = builder.build_timeline([
            {"event_id": "EVT-V", "timestamp": "2026-01-15T14:00:00Z", "source": "video",
             "kind": "video_motion_anomaly", "location_id": "ZONE-LOBBY", "score": 0.95},
            {"event_id": "EVT-B", "timestamp": "2026-01-15T09:00:00Z", "source_type": "badge_log",
             "action": "badge_swipe", "location_id": "ZONE-LOBBY"},
        ])
        assert not any(c["type"] == "uncredentialed_presence" for c in timeline["contradictions"])

    def test_events_jsonl_is_real_json_lines(self, tmp_path) -> None:
        import json

        correlator = MultimodalCorrelator()
        correlator.run_correlation([
            {"event_id": "EVT-1", "timestamp": "2026-01-15T09:00:00Z", "source": "cyber", "actor_id": "user_001", "score": 0.9},
            {"event_id": "EVT-2", "timestamp": "2026-01-16T09:00:00Z", "source": "cyber", "actor_id": "user_002", "score": 0.9},
        ], output_dir=tmp_path)
        lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2 and all(json.loads(line)["cluster_id"] for line in lines)
        contradictions = json.loads((tmp_path / "contradictions.json").read_text(encoding="utf-8"))
        assert all("anomaly_id" in c for c in contradictions)


def test_video_without_location_is_not_uncredentialed_presence():
    events = [
        {"event_id": "EVT-B1", "timestamp": "2026-01-16T21:00:00Z", "actor_id": "user_001",
         "action": "badge_swipe", "location_id": "ZONE-A", "source": "physical", "source_type": "badge_log"},
        {"event_id": "EVT-V1", "timestamp": "2026-01-16T21:05:00Z", "actor_id": "unknown",
         "action": "crime_detected", "source": "video", "source_type": "cctv_video", "confidence": 0.9},
    ]
    result = IncidentTimelineBuilder().build_timeline(events)
    assert not [c for c in result["contradictions"] if c["type"] == "uncredentialed_presence"]


def test_rank_suspects_tolerates_non_numeric_scores():
    events = [
        {"canonical_entity": "user_001", "score": "high", "source": "document", "event_id": "EVT-1"},
        {"canonical_entity": "user_001", "score": 0.9, "source": "cyber", "event_id": "EVT-2"},
    ]
    ranking = MultimodalCorrelator._rank_suspects(events, [])
    assert ranking[0]["entity"] == "user_001"
