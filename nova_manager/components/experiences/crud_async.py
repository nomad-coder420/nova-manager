from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_manager.components.experiences.models import (
    Experiences,
    ExperienceFeatures,
    ExperienceVariants,
)
from nova_manager.components.personalisations.models import (
    PersonalisationExperienceVariants,
    Personalisations,
)
from sqlalchemy.orm import selectinload


class ExperiencesAsyncCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_experiences_by_names(
        self,
        organisation_id: str,
        app_id: str,
        experience_names: list[str] | None = None,
    ) -> list[Experiences]:
        stmt = select(Experiences).where(
            and_(
                Experiences.organisation_id == organisation_id,
                Experiences.app_id == app_id,
            )
        )

        if experience_names:
            stmt = stmt.where(Experiences.name.in_(experience_names))

        stmt = stmt.options(
            # Load default feature flags
            selectinload(Experiences.features).selectinload(
                ExperienceFeatures.feature_flag
            ),
            # Load experience personalisations and experience / feature variants
            selectinload(Experiences.personalisations)
            .selectinload(Personalisations.experience_variants)
            .selectinload(PersonalisationExperienceVariants.experience_variant)
            .selectinload(ExperienceVariants.feature_variants),
            # Load personalisation segment rules
            selectinload(Experiences.personalisations).selectinload(
                Personalisations.segment_rules
            ),
        )

        result = await self.db.execute(stmt)

        return result.scalars().all()
