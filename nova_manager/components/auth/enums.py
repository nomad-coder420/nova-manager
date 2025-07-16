from enum import Enum


class OrganisationRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class AppRole(Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    VIEWER = "viewer"
