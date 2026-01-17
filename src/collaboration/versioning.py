"""Version control for requirements."""

from typing import Optional
from datetime import datetime
from copy import deepcopy

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class VersionControl:
    """
    Version control system for requirements.
    
    Tracks changes, provides diff, and supports rollback.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the version control system."""
        self.settings = settings or get_settings()
        
        # In-memory version history (TODO: Replace with database)
        self._versions: dict[str, list[dict]] = {}
        
        logger.info("VersionControl initialized")

    def create_version(
        self,
        entity_id: str,
        entity_data: dict,
        author: str = "system",
        message: str = "",
    ) -> str:
        """
        Create a new version of an entity.
        
        Args:
            entity_id: Entity identifier
            entity_data: Entity data
            author: Author of the change
            message: Version message
            
        Returns:
            Version identifier
        """
        version_id = f"v{len(self._versions.get(entity_id, [])) + 1}"
        
        if entity_id not in self._versions:
            self._versions[entity_id] = []
        
        version = {
            "version_id": version_id,
            "entity_id": entity_id,
            "data": deepcopy(entity_data),
            "author": author,
            "message": message,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._versions[entity_id].append(version)
        
        logger.info(
            "Version created",
            entity_id=entity_id,
            version_id=version_id,
            author=author,
        )
        
        return version_id

    def get_version(
        self,
        entity_id: str,
        version_id: str,
    ) -> Optional[dict]:
        """Get a specific version of an entity."""
        versions = self._versions.get(entity_id, [])
        for version in versions:
            if version["version_id"] == version_id:
                return version
        return None

    def get_versions(
        self,
        entity_id: str,
    ) -> list[dict]:
        """Get all versions of an entity."""
        return self._versions.get(entity_id, [])

    def diff_versions(
        self,
        entity_id: str,
        version1_id: str,
        version2_id: str,
    ) -> dict:
        """
        Calculate diff between two versions.
        
        Args:
            entity_id: Entity identifier
            version1_id: First version ID
            version2_id: Second version ID
            
        Returns:
            Dictionary with added, removed, and changed fields
        """
        v1 = self.get_version(entity_id, version1_id)
        v2 = self.get_version(entity_id, version2_id)
        
        if not v1 or not v2:
            return {"error": "One or both versions not found"}
        
        data1 = v1.get("data", {})
        data2 = v2.get("data", {})
        
        added = {}
        removed = {}
        changed = {}
        
        # Find added and changed fields
        for key, value in data2.items():
            if key not in data1:
                added[key] = value
            elif data1[key] != value:
                changed[key] = {"old": data1[key], "new": value}
        
        # Find removed fields
        for key in data1:
            if key not in data2:
                removed[key] = data1[key]
        
        return {
            "entity_id": entity_id,
            "version1": version1_id,
            "version2": version2_id,
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    def rollback(
        self,
        entity_id: str,
        target_version_id: str,
    ) -> dict:
        """
        Rollback entity to a specific version.
        
        Args:
            entity_id: Entity identifier
            target_version_id: Target version ID to rollback to
            
        Returns:
            Rolled back entity data
        """
        target_version = self.get_version(entity_id, target_version_id)
        
        if not target_version:
            return {"error": f"Version {target_version_id} not found"}
        
        # Create new version with rolled back data
        rollback_version_id = self.create_version(
            entity_id=entity_id,
            entity_data=target_version["data"],
            author="system",
            message=f"Rollback to {target_version_id}",
        )
        
        logger.info(
            "Rollback completed",
            entity_id=entity_id,
            target_version=target_version_id,
            new_version=rollback_version_id,
        )
        
        return {
            "entity_id": entity_id,
            "rollback_to": target_version_id,
            "new_version": rollback_version_id,
            "data": target_version["data"],
        }
