"""Traceability matrix for requirements tracking."""

from typing import Optional, Any
from datetime import datetime

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class TraceabilityMatrix:
    """
    Maintains traceability links between requirements, design, tests, and deployment.
    
    Provides bidirectional traceability and impact analysis.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the traceability matrix."""
        self.settings = settings or get_settings()
        
        # In-memory traceability links (TODO: Replace with database)
        self._links: dict[str, list[dict]] = {}
        self._entities: dict[str, dict] = {}
        
        logger.info("TraceabilityMatrix initialized")

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        entity_data: dict,
    ) -> None:
        """
        Add an entity to the traceability matrix.
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Type (requirement, design, test, deployment)
            entity_data: Entity metadata and content
        """
        self._entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "data": entity_data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if entity_id not in self._links:
            self._links[entity_id] = []
        
        logger.debug(
            "Entity added to traceability matrix",
            entity_id=entity_id,
            entity_type=entity_type,
        )

    def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "traces_to",
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Add a traceability link between entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            link_type: Type of link (traces_to, implements, tests, etc.)
            metadata: Optional link metadata
        """
        link = {
            "source_id": source_id,
            "target_id": target_id,
            "link_type": link_type,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if source_id not in self._links:
            self._links[source_id] = []
        
        self._links[source_id].append(link)
        
        logger.debug(
            "Traceability link added",
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
        )

    def get_traceability(
        self,
        entity_id: str,
        direction: str = "forward",
    ) -> list[dict]:
        """
        Get traceability links for an entity.
        
        Args:
            entity_id: Entity identifier
            direction: "forward" (downstream) or "backward" (upstream)
            
        Returns:
            List of linked entities
        """
        if entity_id not in self._links:
            return []
        
        links = self._links[entity_id]
        
        if direction == "forward":
            # Get entities this entity traces to
            return [
                {
                    "entity": self._entities.get(link["target_id"]),
                    "link_type": link["link_type"],
                    "metadata": link["metadata"],
                }
                for link in links
            ]
        else:
            # Get entities that trace to this entity (backward)
            backward_links = []
            for source_id, links_list in self._links.items():
                for link in links_list:
                    if link["target_id"] == entity_id:
                        backward_links.append({
                            "entity": self._entities.get(source_id),
                            "link_type": link["link_type"],
                            "metadata": link["metadata"],
                        })
            return backward_links

    def analyze_impact(
        self,
        entity_id: str,
    ) -> dict:
        """
        Analyze impact of changes to an entity.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Impact analysis with all affected entities
        """
        forward = self.get_traceability(entity_id, direction="forward")
        backward = self.get_traceability(entity_id, direction="backward")
        
        # Recursively find all downstream entities
        all_downstream = set()
        queue = [entity_id]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            forward_links = self.get_traceability(current, direction="forward")
            for link in forward_links:
                if link["entity"]:
                    target_id = link["entity"]["id"]
                    all_downstream.add(target_id)
                    queue.append(target_id)
        
        return {
            "entity_id": entity_id,
            "upstream_count": len(backward),
            "downstream_count": len(forward),
            "total_impact": len(all_downstream),
            "upstream_entities": backward,
            "downstream_entities": forward,
            "all_affected": [
                self._entities.get(entity_id) for entity_id in all_downstream
            ],
        }
