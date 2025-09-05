from nova_manager.components.personalisations.models import PersonalisationSegmentRules
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType

from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.segments.models import Segments


class SegmentsCRUD(BaseCRUD):
    """CRUD operations for Segments"""

    def __init__(self, db: Session):
        super().__init__(Segments, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[Segments]:
        """Get segment by name within organization/app"""
        return (
            self.db.query(Segments)
            .filter(
                and_(
                    Segments.name == name,
                    Segments.organisation_id == organisation_id,
                    Segments.app_id == app_id,
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
    ) -> List[Segments]:
        """Get segments for organization/app with pagination"""
        return (
            self.db.query(Segments)
            .filter(
                and_(
                    Segments.organisation_id == organisation_id,
                    Segments.app_id == app_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_segment(
        self,
        name: str,
        description: str,
        rule_config: Dict[str, Any],
        organisation_id: str,
        app_id: str,
    ) -> Segments:
        """Create a new segment"""
        segment = Segments(
            name=name,
            description=description,
            rule_config=rule_config,
            organisation_id=organisation_id,
            app_id=app_id,
        )
        self.db.add(segment)
        self.db.flush()
        self.db.refresh(segment)
        return segment

    def update_rule_config(
        self, pid: UUIDType, rule_config: Dict[str, Any]
    ) -> Optional[Segments]:
        """Update segment rule configuration"""
        segment = self.get_by_pid(pid)
        if segment:
            segment.rule_config = rule_config
            flag_modified(segment, "rule_config")

            self.db.flush()
            self.db.refresh(segment)
        return segment

    def search_segments(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Segments]:
        """Search segments by name or description"""
        search_pattern = f"%{search_term}%"
        return (
            self.db.query(Segments)
            .filter(
                and_(
                    Segments.organisation_id == organisation_id,
                    Segments.app_id == app_id,
                    or_(
                        Segments.name.ilike(search_pattern),
                        Segments.description.ilike(search_pattern),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def clone_segment(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_description: Optional[str] = None,
    ) -> Optional[Segments]:
        """Clone an existing segment with a new name"""
        source = self.get_by_pid(source_pid)
        if not source:
            return None

        cloned_segment = Segments(
            name=new_name,
            description=new_description or f"Copy of {source.description}",
            rule_config=source.rule_config.copy(),
            organisation_id=source.organisation_id,
            app_id=source.app_id,
        )
        self.db.add(cloned_segment)
        self.db.flush()
        self.db.refresh(cloned_segment)
        return cloned_segment

    def get_with_full_details(self, pid: UUIDType) -> Optional[Segments]:
        """Get segment with full details"""
        return (
            self.db.query(Segments)
            .options(
                selectinload(Segments.personalisations).selectinload(
                    PersonalisationSegmentRules.personalisation
                )
            )
            .filter(Segments.pid == pid)
            .first()
        )
