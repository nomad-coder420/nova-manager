from typing import List
from uuid import UUID as UUIDType
from nova_manager.components.user_experience.crud_async import PersonalisationAssignment
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import insert

from nova_manager.components.user_experience.models import (
    UserExperiencePersonalisation,
)
from nova_manager.core.base_crud import BaseCRUD


class UserExperiencePersonalisationCRUD(BaseCRUD):
    """CRUD operations for UserExperiencePersonalisation"""

    def __init__(self, db: Session):
        super().__init__(UserExperiencePersonalisation, db)

    def get_user_experiences_personalisations(
        self,
        user_id: UUIDType,
        organisation_id: str,
        app_id: str,
        experience_ids: List[UUIDType],
    ):
        return (
            self.db.query(UserExperiencePersonalisation)
            .filter(
                UserExperiencePersonalisation.user_id == user_id,
                UserExperiencePersonalisation.organisation_id == organisation_id,
                UserExperiencePersonalisation.app_id == app_id,
                UserExperiencePersonalisation.experience_id.in_(experience_ids),
            )
            .options(
                selectinload(UserExperiencePersonalisation.personalisation),
            )
            .all()
        )

    def bulk_create_user_experience_personalisations(
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
        self.db.execute(stmt)
        self.db.flush()
