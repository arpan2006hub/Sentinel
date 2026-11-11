"""Entity Resolution Module for Cross-Modal Identity Disambiguation."""

from __future__ import annotations

import re
from typing import Any, Optional


class EntityResolver:
    """Disambiguates and unifies cross-modal entity references into canonical IDs.
    
    Resolves usernames, emails, physical badge numbers, workstation hostnames,
    and video actor tracks to standardized investigation entities.
    """

    def __init__(self) -> None:
        # Canonical entity mapping: alias -> canonical_id
        self._alias_to_canonical: dict[str, str] = {}
        # Entity metadata: canonical_id -> dict
        self._entities: dict[str, dict[str, Any]] = {}

    def register_entity(
        self,
        canonical_id: str,
        aliases: Optional[list[str]] = None,
        entity_type: str = "user",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a known canonical entity and its associated aliases."""
        clean_id = canonical_id.strip()
        self._entities[clean_id] = {
            "canonical_id": clean_id,
            "entity_type": entity_type,
            "metadata": metadata or {},
        }
        self._alias_to_canonical[clean_id.lower()] = clean_id

        if aliases:
            for alias in aliases:
                self.add_alias(clean_id, alias)

    def add_alias(self, canonical_id: str, alias: str) -> None:
        """Map an alias to an existing canonical entity ID."""
        clean_alias = alias.strip().lower()
        self._alias_to_canonical[clean_alias] = canonical_id

    def resolve(self, raw_identifier: str | None) -> tuple[str, float]:
        """Resolve a raw entity reference into (canonical_id, confidence).
        
        Confidence:
          1.0 - Exact match in registered entity/alias table
          0.9 - Deterministic domain/email prefix normalization
          0.8 - Standardized regex pattern extraction (e.g. user_xxx, badge-xxx)
          0.0 - Unresolved / unknown
        """
        if not raw_identifier:
            return "unknown", 0.0

        cleaned = str(raw_identifier).strip()
        lower = cleaned.lower()

        # 1. Direct dictionary lookup
        if lower in self._alias_to_canonical:
            return self._alias_to_canonical[lower], 1.0

        # 2. Domain prefix stripping: CORP\jdoe or DOMAIN/jdoe -> jdoe
        domain_match = re.match(r"^[a-zA-Z0-9_\-\.]+[\\/]([a-zA-Z0-9_\-\.]+)$", cleaned)
        if domain_match:
            sub = domain_match.group(1).lower()
            if sub in self._alias_to_canonical:
                return self._alias_to_canonical[sub], 0.95
            lower = sub

        # 3. Email normalization: user_003@company.com -> user_003
        if "@" in lower:
            prefix = lower.split("@")[0]
            if prefix in self._alias_to_canonical:
                return self._alias_to_canonical[prefix], 0.95
            lower = prefix

        # 4. Standard pattern normalization: user_003 / user-003 / USER003
        user_pattern = re.search(r"user[_\-]?(\d{1,4})", lower)
        if user_pattern:
            num = int(user_pattern.group(1))
            canonical = f"user_{num:03d}"
            return canonical, 0.90

        # 5. Badge pattern: badge-003 / card-003 -> user_003
        badge_pattern = re.search(r"(?:badge|card)[_\-]?(\d{1,4})", lower)
        if badge_pattern:
            num = int(badge_pattern.group(1))
            canonical = f"user_{num:03d}"
            return canonical, 0.85

        # 6. Workstation / Host pattern: ws-user-003 / ws-003 -> user_003
        ws_pattern = re.search(r"ws[_\-]?(?:user[_\-]?)?(\d{1,4})", lower)
        if ws_pattern:
            num = int(ws_pattern.group(1))
            canonical = f"user_{num:03d}"
            return canonical, 0.80

        # 7. CCTV Actor cluster: actor_user_003 or track_user_003
        actor_pattern = re.search(r"(?:actor|track)[_\-]?user[_\-]?(\d{1,4})", lower)
        if actor_pattern:
            num = int(actor_pattern.group(1))
            canonical = f"user_{num:03d}"
            return canonical, 0.85

        if lower in ("unknown", "none", "null", ""):
            return "unknown", 0.0

        # Default fallback: preserve normalized lowercase string with lower confidence
        return lower, 0.50

    def resolve_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Enrich a canonical event dictionary with resolved entity and confidence."""
        raw_actor = event.get("actor_id") or event.get("entity") or event.get("user_id")
        canonical_id, confidence = self.resolve(raw_actor)

        enriched = dict(event)
        enriched["canonical_entity"] = canonical_id
        enriched["entity_resolution_confidence"] = confidence
        return enriched

    def cluster_events(self, events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group a collection of events by resolved canonical entity ID."""
        clusters: dict[str, list[dict[str, Any]]] = {}
        for ev in events:
            enriched = self.resolve_event(ev)
            cid = enriched["canonical_entity"]
            clusters.setdefault(cid, []).append(enriched)
        return clusters

