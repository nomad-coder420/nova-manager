from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
from datetime import datetime

from nova_manager.components.experiences.models import Experiences
from nova_manager.core.base_crud import BaseCRUD
from nova_manager.components.campaigns.models import Campaigns


class CampaignsCRUD(BaseCRUD):
    """CRUD operations for Campaigns"""

    def __init__(self, db: Session):
        super().__init__(Campaigns, db)

    def get_by_name(
        self, name: str, organisation_id: str, app_id: str
    ) -> Optional[Campaigns]:
        """Get campaign by name within organization/app"""
        return (
            self.db.query(Campaigns)
            .filter(
                and_(
                    Campaigns.name == name,
                    Campaigns.organisation_id == organisation_id,
                    Campaigns.app_id == app_id,
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
    ) -> List[Campaigns]:
        """Get campaigns for organization/app with pagination and optional status filter"""
        query = self.db.query(Campaigns).filter(
            and_(
                Campaigns.organisation_id == organisation_id,
                Campaigns.app_id == app_id,
            )
        )

        if status:
            query = query.filter(Campaigns.status == status)

        return query.offset(skip).limit(limit).all()

    def create_campaign(
        self,
        name: str,
        description: str,
        status: str,
        rule_config: Dict[str, Any],
        launched_at: datetime,
        organisation_id: str,
        app_id: str,
    ) -> Campaigns:
        """Create a new campaign"""
        campaign = Campaigns(
            name=name,
            description=description,
            status=status,
            rule_config=rule_config,
            launched_at=launched_at,
            organisation_id=organisation_id,
            app_id=app_id,
        )
        self.db.add(campaign)
        self.db.flush()
        self.db.refresh(campaign)
        return campaign

    def update_rule_config(
        self, pid: UUIDType, rule_config: Dict[str, Any]
    ) -> Optional[Campaigns]:
        """Update campaign rule configuration"""
        campaign = self.get_by_pid(pid)
        if campaign:
            campaign.rule_config = rule_config
            self.db.flush()
            self.db.refresh(campaign)
        return campaign

    def update_status(self, pid: UUIDType, status: str) -> Optional[Campaigns]:
        """Update campaign status"""
        campaign = self.get_by_pid(pid)
        if campaign:
            campaign.status = status
            self.db.flush()
            self.db.refresh(campaign)
        return campaign

    def search_campaigns(
        self,
        organisation_id: str,
        app_id: str,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Campaigns]:
        """Search campaigns by name or description"""
        search_pattern = f"%{search_term}%"
        return (
            self.db.query(Campaigns)
            .filter(
                and_(
                    Campaigns.organisation_id == organisation_id,
                    Campaigns.app_id == app_id,
                    or_(
                        Campaigns.name.ilike(search_pattern),
                        Campaigns.description.ilike(search_pattern),
                    ),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_campaigns_with_experiences(
        self, organisation_id: str, app_id: str
    ) -> List[Campaigns]:
        """Get campaigns that have experiences"""
        return (
            self.db.query(Campaigns)
            # .join(ExperienceCampaigns, Campaigns.pid == ExperienceCampaigns.campaign_id)
            .filter(
                and_(
                    Campaigns.organisation_id == organisation_id,
                    Campaigns.app_id == app_id,
                )
            )
            .distinct()
            .all()
        )

    def get_campaign_usage_stats(self, pid: UUIDType) -> Dict[str, Any]:
        """Get usage statistics for a campaign"""
        campaign = self.get_by_pid(pid)
        if not campaign:
            return {}

        # Count experiences using this campaign through junction table
        # experience_count = (
        #     self.db.query(ExperienceCampaigns)
        #     .filter(ExperienceCampaigns.campaign_id == pid)
        #     .count()
        # )

        # # Get active experiences using this campaign through junction table
        # active_experiences = (
        #     self.db.query(ExperienceCampaigns)
        #     .join(Experiences, ExperienceCampaigns.experience_id == Experiences.pid)
        #     .filter(
        #         and_(
        #             ExperienceCampaigns.campaign_id == pid,
        #             Experiences.status == "active"
        #         )
        #     )
        #     .count()
        # )

        return {
            "campaign_name": campaign.name,
            # "experience_count": experience_count,
            # "active_experiences": active_experiences,
            "rule_config": campaign.rule_config,
            "status": campaign.status,
            "launched_at": campaign.launched_at.isoformat(),
        }

    def clone_campaign(
        self,
        source_pid: UUIDType,
        new_name: str,
        new_description: Optional[str] = None,
    ) -> Optional[Campaigns]:
        """Clone an existing campaign with a new name"""
        source = self.get_by_pid(source_pid)
        if not source:
            return None

        cloned_campaign = Campaigns(
            name=new_name,
            description=new_description or f"Copy of {source.description}",
            status="draft",  # New campaigns start as draft
            rule_config=source.rule_config.copy(),
            launched_at=datetime.utcnow(),  # New launch time
            organisation_id=source.organisation_id,
            app_id=source.app_id,
        )
        self.db.add(cloned_campaign)
        self.db.flush()
        self.db.refresh(cloned_campaign)
        return cloned_campaign

    def get_with_experiences(self, pid: UUIDType) -> Optional[Campaigns]:
        """Get campaign with experiences loaded"""
        return (
            self.db.query(Campaigns)
            .options(selectinload(Campaigns.experience_campaigns))
            .filter(Campaigns.pid == pid)
            .first()
        )

    def get_campaign_with_details(self, pid: UUIDType) -> Optional[Dict[str, Any]]:
        """Get campaign with full details including experience relationships"""
        campaign = self.get_with_experiences(pid)

        if not campaign:
            return None

        # Transform experiences for response
        experiences_data = []
        active_experiences = 0

        for exp_campaign in campaign.experience_campaigns:
            experience = exp_campaign.experience
            experience_data = {
                "pid": experience.pid,
                "name": experience.name,
                "description": experience.description,
                "status": experience.status,
                "priority": experience.priority,
                "created_at": experience.created_at.isoformat(),
                "last_updated_at": experience.last_updated_at.isoformat(),
                "target_percentage": exp_campaign.target_percentage,
            }
            experiences_data.append(experience_data)

            # Count active experiences
            if experience.status == "active":
                active_experiences += 1

        return {
            "pid": campaign.pid,
            "name": campaign.name,
            "description": campaign.description,
            "status": campaign.status,
            "rule_config": campaign.rule_config,
            "launched_at": campaign.launched_at.isoformat(),
            "organisation_id": campaign.organisation_id,
            "app_id": campaign.app_id,
            "created_at": campaign.created_at.isoformat(),
            "modified_at": campaign.modified_at.isoformat(),
            "experiences": experiences_data,
            "experience_count": len(experiences_data),
            "active_experiences": active_experiences,
        }

    def get_campaigns_by_status(
        self,
        organisation_id: str,
        app_id: str,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Campaigns]:
        """Get campaigns by status"""
        return (
            self.db.query(Campaigns)
            .filter(
                and_(
                    Campaigns.organisation_id == organisation_id,
                    Campaigns.app_id == app_id,
                    Campaigns.status == status,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_campaigns_launched_after(
        self,
        organisation_id: str,
        app_id: str,
        launched_after: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Campaigns]:
        """Get campaigns launched after a specific date"""
        return (
            self.db.query(Campaigns)
            .filter(
                and_(
                    Campaigns.organisation_id == organisation_id,
                    Campaigns.app_id == app_id,
                    Campaigns.launched_at >= launched_after,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
