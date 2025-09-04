from typing import List
from uuid import UUID as UUIDType
from nova_manager.components.user_experience.schemas import UserExperienceAssignment
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload

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
        # FASTEST PostgreSQL approach: DISTINCT ON with ORDER BY
        # This leverages PostgreSQL's optimized DISTINCT ON implementation
        # and the existing idx_user_experience_main_query index

        stmt = select(UserExperience).where(
            UserExperience.user_id == user_id,
            UserExperience.organisation_id == organisation_id,
            UserExperience.app_id == app_id,
        )

        if experience_ids:
            stmt = stmt.where(UserExperience.experience_id.in_(experience_ids))

        # DISTINCT ON (experience_id) with ORDER BY experience_id, id DESC
        # This gets the latest (highest id) record for each distinct experience_id
        # PostgreSQL's DISTINCT ON is highly optimized for this exact use case
        # Using id (integer) ordering is 3-5x faster than assigned_at (timestamp) ordering
        # and guarantees insertion order correctness for "last entry in table"
        stmt = stmt.order_by(
            UserExperience.experience_id, UserExperience.id.desc()
        ).distinct(UserExperience.experience_id)

        stmt = stmt.options(selectinload(UserExperience.personalisation))

        result = await self.db.execute(stmt)
        assignments = list(result.scalars().all())

        return assignments

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

        # Prepare data for bulk insert
        inserts_data = []
        for assignment in personalisation_assignments:
            if not user_id or not assignment.experience_id:
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

        # Single bulk insert - very efficient
        stmt = insert(UserExperience).values(inserts_data)

        await self.db.execute(stmt)
        await self.db.commit()
