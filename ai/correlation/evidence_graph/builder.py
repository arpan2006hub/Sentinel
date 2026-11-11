"""Evidence Graph Builder for Multimodal Entity and Event Relationship Graphing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class EvidenceGraphBuilder:
    """Builds, analyzes, and exports a multimodal evidence relationship graph.
    
    Generates entity nodes (users, devices, locations, documents), event nodes,
    and semantic relationships (e.g., LOGGED_IN, ACCESSED, DETECTED_AT, CONTRADICTS).
    Outputs Cytoscape.js and React Flow compatible representations for dashboard visualization.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._edge_set: set[tuple[str, str, str]] = set()

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add or update an entity or event node in the graph."""
        clean_id = str(node_id).strip()
        if clean_id not in self.nodes:
            self.nodes[clean_id] = {
                "id": clean_id,
                "label": label,
                "type": node_type,
                "properties": properties or {},
            }
        else:
            if properties:
                self.nodes[clean_id]["properties"].update(properties)

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        weight: float = 1.0,
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a directed relationship between two nodes."""
        s = str(source).strip()
        t = str(target).strip()
        r = str(relationship).strip()

        edge_key = (s, t, r)
        if edge_key not in self._edge_set:
            self._edge_set.add(edge_key)
            self.edges.append({
                "source": s,
                "target": t,
                "relationship": r,
                "weight": weight,
                "properties": properties or {},
            })

    def build_from_events(self, events: list[dict[str, Any]], contradictions: Optional[list[dict[str, Any]]] = None) -> None:
        """Construct graph nodes and relationships automatically from a list of correlated events."""
        for ev in events:
            ev_id = ev.get("event_id") or f"EVT-{len(self.nodes):05d}"
            source_type = ev.get("source") or ev.get("source_type") or "unknown"
            kind = ev.get("kind") or ev.get("action") or "event"
            score = float(ev.get("score") or ev.get("confidence") or 0.0)

            # 1. Event node
            self.add_node(
                node_id=ev_id,
                label=f"{source_type.upper()}: {kind}",
                node_type="event",
                properties={
                    "source": source_type,
                    "kind": kind,
                    "timestamp": ev.get("timestamp"),
                    "score": score,
                },
            )

            # 2. Entity node (User/Actor)
            actor = ev.get("canonical_entity") or ev.get("actor_id") or ev.get("entity")
            if actor and actor != "unknown":
                self.add_node(
                    node_id=actor,
                    label=actor,
                    node_type="user",
                    properties={"resolved_id": actor},
                )
                self.add_edge(source=actor, target=ev_id, relationship="GENERATED", weight=score)

            # 3. Location node
            loc = ev.get("location_id") or ev.get("location")
            if loc:
                self.add_node(
                    node_id=loc,
                    label=loc,
                    node_type="location",
                    properties={"zone": loc},
                )
                self.add_edge(source=ev_id, target=loc, relationship="OCCURRED_AT", weight=1.0)
                if actor and actor != "unknown":
                    self.add_edge(source=actor, target=loc, relationship="PRESENT_IN", weight=1.0)

            # 4. Document node
            doc_id = ev.get("document_id")
            if doc_id:
                self.add_node(
                    node_id=doc_id,
                    label=doc_id,
                    node_type="document",
                    properties={"document_id": doc_id},
                )
                self.add_edge(source=ev_id, target=doc_id, relationship="REFERENCES", weight=1.0)
                if actor and actor != "unknown":
                    self.add_edge(source=doc_id, target=actor, relationship="MENTIONS", weight=1.0)

            # 5. Device / Object node
            obj_id = ev.get("object_id")
            if obj_id:
                self.add_node(
                    node_id=obj_id,
                    label=obj_id,
                    node_type="object",
                    properties={"object_id": obj_id},
                )
                self.add_edge(source=ev_id, target=obj_id, relationship="TARGETS", weight=1.0)

        # 6. Add contradiction edges
        if contradictions:
            for contra in contradictions:
                contra_type = contra.get("type", "contradiction")
                c_events = contra.get("event_ids", [])
                if len(c_events) >= 2 and c_events[0] in self.nodes and c_events[1] in self.nodes:
                    self.add_edge(
                        source=c_events[0],
                        target=c_events[1],
                        relationship="CONTRADICTS",
                        weight=2.0,
                        properties={"contradiction_type": contra_type, "severity": contra.get("severity")},
                    )

    def compute_degree_centrality(self) -> dict[str, int]:
        """Calculate degree centrality (number of connected edges) for each node."""
        degrees: dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            s = edge["source"]
            t = edge["target"]
            if s in degrees:
                degrees[s] += 1
            if t in degrees:
                degrees[t] += 1
        return degrees

    def to_dict(self) -> dict[str, Any]:
        """Export graph as standard nodes/edges dictionary."""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "metrics": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": sorted(list({n["type"] for n in self.nodes.values()})),
                "centrality": self.compute_degree_centrality(),
            },
        }

    def to_cytoscape(self) -> dict[str, Any]:
        """Export graph formatted for Cytoscape.js frontend visualization."""
        cy_nodes = [
            {"data": {"id": n["id"], "label": n["label"], "type": n["type"], **n["properties"]}}
            for n in self.nodes.values()
        ]
        cy_edges = [
            {
                "data": {
                    "id": f"edge_{i}",
                    "source": e["source"],
                    "target": e["target"],
                    "label": e["relationship"],
                    "weight": e["weight"],
                    **e["properties"],
                }
            }
            for i, e in enumerate(self.edges)
        ]
        return {
            "elements": {
                "nodes": cy_nodes,
                "edges": cy_edges,
            }
        }

    def save_json(self, path: Path | str) -> None:
        """Save graph dictionary to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

