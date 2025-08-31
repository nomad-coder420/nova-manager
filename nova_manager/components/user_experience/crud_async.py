from typing import List
from uuid import UUID as UUIDType
from nova_manager.components.user_experience.schemas import UserExperienceAssignment
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, func
from sqlalchemy.orm import selectinload
from nova_manager.core.log import logger

from nova_manager.components.user_experience.models import UserExperience


class UserExperienceAsyncCRUD:
    """Async CRUD operations for UserExperience"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_experiences_personalisations(
        self,
        user_id: UUIDType,
        organisation_id: str,
        app_id: str,
        experience_ids: List[UUIDType] | None = None,
    ) -> List[UserExperience]:
        logger.info(f"[DEBUG-DB] Querying for user experiences. User ID: {user_id} (type: {type(user_id)})")
        logger.info(f"[DEBUG-DB] Organisation ID: {organisation_id}, App ID: {app_id}")

        # Build base query with filters
        base_filters = [
            UserExperience.user_id == user_id,
            UserExperience.organisation_id == organisation_id,
            UserExperience.app_id == app_id,
        ]
        if experience_ids:
            logger.info(f"[DEBUG-DB] Filtering by experience IDs: {experience_ids}")
            base_filters.append(UserExperience.experience_id.in_(experience_ids))

        # Use window function to get the latest assignment per experience
        rn = func.row_number().over(
            partition_by=UserExperience.experience_id,
            order_by=UserExperience.assigned_at.desc(),
        ).label("rn")

        # Subquery to get latest IDs
        latest_per_experience_subq = (
            select(UserExperience.pid, rn)
            .where(*base_filters)
            .subquery()
        )

        latest_ids_stmt = select(latest_per_experience_subq.c.pid).where(
            latest_per_experience_subq.c.rn == 1
        )

        # Main query to get the assignments with relationships
        stmt = (
            select(UserExperience)
            .where(UserExperience.pid.in_(latest_ids_stmt))
            .options(selectinload(UserExperience.personalisation))
        )

        result = await self.db.execute(stmt)
        assignments = list(result.scalars().all())

        logger.info(f"[DEBUG-DB] Found {len(assignments)} latest assignments for user {user_id}")
        for assignment in assignments:
            logger.info(f"[DEBUG-DB] Latest assignment: experience={assignment.experience_id}, personalisation={assignment.personalisation_id}, variant={assignment.experience_variant_id}, assigned_at={assignment.assigned_at}")

        return assignments

    async def delete_by_personalisation_id(
        self,
        personalisation_id: UUIDType,
        organisation_id: str,
        app_id: str,
    ) -> int:
        """
        Delete all user experience assignments for a specific personalisation.
        Used when applying personalisation changes to existing users.
        
        Args:
            personalisation_id: The personalisation ID to delete assignments for
            organisation_id: Organisation scope
            app_id: App scope
            
        Returns:
            Number of deleted records
        """
        from sqlalchemy import delete
        
        logger.info(f"[DEBUG-DB] Deleting assignments for personalisation {personalisation_id}")
        
        stmt = delete(UserExperience).where(
            UserExperience.personalisation_id == personalisation_id,
            UserExperience.organisation_id == organisation_id,
            UserExperience.app_id == app_id
        )
        
        try:
            result = await self.db.execute(stmt)
            await self.db.commit()
            deleted_count = result.rowcount
            logger.info(f"[DEBUG-DB] Successfully deleted {deleted_count} user assignments for personalisation {personalisation_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"[DEBUG-DB] Error deleting assignments for personalisation {personalisation_id}: {str(e)}")
            import traceback
            logger.error(f"[DEBUG-DB] Traceback: {traceback.format_exc()}")
            await self.db.rollback()
            raise
    
    async def bulk_create_user_experience_personalisations(
        self,
        user_id: UUIDType,
        organisation_id: str,
        app_id: str,
        personalisation_assignments: List[UserExperienceAssignment],
    ) -> None:
        """
        Bulk create user experience personalisation records.

        Note: This method only handles creates since the caller (flow) only passes
        assignments that need to be created (i.e., not from cache).
        """
        if not personalisation_assignments:
            return

        logger.info(f"[DEBUG-DB] Preparing to insert {len(personalisation_assignments)} new assignments")
        
        # Prepare data for bulk insert
        inserts_data = []
        for assignment in personalisation_assignments:
            if not user_id or not assignment.experience_id:
                logger.warning(f"[DEBUG-DB] Skipping invalid assignment: missing user_id or experience_id")
                continue

            record_data = {
                "user_id": user_id,
                "organisation_id": organisation_id,
                "app_id": app_id,
                "experience_id": assignment.experience_id,
                "personalisation_id": assignment.personalisation_id,
                "personalisation_name": assignment.personalisation_name,
                "experience_variant_id": assignment.experience_variant_id,
                "features": assignment.features,
                "evaluation_reason": assignment.evaluation_reason,
            }
            inserts_data.append(record_data)
            logger.info(f"[DEBUG-DB] Prepared insert for experience {assignment.experience_id}, personalisation: {assignment.personalisation_name}")

        # Single bulk insert - very efficient
        try:
            stmt = insert(UserExperience).values(inserts_data)
            logger.info(f"[DEBUG-DB] Executing insert statement for {len(inserts_data)} records")
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"[DEBUG-DB] Successfully inserted {len(inserts_data)} assignments")
        except Exception as e:
            logger.error(f"[DEBUG-DB] Error during insert: {str(e)}")
            import traceback
            logger.error(f"[DEBUG-DB] Traceback: {traceback.format_exc()}")
            # Re-raise to let caller handle
            raise
