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
        stmt = select(UserExperience).where(
            UserExperience.user_id == user_id,
            UserExperience.organisation_id == organisation_id,
            UserExperience.app_id == app_id,
        )

        if experience_ids:
            stmt = stmt.where(
                UserExperience.experience_id.in_(experience_ids),
            )

        stmt = stmt.options(selectinload(UserExperience.personalisation))

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

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
                "feature_variants": assignment.feature_variants,
                "evaluation_reason": assignment.evaluation_reason,
            }
            inserts_data.append(record_data)

        # Single bulk insert - very efficient
        stmt = insert(UserExperience).values(inserts_data)

        await self.db.execute(stmt)
        await self.db.commit()
