from typing import Optional, List
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_


from nova_manager.components.user_feature_variant.models import UserFeatureVariants
from nova_manager.components.users.models import Users
from nova_manager.core.base_crud import BaseCRUD


class UsersCRUD(BaseCRUD):
    """CRUD operations for Users"""

    def __init__(self, db: Session):
        super().__init__(Users, db)

    def get_by_user_id(
        self, user_id: str, organisation_id: str, app_id: str
    ) -> Optional[Users]:
        """Get user by user_id within organization/app scope"""
        return (
            self.db.query(Users)
            .filter(
                and_(
                    Users.user_id == user_id,
                    Users.organisation_id == organisation_id,
                    Users.app_id == app_id,
                )
            )
            .first()
        )

    def get_with_feature_assignments(self, pid: UUIDType) -> Optional[Users]:
        """Get user with all feature variant assignments"""
        return (
            self.db.query(Users)
            .options(
                selectinload(Users.user_feature_variants).selectinload(
                    UserFeatureVariants.feature_flag
                ),
                selectinload(Users.user_feature_variants).selectinload(
                    UserFeatureVariants.variant
                ),
            )
            .filter(Users.pid == pid)
            .first()
        )

    def search_users(
        self,
        search_term: str,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Users]:
        """Search users by user_id or profile data"""
        return (
            self.db.query(Users)
            .filter(
                and_(
                    Users.organisation_id == organisation_id,
                    Users.app_id == app_id,
                    or_(
                        Users.user_id.ilike(f"%{search_term}%"),
                        Users.user_profile.op("?")(search_term),  # JSON search
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_users_with_feature_variant(
        self,
        feature_pid: UUIDType,
        variant_name: str,
        organisation_id: str,
        app_id: str,
    ) -> List[Users]:
        """Get all users assigned to a specific feature variant"""
        return (
            self.db.query(Users)
            .join(UserFeatureVariants)
            .filter(
                and_(
                    Users.organisation_id == organisation_id,
                    Users.app_id == app_id,
                    UserFeatureVariants.feature_id == feature_pid,
                    UserFeatureVariants.variant_name == variant_name,
                )
            )
            .all()
        )
