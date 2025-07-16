from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from nova_manager.components.user_experience.models import UserFeatureVariants
from nova_manager.core.base_crud import BaseCRUD


class UserFeatureVariantsCRUD(BaseCRUD):
    """CRUD operations for UserFeatureVariants"""

    def __init__(self, db: Session):
        super().__init__(UserFeatureVariants, db)

    def get_user_assignment(
        self, user_pid: UUIDType, feature_pid: UUIDType
    ) -> Optional[UserFeatureVariants]:
        """Get user's variant assignment for a specific feature"""
        return (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.user_id == user_pid,
                    UserFeatureVariants.feature_id == feature_pid,
                )
            )
            .first()
        )

    def get_user_assignments_for_objects(
        self, user_pid: UUIDType, feature_pids: List[UUIDType]
    ) -> List[UserFeatureVariants]:
        """Get user's variant assignments for multiple features/objects"""
        return (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.user_id == user_pid,
                    UserFeatureVariants.feature_id.in_(feature_pids),
                )
            )
            .all()
        )

    def assign_user_variant(
        self,
        user_pid: UUIDType,
        feature_pid: UUIDType,
        variant_name: str,
        variant_config: dict,
        organisation_id: str,
        app_id: str,
        experience_id: Optional[UUIDType] = None,
    ) -> UserFeatureVariants:
        """Assign or update user's variant for a feature"""
        # Check if assignment already exists
        existing = self.get_user_assignment(user_pid, feature_pid)
        
        if existing:
            # Update existing assignment
            existing.variant_name = variant_name
            existing.variant_config = variant_config
            existing.experience_id = experience_id
            existing.variant_assigned_at = datetime.utcnow()
            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new assignment
            assignment = UserFeatureVariants(
                user_id=user_pid,
                feature_id=feature_pid,
                experience_id=experience_id,
                variant_name=variant_name,
                variant_config=variant_config,
                organisation_id=organisation_id,
                app_id=app_id,
                variant_assigned_at=datetime.utcnow(),
            )
            self.db.add(assignment)
            self.db.flush()
            self.db.refresh(assignment)
            return assignment

    def is_variant_valid(
        self, assignment: UserFeatureVariants, experience_last_updated: datetime
    ) -> bool:
        """Check if variant assignment is valid (assigned after experience last updated)"""
        return assignment.variant_assigned_at > experience_last_updated

    def get_user_assignments_by_org_app(
        self, user_pid: UUIDType, organisation_id: str, app_id: str
    ) -> List[UserFeatureVariants]:
        """Get all user's variant assignments for an org/app"""
        return (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.user_id == user_pid,
                    UserFeatureVariants.organisation_id == organisation_id,
                    UserFeatureVariants.app_id == app_id,
                )
            )
            .all()
        ) 