from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from nova_manager.api.experiences.request_response import PersonalisationCreate
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc

from nova_manager.components.experiences.models import (
    Experiences,
    ExperienceSegments,
    Personalisations,
    PersonalisationFeatureVariants,
    ExperienceSegmentPersonalisations,
)
from nova_manager.components.feature_flags.models import FeatureFlags, FeatureVariants
from nova_manager.components.feature_flags.crud import FeatureVariantsCRUD
from nova_manager.core.base_crud import BaseCRUD


class ExperiencesCRUD(BaseCRUD):
    """CRUD operations for Experiences"""

    def __init__(self, db: Session):
        super().__init__(Experiences, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[Experiences]:
        """Get experience by name within an organization and app"""
        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.name == name,
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
            .first()
        )

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[Experiences]:
        """Get experiences for organization/app with pagination and filtering"""
        query = self.db.query(Experiences).filter(
            and_(
                Experiences.organisation_id == organisation_id,
                Experiences.app_id == app_id,
            )
        )

        # Filter by status if provided
        if status:
            query = query.filter(Experiences.status == status)

        # Apply ordering
        order_column = getattr(Experiences, order_by, Experiences.created_at)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.offset(skip).limit(limit).all()

    def get_with_full_details(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all related data loaded"""
        return (
            self.db.query(Experiences)
            .options(
                # Load feature flags with their variants
                selectinload(Experiences.feature_flags).selectinload(
                    FeatureFlags.variants
                ),
                # Load personalisations with their feature variants through junction table
                selectinload(Experiences.personalisations)
                .selectinload(Personalisations.feature_variants)
                .selectinload(PersonalisationFeatureVariants.feature_variant),
                # Load experience segments with their segments and personalisations
                selectinload(Experiences.experience_segments).selectinload(
                    ExperienceSegments.segment
                ),
                # Load experience segments with their personalisations
                selectinload(Experiences.experience_segments).selectinload(
                    ExperienceSegments.personalisations
                ),
                # Load user experiences
                selectinload(Experiences.user_experiences),
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def update_status(self, pid: UUIDType, status: str) -> Optional[Experiences]:
        """Update experience status"""
        experience = self.get_by_pid(pid)

        if experience:
            experience.status = status
            self.db.flush()
            self.db.refresh(experience)

        return experience

    def search_experiences(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Experiences]:
        """Search experiences by name or description"""
        search_pattern = f"%{search_term}%"

        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                    or_(
                        Experiences.name.ilike(search_pattern),
                        Experiences.description.ilike(search_pattern),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def clone_experience(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_description: Optional[str] = None,
    ) -> Optional[Experiences]:
        """Clone an existing experience"""
        source = self.get_with_full_details(source_pid)
        if not source:
            return None

        # Create cloned experience
        cloned_experience = Experiences(
            name=new_name,
            description=new_description or f"Copy of {source.description}",
            status="draft",  # New cloned experiences start as draft
            organisation_id=source.organisation_id,
            app_id=source.app_id,
        )
        self.db.add(cloned_experience)
        self.db.flush()
        self.db.refresh(cloned_experience)

        # TODO: Clone experience segments, personalisations, etc.

        self.db.flush()
        return cloned_experience

    def delete_by_pid(self, pid: UUIDType) -> bool:
        """Delete experience and all related data"""
        experience = self.get_by_pid(pid)
        if not experience:
            return False

        self.db.delete(experience)
        self.db.flush()
        return True

    def get_experience_segments(
        self, experience_id: UUIDType
    ) -> List[ExperienceSegments]:
        """Get all experience segments for an experience"""
        return (
            self.db.query(ExperienceSegments)
            .filter(ExperienceSegments.experience_id == experience_id)
            .order_by(ExperienceSegments.priority)
            .all()
        )

    def count_experience_segments(self, experience_id: UUIDType) -> int:
        """Count experience segments for a given experience"""
        return (
            self.db.query(ExperienceSegments)
            .filter(ExperienceSegments.experience_id == experience_id)
            .count()
        )

    def create_experience_segment(
        self, segment_data: Dict[str, Any]
    ) -> ExperienceSegments:
        """Create a new experience segment"""
        experience_segment = ExperienceSegments(
            experience_id=segment_data["experience_id"],
            segment_id=segment_data["segment_id"],
            target_percentage=segment_data.get("target_percentage", 100),
            priority=segment_data.get("priority", 0),
        )
        self.db.add(experience_segment)
        self.db.flush()
        self.db.refresh(experience_segment)
        return experience_segment

    def create_experience_segment_personalisation(
        self, personalisation_data: Dict[str, Any]
    ) -> ExperienceSegmentPersonalisations:
        """Create a new experience segment personalisation"""
        experience_segment_personalisation = ExperienceSegmentPersonalisations(
            experience_segment_id=personalisation_data["experience_segment_id"],
            personalisation_id=personalisation_data["personalisation_id"],
            target_percentage=personalisation_data.get("target_percentage", 100),
        )
        self.db.add(experience_segment_personalisation)
        self.db.flush()
        self.db.refresh(experience_segment_personalisation)
        return experience_segment_personalisation


class PersonalisationsCRUD(BaseCRUD):
    """CRUD operations for Personalisations"""

    def __init__(self, db: Session):
        super().__init__(Personalisations, db)

    def get_by_name(
        self, name: str, experience_id: UUIDType
    ) -> Optional[Personalisations]:
        """Get personalisation by name within an experience"""
        return (
            self.db.query(Personalisations)
            .filter(
                and_(
                    Personalisations.name == name,
                    Personalisations.experience_id == experience_id,
                )
            )
            .first()
        )

    def get_by_experience(
        self, experience_id: UUIDType, skip: int = 0, limit: int = 100
    ) -> List[Personalisations]:
        """Get personalisations for a specific experience"""
        return (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .options(
                selectinload(Personalisations.feature_variants).selectinload(
                    PersonalisationFeatureVariants.feature_variant
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_variants(self, pid: UUIDType) -> Optional[Personalisations]:
        """Get personalisation with all its variants"""
        return (
            self.db.query(Personalisations)
            .options(
                selectinload(Personalisations.feature_variants).selectinload(
                    PersonalisationFeatureVariants.feature_variant
                )
            )
            .filter(Personalisations.pid == pid)
            .first()
        )

    def get_default_personalisations_by_ids(
        self, personalisation_ids: List[UUIDType]
    ) -> List[Personalisations]:
        """Get personalisations by IDs that are marked as default"""
        return (
            self.db.query(Personalisations)
            .filter(
                and_(
                    Personalisations.pid.in_(personalisation_ids),
                    Personalisations.is_default == True,
                )
            )
            .all()
        )

    def create_personalisation_with_variants(
        self, personalisation_data: PersonalisationCreate
    ) -> Personalisations:
        """Create a personalisation with its variants"""
        # Create personalisation
        personalisation = Personalisations(
            name=personalisation_data.name,
            description=personalisation_data.description or "",
            experience_id=personalisation_data.experience_id or "",
            last_updated_at=datetime.now(timezone.utc),
        )
        self.db.add(personalisation)
        self.db.flush()
        self.db.refresh(personalisation)

        # Initialize feature variants CRUD
        feature_variants_crud = FeatureVariantsCRUD(self.db)

        # Handle variants - either create new or use existing
        for variant_data in personalisation_data.variants:
            variant = None

            # Check if variant_id is provided (selecting existing variant)
            if variant_data.variant_id:
                variant = feature_variants_crud.get_by_pid(variant_data.variant_id)
                if not variant:
                    raise ValueError(
                        f"Variant with ID {variant_data.variant_id} not found"
                    )
            else:
                # Create new variant
                feature_variants_crud = FeatureVariantsCRUD(self.db)
                variant = feature_variants_crud.create_variant(
                    feature_pid=variant_data.feature_id,
                    variant_data=variant_data.model_dump(
                        exclude={"feature_id", "variant_id"}
                    ),
                )

            # Create junction table entry
            junction_entry = PersonalisationFeatureVariants(
                personalisation_id=personalisation.pid,
                feature_variant_id=variant.pid,
            )
            self.db.add(junction_entry)

        self.db.flush()
        return personalisation

    def update_personalisation_with_variants(
        self,
        pid: UUIDType,
        personalisation_data: Dict[str, Any],
        variants_data: List[Dict[str, Any]],
    ) -> Optional[Personalisations]:
        """Update a personalisation and its variants using ManyToMany relationship"""
        personalisation = self.get_by_pid(pid)
        if not personalisation:
            return None

        # Update personalisation
        personalisation.name = personalisation_data.get("name", personalisation.name)
        personalisation.description = personalisation_data.get(
            "description", personalisation.description
        )
        personalisation.last_updated_at = datetime.now(timezone.utc)

        # Delete existing junction table entries
        self.db.query(PersonalisationFeatureVariants).filter(
            PersonalisationFeatureVariants.personalisation_id == pid
        ).delete()

        # Initialize feature variants CRUD
        feature_variants_crud = FeatureVariantsCRUD(self.db)

        # Handle variants - either create new or use existing
        for variant_data in variants_data:
            variant = None

            # Check if variant_id is provided (selecting existing variant)
            if "variant_id" in variant_data and variant_data["variant_id"]:
                variant = feature_variants_crud.get_by_pid(variant_data["variant_id"])
                if not variant:
                    raise ValueError(
                        f"Variant with ID {variant_data['variant_id']} not found"
                    )
            else:
                # Create new variant
                variant = FeatureVariants(
                    feature_id=variant_data["feature_id"],
                    name=variant_data["name"],
                    config=variant_data["config"],
                )
                self.db.add(variant)
                self.db.flush()
                self.db.refresh(variant)

            # Create junction table entry
            junction_entry = PersonalisationFeatureVariants(
                personalisation_id=personalisation.pid,
                feature_variant_id=variant.pid,
            )
            self.db.add(junction_entry)

        self.db.flush()
        self.db.refresh(personalisation)
        return personalisation

    def delete_personalisation_with_variants(self, pid: UUIDType) -> bool:
        """Delete a personalisation and all its variants"""
        personalisation = self.get_by_pid(pid)
        if not personalisation:
            return False

        # Delete junction table entries first
        self.db.query(PersonalisationFeatureVariants).filter(
            PersonalisationFeatureVariants.personalisation_id == pid
        ).delete()

        # Delete personalisation
        self.db.delete(personalisation)
        self.db.flush()
        return True

    def create_default_personalisation(
        self, experience_id: UUIDType
    ) -> Personalisations:
        """Create a default personalisation with all default variants for an experience"""
        from nova_manager.components.feature_flags.crud import FeatureVariantsCRUD

        # Get experience to find its feature flags
        experience = (
            self.db.query(Experiences).filter(Experiences.pid == experience_id).first()
        )
        if not experience:
            raise ValueError("Experience not found")

        # Generate unique name
        # Get all existing personalisation names in this experience
        existing_names = set()
        existing_personalisations = (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .all()
        )

        for personalisation in existing_personalisations:
            existing_names.add(personalisation.name.lower())

        # Find the next available default personalisation number
        counter = 1
        while True:
            candidate_name = f"Default Experience {counter}"
            if candidate_name.lower() not in existing_names:
                name = candidate_name
                break
            counter += 1

        # Generate description
        description = "Auto-generated default experience"

        # Create personalisation
        personalisation = Personalisations(
            name=name,
            description=description,
            experience_id=experience_id,
            is_default=True,
            last_updated_at=datetime.now(timezone.utc),
        )
        self.db.add(personalisation)
        self.db.flush()
        self.db.refresh(personalisation)

        # Create variants with default values for each feature flag
        feature_variants_crud = FeatureVariantsCRUD(self.db)

        for feature_flag in experience.feature_flags:
            # Find or create default variant for this feature flag
            default_variant = feature_variants_crud.get_by_name(
                name="default", feature_pid=feature_flag.pid
            )

            if default_variant:
                # Create junction table entry
                junction_entry = PersonalisationFeatureVariants(
                    personalisation_id=personalisation.pid,
                    feature_variant_id=default_variant.pid,
                )
                self.db.add(junction_entry)

        self.db.flush()
        return personalisation

    def count_by_experience(self, experience_id: UUIDType) -> int:
        """Count personalisations for a specific experience"""
        return (
            self.db.query(Personalisations)
            .filter(Personalisations.experience_id == experience_id)
            .count()
        )
