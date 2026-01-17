"""Audit logging system."""

from typing import Optional, Any
from datetime import datetime

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Comprehensive audit logging system.
    
    Tracks all user actions for compliance and security.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the audit logger."""
        self.settings = settings or get_settings()
        
        # In-memory audit log (TODO: Replace with database or file storage)
        self._audit_logs: list[dict] = []
        
        logger.info("AuditLogger initialized")

    def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Log an audit event.
        
        Args:
            user_id: User identifier
            action: Action performed (view, create, update, delete)
            resource_type: Type of resource (document, requirement, story)
            resource_id: Resource identifier
            details: Optional additional details
            ip_address: Optional IP address
            
        Returns:
            Audit log entry ID
        """
        log_entry = {
            "log_id": f"audit_{len(self._audit_logs) + 1}",
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._audit_logs.append(log_entry)
        
        # Also log to structured logger
        logger.info(
            "Audit event",
            log_id=log_entry["log_id"],
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        
        return log_entry["log_id"]

    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Query audit logs.
        
        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            action: Filter by action
            limit: Maximum number of results
            
        Returns:
            List of audit log entries
        """
        filtered = self._audit_logs.copy()
        
        if user_id:
            filtered = [log for log in filtered if log["user_id"] == user_id]
        
        if resource_type:
            filtered = [log for log in filtered if log["resource_type"] == resource_type]
        
        if action:
            filtered = [log for log in filtered if log["action"] == action]
        
        # Sort by timestamp (newest first) and limit
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return filtered[:limit]

    def export_audit_logs(
        self,
        format: str = "json",
    ) -> str:
        """
        Export audit logs in specified format.
        
        Args:
            format: Export format (json, csv)
            
        Returns:
            Exported audit logs as string
        """
        if format == "json":
            import json
            return json.dumps(self._audit_logs, indent=2)
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            if self._audit_logs:
                writer = csv.DictWriter(output, fieldnames=self._audit_logs[0].keys())
                writer.writeheader()
                writer.writerows(self._audit_logs)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
