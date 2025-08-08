from enum import Enum


class UserRole(str, Enum):
    """User roles in the organization"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

    @classmethod
    def admin_roles(cls) -> list[str]:
        """Roles that have admin permissions"""
        return [cls.OWNER, cls.ADMIN]

    @classmethod
    def all_roles(cls) -> list[str]:
        """All available roles"""
        return [cls.OWNER, cls.ADMIN, cls.MEMBER]


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