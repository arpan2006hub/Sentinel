"""Multi-Modal Incident Timeline Builder with Contradiction & Anomaly Detection."""

from __future__ import annotations

import datetime
from typing import Any, Optional

# Location keywords that mark a zone as access-controlled.
RESTRICTED_KEYWORDS = ("restricted", "vault", "server", "data-center", "datacenter")

# Badge actions that grant physical access vs. those that refuse it.
BADGE_GRANTED_ACTIONS = {"badge_swipe", "badge_granted", "badge_in"}
BADGE_DENIED_ACTIONS = {"badge_denied", "badge_rejected"}


def _score(ev: dict[str, Any]) -> float:
    try:
        return float(ev.get("score") or ev.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _entity(ev: dict[str, Any]) -> Optional[str]:
    return ev.get("canonical_entity") or ev.get("actor_id") or ev.get("entity")


def _location(ev: dict[str, Any]) -> Optional[str]:
    return ev.get("location_id") or ev.get("location")


def _is_badge(ev: dict[str, Any]) -> bool:
    return "badge" in str(ev.get("source_type", "")) or "badge" in str(ev.get("action", ""))


def _is_restricted(location: Optional[str]) -> bool:
    loc = (location or "").lower()
    return any(k in loc for k in RESTRICTED_KEYWORDS)


class IncidentTimelineBuilder:
    """Constructs a unified, chronological multi-modal incident timeline.

    Performs temporal sliding window clustering, cross-modality alignment,
    and rule-based contradiction detection (impossible travel, uncredentialed
    presence, denied-badge-then-activity, after-hours activity).
    """

    def __init__(self, window_minutes: int = 60, badge_window_minutes: int = 30) -> None:
        self.window_minutes = window_minutes
        self.badge_window_minutes = badge_window_minutes

    @staticmethod
    def parse_timestamp(ts: Any) -> Optional[datetime.datetime]:
        """Parse ISO 8601 strings/datetimes into timezone-aware UTC datetimes.

        Returns ``None`` when the value is missing or cannot be parsed. Callers
        must never substitute the current time: in an investigation a fabricated
        timestamp is worse than a missing one.
        """
        if ts is None:
            return None
        if isinstance(ts, datetime.datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=datetime.timezone.utc)
            return ts.astimezone(datetime.timezone.utc)

        ts_str = str(ts).strip()
        if not ts_str or ts_str.lower() in {"nan", "none", "null", "nat"}:
            return None
        if " " in ts_str and "T" not in ts_str:
            ts_str = ts_str.replace(" ", "T", 1)
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"

        try:
            dt = datetime.datetime.fromisoformat(ts_str)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)

    def build_timeline(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Process canonical events into a timeline with clusters and contradictions."""
        normalized_events: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for ev in events:
            ev_copy = dict(ev)
            raw_ts = ev_copy.get("timestamp") or ev_copy.get("timestamp_start")
            dt = self.parse_timestamp(raw_ts)
            if dt is None:
                skipped.append({
                    "event_id": ev_copy.get("event_id"),
                    "source": ev_copy.get("source"),
                    "reason": f"missing or unparseable timestamp: {raw_ts!r}",
                })
                continue
            ev_copy["_datetime"] = dt
            ev_copy["timestamp"] = dt.isoformat()
            normalized_events.append(ev_copy)

        normalized_events.sort(key=lambda x: x["_datetime"])

        contradictions = self.detect_contradictions(normalized_events)
        clusters = self.cluster_temporal_windows(normalized_events)

        for ev in normalized_events:
            ev.pop("_datetime", None)
        for cluster in clusters:
            for ev in cluster["events"]:
                ev.pop("_datetime", None)

        return {
            "events": normalized_events,
            "clusters": clusters,
            "contradictions": contradictions,
            "skipped_events": skipped,
            "summary": {
                "total_events": len(normalized_events),
                "skipped_events": len(skipped),
                "cluster_count": len(clusters),
                "contradiction_count": len(contradictions),
                "sources_represented": sorted({e.get("source", "unknown") for e in normalized_events}),
            },
        }

    def detect_contradictions(self, sorted_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify multi-source contradictions and cross-modality mismatches."""
        contradictions: list[dict[str, Any]] = []
        badge_window = self.badge_window_minutes * 60

        # 1. Spatial-temporal contradiction (impossible travel)
        for i, ev1 in enumerate(sorted_events):
            actor1, loc1, t1 = _entity(ev1), _location(ev1), ev1["_datetime"]
            if not actor1 or actor1 == "unknown" or not loc1:
                continue
            for ev2 in sorted_events[i + 1:]:
                t2 = ev2["_datetime"]
                delta_minutes = (t2 - t1).total_seconds() / 60.0
                if delta_minutes > 15:
                    break
                actor2, loc2 = _entity(ev2), _location(ev2)
                if actor1 == actor2 and loc2 and loc1 != loc2 and delta_minutes < 2.0:
                    contradictions.append({
                        "type": "impossible_travel",
                        "severity": "high",
                        "entity": actor1,
                        "description": (
                            f"Entity '{actor1}' registered in '{loc1}' at {t1.isoformat()} "
                            f"and in '{loc2}' at {t2.isoformat()} ({delta_minutes:.1f} mins apart). "
                            "Physical transit between these locations in this timeframe is implausible; "
                            "possible credential sharing or a cloned badge."
                        ),
                        "event_ids": [ev1.get("event_id"), ev2.get("event_id")],
                        "time_window_seconds": (t2 - t1).total_seconds(),
                    })

        badges = [e for e in sorted_events if _is_badge(e)]
        granted = [e for e in badges if str(e.get("action", "badge_swipe")) in BADGE_GRANTED_ACTIONS]
        denied = [e for e in badges if str(e.get("action", "")) in BADGE_DENIED_ACTIONS]
        video_events = [
            e for e in sorted_events
            if e.get("source") == "video" or e.get("source_type") == "cctv_video"
        ]

        # 2. Uncredentialed presence: CCTV crime / high anomaly in a zone with no
        #    granted badge swipe at that same location within the badge window.
        #    Only evaluated when badge evidence exists for the case.
        if badges:
            for v_ev in video_events:
                loc = _location(v_ev)
                if not loc:
                    continue  # no camera location: cannot be compared with badge swipes
                is_crime = v_ev.get("action") == "crime_detected" or v_ev.get("kind") == "video_crime"
                high_anomaly = _is_restricted(loc) and _score(v_ev) >= 0.75
                if not (is_crime or high_anomaly):
                    continue
                v_time = v_ev["_datetime"]
                authorized_by = [
                    b for b in granted
                    if _location(b) == loc and abs((b["_datetime"] - v_time).total_seconds()) <= badge_window
                ]
                if not authorized_by:
                    contradictions.append({
                        "type": "uncredentialed_presence",
                        "severity": "critical",
                        "entity": v_ev.get("canonical_entity", "unknown"),
                        "description": (
                            f"Video surveillance detected {'crime' if is_crime else 'a high-severity anomaly'} "
                            f"in '{loc}' at {v_time.isoformat()} with no granted badge access to that "
                            f"location within ±{self.badge_window_minutes} minutes."
                        ),
                        "event_ids": [v_ev.get("event_id")],
                    })

        # 3. Denied badge followed by activity in the same zone (tailgating / forced entry)
        for d_ev in denied:
            loc = _location(d_ev)
            if not loc:
                continue
            d_time = d_ev["_datetime"]
            followers = [
                e for e in sorted_events
                if e is not d_ev
                and _location(e) == loc
                and 0 < (e["_datetime"] - d_time).total_seconds() <= badge_window
                and not _is_badge(e)
                and (_score(e) >= 0.5 or e.get("action") == "crime_detected")
            ]
            if followers:
                contradictions.append({
                    "type": "denied_access_then_activity",
                    "severity": "high",
                    "entity": d_ev.get("canonical_entity", "unknown"),
                    "description": (
                        f"Badge access for '{d_ev.get('canonical_entity', 'unknown')}' was DENIED at '{loc}' "
                        f"at {d_time.isoformat()}, yet {len(followers)} suspicious event(s) were recorded in "
                        f"the same zone within {self.badge_window_minutes} minutes (possible tailgating)."
                    ),
                    "event_ids": [d_ev.get("event_id")] + [e.get("event_id") for e in followers],
                })

        # 4. Off-hours activity
        for ev in sorted_events:
            dt = ev["_datetime"]
            hour = dt.hour
            is_anomaly = ev.get("prediction") == 1 or _score(ev) > 0.75
            if is_anomaly and not _is_badge(ev) and (hour < 6 or hour >= 21 or dt.weekday() >= 5):
                contradictions.append({
                    "type": "after_hours_activity",
                    "severity": "medium",
                    "entity": _entity(ev) or "unknown",
                    "description": (
                        f"Suspicious activity ({ev.get('kind', 'anomaly')}) observed outside standard "
                        f"business hours at {dt.isoformat()} (Hour: {hour:02d}:00 UTC)."
                    ),
                    "event_ids": [ev.get("event_id")],
                })

        for idx, item in enumerate(contradictions, 1):
            item["anomaly_id"] = f"ANOM-{idx:04d}"
        return contradictions

    def cluster_temporal_windows(self, sorted_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group events into discrete incident clusters based on sliding time windows."""
        groups: list[dict[str, Any]] = []

        for ev in sorted_events:
            entity = _entity(ev) or "unknown"
            source = ev.get("source") or ev.get("source_type") or "unknown"
            t = ev["_datetime"]

            match: Optional[dict[str, Any]] = None
            for g in groups:
                time_diff = abs((t - g["last_datetime"]).total_seconds())
                if time_diff > self.window_minutes * 60:
                    continue
                if (entity != "unknown" and entity in g["entities"]) or time_diff <= 900:
                    match = g
                    break

            if match:
                match["events"].append(ev)
                match["last_datetime"] = max(match["last_datetime"], t)
                match["entities"].add(entity)
                match["sources"].add(source)
                match["max_score"] = max(match["max_score"], _score(ev))
            else:
                groups.append({
                    "cluster_id": f"INC-CLUSTER-{len(groups) + 1:03d}",
                    "start_datetime": t,
                    "last_datetime": t,
                    "entities": {entity},
                    "sources": {source},
                    "max_score": _score(ev),
                    "events": [ev],
                })

        result: list[dict[str, Any]] = []
        for g in groups:
            entities = sorted(g["entities"])
            result.append({
                "cluster_id": g["cluster_id"],
                "start_time": g["start_datetime"].isoformat(),
                "end_time": g["last_datetime"].isoformat(),
                "duration_minutes": round((g["last_datetime"] - g["start_datetime"]).total_seconds() / 60.0, 1),
                "entities": entities,
                "known_entities": [e for e in entities if e != "unknown"],
                "sources": sorted(g["sources"]),
                "is_cross_modal": len(g["sources"]) > 1,
                "max_score": round(g["max_score"], 3),
                "event_count": len(g["events"]),
                "event_ids": [e.get("event_id") for e in g["events"]],
                "events": g["events"],
            })
        return result
