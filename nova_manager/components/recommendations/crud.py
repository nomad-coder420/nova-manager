from uuid import UUID
from nova_manager.components.recommendations.models import Recommendations
from nova_manager.core.base_crud import BaseCRUD
from sqlalchemy import and_
from sqlalchemy.orm import Session


class RecommendationsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(Recommendations, db)

    def get_multi_by_org(
        self,
        organisation_id: str,
        app_id: str,
        skip: int = 0,
        limit: int = 100,
        experience_id: UUID | None = None,
    ):
        query = self.db.query(Recommendations).filter(
            and_(
                Recommendations.organisation_id == organisation_id,
                Recommendations.app_id == app_id,
            )
        )

        if experience_id:
            query = query.filter(Recommendations.experience_id == experience_id)

        return query.offset(skip).limit(limit).all()
