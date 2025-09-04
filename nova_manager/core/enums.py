from enum import Enum


class UserRole(str, Enum):
    """User roles in the organization"""

    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    MEMBER = "member"

    @classmethod
    def admin_roles(cls) -> list["UserRole"]:
        """Roles that have admin permissions"""
        return [cls.OWNER, cls.ADMIN]

    @classmethod
    def all_roles(cls) -> list["UserRole"]:
        """All available roles"""
        return [role for role in cls]

    @classmethod
    def developer_roles(cls) -> list["UserRole"]:
        """Roles that have developer permissions"""
        return [cls.OWNER, cls.ADMIN, cls.DEVELOPER]

    @classmethod
    def analyst_roles(cls) -> list["UserRole"]:
        """Roles that have analyst permissions"""
        return [cls.OWNER, cls.ADMIN, cls.ANALYST]


class InvitationStatus(str, Enum):
    """Invitation status values"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    @classmethod
    def active_statuses(cls) -> list[str]:
        """Statuses considered as active invitations"""
        return [cls.PENDING]

    @classmethod
    def inactive_statuses(cls) -> list[str]:
        """Statuses considered as inactive invitations"""
        return [cls.ACCEPTED, cls.EXPIRED, cls.CANCELLED]
