from uuid import UUID
from nova_manager.components.metrics.models import Metrics
from nova_manager.core.base_crud import BaseCRUD
from sqlalchemy.orm import Session


class MetricsCRUD(BaseCRUD):
    def __init__(self, db: Session):
        super().__init__(Metrics, db)

    def get_metric(self, metric_id: UUID) -> Metrics | None:
        return self.db.query(Metrics).filter(self.model.pid == metric_id).first()
