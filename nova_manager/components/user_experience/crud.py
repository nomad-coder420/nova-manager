from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from datetime import datetime

from nova_manager.components.user_experience.models import (
    UserFeatureVariants,
    UserExperience,
)
from nova_manager.core.base_crud import BaseCRUD


class UserExperienceCRUD(BaseCRUD):
    """CRUD operations for UserExperience"""

    def __init__(self, db: Session):
        super().__init__(UserExperience, db)

    def get_user_experiences(
        self, user_pid: UUIDType, organisation_id: str, app_id: str
    ) -> List[UserExperience]:
        """Get all experiences assigned to a user"""
        return (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id == user_pid,
                    UserExperience.organisation_id == organisation_id,
                    UserExperience.app_id == app_id,
                )
            )
            .all()
        )

    def is_user_in_experience(
        self, user_pid: UUIDType, experience_pid: UUIDType
    ) -> bool:
        """Check if user is assigned to an experience"""
        return (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id == user_pid,
                    UserExperience.experience_id == experience_pid,
                )
            )
            .first()
        ) is not None

    def assign_user_to_experience(
        self,
        user_pid: UUIDType,
        experience_pid: UUIDType,
        organisation_id: str,
        app_id: str,
    ) -> UserExperience:
        """Assign user to an experience"""
        # Check if assignment already exists
        existing = (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id == user_pid,
                    UserExperience.experience_id == experience_pid,
                )
            )
            .first()
        )

        if existing:
            return existing

        # Create new assignment
        assignment = UserExperience(
            user_id=user_pid,
            experience_id=experience_pid,
            organisation_id=organisation_id,
            app_id=app_id,
            assigned_at=datetime.utcnow(),
        )
        self.db.add(assignment)
        self.db.flush()
        self.db.refresh(assignment)
        return assignment

    def bulk_assign_users_to_experience(
        self,
        user_pids: List[UUIDType],
        experience_pid: UUIDType,
        organisation_id: str,
        app_id: str,
    ) -> List[UserExperience]:
        """Bulk assign multiple users to an experience"""
        # Check existing assignments
        existing_assignments = (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id.in_(user_pids),
                    UserExperience.experience_id == experience_pid,
                )
            )
            .all()
        )

        existing_user_ids = {assignment.user_id for assignment in existing_assignments}
        new_user_ids = [uid for uid in user_pids if uid not in existing_user_ids]

        # Create new assignments
        new_assignments = []
        for user_pid in new_user_ids:
            assignment = UserExperience(
                user_id=user_pid,
                experience_id=experience_pid,
                organisation_id=organisation_id,
                app_id=app_id,
                assigned_at=datetime.utcnow(),
            )
            new_assignments.append(assignment)

        if new_assignments:
            self.db.add_all(new_assignments)
            self.db.flush()
            for assignment in new_assignments:
                self.db.refresh(assignment)

        return existing_assignments + new_assignments

    def remove_user_from_experience(
        self, user_pid: UUIDType, experience_pid: UUIDType
    ) -> bool:
        """Remove user from an experience"""
        assignment = (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id == user_pid,
                    UserExperience.experience_id == experience_pid,
                )
            )
            .first()
        )

        if assignment:
            self.db.delete(assignment)
            self.db.flush()
            return True
        return False

    def get_experience_users(
        self, experience_pid: UUIDType, skip: int = 0, limit: int = 100
    ) -> List[UserExperience]:
        """Get all users assigned to an experience"""
        return (
            self.db.query(UserExperience)
            .filter(UserExperience.experience_id == experience_pid)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_experience_user_count(self, experience_pid: UUIDType) -> int:
        """Get count of users assigned to an experience"""
        return (
            self.db.query(UserExperience)
            .filter(UserExperience.experience_id == experience_pid)
            .count()
        )

    def bulk_get_user_experiences(
        self, user_pids: List[UUIDType], organisation_id: str, app_id: str
    ) -> Dict[UUIDType, List[UserExperience]]:
        """Bulk get experiences for multiple users"""
        assignments = (
            self.db.query(UserExperience)
            .filter(
                and_(
                    UserExperience.user_id.in_(user_pids),
                    UserExperience.organisation_id == organisation_id,
                    UserExperience.app_id == app_id,
                )
            )
            .all()
        )

        # Group by user_id
        user_experiences = {}
        for assignment in assignments:
            if assignment.user_id not in user_experiences:
                user_experiences[assignment.user_id] = []
            user_experiences[assignment.user_id].append(assignment)

        return user_experiences


class UserFeatureVariantsCRUD(BaseCRUD):
    """CRUD operations for UserFeatureVariants"""

    def __init__(self, db: Session):
        super().__init__(UserFeatureVariants, db)

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
        existing = (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.user_id == user_pid,
                    UserFeatureVariants.feature_id == feature_pid,
                )
            )
            .first()
        )

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

    def bulk_assign_user_variants(
        self, assignments: List[Dict[str, Any]]
    ) -> List[UserFeatureVariants]:
        """Bulk assign variants to users"""
        results = []

        for assignment_data in assignments:
            assignment = self.assign_user_variant(
                user_pid=assignment_data["user_pid"],
                feature_pid=assignment_data["feature_pid"],
                variant_name=assignment_data["variant_name"],
                variant_config=assignment_data["variant_config"],
                organisation_id=assignment_data["organisation_id"],
                app_id=assignment_data["app_id"],
                experience_id=assignment_data.get("experience_id"),
            )
            results.append(assignment)

        return results

    def bulk_get_user_assignments(
        self, user_pids: List[UUIDType], organisation_id: str, app_id: str
    ) -> Dict[UUIDType, List[UserFeatureVariants]]:
        """Bulk get variant assignments for multiple users"""
        assignments = (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.user_id.in_(user_pids),
                    UserFeatureVariants.organisation_id == organisation_id,
                    UserFeatureVariants.app_id == app_id,
                )
            )
            .all()
        )

        # Group by user_id
        user_assignments = {}
        for assignment in assignments:
            if assignment.user_id not in user_assignments:
                user_assignments[assignment.user_id] = []
            user_assignments[assignment.user_id].append(assignment)

        return user_assignments

    def get_assignments_by_experience(
        self, experience_pid: UUIDType, skip: int = 0, limit: int = 100
    ) -> List[UserFeatureVariants]:
        """Get all variant assignments for a specific experience"""
        return (
            self.db.query(UserFeatureVariants)
            .filter(UserFeatureVariants.experience_id == experience_pid)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_assignments_by_experience(self, experience_pid: UUIDType) -> int:
        """Count variant assignments for a specific experience"""
        return (
            self.db.query(UserFeatureVariants)
            .filter(UserFeatureVariants.experience_id == experience_pid)
            .count()
        )

    def get_feature_assignment_stats(
        self, feature_pid: UUIDType, organisation_id: str, app_id: str
    ) -> Dict[str, Any]:
        """Get assignment statistics for a feature"""
        assignments = (
            self.db.query(UserFeatureVariants)
            .filter(
                and_(
                    UserFeatureVariants.feature_id == feature_pid,
                    UserFeatureVariants.organisation_id == organisation_id,
                    UserFeatureVariants.app_id == app_id,
                )
            )
            .all()
        )

        total_assignments = len(assignments)
        variant_counts = {}
        experience_counts = {}

        for assignment in assignments:
            # Count by variant
            if assignment.variant_name not in variant_counts:
                variant_counts[assignment.variant_name] = 0
            variant_counts[assignment.variant_name] += 1

            # Count by experience
            if assignment.experience_id:
                if assignment.experience_id not in experience_counts:
                    experience_counts[assignment.experience_id] = 0
                experience_counts[assignment.experience_id] += 1

        return {
            "total_assignments": total_assignments,
            "variant_distribution": variant_counts,
            "experience_distribution": experience_counts,
        }
