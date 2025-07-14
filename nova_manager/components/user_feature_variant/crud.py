from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from nova_manager.components.feature_flags.models import FeatureFlags, FeatureVariants
from nova_manager.components.user_feature_variant.models import UserFeatureVariants
from nova_manager.core.base_crud import BaseCRUD


class UserFeatureVariantsCRUD(BaseCRUD):
    """CRUD operations for UserFeatureVariants"""

    def __init__(self, db: Session):
        super().__init__(UserFeatureVariants, db)

    def get_user_assignment(
        self, user_pid: UUIDType, feature_pid: UUIDType
    ) -> Optional[UserFeatureVariants]:
        """Get specific user assignment for a feature"""
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

    def get_user_assignments(self, user_pid: UUIDType) -> List[UserFeatureVariants]:
        """Get all feature assignments for a user"""
        return (
            self.db.query(UserFeatureVariants)
            .options(
                joinedload(UserFeatureVariants.feature_flag),
                joinedload(UserFeatureVariants.variant),
            )
            .filter(UserFeatureVariants.user_id == user_pid)
            .all()
        )

    def get_feature_assignments(
        self, feature_pid: UUIDType
    ) -> List[UserFeatureVariants]:
        """Get all user assignments for a feature"""
        return (
            self.db.query(UserFeatureVariants)
            .options(
                joinedload(UserFeatureVariants.user),
                joinedload(UserFeatureVariants.variant),
            )
            .filter(UserFeatureVariants.feature_id == feature_pid)
            .all()
        )

    def get_variant_assignments(self, variant_name: str) -> List[UserFeatureVariants]:
        """Get all user assignments for a specific variant"""
        return (
            self.db.query(UserFeatureVariants)
            .options(
                joinedload(UserFeatureVariants.user),
                joinedload(UserFeatureVariants.feature_flag),
            )
            .filter(UserFeatureVariants.variant_name == variant_name)
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
    ) -> UserFeatureVariants:
        """Assign user to a specific variant (create or update)"""
        # Check for existing assignment
        existing = self.get_user_assignment(user_pid=user_pid, feature_pid=feature_pid)

        if existing:
            # Update existing assignment
            existing.variant_name = variant_name
            existing.variant_config = variant_config
            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new assignment
            assignment = UserFeatureVariants(
                user_id=user_pid,
                feature_id=feature_pid,
                variant_name=variant_name,
                variant_config=variant_config,
                organisation_id=organisation_id,
                app_id=app_id,
            )
            self.db.add(assignment)
            self.db.flush()
            self.db.refresh(assignment)
            return assignment

    def remove_user_assignment(self, user_pid: UUIDType, feature_pid: UUIDType) -> bool:
        """Remove user assignment for a feature (fallback to default)"""
        assignment = self.get_user_assignment(
            self.db, user_pid=user_pid, feature_pid=feature_pid
        )
        if assignment:
            self.db.delete(assignment)
            self.db.flush()
            return True
        return False

    def bulk_assign_users(
        self,
        user_pids: List[UUIDType],
        feature_pid: UUIDType,
        variant_name: str,
        variant_config: str,
        organisation_id: str,
        app_id: str,
    ) -> List[UserFeatureVariants]:
        """Bulk assign multiple users to a variant"""
        assignments = []

        for user_pid in user_pids:
            assignment = self.assign_user_variant(
                self.db,
                user_pid=user_pid,
                feature_pid=feature_pid,
                variant_name=variant_name,
                variant_config=variant_config,
                organisation_id=organisation_id,
                app_id=app_id,
            )
            assignments.append(assignment)

        return assignments

    def get_assignment_stats(self, feature_pid: UUIDType) -> Dict[str, Any]:
        """Get assignment statistics for a feature"""
        assignments = self.get_feature_assignments(feature_pid=feature_pid)

        variant_counts = {}
        for assignment in assignments:
            variant_name = assignment.variant.name
            variant_counts[variant_name] = variant_counts.get(variant_name, 0) + 1

        return {
            "total_assignments": len(assignments),
            "variant_breakdown": variant_counts,
            "unique_users": len(set(a.user_id for a in assignments)),
        }
