"""Multi-Modal Incident Timeline Builder with Contradiction & Anomaly Detection."""

from __future__ import annotations

import datetime
from typing import Any, Optional


class IncidentTimelineBuilder:
    """Constructs a unified, chronological multi-modal incident timeline.
    
    Performs temporal sliding window clustering, cross-modality alignment,
    and automated contradiction detection (e.g. impossible travel, uncredentialed access).
    """

    def __init__(self, window_minutes: int = 60) -> None:
        self.window_minutes = window_minutes

    @staticmethod
    def parse_timestamp(ts: Any) -> datetime.datetime:
        """Parse various ISO 8601 string formats into timezone-aware UTC datetime."""
        if isinstance(ts, datetime.datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=datetime.timezone.utc)
            return ts.astimezone(datetime.timezone.utc)

        ts_str = str(ts).strip()
        # Replace space separator with 'T'
        if " " in ts_str and "T" not in ts_str:
            ts_str = ts_str.replace(" ", "T")

        # Handle 'Z'
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"

        try:
            dt = datetime.datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except Exception:
            # Fallback
            return datetime.datetime.now(datetime.timezone.utc)

    def build_timeline(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Process raw/canonical events into a structured timeline with incident clusters and contradictions."""
        if not events:
            return {
                "events": [],
                "clusters": [],
                "contradictions": [],
                "summary": {
                    "total_events": 0,
                    "cluster_count": 0,
                    "contradiction_count": 0,
                },
            }

        # Normalize and sort events chronologically
        normalized_events: list[dict[str, Any]] = []
        for ev in events:
            ev_copy = dict(ev)
            raw_ts = ev_copy.get("timestamp") or ev_copy.get("timestamp_start") or ev_copy.get("ingested_at")
            dt = self.parse_timestamp(raw_ts)
            ev_copy["_datetime"] = dt
            ev_copy["timestamp"] = dt.isoformat()
            normalized_events.append(ev_copy)

        normalized_events.sort(key=lambda x: x["_datetime"])

        # Detect contradictions across evidence sources
        contradictions = self.detect_contradictions(normalized_events)

        # Form temporal incident clusters
        clusters = self.cluster_temporal_windows(normalized_events)

        # Strip internal _datetime before returning
        for ev in normalized_events:
            ev.pop("_datetime", None)
        for cluster in clusters:
            for ev in cluster["events"]:
                ev.pop("_datetime", None)

        return {
            "events": normalized_events,
            "clusters": clusters,
            "contradictions": contradictions,
            "summary": {
                "total_events": len(normalized_events),
                "cluster_count": len(clusters),
                "contradiction_count": len(contradictions),
                "sources_represented": sorted(list({e.get("source", "unknown") for e in normalized_events})),
            },
        }

    def detect_contradictions(self, sorted_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify multi-source contradictions and anomalous cross-modality mismatches."""
        contradictions: list[dict[str, Any]] = []

        # 1. Spatial-Temporal Contradiction (Impossible Travel)
        for i in range(len(sorted_events)):
            ev1 = sorted_events[i]
            actor1 = ev1.get("canonical_entity") or ev1.get("actor_id") or ev1.get("entity")
            loc1 = ev1.get("location_id") or ev1.get("location")
            t1 = ev1["_datetime"]

            if not actor1 or actor1 == "unknown" or not loc1:
                continue

            for j in range(i + 1, len(sorted_events)):
                ev2 = sorted_events[j]
                actor2 = ev2.get("canonical_entity") or ev2.get("actor_id") or ev2.get("entity")
                loc2 = ev2.get("location_id") or ev2.get("location")
                t2 = ev2["_datetime"]

                delta_minutes = (t2 - t1).total_seconds() / 60.0
                if delta_minutes > 15:
                    break

                if actor1 == actor2 and loc1 != loc2 and delta_minutes < 2.0:
                    contradictions.append({
                        "type": "impossible_travel",
                        "severity": "high",
                        "entity": actor1,
                        "description": (
                            f"Entity '{actor1}' registered in '{loc1}' at {t1.isoformat()} "
                            f"and in '{loc2}' at {t2.isoformat()} ({delta_minutes:.1f} mins apart). "
                            f"Physical transit between locations in this timeframe is impossible."
                        ),
                        "event_ids": [ev1.get("event_id"), ev2.get("event_id")],
                        "time_window_seconds": (t2 - t1).total_seconds(),
                    })

        # 2. Uncredentialed Restricted Presence (CCTV Crime/Anomaly with no authorized badge)
        video_crimes = [e for e in sorted_events if e.get("source") == "video" or e.get("source_type") == "cctv_video"]
        badge_swipes = [e for e in sorted_events if "badge" in str(e.get("source_type", "")) or "badge" in str(e.get("action", ""))]

        for v_ev in video_crimes:
            loc = v_ev.get("location_id") or "RESTRICTED-ZONE"
            v_time = v_ev["_datetime"]
            is_crime = (
                v_ev.get("action") == "crime_detected"
                or v_ev.get("kind") == "video_crime"
                or float(v_ev.get("confidence", 0.0)) > 0.80
            )

            if is_crime and "restricted" in loc.lower() or "vault" in loc.lower() or is_crime:
                # Check for badge swipe in the same area within 30 minutes
                authorized = False
                for b_ev in badge_swipes:
                    b_loc = b_ev.get("location_id") or ""
                    b_time = b_ev["_datetime"]
                    if abs((b_time - v_time).total_seconds()) <= 1800:
                        authorized = True
                        break

                if not authorized and badge_swipes:
                    contradictions.append({
                        "type": "uncredentialed_presence",
                        "severity": "critical",
                        "entity": v_ev.get("canonical_entity", "unknown"),
                        "description": (
                            f"Video surveillance detected high-severity anomaly / crime in '{loc}' "
                            f"at {v_time.isoformat()} with NO corresponding badge reader authentication."
                        ),
                        "event_ids": [v_ev.get("event_id")],
                    })

        # 3. Off-Hours Spike
        for ev in sorted_events:
            dt = ev["_datetime"]
            hour = dt.hour
            is_anomaly = ev.get("prediction") == 1 or ev.get("score", 0) > 0.75 or ev.get("confidence", 0) > 0.8
            if is_anomaly and (hour < 6 or hour >= 21 or dt.weekday() >= 5):
                contradictions.append({
                    "type": "after_hours_activity",
                    "severity": "medium",
                    "entity": ev.get("canonical_entity") or ev.get("actor_id", "unknown"),
                    "description": (
                        f"Suspicious activity ({ev.get('kind', 'anomaly')}) observed outside standard "
                        f"business hours at {dt.isoformat()} (Hour: {hour}:00 UTC)."
                    ),
                    "event_ids": [ev.get("event_id")],
                })

        return contradictions

    def cluster_temporal_windows(self, sorted_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group events into discrete incident clusters based on sliding time windows."""
        groups: list[dict[str, Any]] = []

        for ev in sorted_events:
            entity = ev.get("canonical_entity") or ev.get("actor_id") or ev.get("entity") or "unknown"
            source = ev.get("source") or ev.get("source_type") or "unknown"
            t = ev["_datetime"]

            # Find matching active group
            matching: list[dict[str, Any]] = []
            for g in groups:
                time_diff = abs((t - g["last_datetime"]).total_seconds())
                if time_diff <= self.window_minutes * 60:
                    if entity != "unknown" and entity in g["entities"]:
                        matching.append(g)
                    elif time_diff <= 900:  # 15 minutes burst across any actors
                        matching.append(g)

            if matching:
                group = matching[0]
                group["events"].append(ev)
                group["last_datetime"] = max(group["last_datetime"], t)
                group["entities"].add(entity)
                group["sources"].add(source)
                group["max_score"] = max(
                    group["max_score"],
                    float(ev.get("score", 0.0) or ev.get("confidence", 0.0) or 0.0),
                )
            else:
                groups.append({
                    "cluster_id": f"INC-CLUSTER-{len(groups) + 1:03d}",
                    "start_time": t.isoformat(),
                    "last_datetime": t,
                    "entities": {entity},
                    "sources": {source},
                    "max_score": float(ev.get("score", 0.0) or ev.get("confidence", 0.0) or 0.0),
                    "events": [ev],
                })

        # Format output
        result: list[dict[str, Any]] = []
        for g in groups:
            result.append({
                "cluster_id": g["cluster_id"],
                "start_time": g["start_time"],
                "end_time": g["last_datetime"].isoformat(),
                "duration_minutes": round((g["last_datetime"] - IncidentTimelineBuilder.parse_timestamp(g["start_time"])).total_seconds() / 60.0, 1),
                "entities": sorted(list(g["entities"])),
                "sources": sorted(list(g["sources"])),
                "max_score": round(g["max_score"], 3),
                "event_count": len(g["events"]),
                "events": g["events"],
            })

        return result

