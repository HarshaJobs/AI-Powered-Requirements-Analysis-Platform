"""Role-Based Access Control (RBAC) implementation."""

from typing import Optional
from enum import Enum

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class Role(str, Enum):
    """User roles."""
    ADMIN = "admin"
    BUSINESS_ANALYST = "business_analyst"
    STAKEHOLDER = "stakeholder"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Permissions."""
    # Document permissions
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_DELETE = "document:delete"
    
    # Requirement permissions
    REQUIREMENT_CREATE = "requirement:create"
    REQUIREMENT_EDIT = "requirement:edit"
    REQUIREMENT_DELETE = "requirement:delete"
    REQUIREMENT_VIEW = "requirement:view"
    
    # User story permissions
    STORY_CREATE = "story:create"
    STORY_EDIT = "story:edit"
    STORY_DELETE = "story:delete"
    
    # Conflict permissions
    CONFLICT_VIEW = "conflict:view"
    CONFLICT_RESOLVE = "conflict:resolve"
    
    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"


class RBAC:
    """
    Role-Based Access Control system.
    
    Defines roles, permissions, and access control logic.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize RBAC system."""
        self.settings = settings or get_settings()
        
        # Role-permission mapping
        self._role_permissions = {
            Role.ADMIN: list(Permission),  # Admin has all permissions
            Role.BUSINESS_ANALYST: [
                Permission.DOCUMENT_UPLOAD,
                Permission.DOCUMENT_VIEW,
                Permission.REQUIREMENT_CREATE,
                Permission.REQUIREMENT_EDIT,
                Permission.REQUIREMENT_VIEW,
                Permission.STORY_CREATE,
                Permission.STORY_EDIT,
                Permission.CONFLICT_VIEW,
                Permission.CONFLICT_RESOLVE,
            ],
            Role.STAKEHOLDER: [
                Permission.DOCUMENT_VIEW,
                Permission.REQUIREMENT_VIEW,
                Permission.STORY_CREATE,  # Can create stories
                Permission.CONFLICT_VIEW,
            ],
            Role.VIEWER: [
                Permission.DOCUMENT_VIEW,
                Permission.REQUIREMENT_VIEW,
                Permission.CONFLICT_VIEW,
            ],
        }
        
        # User-role mapping (in-memory, TODO: Replace with database)
        self._user_roles: dict[str, Role] = {}
        
        logger.info("RBAC system initialized")

    def assign_role(
        self,
        user_id: str,
        role: Role,
    ) -> None:
        """Assign a role to a user."""
        self._user_roles[user_id] = role
        logger.info(
            "Role assigned",
            user_id=user_id,
            role=role.value,
        )

    def get_user_role(
        self,
        user_id: str,
    ) -> Optional[Role]:
        """Get role for a user."""
        return self._user_roles.get(user_id)

    def has_permission(
        self,
        user_id: str,
        permission: Permission,
    ) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: User identifier
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        role = self.get_user_role(user_id)
        
        if not role:
            return False
        
        user_permissions = self._role_permissions.get(role, [])
        return permission in user_permissions

    def check_access(
        self,
        user_id: str,
        permission: Permission,
    ) -> bool:
        """
        Check access and log the attempt.
        
        Args:
            user_id: User identifier
            permission: Permission to check
            
        Returns:
            True if access granted
        """
        has_access = self.has_permission(user_id, permission)
        
        logger.info(
            "Access check",
            user_id=user_id,
            permission=permission.value,
            granted=has_access,
        )
        
        return has_access
