from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from nova_manager.components.feature_flags.models import FeatureFlags, FeatureVariants
from nova_manager.components.experiences.models import (
    Experiences,
    ExperienceSegments,
    Personalisations,
    PersonalisationFeatureVariants,
)


class FeatureFlagsAsyncCRUD:
    """Async CRUD operations for FeatureFlags"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_flags_with_full_experience_data(
        self,
        organisation_id: str,
        app_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> List[FeatureFlags]:
        """
        Get feature flags with all related experience data loaded in a single query.
        Loads complete evaluation chain:
        - FeatureFlags.variants (for feature flag variants)
        - FeatureFlags.experience (experience details)
        - Experience.experience_segments + ExperienceSegments.segment (segments with rules)
        - ExperienceSegments.personalisations -> ExperienceSegmentPersonalisations.personalisation (segment assignments)
        - Personalisations.feature_variants -> PersonalisationFeatureVariants.feature_variant (personalisation variants)
        - Experience.personalisations (direct personalisation access for evaluation)
        """
        stmt = select(FeatureFlags).where(
            and_(
                FeatureFlags.organisation_id == organisation_id,
                FeatureFlags.app_id == app_id,
                FeatureFlags.is_active == True,
            )
        )

        # Filter by feature names if provided
        if feature_names:
            stmt = stmt.where(FeatureFlags.name.in_(feature_names))

        # Load all related data in a single query
        stmt = stmt.options(
            # Load feature variants directly on the feature flag
            selectinload(FeatureFlags.variants),
            # Load experience
            selectinload(FeatureFlags.experience),
            # Load experience segments with their segments (ordered by priority)
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.experience_segments)
            .selectinload(ExperienceSegments.segment),
            # Load experience segment personalisations
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.experience_segments)
            .selectinload(ExperienceSegments.personalisations),
            # Also load personalisations directly from experience
            selectinload(FeatureFlags.experience)
            .selectinload(Experiences.personalisations)
            .selectinload(Personalisations.feature_variants)
            .selectinload(PersonalisationFeatureVariants.feature_variant)
            .selectinload(FeatureVariants.feature_flag),
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())
