from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType

from nova_manager.components.experiences.models import ExperienceSegments, Experiences
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
        self.db.commit()
        self.db.refresh(segment)
        return segment

    def update_rule_config(
        self, pid: UUIDType, rule_config: Dict[str, Any]
    ) -> Optional[Segments]:
        """Update segment rule configuration"""
        segment = self.get_by_pid(pid)
        if segment:
            segment.rule_config = rule_config
            self.db.commit()
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

    def get_segments_with_experiences(
        self, organisation_id: str, app_id: str
    ) -> List[Segments]:
        """Get segments that are used in experiences"""
        return (
            self.db.query(Segments)
            .join(ExperienceSegments, Segments.pid == ExperienceSegments.segment_id)
            .filter(
                and_(
                    Segments.organisation_id == organisation_id,
                    Segments.app_id == app_id,
                )
            )
            .distinct()
            .all()
        )

    def get_segment_usage_stats(self, pid: UUIDType) -> Dict[str, Any]:
        """Get usage statistics for a segment"""
        segment = self.get_by_pid(pid)
        if not segment:
            return {}

        # Count experiences using this segment
        experience_count = (
            self.db.query(ExperienceSegments)
            .filter(ExperienceSegments.segment_id == pid)
            .count()
        )

        # Get active experiences using this segment
        active_experiences = (
            self.db.query(Experiences)
            .join(
                ExperienceSegments, Experiences.pid == ExperienceSegments.experience_id
            )
            .filter(
                and_(
                    ExperienceSegments.segment_id == pid, Experiences.status == "active"
                )
            )
            .count()
        )

        return {
            "segment_name": segment.name,
            "experience_count": experience_count,
            "active_experiences": active_experiences,
            "rule_config": segment.rule_config,
        }

    def validate_rule_config(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate segment rule configuration"""
        # TODO: Fix this
        return {"valid": True, "errors": [], "warnings": []}
        errors = []
        warnings = []

        if not rule_config:
            errors.append("Rule configuration cannot be empty")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check for required fields in rule config
        if "conditions" not in rule_config:
            errors.append("Rule configuration must contain 'conditions'")

        # Validate conditions structure
        if "conditions" in rule_config:
            conditions = rule_config["conditions"]
            if not isinstance(conditions, list):
                errors.append("Conditions must be a list")
            else:
                for i, condition in enumerate(conditions):
                    if not isinstance(condition, dict):
                        errors.append(f"Condition {i} must be an object")
                        continue

                    required_fields = ["field", "operator", "value"]
                    for field in required_fields:
                        if field not in condition:
                            errors.append(
                                f"Condition {i} missing required field: {field}"
                            )

                    # Validate operator
                    valid_operators = [
                        "equals",
                        "not_equals",
                        "greater_than",
                        "less_than",
                        "greater_than_or_equal",
                        "less_than_or_equal",
                        "in",
                        "not_in",
                        "contains",
                        "starts_with",
                        "ends_with",
                    ]
                    if (
                        "operator" in condition
                        and condition["operator"] not in valid_operators
                    ):
                        warnings.append(
                            f"Condition {i} uses unknown operator: {condition['operator']}"
                        )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

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
        self.db.commit()
        self.db.refresh(cloned_segment)
        return cloned_segment

    def get_with_experience_segments(self, pid: UUIDType) -> Optional[Segments]:
        """Get segment with experience segments loaded"""
        return (
            self.db.query(Segments)
            .options(
                selectinload(Segments.experience_segments).selectinload(
                    ExperienceSegments.experience
                )
            )
            .filter(Segments.pid == pid)
            .first()
        )

    def get_segment_with_details(self, pid: UUIDType) -> Optional[Dict[str, Any]]:
        """Get segment with full details including experience relationships"""
        segment = self.get_with_experience_segments(pid=pid)
        if not segment:
            return None

        # Transform experience_segments for response
        experience_segments_data = []
        active_experiences = 0

        for exp_seg in segment.experience_segments:
            experience_data = {
                "pid": exp_seg.pid,
                "experience_id": exp_seg.experience_id,
                "name": exp_seg.experience.name if exp_seg.experience else "Unknown",
                "status": (
                    exp_seg.experience.status if exp_seg.experience else "Unknown"
                ),
                "target_percentage": exp_seg.target_percentage,
                "created_at": exp_seg.created_at.isoformat(),
            }
            experience_segments_data.append(experience_data)

            # Count active experiences
            if exp_seg.experience and exp_seg.experience.status == "active":
                active_experiences += 1

        return {
            "pid": segment.pid,
            "name": segment.name,
            "description": segment.description,
            "rule_config": segment.rule_config,
            "organisation_id": segment.organisation_id,
            "app_id": segment.app_id,
            "created_at": segment.created_at.isoformat(),
            "modified_at": segment.modified_at.isoformat(),
            "experience_segments": experience_segments_data,
            "experience_count": len(experience_segments_data),
            "active_experiences": active_experiences,
        }
