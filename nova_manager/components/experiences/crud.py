from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID as UUIDType
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, desc, asc

from nova_manager.components.experiences.models import Experiences, ExperienceSegments
from nova_manager.components.segments.models import Segments
from nova_manager.core.base_crud import BaseCRUD


class ExperiencesCRUD(BaseCRUD):
    """CRUD operations for Experiences"""

    def __init__(self, db: Session):
        super().__init__(Experiences, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[Experiences]:
        """Get experience by name within organization/app scope"""
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

    def get_active_experiences(
        self, organisation_id: str, app_id: str
    ) -> List[Experiences]:
        """Get all active experiences for an organization/app"""
        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.status == "active",
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
            .order_by(asc(Experiences.priority))
            .all()
        )

    def get_by_priority(
        self, priority: int, organisation_id: str, app_id: str
    ) -> Optional[Experiences]:
        """Get experience by priority within organization/app"""
        return (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.priority == priority,
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
            .first()
        )

    def get_with_segments(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all segments loaded"""
        return (
            self.db.query(Experiences)
            .options(
                selectinload(Experiences.experience_segments).selectinload(
                    ExperienceSegments.segment
                )
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def get_with_feature_variants(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with feature variants loaded"""
        return (
            self.db.query(Experiences)
            .options(
                selectinload(Experiences.feature_variants),
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def get_with_full_details(self, pid: UUIDType) -> Optional[Experiences]:
        """Get experience with all related data loaded"""
        return (
            self.db.query(Experiences)
            .options(
                selectinload(Experiences.experience_segments).selectinload(
                    ExperienceSegments.segment
                ),
                selectinload(Experiences.feature_variants),
                selectinload(Experiences.user_experiences),
            )
            .filter(Experiences.pid == pid)
            .first()
        )

    def create_experience(
        self,
        name: str,
        description: str,
        priority: int,
        status: str,
        organisation_id: str,
        app_id: str,
    ) -> Experiences:
        """Create a new experience"""
        # Check if priority is already taken
        existing_priority = self.get_by_priority(priority, organisation_id, app_id)
        if existing_priority:
            # Shift priorities to make room
            self._shift_priorities_up(priority, organisation_id, app_id)

        experience = Experiences(
            name=name,
            description=description,
            priority=priority,
            status=status,
            organisation_id=organisation_id,
            app_id=app_id,
            last_updated_at=datetime.utcnow(),
        )
        self.db.add(experience)
        self.db.flush()
        self.db.refresh(experience)
        return experience

    def update_priority(
        self, pid: UUIDType, new_priority: int
    ) -> Optional[Experiences]:
        """Update experience priority, handling conflicts"""
        experience = self.get_by_pid(pid)
        if not experience:
            return None

        old_priority = experience.priority
        if old_priority == new_priority:
            return experience

        # Check if new priority is taken
        existing = self.get_by_priority(
            new_priority, experience.organisation_id, experience.app_id
        )
        if existing:
            # Shift priorities to make room
            self._shift_priorities_up(new_priority, experience.organisation_id, experience.app_id)

        experience.priority = new_priority
        experience.last_updated_at = datetime.utcnow()
        self.db.flush()
        self.db.refresh(experience)
        return experience

    def update_status(self, pid: UUIDType, status: str) -> Optional[Experiences]:
        """Update experience status"""
        experience = self.get_by_pid(pid)
        if experience:
            experience.status = status
            experience.last_updated_at = datetime.utcnow()
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
            .order_by(asc(Experiences.priority))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_experiences_by_segment(
        self, segment_id: UUIDType
    ) -> List[Experiences]:
        """Get all experiences that use a specific segment"""
        return (
            self.db.query(Experiences)
            .join(ExperienceSegments, Experiences.pid == ExperienceSegments.experience_id)
            .filter(ExperienceSegments.segment_id == segment_id)
            .order_by(asc(Experiences.priority))
            .all()
        )

    def clone_experience(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_description: Optional[str] = None,
        new_priority: Optional[int] = None,
    ) -> Optional[Experiences]:
        """Clone an existing experience with segments"""
        source = self.get_with_segments(source_pid)
        if not source:
            return None

        # Determine new priority
        if new_priority is None:
            max_priority = (
                self.db.query(Experiences.priority)
                .filter(
                    and_(
                        Experiences.organisation_id == source.organisation_id,
                        Experiences.app_id == source.app_id,
                    )
                )
                .order_by(desc(Experiences.priority))
                .first()
            )
            new_priority = (max_priority[0] + 1) if max_priority else 1

        # Create cloned experience
        cloned_experience = Experiences(
            name=new_name,
            description=new_description or f"Copy of {source.description}",
            priority=new_priority,
            status="draft",  # New cloned experiences start as draft
            organisation_id=source.organisation_id,
            app_id=source.app_id,
            last_updated_at=datetime.utcnow(),
        )
        self.db.add(cloned_experience)
        self.db.flush()
        self.db.refresh(cloned_experience)

        # Clone experience segments
        for exp_seg in source.experience_segments:
            cloned_segment = ExperienceSegments(
                experience_id=cloned_experience.pid,
                segment_id=exp_seg.segment_id,
                target_percentage=exp_seg.target_percentage,
            )
            self.db.add(cloned_segment)

        self.db.flush()
        return cloned_experience

    def _shift_priorities_up(self, from_priority: int, organisation_id: str, app_id: str):
        """Shift all priorities up by 1 starting from the given priority"""
        experiences = (
            self.db.query(Experiences)
            .filter(
                and_(
                    Experiences.priority >= from_priority,
                    Experiences.organisation_id == organisation_id,
                    Experiences.app_id == app_id,
                )
            )
            .order_by(desc(Experiences.priority))
            .all()
        )

        for exp in experiences:
            exp.priority += 1
            exp.last_updated_at = datetime.utcnow()

    def get_experience_stats(self, pid: UUIDType) -> Dict[str, Any]:
        """Get statistics for an experience"""
        experience = self.get_with_full_details(pid)
        if not experience:
            return {}

        return {
            "experience_name": experience.name,
            "status": experience.status,
            "priority": experience.priority,
            "segment_count": len(experience.experience_segments),
            "feature_variant_count": len(experience.feature_variants),
            "user_experience_count": len(experience.user_experiences),
            "created_at": experience.created_at.isoformat(),
            "last_updated_at": experience.last_updated_at.isoformat(),
        }


class ExperienceSegmentsCRUD(BaseCRUD):
    """CRUD operations for ExperienceSegments"""

    def __init__(self, db: Session):
        super().__init__(ExperienceSegments, db)

    def get_by_experience_and_segment(
        self, experience_id: UUIDType, segment_id: UUIDType
    ) -> Optional[ExperienceSegments]:
        """Get experience segment by experience and segment IDs"""
        return (
            self.db.query(ExperienceSegments)
            .filter(
                and_(
                    ExperienceSegments.experience_id == experience_id,
                    ExperienceSegments.segment_id == segment_id,
                )
            )
            .first()
        )

    def get_by_experience(self, experience_id: UUIDType) -> List[ExperienceSegments]:
        """Get all segments for an experience"""
        return (
            self.db.query(ExperienceSegments)
            .options(selectinload(ExperienceSegments.segment))
            .filter(ExperienceSegments.experience_id == experience_id)
            .all()
        )

    def get_by_segment(self, segment_id: UUIDType) -> List[ExperienceSegments]:
        """Get all experiences using a segment"""
        return (
            self.db.query(ExperienceSegments)
            .options(selectinload(ExperienceSegments.experience))
            .filter(ExperienceSegments.segment_id == segment_id)
            .all()
        )

    def add_segment_to_experience(
        self,
        experience_id: UUIDType,
        segment_id: UUIDType,
        target_percentage: int = 100,
    ) -> ExperienceSegments:
        """Add a segment to an experience"""
        # Check if relationship already exists
        existing = self.get_by_experience_and_segment(experience_id, segment_id)
        if existing:
            # Update the existing relationship
            existing.target_percentage = target_percentage
            self.db.flush()
            self.db.refresh(existing)
            return existing

        # Create new relationship
        exp_segment = ExperienceSegments(
            experience_id=experience_id,
            segment_id=segment_id,
            target_percentage=target_percentage,
        )
        self.db.add(exp_segment)
        self.db.flush()
        self.db.refresh(exp_segment)
        return exp_segment

    def remove_segment_from_experience(
        self, experience_id: UUIDType, segment_id: UUIDType
    ) -> bool:
        """Remove a segment from an experience"""
        exp_segment = self.get_by_experience_and_segment(experience_id, segment_id)
        if exp_segment:
            self.db.delete(exp_segment)
            self.db.flush()
            return True
        return False

    def update_target_percentage(
        self, experience_id: UUIDType, segment_id: UUIDType, target_percentage: int
    ) -> Optional[ExperienceSegments]:
        """Update target percentage for an experience segment"""
        exp_segment = self.get_by_experience_and_segment(experience_id, segment_id)
        if exp_segment:
            exp_segment.target_percentage = target_percentage
            self.db.flush()
            self.db.refresh(exp_segment)
        return exp_segment

    def bulk_update_segments(
        self,
        experience_id: UUIDType,
        segment_configs: List[Dict[str, Any]],
    ) -> List[ExperienceSegments]:
        """Bulk update segments for an experience"""
        # Remove existing segments
        existing_segments = self.get_by_experience(experience_id)
        for exp_seg in existing_segments:
            self.db.delete(exp_seg)

        # Add new segments
        new_segments = []
        for config in segment_configs:
            exp_segment = ExperienceSegments(
                experience_id=experience_id,
                segment_id=config["segment_id"],
                target_percentage=config.get("target_percentage", 100),
            )
            self.db.add(exp_segment)
            new_segments.append(exp_segment)

        self.db.flush()
        for exp_seg in new_segments:
            self.db.refresh(exp_seg)

        return new_segments

    def get_segment_usage_in_experience(
        self, segment_id: UUIDType
    ) -> List[Dict[str, Any]]:
        """Get detailed usage of a segment across experiences"""
        usage = (
            self.db.query(ExperienceSegments)
            .options(selectinload(ExperienceSegments.experience))
            .filter(ExperienceSegments.segment_id == segment_id)
            .all()
        )

        return [
            {
                "experience_id": exp_seg.experience_id,
                "experience_name": exp_seg.experience.name if exp_seg.experience else "Unknown",
                "experience_status": exp_seg.experience.status if exp_seg.experience else "Unknown",
                "target_percentage": exp_seg.target_percentage,
                "created_at": exp_seg.created_at.isoformat(),
            }
            for exp_seg in usage
        ]
