from typing import List
from uuid import UUID as UUIDType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload

from nova_manager.components.user_experience.models import UserExperiencePersonalisation


class PersonalisationAssignment:
    """Data structure for personalisation assignments"""

    def __init__(
        self,
        experience_id: UUIDType,
        personalisation_id: UUIDType | None,
        segment_id: UUIDType | None,
        segment_name: str | None,
        experience_segment_id: UUIDType | None,
        experience_segment_personalisation_id: UUIDType | None,
        evaluation_reason: str,
    ):
        self.experience_id = experience_id
        self.personalisation_id = personalisation_id
        self.segment_id = segment_id
        self.segment_name = segment_name
        self.experience_segment_id = experience_segment_id
        self.experience_segment_personalisation_id = (
            experience_segment_personalisation_id
        )
        self.evaluation_reason = evaluation_reason


class UserExperiencePersonalisationAsyncCRUD:
    """Async CRUD operations for UserExperiencePersonalisation"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_experiences_personalisations(
        self,
        user_id: UUIDType,
        organisation_id: str,
        app_id: str,
        experience_ids: List[UUIDType],
    ) -> List[UserExperiencePersonalisation]:
        stmt = (
            select(UserExperiencePersonalisation)
            .where(
                UserExperiencePersonalisation.user_id == user_id,
                UserExperiencePersonalisation.organisation_id == organisation_id,
                UserExperiencePersonalisation.app_id == app_id,
                UserExperiencePersonalisation.experience_id.in_(experience_ids),
            )
            .options(
                selectinload(UserExperiencePersonalisation.personalisation),
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def bulk_create_user_experience_personalisations(
        self,
        user_id: UUIDType,
        organisation_id: str,
        app_id: str,
        personalisation_assignments: List[PersonalisationAssignment],
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
                "segment_id": assignment.segment_id,
                "segment_name": assignment.segment_name,
                "experience_segment_id": assignment.experience_segment_id,
                "experience_segment_personalisation_id": (
                    assignment.experience_segment_personalisation_id
                ),
                "evaluation_reason": assignment.evaluation_reason,
            }
            inserts_data.append(record_data)

        # Single bulk insert - very efficient
        stmt = insert(UserExperiencePersonalisation).values(inserts_data)

        await self.db.execute(stmt)
        await self.db.commit()
